"""Two same-household Infuse services must stay independent."""

import asyncio
import aiohttp
from aiohttp import web
import pytest
from conftest import api


@pytest.mark.asyncio
async def test_two_parallel_infuse_devices_have_separate_playback_states():
    async def start_server(movie, position):
        async def playback(_request):
            return web.json_response({
                "state": "playing", "positionSeconds": position,
                "durationSeconds": 300,
                "item": {"kind": "movie", "title": movie, "tmdbID": "100"},
            })
        app = web.Application()
        app.router.add_get("/nowplaying", playback)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        return runner, site._server.sockets[0].getsockname()[1]

    tv_runner, tv_port = await start_server("Living room", 80)
    pad_runner, pad_port = await start_server("iPad", 140)
    try:
        async with aiohttp.ClientSession() as session:
            tv, pad = await asyncio.gather(
                api.InfuseClient(session, "127.0.0.1", tv_port).get_now_playing(),
                api.InfuseClient(session, "127.0.0.1", pad_port).get_now_playing(),
            )
            assert tv.item.title == "Living room"
            assert pad.item.title == "iPad"
            assert tv.position == 80
            assert pad.position == 140
            assert tv.item.tmdb_id == pad.item.tmdb_id
    finally:
        await asyncio.gather(tv_runner.cleanup(), pad_runner.cleanup())
