INDICATOR_META = {
    "accidents": {"label": "Число ДТП", "unit": "шт."},
    "killed": {"label": "Погибшие", "unit": "чел."},
    "injured": {"label": "Раненые", "unit": "чел."},
    "severity": {"label": "Коэффициент тяжести последствий", "unit": ""},
    "social_risk": {"label": "Социальный риск", "unit": "на 100 тыс."},
    "network_freq": {"label": "Частота на км сети", "unit": "ДТП/км"},
    "transport_risk": {"label": "Транспортный риск", "unit": "погибших на 10 тыс. ТС"},
}

CHART_TYPE = {
    "accidents": "c-chart",
    "killed": "c-chart",
    "injured": "c-chart",
    "severity": "i-chart",
    "social_risk": "i-chart",
    "network_freq": "i-chart",
    "transport_risk": "i-chart",
}


def compute_indicator(
    code: str,
    n_accidents: int,
    n_killed: int,
    n_injured: int,
    *,
    population: int,
    network_length_km: float,
    vehicles_count: int,
) -> float:
    """
    Compute a single indicator by code.

    Args:
        code: Indicator code.
        n_accidents: Number of accidents.
        n_killed: Number of killed.
        n_injured: Number of injured.
        population: Region population.
        network_length_km: Road network length in km.
        vehicles_count: Number of vehicles.

    Returns:
        Indicator value as float (no rounding).

    Raises:
        ValueError: If code is unknown.
    """
    if code == "accidents":
        # Формула: N_дтп
        return float(n_accidents)

    elif code == "killed":
        # Формула: N_пог
        return float(n_killed)

    elif code == "injured":
        # Формула: N_ран
        return float(n_injured)

    elif code == "severity":
        # Формула 2.3 ВКР: K_T = N_пог / (N_пог + N_ран) × 100
        denominator = n_killed + n_injured
        if denominator == 0:
            return 0.0
        return (n_killed / denominator) * 100.0

    elif code == "social_risk":
        # Формула 2.4 ВКР: R_S = N_пог / P_нас × 10^5
        return (n_killed / population) * 100_000

    elif code == "network_freq":
        # Формула 2.1 ВКР: K_L = N_дтп / L_сети
        return n_accidents / network_length_km

    elif code == "transport_risk":
        # Формула: R_T = N_пог / N_тс × 10^4
        return (n_killed / vehicles_count) * 10_000

    else:
        raise ValueError(f"Unknown indicator code: {code}")
