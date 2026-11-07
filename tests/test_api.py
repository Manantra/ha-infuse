"""HTTP contract tests with a simulated local Firecore endpoint."""

import aiohttp
from aiohttp import web
import pytest
from conftest import api, model


@pytest.mark.asyncio
async def test_get_nowplaying_from_local_http_server():
    async def now_playing(_request):
        return web.json_response({
            "state": "playing", "positionSeconds": 12.25,
            "durationSeconds": 120, "item": {"kind": "movie", "title": "Example"},
        })
    app = web.Application()
    app.router.add_get("/nowplaying", now_playing)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            result = await api.InfuseClient(session, "127.0.0.1", port).get_now_playing()
            assert result.item.title == "Example"
            assert result.position == 12.25
            assert result.latency_ms >= 0
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_invalid_payload_is_rejected():
    async def bad(_request):
        return web.json_response({"state": "unsupported"})
    app = web.Application()
    app.router.add_get("/nowplaying", bad)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        async with aiohttp.ClientSession() as session:
            with pytest.raises(model.InfuseInvalidResponse):
                await api.InfuseClient(session, "127.0.0.1", port).get_now_playing()
    finally:
        await runner.cleanup()
