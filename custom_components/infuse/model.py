"""Strict, dependency-free parsing of the documented Firecore Now Playing response."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


class InfuseInvalidResponse(ValueError):
    """The Now Playing endpoint returned unexpected data."""


@dataclass(frozen=True, slots=True)
class InfuseItem:
    kind: str
    tmdb_id: str | None = None
    imdb_id: str | None = None
    tvdb_id: str | None = None
    season: int | None = None
    episode: int | None = None
    title: str | None = None
    series_title: str | None = None

    @property
    def identity(self) -> tuple[Any, ...]:
        """Identity for media-change detection; robust to missing TMDB IDs."""
        return (self.kind, self.tmdb_id, self.imdb_id, self.tvdb_id,
                self.season, self.episode, self.title, self.series_title)


@dataclass(frozen=True, slots=True)
class Playback:
    state: str
    position: float | None
    duration: float | None
    item: InfuseItem | None
    artwork_url: str | None = None
    latency_ms: int | None = None

    @property
    def progress(self) -> float | None:
        if self.position is None or not self.duration or self.duration <= 0:
            return None
        return round(min(100.0, max(0.0, self.position * 100 / self.duration)), 1)

    @property
    def remaining_seconds(self) -> float | None:
        if self.duration is None or self.position is None:
            return None
        return max(0.0, self.duration - self.position)


def _nullable_str(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InfuseInvalidResponse(f"{field} must be a string or null")
    return value


def _nullable_number(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InfuseInvalidResponse(f"{field} must be a number or null")
    number = float(value)
    if not isfinite(number) or number < 0:
        raise InfuseInvalidResponse(f"{field} must be finite and non-negative")
    return number


def _nullable_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InfuseInvalidResponse(f"{field} must be a non-negative integer or null")
    return value


def parse_now_playing(data: Any) -> Playback:
    """Parse only fields documented by Firecore; ignore future extra fields."""
    if not isinstance(data, dict):
        raise InfuseInvalidResponse("response must be an object")
    state = data.get("state")
    if state not in ("playing", "paused", "idle"):
        raise InfuseInvalidResponse("unsupported playback state")
    position = _nullable_number(data.get("positionSeconds"), "positionSeconds")
    duration = _nullable_number(data.get("durationSeconds"), "durationSeconds")
    item_data = data.get("item")
    item: InfuseItem | None = None
    if item_data is not None:
        if not isinstance(item_data, dict):
            raise InfuseInvalidResponse("item must be an object or null")
        kind = item_data.get("kind")
        if kind not in ("movie", "episode"):
            raise InfuseInvalidResponse("item.kind must be movie or episode")
        item = InfuseItem(
            kind=kind,
            tmdb_id=_nullable_str(item_data.get("tmdbID"), "tmdbID"),
            imdb_id=_nullable_str(item_data.get("imdbID"), "imdbID"),
            tvdb_id=_nullable_str(item_data.get("tvdbID"), "tvdbID"),
            season=_nullable_int(item_data.get("season"), "season"),
            episode=_nullable_int(item_data.get("episode"), "episode"),
            title=_nullable_str(item_data.get("title"), "title"),
            series_title=_nullable_str(item_data.get("seriesTitle"), "seriesTitle"),
        )
    if state == "idle":
        return Playback("idle", None, None, None)
    return Playback(state, position, duration, item)
