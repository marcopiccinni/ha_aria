"""Data update coordinator for the 3BMeteo Air Quality integration."""

from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import AirClient, AirDay, AirReport
from .const import (
    CONF_CANONICAL,
    CONF_POLLUTANTS,
    CONF_SCAN_INTERVAL,
    DEFAULT_POLLUTANTS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PERIODS,
)

_LOGGER = logging.getLogger(__name__)


def current_period(now) -> str:
    """Return the time-of-day bucket for ``now`` (local time)."""
    if now.hour < 6:
        return PERIODS[0]
    if now.hour < 12:
        return PERIODS[1]
    if now.hour < 18:
        return PERIODS[2]
    return PERIODS[3]


class AirCoordinator(DataUpdateCoordinator[AirReport]):
    """Coordinator exposing the air-quality report of one location."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.canonical: str = str(entry.data[CONF_CANONICAL])
        self.client = AirClient(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self.canonical}",
            update_interval=timedelta(
                seconds=int(
                    entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                )
            ),
            config_entry=entry,
        )
        self.entry = entry
        self.previous_data: AirReport | None = None

    @property
    def pollutants(self) -> list[str]:
        """Pollutants selected by the user (ordered as configured)."""
        selected = self.entry.options.get(CONF_POLLUTANTS, DEFAULT_POLLUTANTS)
        return [key for key in selected if key in self.data.pollutants] if self.data else list(selected)

    async def _async_update_data(self) -> AirReport:
        previous = self.data
        try:
            report = await self.client.async_get(self.canonical)
        except TimeoutError as err:
            raise UpdateFailed("Timeout fetching air-quality page") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching air-quality page: {err}") from err
        except ValueError as err:
            raise UpdateFailed(f"Invalid air-quality page: {err}") from err
        self.previous_data = previous
        return report

    def current_day(self, key: str) -> AirDay | None:
        """Return today's forecast entry for ``key``.

        3BMeteo always lists today first, so the first parsed day is today.
        """
        days = self.data.pollutants.get(key) if self.data else None
        if not days:
            return None
        return days[0]
