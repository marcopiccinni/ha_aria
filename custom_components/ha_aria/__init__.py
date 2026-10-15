"""The 3BMeteo Air Quality integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION
from .coordinator import AirCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type AirConfigEntry = ConfigEntry[AirCoordinator]

CARD_URL = f"/{DOMAIN}/ha-aria-card.js"
_WWW = Path(__file__).parent / "www"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the bundled Lovelace card (best effort)."""
    await _async_register_card(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AirConfigEntry) -> bool:
    """Set up an air-quality location from a config entry."""
    coordinator = AirCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: AirConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AirConfigEntry) -> bool:
    """Unload an air-quality location config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve and load the bundled card, if the frontend is available."""
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig
    except ImportError:  # pragma: no cover - frontend always present in HA
        return

    if not _WWW.is_dir():
        return

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(_WWW / "ha-aria-card.js"), False)]
        )
    except (RuntimeError, ValueError):
        # Already registered (e.g. reload): safe to ignore.
        pass
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
