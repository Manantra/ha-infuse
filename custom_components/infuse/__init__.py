"""Infuse Now Playing – native Home Assistant integration.

The local Firecore HTTP endpoint is read-only. URL-scheme actions return
URLs intended to be opened on the device running Infuse; they are not remote
control actions.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InfuseClient
from .const import CONF_HOST, CONF_POLL_INTERVAL, CONF_PORT, DEFAULT_POLL_INTERVAL, DOMAIN
from .coordinator import InfuseCoordinator
from .links import library_link, stream_link

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SENSOR, Platform.BINARY_SENSOR]
# Config-entry-only integration; no legacy YAML configuration is accepted.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LIBRARY_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("media_type"): vol.In(["movie", "series", "season", "episode"]),
        vol.Required("tmdb_id"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("season"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("episode"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("autoplay", default=False): cv.boolean,
    }
)
_STREAM_SCHEMA = vol.Schema(
    {
        vol.Required("url"): cv.string,
        vol.Optional("filename"): cv.string,
        vol.Optional("subtitle"): cv.string,
        vol.Optional("position"): vol.All(vol.Coerce(int), vol.Range(min=0)),
    }
)
_STREAM_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("action"): vol.In(["play", "save"]),
        vol.Optional("url"): cv.string,
        vol.Optional("filename"): cv.string,
        vol.Optional("subtitle"): cv.string,
        vol.Optional("position"): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional("streams"): vol.All(cv.ensure_list, [_STREAM_SCHEMA]),
        vol.Optional("download", default=False): cv.boolean,
        vol.Optional("x_success"): cv.string,
        vol.Optional("x_error"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register useful actions even before a device is paired."""

    async def create_library_link(call: ServiceCall) -> dict[str, str]:
        try:
            link = library_link(
                call.data["media_type"], call.data["tmdb_id"],
                season=call.data.get("season"), episode=call.data.get("episode"),
                autoplay=call.data.get("autoplay", False),
            )
        except ValueError as exc:
            raise HomeAssistantError(str(exc)) from exc
        return {"url": link}

    async def create_stream_link(call: ServiceCall) -> dict[str, str]:
        values = dict(call.data)
        streams = values.get("streams")
        if streams and "url" in values:
            raise HomeAssistantError("Use either 'streams' or 'url', not both")
        if not streams:
            if "url" not in values:
                raise HomeAssistantError("Supply 'url' or 'streams'")
            streams = [{key: values[key] for key in ("url", "filename", "subtitle", "position") if key in values}]
        try:
            link = stream_link(
                values["action"], streams, download=values.get("download", False),
                x_success=values.get("x_success"), x_error=values.get("x_error"),
            )
        except ValueError as exc:
            raise HomeAssistantError(str(exc)) from exc
        return {"url": link}

    hass.services.async_register(
        DOMAIN, "create_library_link", create_library_link,
        schema=_LIBRARY_SERVICE_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "create_stream_link", create_stream_link,
        schema=_STREAM_SERVICE_SCHEMA, supports_response=SupportsResponse.ONLY,
    )
    # The bundled single-device and Household cards share one versioned
    # dashboard resource, registered only once for all configured devices.
    from .frontend import async_register_dashboard_cards

    await async_register_dashboard_cards(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect and expose one Infuse device."""
    session = async_get_clientsession(hass)
    client = InfuseClient(session, entry.data[CONF_HOST], entry.data[CONF_PORT])
    coordinator = InfuseCoordinator(
        hass, entry, client, session,
        int(entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)),
    )
    # Infuse can be suspended by tvOS while Home Assistant starts. Set up the
    # entities even when its HTTP listener is unavailable: scheduled polling
    # and the Bonjour watcher can then restore the device without a reload.
    await coordinator.async_refresh()
    await coordinator.async_start_bonjour_updates()
    entry.async_on_unload(coordinator.async_stop_bonjour_updates)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Restart cleanly when poll interval or optional TMDB settings change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Cancel polling and unload all entities."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
