"""PDF report generation: Jinja2 template + WeasyPrint render.

Tests monkey-patch `_render_pdf` so they don't need GTK.
"""

import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dateutil.relativedelta import relativedelta
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.config.settings import settings
from app.core.logging import get_logger
from app.core.period_window import resolve_window
from app.models.alerts import AlertItem
from app.models.hotspots import HotspotItem
from app.models.indicators import IndicatorCard
from app.models.reports import ReportItem, ReportPeriodicity
from app.services.alert_service import alert_service
from app.services.hotspot_service import hotspot_service
from app.services.indicator_service import indicator_service

logger = get_logger(__name__)

# English month abbreviations for filenames (e.g., "Dec_2025").
EN_MONTHS_SHORT = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]

RU_MONTHS_LONG = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

REGION_LABELS = {"moscow": "Москва"}

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "templates")


def _render_pdf(html: str, base_url: str) -> bytes:
    """Wrap WeasyPrint so tests can monkey-patch it."""
    return HTML(string=html, base_url=base_url).write_pdf()


_OSM_USER_AGENT = "IGIS-BDD-M10/1.0 (thesis project; contact: github)"


def _render_hotspot_snippet(lat: float, lon: float) -> Optional[str]:
    """Render a small OSM-tile static map around the hotspot and return a PNG data URI.

    Lazy-imports staticmap so the rest of the service doesn't fail if network/lib
    is unavailable. On any error the function returns None and the PDF will fall
    back to plain text coordinates.
    """
    try:
        from staticmap import CircleMarker, StaticMap

        m = StaticMap(
            500, 300,
            url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
            headers={"User-Agent": _OSM_USER_AGENT},
        )
        m.add_marker(CircleMarker((lon, lat), "#ef4444", 18))
        m.add_marker(CircleMarker((lon, lat), "#ffffff", 8))
        img = m.render(zoom=15)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning(f"Hotspot snippet failed for ({lat},{lon}): {e}")
        return None


def _build_filename(period: str, periodicity: ReportPeriodicity) -> str:
    year, month = period.split("-")
    month_short = EN_MONTHS_SHORT[int(month) - 1]
    prefix = {"month": "M", "quarter": "Q", "year": "Y"}[periodicity]
    return f"BDD_Moscow_{prefix}_{month_short}_{year}.pdf"


def _build_period_label(period: str, periodicity: ReportPeriodicity) -> str:
    year, month = period.split("-")
    long_month = RU_MONTHS_LONG[int(month) - 1]
    if periodicity == "month":
        return f"{long_month} {year}"
    if periodicity == "quarter":
        # Window covers months [m-2 .. m] inclusive
        m = int(month)
        start = m - 2
        if start <= 0:
            start += 12
            start_year = int(year) - 1
        else:
            start_year = int(year)
        start_label = f"{RU_MONTHS_LONG[start - 1]} {start_year}"
        end_label = f"{long_month} {year}"
        return f"{start_label} — {end_label}"
    # year
    m = int(month)
    start = m - 11
    start_year = int(year) - 1 if start <= 0 else int(year)
    if start <= 0:
        start += 12
    return f"{RU_MONTHS_LONG[start - 1]} {start_year} — {long_month} {year}"


def _format_value(card: IndicatorCard) -> str:
    """Match the frontend's number formatting (integers for counts, 2 decimals otherwise)."""
    if card.unit in ("шт.", "чел."):
        return str(int(round(card.value)))
    # Strip trailing zeros for nicer display.
    return f"{card.value:.2f}".rstrip("0").rstrip(".") or "0"


def _format_delta(delta_pct: Optional[float]) -> Optional[str]:
    if delta_pct is None:
        return None
    sign = "+" if delta_pct >= 0 else ""
    return f"{sign}{delta_pct:.1f}%"


def _alert_period_label(iso_date: str) -> str:
    # iso_date = "YYYY-MM-DDTHH:MM:SS" → "Месяц YYYY"
    y, m, _ = iso_date[:10].split("-")
    return f"{RU_MONTHS_LONG[int(m) - 1]} {y}"


