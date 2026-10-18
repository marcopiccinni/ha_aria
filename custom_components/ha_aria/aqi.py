"""US EPA Air Quality Index (AQI) computed from 3BMeteo concentrations.

3BMeteo publishes every pollutant in ``µg/m³``. The US Environmental Protection
Agency (EPA) AQI is defined on pollutant-specific scales (``µg/m³`` for the
particulates, ``ppb``/``ppm`` for the gases) using the standard piecewise-linear
breakpoint table. This module converts the site values and returns a 0-500 AQI
together with the dominant pollutant and the per-pollutant sub-indices.

The module deliberately has **no Home Assistant imports** so it can be tested in
isolation. The AQI is an approximation: the site values are short-period
measurements, while some EPA species (e.g. PM2.5) are defined on a 24-hour
average, so the result is meant as an intuitive 0-500 scale, not a regulatory
index.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

# Molar volume at 25 °C, 1 atm, in L/mol.
MOLAR_VOLUME: Final = 24.45

# Molecular weights (g/mol) of the gases exposed by 3BMeteo.
MOLECULAR_WEIGHT: Final[dict[str, float]] = {
    "o3": 48.00,
    "no2": 46.01,
    "so2": 64.07,
    "co": 28.01,
}

# Breakpoints (gas species only) expressed in ppb, and the ones in ppm.
_PPB_SPECIES: Final[tuple[str, ...]] = ("o3", "no2", "so2")
_PPM_SPECIES: Final = ("co",)

# Breakpoint tables: (concentration_lo, concentration_high, aqi_lo, i_high).
# Particulates are µg/m³; gases use the unit noted above.
BREAKPOINTS: Final[dict[str, tuple[tuple[float, float, float, float], ...]]] = {
    # PM2.5, 24-hour, µg/m³ (EPA 2024 revision).
    "pm25": (
        (0.0, 9.0, 0, 50),
        (9.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 125.4, 151, 200),
        (125.5, 225.4, 201, 300),
        (225.5, 325.4, 301, 500),
    ),
    # PM10, 24-hour, µg/m³.
    "pm10": (
        (0, 54, 0, 50),
        (55, 154, 51, 100),
        (155, 254, 101, 150),
        (255, 354, 151, 200),
        (355, 424, 201, 300),
        (425, 604, 301, 500),
    ),
    # Ozone, 8-hour, ppb.
    "o3": (
        (0, 54, 0, 50),
        (55, 70, 51, 100),
        (71, 85, 101, 150),
        (86, 105, 151, 200),
        (106, 200, 201, 300),
    ),
    # Nitrogen dioxide, 1-hour, ppb.
    "no2": (
        (0, 53, 0, 50),
        (54, 100, 51, 100),
        (101, 360, 101, 150),
        (361, 649, 151, 200),
        (650, 1249, 201, 300),
        (1250, 2049, 301, 500),
    ),
    # Sulphur dioxide, 1-hour, ppb.
    "so2": (
        (0, 35, 0, 50),
        (36, 75, 51, 100),
        (76, 185, 101, 150),
        (186, 304, 151, 200),
        (305, 604, 201, 300),
        (605, 1004, 301, 500),
    ),
    # Carbon monoxide, 8-hour, ppm.
    "co": (
        (0.0, 4.4, 0, 50),
        (4.5, 9.4, 51, 100),
        (9.5, 12.4, 101, 150),
        (12.5, 15.4, 151, 200),
        (15.5, 30.4, 201, 300),
        (30.5, 50.4, 301, 500),
    ),
}

# Gases whose breakpoints are in ppb -> (molecular weight); CO is in ppm.
_GAS_PPB: Final[dict[str, float]] = {
    "o3": MOLAR_VOLUME / 48.00,
    "no2": MOLAR_VOLUME / 46.0055,
    "so2": MOLAR_VOLUME / 64.066,
}
_GAS_PPM: Final[dict[str, float]] = {"co": MOLAR_VOLUME / (28.010 * 1000.0)}


@dataclass(slots=True)
class AqiResult:
    """Aggregated AQI for one location."""

    aqi: int | None
    category: str | None
    color: str | None
    dominant: str | None
    sub_indices: dict[str, int] = field(default_factory=dict)


def _piecewise(
    value: float, table: tuple[tuple[float, float, float, float], ...]
) -> float:
    """Piecewise-linear EPA breakpoint interpolation, clamped to 0-500.

    The EPA tables leave small gaps between bands (e.g. PM2.5 goes 0-9.0 then
    9.1-35.4); a value landing in a gap keeps the previous band's upper index.
    """
    if value <= table[0][0]:
        return float(table[0][2])
    previous = float(table[0][2])
    for c_low, c_high, i_low, i_high in table:
        if value <= c_high:
            if value < c_low:
                return previous
            return i_low + (i_high - i_low) * (value - c_low) / (c_high - c_low)
        previous = float(i_high)
    return 500.0


def sub_index(pollutant: str, concentration: float | None) -> int | None:
    """Return the 0-500 AQI sub-index of one pollutant (``µg/m³`` input)."""
    table = BREAKPOINTS.get(pollutant)
    if table is None or concentration is None:
        return None
    scaled = concentration
    if pollutant in _GAS_PPB:
        scaled = concentration * _GAS_PPB[pollutant]
    elif pollutant in _GAS_PPM:
        scaled = concentration * _GAS_PPM[pollutant]
    return round(_piecewise(scaled, table))


def aqi_category(value: float | None) -> str:
    """Return the Italian name of the AQI band for ``value``."""
    if value is None:
        return "—"
    if value <= 50:
        return "Buona"
    if value <= 100:
        return "Moderata"
    if value <= 150:
        return "Insoddisfacente"
    if value <= 200:
        return "Insalubre"
    if value <= 300:
        return "Molto insalubre"
    return "Pericolosa"


def compute_aqi(values: dict[str, float | None]) -> AqiResult:
    """Return the aggregated 0-500 AQI for a set of concentrations (µg/m³).

    The overall AQI is the highest pollutant sub-index; the dominant pollutant
    is the one carrying it. Pollutants without a breakpoint table (or with a
    ``None`` value) are skipped.
    """
    sub_indices: dict[str, int] = {}
    for key, value in values.items():
        index = sub_index(key, value)
        if index is not None:
            sub_indices[key] = index
    if not sub_indices:
        return AqiResult(aqi=None, category=None, color=None, dominant=None)
    dominant = max(sub_indices, key=lambda key: sub_indices[key])
    aqi = sub_indices[dominant]
    category = aqi_category(aqi)
    return AqiResult(
        aqi=aqi,
        category=category,
        color=color_for(category),
        dominant=dominant,
        sub_indices=sub_indices,
    )


_AQI_COLORS: Final[dict[str, str]] = {
    "Buona": "#4caf50",
    "Moderata": "#f9a825",
    "Insoddisfacente": "#ef6c00",
    "Insalubre": "#c62828",
    "Molto insalubre": "#6a1b9a",
    "Pericolosa": "#4d2c3d",
}


def color_for(category: str | None) -> str:
    """Return the AQI band colour (used by the sensor and the card)."""
    return _AQI_COLORS.get(category or "", "#9e9e9e")
