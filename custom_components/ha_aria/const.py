"""Constants for the 3BMeteo Air Quality integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ha_aria"
VERSION: Final = "0.1.5"

# 3BMeteo public web pages (scraped; see DISCLAIMER).
BASE_URL: Final = "https://www.3bmeteo.com"
AIR_PATH: Final = "/aria/{canonical}"
SEARCH_PATH: Final = "/search/search_localita/{query}"
SITE_URL: Final = "https://www.3bmeteo.com/aria/italia"

USER_AGENT: Final = (
    f"ha_aria/{VERSION} (+https://github.com/marcopiccinni/ha_aria)"
)

# Refresh interval in seconds. The forecast changes a few times per day.
DEFAULT_SCAN_INTERVAL: Final = 3600
MIN_SCAN_INTERVAL: Final = 900
MAX_SCAN_INTERVAL: Final = 86400

# Short-lived cache shared by all locations (same host, be nice).
CACHE_TTL: Final = timedelta(seconds=120)

CONF_CANONICAL: Final = "canonical"
CONF_LOCATION: Final = "location"
CONF_PROVINCE: Final = "province"
CONF_POLLUTANTS: Final = "pollutants"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Pollutant key (as used by 3BMeteo) -> human label.
POLLUTANTS: Final[dict[str, str]] = {
    "pm10": "PM10",
    "pm25": "PM2.5",
    "co": "CO",
    "so2": "SO2",
    "o3": "O3",
    "no2": "NO2",
}
DEFAULT_POLLUTANTS: Final = list(POLLUTANTS)

# Time-of-day buckets used by the page, in order.
PERIODS: Final = ("Notte", "Mattina", "Pomeriggio", "Sera")

# Air-quality categories, best -> worst, with the colour used on the site.
# The 5 reliability-bar segments map 1:1 to these categories.
CATEGORIES: Final[dict[str, dict[str, object]]] = {
    "Ottima": {"index": 1, "color": "#2e7d32"},
    "Buona": {"index": 2, "color": "#f9a825"},
    "Accettabile": {"index": 3, "color": "#ef6c00"},
    "Scadente": {"index": 4, "color": "#c62828"},
    "Pessima": {"index": 5, "color": "#4527a0"},
}
UNIT: Final = "µg/m³"

# Reference concentrations (µg/m³) used to normalise each pollutant to a 0-100
# index where 100 equals the reference limit (values above 100 exceed it).
# Based on the EU ambient air quality limit values (Directive 2008/50/EC):
# PM10 daily, PM2.5 annual, CO 8h, SO2 daily, O3 8h, NO2 hourly.
POLLUTANT_LIMITS: Final[dict[str, float]] = {
    "pm10": 50.0,
    "pm25": 25.0,
    "co": 10000.0,
    "so2": 125.0,
    "o3": 120.0,
    "no2": 200.0,
}

# Relative weight (health relevance) of each pollutant in the weighted index.
POLLUTANT_WEIGHTS: Final[dict[str, int]] = {
    "pm25": 5,
    "pm10": 4,
    "o3": 3,
    "no2": 3,
    "so2": 2,
    "co": 1,
}

# Exponent of the weighted generalised mean: >1 makes the worst pollutants
# weigh more than a plain weighted average.
INDEX_POWER: Final = 2

# Upper bounds of the 0-100 index categories (same names/colours as the site).
INDEX_BANDS: Final[tuple[tuple[float, str], ...]] = (
    (20.0, "Ottima"),
    (40.0, "Buona"),
    (60.0, "Accettabile"),
    (80.0, "Scadente"),
)

ATTRIBUTION: Final = "Dati: 3BMeteo (www.3bmeteo.com)"

DISCLAIMER: Final = (
    "Integrazione NON ufficiale, non affiliata a 3BMeteo. I dati sono letti "
    "dalle pagine pubbliche del sito e la loro disponibilita' non e' "
    "garantita. Uso soggetto ai termini di servizio di 3BMeteo."
)
