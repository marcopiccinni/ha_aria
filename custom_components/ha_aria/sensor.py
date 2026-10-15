"""Sensor platform for the 3BMeteo Air Quality integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    AIR_PATH,
    ATTRIBUTION,
    BASE_URL,
    CATEGORIES,
    CONF_LOCATION,
    CONF_POLLUTANTS,
    DEFAULT_POLLUTANTS,
    DOMAIN,
    POLLUTANTS,
    UNIT,
)
from .coordinator import AirCoordinator, current_period


def _selected_keys(coordinator: AirCoordinator) -> list[str]:
    return [
        key
        for key in coordinator.entry.options.get(CONF_POLLUTANTS, DEFAULT_POLLUTANTS)
        if key in POLLUTANTS
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one sensor per selected pollutant, plus an overall index."""
    coordinator: AirCoordinator = entry.runtime_data
    keys = _selected_keys(coordinator)
    _remove_orphan_entities(hass, entry, coordinator.canonical, keys)
    entities: list[SensorEntity] = [
        AirPollutantSensor(coordinator, key) for key in keys
    ]
    entities.append(AirIndexSensor(coordinator))
    async_add_entities(entities)


def _remove_orphan_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    canonical: str,
    keys: list[str],
) -> None:
    """Drop registry entries for pollutants no longer exposed."""
    expected = {f"{canonical}_{key}" for key in keys}
    expected.add(f"{canonical}_index")
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id not in expected:
            registry.async_remove(reg_entry.entity_id)


class _AirBaseSensor(SensorEntity):
    """Common attributes for the air-quality sensors."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: AirCoordinator) -> None:
        self.coordinator = coordinator
        self._location = coordinator.entry.data.get(
            CONF_LOCATION, coordinator.canonical
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self.coordinator.canonical)},
            "name": f"Qualità aria {self._location}",
            "manufacturer": "3BMeteo",
            "model": "Qualità dell'aria",
            "configuration_url": BASE_URL
            + AIR_PATH.format(canonical=self.coordinator.canonical),
        }

    def _current_period(self):
        day = self.coordinator.current_day(getattr(self, "key", ""))
        if day is None:
            return None, None
        return day, day.periods.get(current_period(dt_util.now()))


class AirPollutantSensor(_AirBaseSensor):
    """Current value of a single pollutant with its forecast."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT

    def __init__(self, coordinator: AirCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self.key = key
        self._attr_name = POLLUTANTS[key]
        self._attr_unique_id = f"{coordinator.canonical}_{key}"
        self._attr_icon = _ICONS.get(key, "mdi:air-filter")

    @property
    def native_value(self) -> float | None:
        _day, period = self._current_period()
        return period.value if period else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        day, period = self._current_period()
        attributes: dict[str, Any] = {
            "localita": self._location,
            "inquinante": self.key,
            "periodo": current_period(dt_util.now()),
        }
        if period is not None:
            attributes["categoria"] = period.category
            attributes["indice"] = CATEGORIES.get(period.category, {}).get("index")
            attributes["indice_pct"] = period.indicator
            attributes["colore"] = CATEGORIES.get(period.category, {}).get("color")
        if day is not None:
            attributes["categoria_oggi"] = day.category
            attributes["max_oggi"] = day.maximum
            attributes["media_oggi"] = day.mean
        attributes["previsioni"] = _serialize_days(self.coordinator, self.key)
        return attributes


class AirIndexSensor(_AirBaseSensor):
    """Overall air quality: the worst category among the selected pollutants."""

    _attr_name = "Indice"
    _attr_icon = "mdi:weather-hazy"

    def __init__(self, coordinator: AirCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.canonical}_index"

    def _worst_category(self) -> str | None:
        worst: str | None = None
        worst_index = 0
        for key in _selected_keys(self.coordinator):
            day = self.coordinator.current_day(key)
            if day is None:
                continue
            period = day.periods.get(current_period(dt_util.now()))
            category = period.category if period else day.category
            index = CATEGORIES.get(category or "", {}).get("index", 0)
            if index >= worst_index:
                worst_index = index
                worst = category
        return worst

    @property
    def native_value(self) -> str | None:
        return self._worst_category()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        category = self._worst_category()
        return {
            "localita": self._location,
            "indice": CATEGORIES.get(category or "", {}).get("index"),
            "colore": CATEGORIES.get(category or "", {}).get("color"),
            "giorni": _worst_by_day(self.coordinator),
        }


def _worst_by_day(coordinator: AirCoordinator) -> list[dict[str, Any]]:
    """For each forecast day, the worst category across selected pollutants."""
    keys = _selected_keys(coordinator)
    days_count = 0
    for key in keys:
        days = coordinator.data.pollutants.get(key) if coordinator.data else None
        if days:
            days_count = max(days_count, len(days))
    result = []
    for i in range(days_count):
        worst: str | None = None
        worst_index = 0
        label: str | None = None
        for key in keys:
            days = coordinator.data.pollutants.get(key) if coordinator.data else None
            if not days or i >= len(days):
                continue
            day = days[i]
            label = day.short
            index = CATEGORIES.get(day.category or "", {}).get("index", 0)
            if index >= worst_index:
                worst_index = index
                worst = day.category
        result.append({"giorno": label, "categoria": worst})
    return result


def _serialize_days(coordinator: AirCoordinator, key: str) -> list[dict[str, Any]]:
    days = coordinator.data.pollutants.get(key) if coordinator.data else None
    if not days:
        return []
    return [
        {
            "giorno": day.short,
            "data": day.label,
            "categoria": day.category,
            "max": day.maximum,
            "media": day.mean,
            "periodi": {
                name: {
                    "valore": p.value,
                    "categoria": p.category,
                    "indice_pct": p.indicator,
                }
                for name, p in day.periods.items()
            },
        }
        for day in days
    ]


_ICONS = {
    "pm10": "mdi:blur",
    "pm25": "mdi:blur-linear",
    "co": "mdi:molecule-co",
    "so2": "mdi:molecule",
    "o3": "mdi:weather-sunny-alert",
    "no2": "mdi:weather-windy-variant",
}
