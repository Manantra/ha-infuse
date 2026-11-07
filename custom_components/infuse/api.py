"""Lightweight async client for Firecore's read-only LAN API."""

from __future__ import annotations

from dataclasses import replace
from time import monotonic

import aiohttp
from yarl import URL

from .model import Playback, parse_now_playing


class InfuseClient:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int) -> None:
        self._url = URL.build(scheme="http", host=host, port=port, path="/nowplaying")
        self._session = session

    async def get_now_playing(self) -> Playback:
        start = monotonic()
        timeout = aiohttp.ClientTimeout(total=5)
        async with self._session.get(self._url, timeout=timeout, headers={"Connection": "close"}) as response:
            response.raise_for_status()
            data = await response.json(content_type=None)
        playback = parse_now_playing(data)
        return replace(playback, latency_ms=round((monotonic() - start) * 1000))
