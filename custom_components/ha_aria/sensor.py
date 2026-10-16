"""Sensor platform for the 3BMeteo Air Quality integration."""

from __future__ import annotations

import itertools
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .client import AirDay
from .const import (
    AIR_PATH,
    ATTRIBUTION,
    BASE_URL,
    CATEGORIES,
    CONF_LOCATION,
    CONF_POLLUTANTS,
    DEFAULT_POLLUTANTS,
    DOMAIN,
    INDEX_BANDS,
    INDEX_POWER,
    POLLUTANT_WEIGHTS,
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
    """Create one sensor per selected pollutant, an overall index and a summary."""
    coordinator: AirCoordinator = entry.runtime_data
    keys = _selected_keys(coordinator)
    _remove_orphan_entities(hass, entry, coordinator.canonical, keys)
    entities: list[SensorEntity] = [
        AirPollutantSensor(coordinator, key) for key in keys
    ]
    entities.append(AirIndexSensor(coordinator))
    entities.append(AirSummarySensor(coordinator))
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
    expected.add(f"{canonical}_riepilogo")
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
            attributes["min_oggi"] = _day_stats(day)["min"]
        attributes["previsioni"] = _serialize_days(self.coordinator, self.key)
        return attributes


class AirIndexSensor(_AirBaseSensor):
    """Overall air quality: the worst category among the selected pollutants."""

    _attr_name = "Indice"
    _attr_icon = "mdi:weather-hazy"

    def __init__(self, coordinator: AirCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.canonical}_index"

    @property
    def native_value(self) -> str | None:
        return _worst_category(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        category = _worst_category(self.coordinator)
        return {
            "localita": self._location,
            "indice": CATEGORIES.get(category or "", {}).get("index"),
            "colore": CATEGORIES.get(category or "", {}).get("color"),
            "giorni": _worst_by_day(self.coordinator),
        }


def _worst_category(coordinator: AirCoordinator) -> str | None:
    worst: str | None = None
    worst_index = 0
    for key in _selected_keys(coordinator):
        day = coordinator.current_day(key)
        if day is None:
            continue
        period = day.periods.get(current_period(dt_util.now()))
        category = period.category if period else day.category
        index = CATEGORIES.get(category or "", {}).get("index", 0)
        if index >= worst_index:
            worst_index = index
            worst = category
    return worst


def _weighted_index(values: dict[str, float | None]) -> float | None:
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


def _index_category(value: float | None) -> str | None:
    """Map a 0-100 index value to a site category name."""
    if value is None:
        return None
    for bound, name in INDEX_BANDS:
        if value < bound:
            return name
    return "Pessima"


class AirSummarySensor(_AirBaseSensor):
    """Summary of the air quality: a weighted 0-100 index and the main sources.

    The index lives on the same 0-100 scale and category bands used by the
    single pollutants (the 3BMeteo reliability bar, 100 = worst): each
    pollutant's index is combined with a weighted generalised mean, so the
    summary is never worse than the worst pollutant. A ranked list of the
    highest pollutants is exposed as well.
    """

    _attr_name = "Riepilogo"
    _attr_icon = "mdi:chart-box"

    def __init__(self, coordinator: AirCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.canonical}_riepilogo"

    def _current_values(self) -> dict[str, float | None]:
        """Current-period 0-100 reliability index of every selected pollutant."""
        period_name = current_period(dt_util.now())
        values: dict[str, float | None] = {}
        for key in _selected_keys(self.coordinator):
            day = self.coordinator.current_day(key)
            if day is None:
                values[key] = None
                continue
            period = day.periods.get(period_name)
            if period is not None:
                values[key] = period.indicator
            else:
                values[key] = _day_stats(day)["max_indice_pct"]
        return values

    def _index(self) -> float | None:
        return _weighted_index(self._current_values())

    def _rows(self) -> list[dict[str, Any]]:
        """Every selected pollutant, ranked by its 0-100 index (worst first)."""
        period_name = current_period(dt_util.now())
        rows: list[dict[str, Any]] = []
        for key in _selected_keys(self.coordinator):
            day = self.coordinator.current_day(key)
            if day is None:
                continue
            period = day.periods.get(period_name)
            value = period.value if period else day.maximum
            stats = _day_stats(day)
            norm = period.indicator if period else stats["max_indice_pct"]
            category = period.category if period else day.category
            rows.append(
                {
                    "chiave": key,
                    "nome": POLLUTANTS[key],
                    "valore": value,
                    "normalizzato": norm,
                    "peso": POLLUTANT_WEIGHTS.get(key),
                    "categoria": category or _index_category(norm),
                    "colore": CATEGORIES.get(
                        category or _index_category(norm) or "", {}
                    ).get("color"),
                }
            )
        rows.sort(key=lambda row: -(row["normalizzato"] or 0))
        return rows

    def _serialize_days(self) -> list[dict[str, Any]]:
        """Per-day weighted index (min/media/max) across the selected pollutants."""
        keys = _selected_keys(self.coordinator)
        count = 0
        label = None
        for key in keys:
            days = (
                self.coordinator.data.pollutants.get(key)
                if self.coordinator.data
                else None
            )
            if days:
                count = max(count, len(days))
                if label is None:
                    label = days
        result: list[dict[str, Any]] = []
        for i in range(count):
            lows: dict[str, float | None] = {}
            means: dict[str, float | None] = {}
            highs: dict[str, float | None] = {}
            rows: list[dict[str, Any]] = []
            for key in keys:
                days = (
                    self.coordinator.data.pollutants.get(key)
                    if self.coordinator.data
                    else None
                )
                if not days or i >= len(days):
                    continue
                stats = _day_stats(days[i])
                lows[key] = stats["min_indice_pct"]
                means[key] = stats["media_indice_pct"]
                highs[key] = stats["max_indice_pct"]
                norm = stats["max_indice_pct"]
                rows.append(
                    {
                        "chiave": key,
                        "nome": POLLUTANTS[key],
                        "valore": stats["max"],
                        "normalizzato": norm,
                        "categoria": days[i].category,
                        "colore": CATEGORIES.get(
                            days[i].category or "", {}
                        ).get("color"),
                    }
                )
            rows.sort(key=lambda row: -(row["normalizzato"] or 0))
            media = _weighted_index(means)
            category = _index_category(media)
            result.append(
                {
                    "giorno": label[i].short if label and i < len(label) else "",
                    "categoria": category,
                    "colore": CATEGORIES.get(category or "", {}).get("color"),
                    "indice_pct": media,
                    "min": _weighted_index(lows),
                    "media": media,
                    "max": _weighted_index(highs),
                    "min_indice_pct": _weighted_index(lows),
                    "media_indice_pct": media,
                    "max_indice_pct": _weighted_index(highs),
                    "inquinanti": rows,
                    "inquinanti_piu_alti": [
                        row for row in rows if (row["normalizzato"] or 0) >= 20
                    ][:3],
                }
            )
        return result

    @property
    def native_value(self) -> str | None:
        return _index_category(self._index())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        index = self._index()
        category = _index_category(index)
        rows = self._rows()
        top = [row for row in rows if (row["normalizzato"] or 0) >= 20][:3]
        counts: dict[str, int] = {}
        for row in rows:
            name = row["categoria"] or "—"
            counts[name] = counts.get(name, 0) + 1
        days = self._serialize_days()
        return {
            "localita": self._location,
            "categoria": category,
            "indice": CATEGORIES.get(category or "", {}).get("index"),
            "colore": CATEGORIES.get(category or "", {}).get("color"),
            "indice_pct": index,
            "scala": "3BMeteo 0-100",
            "periodo": current_period(dt_util.now()),
            "riepilogo": rows,
            "inquinanti_piu_alti": top,
            "conteggio_per_categoria": counts,
            "totale_inquinanti": len(rows),
            "inquinanti_non_ottimi": len(top),
            "pesi": POLLUTANT_WEIGHTS,
            "esponente": INDEX_POWER,
            "previsioni": days,
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


def _interp_pct(points: list[tuple[float, float]], x: float | None) -> float | None:
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


def _day_stats(day: AirDay) -> dict[str, float | None]:
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
            max_pct = _interp_pct(points, max_v)
    return {
        "min": min_v,
        "min_indice_pct": min_pct,
        "max": max_v,
        "max_indice_pct": max_pct,
        "media": day.mean,
        "media_indice_pct": _interp_pct(points, day.mean),
    }


def _serialize_days(coordinator: AirCoordinator, key: str) -> list[dict[str, Any]]:
    days = coordinator.data.pollutants.get(key) if coordinator.data else None
    if not days:
        return []
    result: list[dict[str, Any]] = []
    for day in days:
        stats = _day_stats(day)
        result.append(
            {
                "giorno": day.short,
                "data": day.label,
                "categoria": day.category,
                "max": stats["max"],
                "media": stats["media"],
                "min": stats["min"],
                "min_indice_pct": stats["min_indice_pct"],
                "max_indice_pct": stats["max_indice_pct"],
                "media_indice_pct": stats["media_indice_pct"],
                "periodi": {
                    name: {
                        "valore": p.value,
                        "categoria": p.category,
                        "indice_pct": p.indicator,
                    }
                    for name, p in day.periods.items()
                },
            }
        )
    return result


_ICONS = {
    "pm10": "mdi:blur",
    "pm25": "mdi:blur-linear",
    "co": "mdi:molecule-co",
    "so2": "mdi:molecule",
    "o3": "mdi:weather-sunny-alert",
    "no2": "mdi:weather-windy-variant",
}
