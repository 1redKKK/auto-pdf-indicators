import json
import os
from datetime import datetime
from typing import Optional

from app.config.moscow import MOSCOW_PROFILE
from app.config.settings import settings
from app.core.indicators import INDICATOR_META, compute_indicator
from app.core.nelson import detect_first_match
from app.models.alerts import AlertAcknowledgeResponse, AlertItem
from app.services.indicator_service import indicator_service


KPI_INDICATORS_FOR_ALERTS = ["accidents", "severity", "social_risk", "network_freq"]

LEVEL_PRIORITY = {"critical": 0, "warning": 1, "info": 2}
LEVEL_LABELS = {
    "critical": "Критическое",
    "warning": "Предупреждение",
    "info": "Информация",
}

RULE_LABELS = {
    "ucl_exceeded": "Выход за UCL",
    "warning_zone": "Зона предупреждения",
    "lcl_exceeded": "Выход за LCL",
    "nelson_rule_2": "Правило Нельсона 2 (серия 9)",
    "nelson_rule_3": "Правило Нельсона 3 (тренд 6)",
    "nelson_rule_4": "Правило Нельсона 4 (чередование 14)",
}

# Type mapping per ВКР 2.2.3:
# - n_dtp (accidents), k_l (network_freq), R_S (social_risk) → A
# - k_t (severity) → C
# - any nelson rule firing → B (overrides indicator-based mapping)
INDICATOR_TYPE = {
    "accidents": "A",
    "network_freq": "A",
    "social_risk": "A",
    "severity": "C",
}


def _resolve_type(indicator_code: str, rule: str) -> str:
    if rule.startswith("nelson_"):
        return "B"
    return INDICATOR_TYPE.get(indicator_code, "A")


def _build_description(rule: str, indicator_label: str, month_label: str, value: float, threshold: float) -> str:
    if rule == "ucl_exceeded":
        return (
            f"{indicator_label} за {month_label} ({value:.2f}) "
            f"превысило верхнюю контрольную границу ({threshold:.2f})."
        )
    if rule == "warning_zone":
        return (
            f"{indicator_label} за {month_label} ({value:.2f}) "
            f"находится в зоне предупреждения (CL+2σ = {threshold:.2f})."
        )
    if rule == "lcl_exceeded":
        return (
            f"{indicator_label} за {month_label} ({value:.2f}) "
            f"опустилось ниже нижней контрольной границы ({threshold:.2f})."
        )
    if rule == "nelson_rule_2":
        return f"Зафиксирована серия из 9 точек {indicator_label} по одну сторону от центральной линии."
    if rule == "nelson_rule_3":
        return f"Зафиксирован монотонный тренд {indicator_label} на протяжении 6 точек подряд."
    if rule == "nelson_rule_4":
        return f"Зафиксированы 14 чередующихся точек {indicator_label} вверх-вниз."
    return f"{indicator_label}: {rule}"


