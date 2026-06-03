from datetime import datetime
from typing import Optional

import pandas as pd
from dateutil.relativedelta import relativedelta

from app.config.moscow import MOSCOW_PROFILE
from app.config.settings import settings
from app.core.indicators import CHART_TYPE, INDICATOR_META, compute_indicator
from app.core.period_window import resolve_window
from app.core.periods import compute_periods
from app.core.shewhart import c_chart_limits, u_chart_limits, i_chart_limits
from app.models.indicators import IndicatorCard, IndicatorsResponse, PeriodInfo
from app.models.trend import TrendPoint, TrendResponse
from app.services.data_service import data_service
from app.core.logging import get_logger

logger = get_logger(__name__)

RU_MONTHS_SHORT = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
]

KPI_INDICATORS = ["accidents", "severity", "social_risk", "network_freq"]


class IndicatorService:
    """Singleton service for computing and caching indicators."""

    _instance: Optional["IndicatorService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._monthly_agg: Optional[pd.DataFrame] = None
            cls._instance._periods: Optional[dict] = None
            cls._instance._cards_cache: Optional[list[IndicatorCard]] = None
            cls._instance._trends_cache: Optional[dict[str, TrendResponse]] = None
            # Лимиты Шухарта на КАЖДЫЙ видимый год: для года Y baseline = год Y-1.
            # Раньше использовался один общий baseline (Jan-Dec 2024) и его лимиты
            # сравнивались с самим же baseline → точки 2024 проверялись против
            # лимитов, посчитанных из них самих. Теперь:
            #   2024 → лимиты из 2023 (hidden pool)
            #   2025 → лимиты из 2024 (visible baseline)
            cls._instance._limits_by_year: Optional[dict[int, dict[str, dict]]] = None
            cls._instance._last_calculated_at: Optional[datetime] = None
        return cls._instance

    def _compute_limits(self, baseline_df: pd.DataFrame, indicator_code: str) -> dict:
        """Лимиты контрольной карты для одного индикатора по baseline-окну."""
        chart_type = CHART_TYPE[indicator_code]

        if indicator_code in ("accidents", "killed", "injured"):
            baseline_values = baseline_df[f"n_{indicator_code}"].tolist()
        else:
            baseline_values = [
                compute_indicator(
                    indicator_code,
                    int(row["n_accidents"]),
                    int(row["n_killed"]),
                    int(row["n_injured"]),
                    population=MOSCOW_PROFILE["population"],
                    network_length_km=MOSCOW_PROFILE["network_length_km"],
                    vehicles_count=MOSCOW_PROFILE["vehicles_count"],
                )
                for _, row in baseline_df.iterrows()
            ]

        if chart_type == "c-chart":
            return c_chart_limits(baseline_values)
        if chart_type == "i-chart":
            return i_chart_limits(baseline_values)
        # u-chart (legacy)
        if indicator_code == "severity":
            n_const = baseline_df[["n_killed", "n_injured"]].sum(axis=1).mean()
        elif indicator_code == "social_risk":
            n_const = MOSCOW_PROFILE["population"]
        elif indicator_code == "network_freq":
            n_const = MOSCOW_PROFILE["network_length_km"]
        else:
            n_const = 1.0
        return u_chart_limits(baseline_values, n_const=n_const)

    def recompute(self) -> None:
        """Compute indicators from data_service and cache results."""
        df = data_service.get_df()
        if df is None or df.empty:
            raise RuntimeError("No data loaded")

        # Create year_month column as Timestamp (1st day of month)
        df = df.copy()
        df["year_month"] = pd.to_datetime(df["datetime"]).dt.to_period("M")

        # Monthly aggregates
        monthly = df.groupby("year_month").agg(
            n_accidents=("crash_id", "count"),
            n_killed=("dead_count", "sum"),
            n_injured=("injured_count", "sum"),
        ).reset_index()

        # Convert year_month to Timestamp
        monthly["year_month"] = monthly["year_month"].dt.to_timestamp()
        monthly = monthly.sort_values("year_month").reset_index(drop=True)

        # Reindex to fill missing months with 0
        full_range = pd.date_range(
            start=monthly["year_month"].min(),
            end=monthly["year_month"].max(),
            freq="MS"
        )
        monthly = monthly.set_index("year_month").reindex(full_range, fill_value=0).reset_index()
        monthly.rename(columns={"year_month": "year_month"}, inplace=False)
        monthly.columns = ["year_month", "n_accidents", "n_killed", "n_injured"]

        self._monthly_agg = monthly

        # Compute periods. Hidden baseline months are loaded but excluded from the visible
        # baseline/report range — they only feed the trailing-12mo baseline in get_indicators_for_window.
        self._periods = compute_periods(
            df["datetime"].min(),
            df["datetime"].max(),
            hidden_baseline_months=settings.HIDDEN_BASELINE_MONTHS,
        )

        # Split into baseline and report
        baseline = monthly[
            (monthly["year_month"] >= self._periods["baseline_start"]) &
            (monthly["year_month"] < self._periods["baseline_end"])
        ].copy()

        report = monthly[
            (monthly["year_month"] >= self._periods["report_start"]) &
            (monthly["year_month"] < self._periods["report_end"])
        ].copy()

        # Compute KPI cards (4 indicators) — value = period total, baseline = total of the same-length period before
        self._cards_cache = []
        for code in KPI_INDICATORS:
            report_value = self._compute_window_indicator(code, report, len(report))
            baseline_value = self._compute_window_indicator(code, baseline, len(baseline))

            delta_abs = report_value - baseline_value
            delta_pct = None
            if baseline_value != 0:
                delta_pct = round((delta_abs / baseline_value) * 100, 1)

            is_improvement = bool(delta_abs < 0)

            card = IndicatorCard(
                code=code,
                label=INDICATOR_META[code]["label"],
                unit=INDICATOR_META[code]["unit"],
                value=round(report_value, 2),
                delta_abs=round(delta_abs, 2) if delta_abs != 0 else None,
                delta_pct=delta_pct,
                is_improvement=is_improvement,
            )
            self._cards_cache.append(card)

        # Лимиты на КАЖДЫЙ видимый год — для года Y baseline = весь год Y-1.
        # 2024 → baseline 2023 (hidden pool), 2025 → baseline 2024.
        visible_years = sorted({
            int(ts.year) for ts in monthly["year_month"]
            if self._periods["baseline_start"] <= ts < self._periods["report_end"]
        })
        self._limits_by_year = {}
        for y in visible_years:
            prior_start = pd.Timestamp(year=y - 1, month=1, day=1)
            prior_end = pd.Timestamp(year=y, month=1, day=1)
            prior = monthly[
                (monthly["year_month"] >= prior_start)
                & (monthly["year_month"] < prior_end)
            ]
            if len(prior) < 12:
                continue
            self._limits_by_year[y] = {
                code: self._compute_limits(prior, code) for code in CHART_TYPE.keys()
            }

        # Дефолтный «горячий» кеш трендов = последний полный год отчётного периода.
        # Точки берутся из report_period (текущая логика), лимиты — из _limits_by_year
        # для соответствующего года (для дефолтного report = 2025 это лимиты 2025 = 2024-baseline).
        report_year = int(self._periods["report_start"].year)

        # Compute trends (6 indicators from CHART_TYPE)
        self._trends_cache = {}
        for indicator_code in CHART_TYPE.keys():
            chart_type = CHART_TYPE[indicator_code]
            limits = (
                self._limits_by_year.get(report_year, {}).get(indicator_code)
                or self._compute_limits(baseline, indicator_code)
            )

            # Compute report period points
            points = []
            for _, row in report.iterrows():
                if indicator_code in ["accidents", "killed", "injured"]:
                    value = row[f"n_{indicator_code}"]
                else:
                    value = compute_indicator(
                        indicator_code,
                        row["n_accidents"],
                        row["n_killed"],
                        row["n_injured"],
                        population=MOSCOW_PROFILE["population"],
                        network_length_km=MOSCOW_PROFILE["network_length_km"],
                        vehicles_count=MOSCOW_PROFILE["vehicles_count"],
                    )

                out_of_control = value > limits["ucl"] or value < limits["lcl"]

                alert_level = None
                if out_of_control:
                    alert_level = "critical" if value > limits["ucl"] else "info"

                ts = row["year_month"]
                month_label = f"{RU_MONTHS_SHORT[ts.month - 1]} {ts.year}"

                point = TrendPoint(
                    date=ts.strftime("%Y-%m-%d"),
                    month_label=month_label,
                    value=round(value, 2),
                    out_of_control=out_of_control,
                    alert_level=alert_level,
                )
                points.append(point)

            trend_response = TrendResponse(
                indicator=indicator_code,
                label=INDICATOR_META[indicator_code]["label"],
                unit=INDICATOR_META[indicator_code]["unit"],
                chart_type=chart_type,
                cl=round(limits["cl"], 2),
                ucl=round(limits["ucl"], 2),
                lcl=round(limits["lcl"], 2),
                points=points,
                baseline_months=len(baseline),
                report_months=len(report),
            )
            self._trends_cache[indicator_code] = trend_response

        self._last_calculated_at = datetime.now()
        logger.info(f"Indicator service recomputed: {len(self._monthly_agg)} months, {len(self._cards_cache)} cards, {len(self._trends_cache)} trends")

    def get_indicators(self) -> IndicatorsResponse:
        """Return cached KPI indicators."""
        if self._cards_cache is None:
            raise RuntimeError("Indicators not computed yet")

        period_info = PeriodInfo(
            baseline_start=self._periods["baseline_start"].strftime("%Y-%m-%d"),
            baseline_end=self._periods["baseline_end"].strftime("%Y-%m-%d"),
            report_start=self._periods["report_start"].strftime("%Y-%m-%d"),
            report_end=self._periods["report_end"].strftime("%Y-%m-%d"),
            baseline_months=self._periods["baseline_months"],
            report_months=self._periods["report_months"],
        )

        return IndicatorsResponse(
            region="Москва",
            period=period_info,
            last_calculated_at=self._last_calculated_at.isoformat(),
            cards=self._cards_cache,
        )

    def get_indicators_for_window(
        self,
        *,
        period: Optional[str],
        periodicity: str,
    ) -> IndicatorsResponse:
        """Recompute KPI cards on-the-fly for a custom (period, periodicity) window.

        Value = period total (sum over the window).
        Baseline = АППГ (Аналогичный Период Прошлого Года) — то же окно,
        сдвинутое ровно на 12 месяцев назад:
        - month: Дек 2025 vs Дек 2024
        - quarter: Q4 2025 vs Q4 2024
        - year: 2025 vs 2024 (≡ предыдущий год)
        Если данных за baseline нет — delta = None.
        """
        if self._monthly_agg is None or self._periods is None:
            raise RuntimeError("Indicators not computed yet")

        report_window = resolve_window(
            period,
            periodicity,
            fallback_start=self._periods["report_start"],
            fallback_end=self._periods["report_end"],
        )
        n = report_window["months"]
        baseline_window = {
            "start": report_window["start"] - relativedelta(months=12),
            "end": report_window["end"] - relativedelta(months=12),
            "months": n,
        }

        report_slice = self._slice_monthly(report_window["start"], report_window["end"])
        baseline_slice = self._slice_monthly(baseline_window["start"], baseline_window["end"])

        # Baseline only meaningful if the full 12-month window is covered by data.
        baseline_complete = len(baseline_slice) >= baseline_window["months"]

        cards: list[IndicatorCard] = []
        for code in KPI_INDICATORS:
            report_avg = self._compute_window_indicator(code, report_slice, report_window["months"])
            baseline_avg = self._compute_window_indicator(code, baseline_slice, baseline_window["months"])

            if not baseline_complete:
                delta_abs = None
                delta_pct = None
                is_improvement = None
            else:
                delta_abs = report_avg - baseline_avg
                delta_pct = round((delta_abs / baseline_avg) * 100, 1) if baseline_avg != 0 else None
                is_improvement = bool(delta_abs < 0)

            cards.append(IndicatorCard(
                code=code,
                label=INDICATOR_META[code]["label"],
                unit=INDICATOR_META[code]["unit"],
                value=round(report_avg, 2),
                delta_abs=round(delta_abs, 2) if delta_abs is not None else None,
                delta_pct=delta_pct,
                is_improvement=is_improvement,
            ))

        period_info = PeriodInfo(
            baseline_start=baseline_window["start"].strftime("%Y-%m-%d"),
            baseline_end=baseline_window["end"].strftime("%Y-%m-%d"),
            report_start=report_window["start"].strftime("%Y-%m-%d"),
            report_end=report_window["end"].strftime("%Y-%m-%d"),
            baseline_months=baseline_window["months"],
            report_months=report_window["months"],
        )

        return IndicatorsResponse(
            region="Москва",
            period=period_info,
            last_calculated_at=self._last_calculated_at.isoformat() if self._last_calculated_at else "",
            cards=cards,
        )

    def _slice_monthly(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        return self._monthly_agg[
            (self._monthly_agg["year_month"] >= start)
            & (self._monthly_agg["year_month"] < end)
        ]

    def _compute_window_indicator(self, code: str, slice_df: pd.DataFrame, months: int) -> float:
        """Return the indicator value for the whole window (period total).

        Inputs (n_accidents/n_killed/n_injured) are summed over the window,
        not averaged — formulas 2.1–2.4 are correct on sums:
        - K_T = N_пог / (N_пог + N_ран) is a ratio (length-invariant)
        - R_S = N_пог / P_нас × 10^5 scales linearly with the period sum
        - K_L = N_дтп / L_сети scales linearly with the period sum
        - accidents = N_дтп is the total count
        So a 12-month value is the sum/aggregate over 12 months.
        """
        if slice_df.empty or months <= 0:
            return 0.0
        n_acc = slice_df["n_accidents"].sum()
        n_killed = slice_df["n_killed"].sum()
        n_injured = slice_df["n_injured"].sum()
        return compute_indicator(
            code,
            int(n_acc),
            int(n_killed),
            int(n_injured),
            population=MOSCOW_PROFILE["population"],
            network_length_km=MOSCOW_PROFILE["network_length_km"],
            vehicles_count=MOSCOW_PROFILE["vehicles_count"],
        )

    def get_trend(self, indicator_code: str) -> TrendResponse:
        """Return cached trend for a single indicator."""
        if self._trends_cache is None:
            raise RuntimeError("Trends not computed yet")

        if indicator_code not in self._trends_cache:
            raise KeyError(f"Indicator {indicator_code} not in trends cache")

        return self._trends_cache[indicator_code]

    def get_trend_for_window(self, indicator_code: str, end_period: str) -> TrendResponse:
        """Return trend with 12 points ending at `end_period` (inclusive).

        UCL/CL/LCL берутся из `_limits_by_year` по году окна. Для года Y
        baseline — год Y-1 (для 2024 это 2023 hidden pool, для 2025 — 2024).
        Точки считаются из monthly_agg, в котором есть hidden pool, поэтому
        любой видимый end_period даёт полное 12-месячное окно.
        """
        if self._monthly_agg is None or self._trends_cache is None:
            raise RuntimeError("Indicators not computed yet")
        if indicator_code not in self._trends_cache:
            raise KeyError(f"Indicator {indicator_code} not in trends cache")

        cached = self._trends_cache[indicator_code]

        end_ts = pd.Timestamp(end_period + "-01")
        window_end = end_ts + relativedelta(months=1)
        window_start = window_end - relativedelta(months=12)

        slice_df = self._monthly_agg[
            (self._monthly_agg["year_month"] >= window_start)
            & (self._monthly_agg["year_month"] < window_end)
        ]
        if slice_df.empty:
            raise ValueError(f"No data for window ending at {end_period}")

        # Лимиты по году окна (year of end_period); fallback — лимиты из cached.
        window_year = end_ts.year
        year_limits = (self._limits_by_year or {}).get(window_year, {}).get(indicator_code)
        if year_limits is None:
            ucl, cl, lcl = cached.ucl, cached.cl, cached.lcl
        else:
            ucl = float(year_limits["ucl"])
            cl = float(year_limits["cl"])
            lcl = float(year_limits["lcl"])

        points: list[TrendPoint] = []
        for _, row in slice_df.iterrows():
            if indicator_code in ("accidents", "killed", "injured"):
                value = float(row[f"n_{indicator_code}"])
            else:
                value = compute_indicator(
                    indicator_code,
                    int(row["n_accidents"]),
                    int(row["n_killed"]),
                    int(row["n_injured"]),
                    population=MOSCOW_PROFILE["population"],
                    network_length_km=MOSCOW_PROFILE["network_length_km"],
                    vehicles_count=MOSCOW_PROFILE["vehicles_count"],
                )
            ts = row["year_month"]
            out_of_control = value > ucl or value < lcl
            alert_level = None
            if out_of_control:
                alert_level = "critical" if value > ucl else "info"
            points.append(TrendPoint(
                date=ts.strftime("%Y-%m-%d"),
                month_label=f"{RU_MONTHS_SHORT[ts.month - 1]} {ts.year}",
                value=round(value, 2),
                out_of_control=out_of_control,
                alert_level=alert_level,
            ))

        return TrendResponse(
            indicator=cached.indicator,
            label=cached.label,
            unit=cached.unit,
            chart_type=cached.chart_type,
            cl=round(cl, 2),
            ucl=round(ucl, 2),
            lcl=round(lcl, 2),
            points=points,
            baseline_months=cached.baseline_months,
            report_months=len(points),
        )

    @property
    def is_ready(self) -> bool:
        return self._cards_cache is not None


indicator_service = IndicatorService()
