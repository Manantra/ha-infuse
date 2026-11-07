"""Optional, privacy-conscious TMDB cover enrichment."""

from __future__ import annotations

import aiohttp

from .model import InfuseItem


async def fetch_tmdb_artwork(
    session: aiohttp.ClientSession, token: str, item: InfuseItem, language: str,
) -> str | None:
    """Return a cover URL, or None if TMDB does not know the item."""
    if not item.tmdb_id or not item.tmdb_id.isdecimal():
        return None
    media_type = "movie" if item.kind == "movie" else "tv"
    url = f"https://api.themoviedb.org/3/{media_type}/{int(item.tmdb_id)}"
    async with session.get(
        url,
        params={"language": language},
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=aiohttp.ClientTimeout(total=5),
    ) as response:
        response.raise_for_status()
        data = await response.json()
    path = data.get("poster_path") if isinstance(data, dict) else None
    if not isinstance(path, str) or not path.startswith("/") or ".." in path:
        return None
    return "https://image.tmdb.org/t/p/w500" + path
