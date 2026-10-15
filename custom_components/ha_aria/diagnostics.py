"""Diagnostics support for the 3BMeteo Air Quality integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CANONICAL, CONF_LOCATION, CONF_PROVINCE


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "canonical": entry.data.get(CONF_CANONICAL),
            "location": entry.data.get(CONF_LOCATION),
            "province": entry.data.get(CONF_PROVINCE),
        },
        "options": dict(entry.options),
        "pollutants": {
            key: [
                {
                    "day": day.label,
                    "category": day.category,
                    "max": day.maximum,
                    "mean": day.mean,
                    "periods": {
                        name: {
                            "value": p.value,
                            "indicator": p.indicator,
                            "category": p.category,
                        }
                        for name, p in day.periods.items()
                    },
                }
                for day in days
            ]
            for key, days in (data.pollutants.items() if data else [])
        },
    }
