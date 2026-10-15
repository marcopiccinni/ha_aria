"""HTTP client and HTML parser for 3BMeteo air-quality pages.

The air-quality page (``/aria/<canonical>``) is server-rendered. For every
pollutant it lists up to five days; each day has a ``Max``/``Media`` summary
plus four time-of-day values (Notte, Mattina, Pomeriggio, Sera), each with a
category label ("Ottima", "Buona", ...) and a normalised indicator (0-100)
mapping to five colour bands.
"""

from __future__ import annotations

import asyncio
import html
import logging
import re
import time
from dataclasses import dataclass, field

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import AIR_PATH, BASE_URL, CACHE_TTL, SEARCH_PATH, USER_AGENT

_LOGGER = logging.getLogger(__name__)

_WEEKDAY_RE = re.compile(
    r"aria-label=\"((?:luned|marted|mercoled|gioved|venerd|sabato|domenica)[^\"]*)\""
)
_DAY_ITEM_RE = re.compile(r"<li class=\"fc-accordion-item[^\"]*\">(.*?)</li>", re.DOTALL)
_PANEL_RE = re.compile(r"<div id=\"(\d+)\" class=\"content-day[^\"]*\"")
_TAB_RE = re.compile(
    r"data-pollutant=\"([^\"]+)\"[^>]*>\s*<div class=\"chips outlined\">\s*([^<]+)"
)
_MAX_RE = re.compile(r"Max:\s*([\d.,]+)\s*µg/m")
_MEAN_RE = re.compile(r"Media:\s*([\d.,]+)\s*µg/m")
_PERIOD_RE = re.compile(
    r"style=\"flex-basis:120px\">\s*([^<]+)</div>.*?"
    r"<span class=\"value[^\"]*\"[^>]*>([\d.,]+)\s*µg/m.*?"
    r"reliability-indicator\" style=\"left:([\d.]+)%\".*?"
    r"tag-[a-z]+ ds-label-small\">\s*([A-Za-zÀ-ÿ]+)",
    re.DOTALL,
)
_DAY_CAT_RE = re.compile(r"tag-[a-z]+ ds-label-small\">\s*([A-Za-zÀ-ÿ]+)")


def _to_float(value: str) -> float:
    return float(value.replace(",", "."))


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


def parse_air(html_text: str, canonical: str = "") -> AirReport:
    """Parse the air-quality HTML page into an :class:`AirReport`."""
    tabs = _TAB_RE.findall(html_text)
    panels = list(_PANEL_RE.finditer(html_text))
    pollutants: dict[str, list[AirDay]] = {}

    for index, match in enumerate(panels):
        start = match.end()
        end = panels[index + 1].start() if index + 1 < len(panels) else start + 300_000
        segment = html_text[start:end]
        key = tabs[index][0] if index < len(tabs) else match.group(1)
        days: list[AirDay] = []

        for item in _DAY_ITEM_RE.findall(segment):
            day_match = _WEEKDAY_RE.search(item)
            if not day_match:
                break
            short_match = re.search(
                r"aria-label=\"[^\"]+\"[^>]*>([^<]+)</span>", item
            )
            cats = _DAY_CAT_RE.findall(item)
            max_match = _MAX_RE.search(item)
            mean_match = _MEAN_RE.search(item)
            periods: dict[str, AirPeriod] = {}
            for pm in _PERIOD_RE.finditer(item):
                period = html.unescape(pm.group(1)).strip()
                periods[period] = AirPeriod(
                    period=period,
                    value=_to_float(pm.group(2)),
                    indicator=float(pm.group(3)),
                    category=pm.group(4),
                )
            days.append(
                AirDay(
                    label=day_match.group(1),
                    short=short_match.group(1).strip() if short_match else None,
                    category=cats[0] if cats else None,
                    maximum=_to_float(max_match.group(1)) if max_match else None,
                    mean=_to_float(mean_match.group(1)) if mean_match else None,
                    periods=periods,
                )
            )
        pollutants[key] = days

    return AirReport(canonical=canonical, pollutants=pollutants)


async def async_search_locations(
    hass: HomeAssistant, query: str
) -> list[dict[str, object]]:
    """Search 3BMeteo for locations matching ``query``."""
    query = query.strip()
    if len(query) < 2:
        return []
    session = async_get_clientsession(hass)
    url = f"{BASE_URL}{SEARCH_PATH.format(query=_slugify(query))}"
    async with session.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=aiohttp.ClientTimeout(total=20)
    ) as resp:
        resp.raise_for_status()
        data = await resp.json(content_type=None)
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("canonical")]


def _slugify(query: str) -> str:
    """Turn a free-text query into the path segment 3BMeteo expects."""
    return (
        query.strip().lower().replace(" ", "+").replace("'", "").replace("’", "")
    )


class AirClient:
    """Fetch and cache air-quality pages."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._session = async_get_clientsession(hass)
        self._cache: dict[str, tuple[float, AirReport]] = {}
        self._lock = asyncio.Lock()

    async def async_get(self, canonical: str) -> AirReport:
        """Return the (cached) air-quality report for ``canonical``."""
        async with self._lock:
            cached = self._cache.get(canonical)
            if cached and time.monotonic() - cached[0] < CACHE_TTL.total_seconds():
                return cached[1]

        url = f"{BASE_URL}{AIR_PATH.format(canonical=canonical)}"
        async with self._session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            text = await resp.text()

        report = parse_air(text, canonical)
        if not report.pollutants:
            raise ValueError(f"No air-quality data parsed for {canonical!r}")

        async with self._lock:
            self._cache[canonical] = (time.monotonic(), report)
        return report
