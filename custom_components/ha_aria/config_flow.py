"""Config flow for the 3BMeteo Air Quality integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .client import async_search_locations
from .const import (
    CONF_CANONICAL,
    CONF_LOCATION,
    CONF_POLLUTANTS,
    CONF_PROVINCE,
    CONF_SCAN_INTERVAL,
    DEFAULT_POLLUTANTS,
    DEFAULT_SCAN_INTERVAL,
    DISCLAIMER,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    POLLUTANTS,
    SITE_URL,
)

_LOGGER = logging.getLogger(__name__)


class AirConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step flow: search a town, then choose it."""

    VERSION = 1

    def __init__(self) -> None:
        self._results: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the town name to search."""
        errors: dict[str, str] = {}
        if user_input is not None:
            query = str(user_input.get(CONF_LOCATION, "")).strip()
            try:
                self._results = await async_search_locations(self.hass, query)
            except (aiohttp.ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                if not self._results:
                    errors["base"] = "no_results"
                else:
                    return await self.async_step_select()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_LOCATION): str}),
            errors=errors,
            description_placeholders={"disclaimer": DISCLAIMER, "site": SITE_URL},
        )

    async def async_step_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user pick one of the search results."""
        choices = {
            str(item["canonical"]): _label(item) for item in self._results
        }
        if user_input is not None:
            canonical = str(user_input[CONF_CANONICAL])
            item = next(
                (it for it in self._results if str(it["canonical"]) == canonical),
                None,
            )
            if item is None:
                return await self.async_step_user()
            await self.async_set_unique_id(f"air:{canonical}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Qualità aria {item['nome_loc']}",
                data={
                    CONF_CANONICAL: canonical,
                    CONF_LOCATION: str(item["nome_loc"]),
                    CONF_PROVINCE: str(item.get("prov", "")),
                },
            )

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({vol.Required(CONF_CANONICAL): vol.In(choices)}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return AirOptionsFlow()


class AirOptionsFlow(OptionsFlow):
    """Options: which pollutants to expose and the refresh interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.config_entry
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLLUTANTS,
                    default=entry.options.get(CONF_POLLUTANTS, DEFAULT_POLLUTANTS),
                ): cv.multi_select(POLLUTANTS),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _label(item: dict[str, Any]) -> str:
    name = item.get("nome_loc", "?")
    prov = item.get("prov") or ""
    region = item.get("regione") or ""
    extra = ", ".join(part for part in (prov, region) if part)
    return f"{name} ({extra})" if extra else str(name)
