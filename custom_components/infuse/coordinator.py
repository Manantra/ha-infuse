"""Centralized LAN polling, optional artwork enrichment, and state events."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import logging
from time import monotonic

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InfuseClient
from .const import (
    CONF_LANGUAGE, CONF_TMDB_TOKEN, DEFAULT_LANGUAGE, DOMAIN,
    EVENT_MEDIA_CHANGED, EVENT_PLAYBACK_IDLE, EVENT_PLAYBACK_PAUSED,
    EVENT_PLAYBACK_RESUMED, EVENT_PLAYBACK_STARTED, EVENT_STATE_CHANGED,
)
from .metadata import fetch_tmdb_artwork
from .model import InfuseInvalidResponse, Playback

_LOGGER = logging.getLogger(__name__)


class InfuseCoordinator(DataUpdateCoordinator[Playback]):
    """Exactly one HTTP poll per device; all entities share its snapshot."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: InfuseClient,
        session: aiohttp.ClientSession, interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.entry = entry
        self.client = client
        self.session = session
        self._artwork_cache: dict[tuple[str, str, str], tuple[float, str | None]] = {}

    async def _async_update_data(self) -> Playback:
        previous = self.data
        try:
            current = await self.client.get_now_playing()
        except (aiohttp.ClientError, TimeoutError, ValueError, InfuseInvalidResponse) as exc:
            raise UpdateFailed(f"Unable to contact Infuse Now Playing API: {type(exc).__name__}") from exc

        item = current.item
        token: str = self.entry.options.get(CONF_TMDB_TOKEN, "")
        language: str = self.entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        if item and token and item.tmdb_id:
            cache_key = (item.kind, item.tmdb_id, language)
            cached = self._artwork_cache.get(cache_key)
            if cached and cached[0] > monotonic():
                artwork = cached[1]
            else:
                try:
                    artwork = await fetch_tmdb_artwork(self.session, token, item, language)
                except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
                    _LOGGER.debug("Optional TMDB artwork lookup failed: %s", type(exc).__name__)
                    artwork = None
                    self._artwork_cache[cache_key] = (monotonic() + 300, None)
                else:
                    self._artwork_cache[cache_key] = (monotonic() + 12 * 3600, artwork)
            current = replace(current, artwork_url=artwork)

        if previous is not None:
            self._emit_events(previous, current)
        return current

    def _emit_events(self, previous: Playback, current: Playback) -> None:
        old_item = previous.item.identity if previous.item else None
        new_item = current.item.identity if current.item else None
        context = {
            "config_entry_id": self.entry.entry_id,
            "device_name": self.entry.title,
            "state": current.state,
            "title": current.item.title if current.item else None,
            "series_title": current.item.series_title if current.item else None,
            "tmdb_id": current.item.tmdb_id if current.item else None,
        }
        if old_item != new_item:
            self.hass.bus.async_fire(EVENT_MEDIA_CHANGED, context)
        if previous.state == current.state:
            return
        self.hass.bus.async_fire(
            EVENT_STATE_CHANGED,
            {**context, "previous_state": previous.state},
        )
        if current.state == "idle":
            specific = EVENT_PLAYBACK_IDLE
        elif current.state == "paused":
            specific = EVENT_PLAYBACK_PAUSED
        elif previous.state == "paused":
            specific = EVENT_PLAYBACK_RESUMED
        else:
            specific = EVENT_PLAYBACK_STARTED
        self.hass.bus.async_fire(specific, context)