class ReportService:
    """Generate, list and serve PDF reports. Index persisted to JSON."""

    _instance: Optional["ReportService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._reports: list[ReportItem] = []
            cls._instance._loaded = False
        return cls._instance

    def _load_index(self) -> None:
        if self._loaded:
            return
        if os.path.exists(settings.REPORTS_INDEX_PATH):
            try:
                with open(settings.REPORTS_INDEX_PATH, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, list):
                    parsed = [ReportItem(**item) for item in payload]
                    # Deduplicate by id (keeping first occurrence) — heals old indices
                    # produced by the buggy len-based id generator before stage 8.5.
                    seen: set[str] = set()
                    unique: list[ReportItem] = []
                    for r in parsed:
                        if r.id in seen:
                            logger.warning(f"Duplicate report id in index — dropped: {r.id}")
                            continue
                        seen.add(r.id)
                        unique.append(r)
                    self._reports = unique
                    if len(unique) != len(parsed):
                        # Persist the cleaned-up index immediately.
                        self._save_index()
            except (json.JSONDecodeError, OSError, ValueError) as e:
                logger.warning(f"Failed to load reports index: {e}")
                self._reports = []
        self._loaded = True

    def _next_id(self) -> str:
        """Generate the next report id as max(existing numeric suffix) + 1.

        Robust against deletions: even if reports are removed, new ids never
        collide with surviving ones.
        """
        nums: list[int] = []
        for r in self._reports:
            try:
                nums.append(int(r.id.split("_")[1]))
            except (IndexError, ValueError):
                continue
        return f"rpt_{(max(nums, default=0) + 1):03d}"

    def _compute_extra_indicators(self, window: dict) -> dict:
        """Killed/Injured totals + АППГ delta — для PDF, на дашборде их нет."""
        n = window["months"]
        baseline_start = window["start"] - relativedelta(months=12)
        baseline_end = window["end"] - relativedelta(months=12)

        report_slice = indicator_service._slice_monthly(window["start"], window["end"])
        baseline_slice = indicator_service._slice_monthly(baseline_start, baseline_end)
        baseline_complete = len(baseline_slice) >= n

        out: dict[str, dict] = {}
        for code, label in [("killed", "Погибло"), ("injured", "Ранено")]:
            rep_val = indicator_service._compute_window_indicator(code, report_slice, n)
            if baseline_complete:
                base_val = indicator_service._compute_window_indicator(code, baseline_slice, n)
                delta_abs = rep_val - base_val
                delta_pct = round((delta_abs / base_val) * 100, 1) if base_val != 0 else None
                is_improvement: bool | None = bool(delta_abs < 0)
            else:
                delta_pct = None
                is_improvement = None
            out[code] = {
                "label": label,
                "unit": "чел.",
                "value_display": str(int(round(rep_val))),
                "delta_pct": delta_pct,
                "delta_display": _format_delta(delta_pct),
                "is_improvement": is_improvement,
            }
        return out

    def _save_index(self) -> None:
        os.makedirs(os.path.dirname(settings.REPORTS_INDEX_PATH), exist_ok=True)
        with open(settings.REPORTS_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(
                [r.model_dump() for r in self._reports],
                f, ensure_ascii=False, indent=2,
            )

    def list_reports(self) -> list[ReportItem]:
        self._load_index()
        # Sort by generated_at desc.
        return sorted(self._reports, key=lambda r: r.generated_at, reverse=True)

    def get_path(self, report_id: str) -> str:
        self._load_index()
        for r in self._reports:
            if r.id == report_id:
                return os.path.join(settings.REPORTS_DIR, f"{r.id}.pdf")
        raise KeyError(report_id)

    def delete(self, report_id: str) -> None:
        """Remove report from disk and from the index."""
        self._load_index()
        for i, r in enumerate(self._reports):
            if r.id == report_id:
                pdf_path = os.path.join(settings.REPORTS_DIR, f"{r.id}.pdf")
                if os.path.exists(pdf_path):
                    try:
                        os.remove(pdf_path)
                    except OSError as e:
                        logger.warning(f"Failed to remove {pdf_path}: {e}")
                self._reports.pop(i)
                self._save_index()
                logger.info(f"Deleted report {report_id}")
                return
        raise KeyError(report_id)

    def generate(
        self,
        *,
        region: str,
        period: str,
        periodicity: ReportPeriodicity,
    ) -> ReportItem:
        if region != "moscow":
            raise ValueError(f"Region not supported: {region}")
        if not indicator_service.is_ready:
            raise RuntimeError("Indicators not ready yet")

        self._load_index()

        # 1. Pull data for the requested window.
        kpi_resp = indicator_service.get_indicators_for_window(period=period, periodicity=periodicity)
        hotspots_resp = hotspot_service.get_top(limit=5, period=period, periodicity=periodicity)

        # Filter alerts to the same window.
        window = resolve_window(
            period, periodicity,
            fallback_start=indicator_service._periods["report_start"],
            fallback_end=indicator_service._periods["report_end"],
        )

        # Extra KPIs only for the PDF: абсолютное число погибших/раненых.
        # На дашборде их нет, но в отчёте они нужны.
        extra_indicators = self._compute_extra_indicators(window)
        all_alerts = alert_service.get_alerts(limit=500)
        # a.datetime = 'YYYY-MM-DDTHH:MM:SSZ'; window — pandas tz-naive Timestamps,
        # поэтому отрезаем Z и сравниваем как naive (UTC midnight).
        scoped_alerts = [
            a for a in all_alerts
            if window["start"] <= datetime.fromisoformat(a.datetime[:19]) < window["end"]
        ]

        period_label = _build_period_label(period, periodicity)

        # Indicators в порядке: ДТП, Погибло, Ранено, K_T, R_S, K_L
        cards_by_code = {c.code: c for c in kpi_resp.cards}
        kpi_entry = lambda c: {
            "label": c.label,
            "unit": c.unit,
            "value_display": _format_value(c),
            "delta_pct": c.delta_pct,
            "delta_display": _format_delta(c.delta_pct),
            "is_improvement": c.is_improvement,
        }
        indicators_for_pdf = [
            kpi_entry(cards_by_code["accidents"]),
            extra_indicators["killed"],
            extra_indicators["injured"],
            kpi_entry(cards_by_code["severity"]),
            kpi_entry(cards_by_code["social_risk"]),
            kpi_entry(cards_by_code["network_freq"]),
        ]

        # Mini-карты для топ-5 очагов (опционально — fallback на текст если OSM недоступен).
        # Прокидываем все поля, которые показываются в popup на карте дашборда,
        # чтобы PDF и UI давали идентичную сводку по очагу.
        hotspot_maps = []
        for h in hotspots_resp.hotspots:
            hotspot_maps.append({
                "rank": h.rank,
                "name": h.name,
                "lat": h.lat,
                "lon": h.lon,
                "accidents_count": h.accidents_count,
                "killed": h.killed,
                "injured": h.injured,
                "severity_coef": h.severity_coef,
                "frequency": h.frequency,
                "frequency_per_km": h.frequency_per_km,
                "dominant_type": h.dominant_type,
                "status": h.status,
                "period_label": hotspots_resp.period_label,
                "image": _render_hotspot_snippet(h.lat, h.lon),
            })

        # 2. Build template context.
        ctx = {
            "title": f"Аналитический отчёт за {period_label}",
            "region_name": REGION_LABELS.get(region, region),
            "period_label": period_label,
            "generated_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "indicators": indicators_for_pdf,
            "hotspots": [h.model_dump() for h in hotspots_resp.hotspots],
            "hotspot_maps": hotspot_maps,
            "alerts": [
                {**a.model_dump(), "period_label": _alert_period_label(a.datetime)}
                for a in scoped_alerts
            ],
        }

        # 3. Render HTML.
        env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
        tpl = env.get_template("monthly.html")
        html = tpl.render(**ctx)

        # 4. Render PDF.
        pdf_bytes = _render_pdf(html, base_url=TEMPLATE_DIR)

        # 5. Persist.
        report_id = self._next_id()
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        pdf_path = os.path.join(settings.REPORTS_DIR, f"{report_id}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        item = ReportItem(
            id=report_id,
            title=ctx["title"],
            region=region,
            region_label=REGION_LABELS.get(region, region),
            period=period,
            periodicity=periodicity,
            period_label=period_label,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            file_name=_build_filename(period, periodicity),
            size_bytes=len(pdf_bytes),
        )
        self._reports.append(item)
        self._save_index()
        logger.info(f"Generated report {report_id} ({item.file_name}, {item.size_bytes} bytes)")
        return item


report_service = ReportService()
