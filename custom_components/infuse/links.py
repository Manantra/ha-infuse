"""Firecore's local-to-device URL scheme helpers, not HTTP remote control."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote, urlencode, urlsplit


def _validated_uri(value: str) -> str:
    """Require an absolute URI; reject script/data URI injection."""
    if not isinstance(value, str) or len(value) > 8192 or any(ord(c) < 32 for c in value):
        raise ValueError("URI must be a non-empty, printable string (max 8192 chars)")
    parsed = urlsplit(value)
    if not parsed.scheme or parsed.scheme.lower() in ("javascript", "data", "file"):
        raise ValueError("URI needs a supported absolute scheme")
    return value


def library_link(
    media_type: str, tmdb_id: int | str, *, season: int | None = None,
    episode: int | None = None, autoplay: bool = False,
) -> str:
    """Create one of Firecore's documented TMDB deep links."""
    if media_type not in ("movie", "series", "season", "episode"):
        raise ValueError("media_type must be movie, series, season, or episode")
    if not str(tmdb_id).isdigit() or int(tmdb_id) <= 0:
        raise ValueError("TMDB ID must be a positive integer")
    identifier = str(int(tmdb_id))
    if media_type in ("season", "episode"):
        if season is None or isinstance(season, bool) or not isinstance(season, int) or season < 0:
            raise ValueError("season is required and must be non-negative")
        identifier += f"-{season}"
    if media_type == "episode":
        if episode is None or isinstance(episode, bool) or not isinstance(episode, int) or episode <= 0:
            raise ValueError("episode is required and must be positive")
        identifier += f"-{episode}"
    category = "movie" if media_type == "movie" else "series"
    return f"infuse://{category}/{identifier}" + ("?play" if autoplay else "")


def stream_link(
    action: str,
    streams: list[dict[str, Any]],
    *,
    download: bool = False,
    x_success: str | None = None,
    x_error: str | None = None,
) -> str:
    """Build the documented x-callback-url play/save request."""
    if action not in ("play", "save"):
        raise ValueError("action must be play or save")
    if not isinstance(streams, list) or not (1 <= len(streams) <= 50):
        raise ValueError("streams must be a non-empty list of up to 50 URLs")
    if action == "play" and download:
        raise ValueError("download is supported only with the save action")
    params: list[tuple[str, str]] = []
    for stream in streams:
        if not isinstance(stream, dict) or "url" not in stream:
            raise ValueError("every stream needs a url")
        params.append(("url", _validated_uri(stream["url"])))
        if "position" in stream and stream["position"] is not None:
            seconds = stream["position"]
            if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
                raise ValueError("position must be an integer number of seconds >= 0")
            if action == "save":
                raise ValueError("position is supported only with play")
            params.append(("position", str(seconds)))
        if stream.get("filename"):
            params.append(("filename", str(stream["filename"])))
        if stream.get("subtitle"):
            params.append(("sub", _validated_uri(stream["subtitle"])))
    if action == "save":
        params.append(("download", "1" if download else "0"))
    if x_success:
        params.append(("x-success", _validated_uri(x_success)))
    if x_error:
        params.append(("x-error", _validated_uri(x_error)))
    return f"infuse://x-callback-url/{action}?" + urlencode(params, quote_via=quote)
