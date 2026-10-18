"""Unit tests for the US EPA AQI computation (no Home Assistant needed)."""

from __future__ import annotations

import pytest
from ha_aria import aqi


@pytest.mark.parametrize(
    ("concentration", "expected"),
    [
        (0.0, 0),
        (9.0, 50),
        (9.05, 50),  # gap between bands keeps the previous band
        (9.1, 51),
        (35.4, 100),
        (55.4, 150),
        (125.4, 200),
        (225.4, 300),
        (325.4, 500),
        (400.0, 500),  # clamped
    ],
)
def test_pm25_sub_index(concentration: float, expected: int) -> None:
    assert aqi.sub_index("pm25", concentration) == expected


@pytest.mark.parametrize(
    ("concentration", "expected"),
    [(54.0, 50), (55.0, 51), (604.0, 500)],
)
def test_pm10_sub_index(concentration: float, expected: int) -> None:
    assert aqi.sub_index("pm10", concentration) == expected


def test_o3_converts_ugm3_to_ppb() -> None:
    # 100 µg/m³ O3 ~= 50.9 ppb -> ~47 AQI.
    assert aqi.sub_index("o3", 100.0) == 47


def test_no2_gap_between_bands() -> None:
    # 100 µg/m³ NO2 ~= 53.1 ppb, in the 53-54 gap -> previous band (50).
    assert aqi.sub_index("no2", 100.0) == 50


def test_co_converts_ugm3_to_ppm() -> None:
    # 5000 µg/m³ CO ~= 4.36 ppm -> ~50 AQI.
    assert aqi.sub_index("co", 5000.0) == 50


def test_sub_index_edges() -> None:
    assert aqi.sub_index("pm25", None) is None
    assert aqi.sub_index("unobtainium", 10.0) is None


def test_compute_aqi_picks_dominant() -> None:
    result = aqi.compute_aqi({"pm25": 60.0, "o3": 100.0})
    assert result.aqi == 154
    assert result.dominant == "pm25"
    assert result.category == "Insalubre"
    assert result.sub_indices == {"pm25": 154, "o3": 47}


def test_compute_aqi_empty() -> None:
    result = aqi.compute_aqi({"pm25": None})
    assert result.aqi is None
    assert result.dominant is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (50, "Buona"),
        (51, "Moderata"),
        (100, "Moderata"),
        (101, "Insoddisfacente"),
        (150, "Insoddisfacente"),
        (151, "Insalubre"),
        (200, "Insalubre"),
        (201, "Molto insalubre"),
        (300, "Molto insalubre"),
        (301, "Pericolosa"),
    ],
)
def test_aqi_category(value: int, expected: str) -> None:
    assert aqi.aqi_category(value) == expected
