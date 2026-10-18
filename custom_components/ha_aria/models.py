"""Dataclasses describing a parsed 3BMeteo air-quality page.

Kept free of Home Assistant imports so the parser and the statistics can be
unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AirPeriod:
    """One time-of-day measurement."""

    period: str
    value: float
    indicator: float
    category: str


@dataclass(slots=True)
class AirDay:
    """One day of forecast for a single pollutant."""

    label: str
    short: str | None
    category: str | None
    maximum: float | None
    mean: float | None
    periods: dict[str, AirPeriod] = field(default_factory=dict)


@dataclass(slots=True)
class AirReport:
    """Parsed air-quality page for one location."""

    canonical: str
    pollutants: dict[str, list[AirDay]]
