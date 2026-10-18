"""Pure statistics for the air-quality index (no Home Assistant imports)."""

from __future__ import annotations

import itertools

from .const import INDEX_BANDS, INDEX_POWER, POLLUTANT_WEIGHTS
from .models import AirDay


def weighted_index(values: dict[str, float | None]) -> float | None:
    """Weighted generalised mean (power ``INDEX_POWER``) of the 0-100 indices.

    ``values`` holds the 3BMeteo reliability index (0-100, 100 = worst) of every
    selected pollutant. ``I = ( Σ w_i · v_i^p / Σ w_i )^(1/p)`` with the
    health-relevance weights ``w_i``: with ``p > 1`` the worst pollutants
    dominate more than a plain weighted average, while the result stays on the
    same 0-100 scale (and category bands) used by the single pollutants.
    """
    numerator = 0.0
    denominator = 0.0
    for key, value in values.items():
        if value is None:
            continue
        weight = POLLUTANT_WEIGHTS.get(key, 1)
        numerator += weight * (float(value) ** INDEX_POWER)
        denominator += weight
    if not denominator:
        return None
    return round((numerator / denominator) ** (1.0 / INDEX_POWER), 1)


def index_category(value: float | None) -> str | None:
    """Map a 0-100 index value to a site category name."""
    if value is None:
        return None
    for bound, name in INDEX_BANDS:
        if value < bound:
            return name
    return "Pessima"


def trend(
    current: float | None, previous: float | None, threshold: float = 1.0
) -> str | None:
    """Return ``su``/``giu``/``stabile`` comparing two index values.

    ``threshold`` (in index points) filters out noise. Returns ``None`` when
    either value is missing (e.g. the first refresh after a restart).
    """
    if current is None or previous is None:
        return None
    if current > previous + threshold:
        return "su"
    if current < previous - threshold:
        return "giu"
    return "stabile"


def interp_pct(
    points: list[tuple[float, float]], x: float | None
) -> float | None:
    """Interpolate the reliability indicator for a raw value.

    ``points`` are the (value, indicator%) pairs of the day's periods, sorted by
    value. The site only publishes an indicator for the single periods, so the
    daily mean needs interpolating between the closest period points.
    """
    if x is None or not points:
        return None
    if x <= points[0][0]:
        return round(points[0][1], 2)
    if x >= points[-1][0]:
        return round(points[-1][1], 2)
    for (x0, y0), (x1, y1) in itertools.pairwise(points):
        if x0 <= x <= x1:
            if x1 == x0:
                return round(y0, 2)
            return round(y0 + (y1 - y0) * (x - x0) / (x1 - x0), 2)
    return round(points[-1][1], 2)


def day_stats(day: AirDay) -> dict[str, float | None]:
    """Min / max / mean of a day with their position on the reliability bar.

    The site publishes Max and Media per day but not Min: the minimum is taken
    from the lowest of the four time-of-day periods, which also carries its own
    indicator, so no interpolation is needed for min and max.
    """
    points = sorted(
        (
            (p.value, p.indicator)
            for p in day.periods.values()
            if p.value is not None
        ),
        key=lambda pair: pair[0],
    )
    min_v: float | None = None
    min_pct: float | None = None
    max_v: float | None = day.maximum
    max_pct: float | None = None
    if points:
        min_v, min_pct = points[0]
        if max_v is None:
            max_v = points[-1][0]
            max_pct = points[-1][1]
        elif abs(max_v - points[-1][0]) < 1e-9:
            max_pct = points[-1][1]
        else:
            max_pct = interp_pct(points, max_v)
    return {
        "min": min_v,
        "min_indice_pct": min_pct,
        "max": max_v,
        "max_indice_pct": max_pct,
        "media": day.mean,
        "media_indice_pct": interp_pct(points, day.mean),
    }
