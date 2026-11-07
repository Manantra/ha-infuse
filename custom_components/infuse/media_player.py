"""A truthful read-only Home Assistant media player for Infuse."""

from __future__ import annotations

from datetime import datetime
from homeassistant.components.media_player import (
    MediaPlayerEntity, MediaPlayerEntityFeature, MediaPlayerState, MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import InfuseCoordinator
from .entity import InfuseEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities,
) -> None:
    coordinator: InfuseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InfuseMediaPlayer(coordinator, entry)])


class InfuseMediaPlayer(InfuseEntity, MediaPlayerEntity):
    """Playback state, metadata and poster; no unsupported remote-control buttons."""

    _attr_name = None
    _attr_icon = "mdi:play-box-outline"
    _attr_supported_features = MediaPlayerEntityFeature(0)
    _attr_media_image_remotely_accessible = True

    def __init__(self, coordinator: InfuseCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "player")
        self._position: float | None = None
        self._position_updated_at: datetime | None = None
        self._last_state: str | None = None
        self._last_media_id: tuple | None = None
        self._refresh_position()

    @property
    def state(self) -> MediaPlayerState | None:
        data = self.coordinator.data
        if not data:
            return None
        return {
            "playing": MediaPlayerState.PLAYING,
            "paused": MediaPlayerState.PAUSED,
            "idle": MediaPlayerState.IDLE,
        }.get(data.state)

    @property
    def media_title(self) -> str | None:
        item = self.coordinator.data.item if self.coordinator.data else None
        return item.title if item else None

    @property
    def media_series_title(self) -> str | None:
        item = self.coordinator.data.item if self.coordinator.data else None
        return item.series_title if item else None

    @property
    def media_season(self) -> str | None:
        item = self.coordinator.data.item if self.coordinator.data else None
        return str(item.season) if item and item.season is not None else None

    @property
    def media_episode(self) -> str | None:
        item = self.coordinator.data.item if self.coordinator.data else None
        return str(item.episode) if item and item.episode is not None else None

    @property
    def media_content_id(self) -> str | None:
        item = self.coordinator.data.item if self.coordinator.data else None
        if not item or not item.tmdb_id:
            return None
        return f"tmdb:{item.kind}:{item.tmdb_id}"

    @property
    def media_content_type(self) -> MediaType | None:
        item = self.coordinator.data.item if self.coordinator.data else None
        if not item:
            return None
        return MediaType.MOVIE if item.kind == "movie" else MediaType.EPISODE

    @property
    def media_duration(self) -> int | None:
        data = self.coordinator.data
        return round(data.duration) if data and data.duration is not None else None

    @property
    def media_position(self) -> int | None:
        return round(self._position) if self._position is not None else None

    @property
    def media_position_updated_at(self) -> datetime | None:
        return self._position_updated_at

    @property
    def media_image_url(self) -> str | None:
        data = self.coordinator.data
        return data.artwork_url if data else None

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        data = self.coordinator.data
        item = data.item if data else None
        return {
            "tmdb_id": item.tmdb_id if item else None,
            "imdb_id": item.imdb_id if item else None,
            "tvdb_id": item.tvdb_id if item else None,
            "media_kind": item.kind if item else None,
        }

    def _refresh_position(self) -> None:
        data = self.coordinator.data
        if not data:
            return
        identity = data.item.identity if data.item else None
        now = dt_util.utcnow()
        new_position = data.position
        force = (data.state != self._last_state or identity != self._last_media_id
                 or self._position_updated_at is None)
        if new_position is None:
            if self._position is not None:
                force = True
        elif not force and self._position is not None and self._position_updated_at is not None:
            elapsed = (now - self._position_updated_at).total_seconds()
            expected = self._position + (elapsed if data.state == "playing" else 0)
            force = abs(expected - new_position) > 3
        if force:
            self._position = new_position
            self._position_updated_at = now if new_position is not None else None
        self._last_state = data.state
        self._last_media_id = identity

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh_position()
        super()._handle_coordinator_update()