class AlertService:
    """In-memory alerts with persisted acknowledge state."""

    _instance: Optional["AlertService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._alerts: list[AlertItem] = []
            cls._instance._ack_state: dict[str, str] = {}
            cls._instance._loaded_state = False
        return cls._instance

    def _load_state(self) -> None:
        if self._loaded_state:
            return

        if os.path.exists(settings.ALERTS_STATE_PATH):
            try:
                with open(settings.ALERTS_STATE_PATH, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    self._ack_state = payload
            except (json.JSONDecodeError, OSError):
                self._ack_state = {}

        self._loaded_state = True

    def _save_state(self) -> None:
        os.makedirs(os.path.dirname(settings.ALERTS_STATE_PATH), exist_ok=True)
        with open(settings.ALERTS_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self._ack_state, f, ensure_ascii=False, indent=2)

    def recompute(self) -> None:
        """Build alerts per ВКР algorithm (раздел 2.2.3) for 4 KPI indicators.

        For each indicator and each month in the report period:
            Step 4 — compare value vs control limits:
                x > UCL          → CRITICAL ucl_exceeded
                CL+2σ < x ≤ UCL  → WARNING  warning_zone
                x < LCL          → INFO     lcl_exceeded
            Step 5 — if no Step 4 alert: check Nelson rules 2/3/4 on full series.
        """
        self._load_state()
        if not indicator_service.is_ready:
            raise RuntimeError("Indicators not ready yet")

        monthly_agg = indicator_service._monthly_agg
        periods = indicator_service._periods
        trends_cache = indicator_service._trends_cache
        limits_by_year = indicator_service._limits_by_year or {}
        if monthly_agg is None or periods is None or trends_cache is None:
            raise RuntimeError("Indicator caches missing")

        alerts: list[AlertItem] = []
        counter = 1

        for indicator_code in KPI_INDICATORS_FOR_ALERTS:
            trend = trends_cache.get(indicator_code)
            if trend is None:
                continue

            indicator_label = INDICATOR_META.get(indicator_code, {}).get("label", indicator_code)

            # Build full series (baseline + report) so Nelson rules can look back across the boundary.
            full_values: list[float] = []
            full_dates: list = []
            for _, row in monthly_agg.iterrows():
                value = compute_indicator(
                    indicator_code,
                    int(row["n_accidents"]),
                    int(row["n_killed"]),
                    int(row["n_injured"]),
                    population=MOSCOW_PROFILE["population"],
                    network_length_km=MOSCOW_PROFILE["network_length_km"],
                    vehicles_count=MOSCOW_PROFILE["vehicles_count"],
                )
                full_values.append(value)
                full_dates.append(row["year_month"])

            # Проверяем весь видимый диапазон (baseline + report = 24 месяца),
            # чтобы пользователь мог фильтровать алерты по любому видимому году/кварталу.
            # Скрытый pool (12 месяцев перед baseline) не проверяем — он только источник
            # данных для Nelson-look-back через full_values, но сами алерты в нём не
            # создаём (методологически: hidden pool — служебные данные для baseline).
            visible_indices = [
                i for i, ts in enumerate(full_dates)
                if periods["baseline_start"] <= ts < periods["report_end"]
            ]

            for i in visible_indices:
                x = full_values[i]
                ts = full_dates[i]

                # Лимиты по году точки — Y использует baseline из Y-1.
                year_limits = limits_by_year.get(int(ts.year), {}).get(indicator_code)
                if year_limits is None:
                    # Нет baseline для этого года (например, 2023 без 2022) — пропускаем.
                    continue
                cl = float(year_limits["cl"])
                ucl = float(year_limits["ucl"])
                lcl = float(year_limits["lcl"])
                sigma = (ucl - cl) / 3.0 if ucl > cl else 0.0
                warning_threshold = cl + 2.0 * sigma

                rule: Optional[str] = None
                level: Optional[str] = None
                threshold: float = 0.0

                if x > ucl:
                    rule, level, threshold = "ucl_exceeded", "critical", ucl
                elif sigma > 0 and warning_threshold < x <= ucl:
                    rule, level, threshold = "warning_zone", "warning", warning_threshold
                elif x < lcl:
                    rule, level, threshold = "lcl_exceeded", "info", lcl
                else:
                    matched = detect_first_match(full_values, cl, i)
                    if matched is not None:
                        rule, level, threshold = matched, "warning", cl

                if rule is None:
                    continue

                month_label = _ru_month_label(ts)
                alert_id = f"alrt_{counter:03d}"
                counter += 1
                key = f"{indicator_code}|{ts.strftime('%Y-%m-%d')}|{rule}"
                status = "acknowledged" if key in self._ack_state else "new"
                type_ = _resolve_type(indicator_code, rule)

                alerts.append(
                    AlertItem(
                        id=alert_id,
                        # Z suffix → JS Date treats this as UTC, не local-time;
                        # без него фильтр по году/кварталу «течёт» на ±1 период
                        # из-за смещения локальной таймзоны.
                        datetime=f"{ts.strftime('%Y-%m-%d')}T00:00:00Z",
                        region="moscow",
                        indicator=indicator_code,
                        indicator_label=indicator_label,
                        rule=rule,
                        rule_label=RULE_LABELS[rule],
                        level=level,
                        level_label=LEVEL_LABELS[level],
                        type=type_,
                        value=round(x, 2),
                        threshold=round(threshold, 2),
                        status=status,
                        description=_build_description(rule, indicator_label, month_label, x, threshold),
                    )
                )

        # Sort by date desc — newest alerts first regardless of severity.
        # Уровень всё равно отображается бейджем в таблице, отдельная группировка не нужна.
        alerts.sort(key=lambda a: a.datetime, reverse=True)
        self._alerts = alerts

    def get_alerts(
        self,
        *,
        status: str = "all",
        level: str = "all",
        limit: int = 50,
    ) -> list[AlertItem]:
        """Return filtered alerts."""
        items = self._alerts
        if status != "all":
            items = [a for a in items if a.status == status]
        if level != "all":
            items = [a for a in items if a.level == level]
        return items[:limit]

    def acknowledge(self, alert_id: str) -> AlertAcknowledgeResponse:
        """Mark alert as acknowledged and persist state."""
        target: Optional[AlertItem] = None
        for alert in self._alerts:
            if alert.id == alert_id:
                target = alert
                break
        if target is None:
            raise KeyError(alert_id)

        ack_time = datetime.now().isoformat(timespec="seconds")
        key = f"{target.indicator}|{target.datetime[:10]}|{target.rule}"
        self._ack_state[key] = ack_time
        self._save_state()
        target.status = "acknowledged"
        return AlertAcknowledgeResponse(id=alert_id, status="acknowledged", acknowledged_at=ack_time)

    def unacknowledge(self, alert_id: str) -> AlertAcknowledgeResponse:
        """Revert alert from acknowledged back to new."""
        target: Optional[AlertItem] = None
        for alert in self._alerts:
            if alert.id == alert_id:
                target = alert
                break
        if target is None:
            raise KeyError(alert_id)

        key = f"{target.indicator}|{target.datetime[:10]}|{target.rule}"
        self._ack_state.pop(key, None)
        self._save_state()
        target.status = "new"
        return AlertAcknowledgeResponse(id=alert_id, status="new", acknowledged_at="")

    @property
    def is_ready(self) -> bool:
        return len(self._alerts) >= 0


_RU_MONTHS_SHORT = [
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
]


def _ru_month_label(ts) -> str:
    return f"{_RU_MONTHS_SHORT[ts.month - 1]} {ts.year}"


alert_service = AlertService()
