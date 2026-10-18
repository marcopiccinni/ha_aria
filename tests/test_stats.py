"""Unit tests for the pure index statistics (no Home Assistant needed)."""

from __future__ import annotations

import pytest
from ha_aria import stats
from ha_aria.models import AirDay, AirPeriod


def _day(periods: dict[str, tuple[float, float]], maximum=None, mean=None) -> AirDay:
    return AirDay(
        label="lunedì 14",
        short="Lun",
        category="Buona",
        maximum=maximum,
        mean=mean,
        periods={
            name: AirPeriod(period=name, value=value, indicator=pct, category="Buona")
            for name, (value, pct) in periods.items()
        },
    )


def test_weighted_index_all_none() -> None:
    assert stats.weighted_index({"pm25": None, "co": None}) is None


def test_weighted_index_single_pollutant() -> None:
    assert stats.weighted_index({"pm25": 42.0}) == 42.0


def test_weighted_index_worst_dominates() -> None:
    # pm25 weight 5 (100), co weight 1 (0): with power 2 the worst dominates.
    value = stats.weighted_index({"pm25": 100.0, "co": 0.0})
    assert value == pytest.approx(91.3, abs=0.05)


def test_weighted_index_skips_none_values() -> None:
    assert stats.weighted_index({"pm25": 40.0, "co": None}) == 40.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "Ottima"),
        (19.9, "Ottima"),
        (20.0, "Buona"),
        (39.9, "Buona"),
        (40.0, "Accettabile"),
        (59.9, "Accettabile"),
        (60.0, "Scadente"),
        (79.9, "Scadente"),
        (80.0, "Pessima"),
        (100.0, "Pessima"),
    ],
)
def test_index_category_bands(value: float, expected: str) -> None:
    assert stats.index_category(value) == expected


def test_index_category_none() -> None:
    assert stats.index_category(None) is None


def test_interp_pct_edge_cases() -> None:
    points = [(10.0, 20.0), (20.0, 60.0), (30.0, 90.0)]
    assert stats.interp_pct(points, None) is None
    assert stats.interp_pct([], 5.0) is None
    assert stats.interp_pct(points, 5.0) == 20.0
    assert stats.interp_pct(points, 99.0) == 90.0
    assert stats.interp_pct(points, 25.0) == 75.0


def test_interp_pct_flat_segment() -> None:
    assert stats.interp_pct([(10.0, 30.0), (10.0, 30.0)], 10.0) == 30.0


def test_day_stats_uses_period_min_and_interpolates_mean() -> None:
    day = _day(
        {
            "Notte": (10.0, 20.0),
            "Mattina": (20.0, 60.0),
            "Pomeriggio": (30.0, 90.0),
            "Sera": (15.0, 40.0),
        },
        maximum=30.0,
        mean=18.0,
    )
    result = stats.day_stats(day)
    assert result["min"] == 10.0
    assert result["min_indice_pct"] == 20.0
    assert result["max"] == 30.0
    assert result["max_indice_pct"] == 90.0
    # 18 lies between 15 (40%) and 20 (60%): 40 + 20 * 3/5 = 52%
    assert result["media_indice_pct"] == 52.0


def test_day_stats_without_periods() -> None:
    day = _day({}, maximum=12.0, mean=8.0)
    result = stats.day_stats(day)
    assert result["min"] is None
    assert result["max"] == 12.0
    assert result["max_indice_pct"] is None
    assert result["media_indice_pct"] is None
