"""Privacy-safe diagnostics; never export credentials or watched titles."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data
    return {
        "integration_version": "0.2.5",
        "name": entry.title,
        "host": "[redacted]",
        "port": entry.data.get("port"),
        "active_port": coordinator.client.endpoint[1],
        "endpoint_changes": coordinator.endpoint_changes,
        "last_bonjour_resolution": coordinator.last_resolution,
        "discovered": "discovery_name" in entry.data,
        "poll_interval": coordinator.update_interval.total_seconds(),
        "tmdb_configured": bool(entry.options.get("tmdb_token")),
        "connected": coordinator.last_update_success,
        "playback_state": snapshot.state if snapshot else None,
        "has_item": bool(snapshot and snapshot.item),
        "has_artwork": bool(snapshot and snapshot.artwork_url),
        "latency_ms": snapshot.latency_ms if snapshot else None,
    }
