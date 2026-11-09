"""Regression tests: optional TMDB must never block playback or leak stale art."""

import asyncio
from collections import OrderedDict
from types import SimpleNamespace

import aiohttp
import pytest

from conftest import model
from test_coordinator_bonjour_reconnect import Hass, Client, make_coordinator, coordinator_module


def media(item_id: str, *, state: str = "playing"):
    return model.Playback(
        state, 5, 100,
        model.InfuseItem(kind="movie", tmdb_id=item_id, title=f"Movie {item_id}"),
    )


class MediaClient(Client):
    def __init__(self, item_id: str = "101"):
        super().__init__()
        self.now = media(item_id)

    async def get_now_playing(self):
        self.calls.append(self.endpoint)
        return self.now


def setup_artwork_coordinator(module, client=None):
    hass = Hass()
    events = []
    hass.bus = SimpleNamespace(async_fire=lambda name, data: events.append((name, data)))
    coordinator = make_coordinator(module, hass=hass, client=client or MediaClient())
    coordinator.entry.options = {"tmdb_token": "fake-secret-token", "language": "de-DE"}
    applied = []

    def update(snapshot):
        coordinator.data = snapshot
        applied.append(snapshot)

    coordinator.async_set_updated_data = update
    return coordinator, events, applied


@pytest.mark.asyncio
async def test_playback_event_is_immediate_while_tmdb_is_blocked(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    coordinator, events, applied = setup_artwork_coordinator(module)
    coordinator.data = model.Playback("idle", None, None, None)
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_tmdb(_session, _token, _item, _language):
        started.set()
        await release.wait()
        return "https://image.tmdb.org/t/p/w500/101.jpg"

    monkeypatch.setattr(module, "fetch_tmdb_artwork", slow_tmdb)
    snapshot = await asyncio.wait_for(coordinator._async_update_data(), timeout=0.5)
    assert snapshot.state == "playing"
    assert snapshot.artwork_url is None
    assert [name for name, _ in events] == ["infuse_media_changed", "infuse_state_changed", "infuse_playback_started"]
    coordinator.data = snapshot  # HA commits the coordinator update after the poll.
    assert len(coordinator._artwork_tasks) == 1
    await started.wait()
    assert not release.is_set()  # Playback returned while TMDB is still waiting.
    task = next(iter(coordinator._artwork_tasks.values()))
    release.set()
    await task
    assert len(events) == 3  # Artwork must not re-fire playback automation.
    assert len(applied) == 1
    assert applied[0].artwork_url.endswith("/101.jpg")
    assert applied[0].item.identity == snapshot.item.identity
    assert not coordinator._artwork_tasks
    assert (await coordinator._async_update_data()).artwork_url.endswith("/101.jpg")


@pytest.mark.asyncio
async def test_old_tmdb_response_cannot_replace_new_media(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    client = MediaClient("101")
    coordinator, _, applied = setup_artwork_coordinator(module, client)
    release_old = asyncio.Event()

    async def tmdb(_session, _token, item, _language):
        if item.tmdb_id == "101":
            await release_old.wait()
        return f"https://image.tmdb.org/t/p/w500/{item.tmdb_id}.jpg"

    monkeypatch.setattr(module, "fetch_tmdb_artwork", tmdb)
    initial = await coordinator._async_update_data()
    coordinator.data = initial
    old_task = next(iter(coordinator._artwork_tasks.values()))
    await asyncio.sleep(0)
    client.now = media("202")
    newer = await coordinator._async_update_data()
    coordinator.data = newer
    new_task = coordinator._artwork_tasks[("movie", "202", "de-DE")]
    await new_task
    assert coordinator.data.artwork_url.endswith("/202.jpg")
    release_old.set()
    await old_task
    assert coordinator.data.item.tmdb_id == "202"
    assert coordinator.data.artwork_url.endswith("/202.jpg")
    assert len(applied) == 1
    # The old cover is safely cached for later re-selection, not applied now.
    client.now = media("101")
    back = await coordinator._async_update_data()
    assert back.artwork_url.endswith("/101.jpg")


@pytest.mark.asyncio
async def test_tmdb_failure_is_negative_cached_without_breaking_playback(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    coordinator, _, applied = setup_artwork_coordinator(module)
    ticks, calls = [100.0], []
    monkeypatch.setattr(module, "monotonic", lambda: ticks[0])

    async def failing(_session, _token, item, _language):
        calls.append(item.tmdb_id)
        raise aiohttp.ClientError("TMDB is unavailable")

    monkeypatch.setattr(module, "fetch_tmdb_artwork", failing)
    initial = await coordinator._async_update_data()
    coordinator.data = initial
    task = next(iter(coordinator._artwork_tasks.values()))
    await task
    assert calls == ["101"]
    assert applied == []
    assert (await coordinator._async_update_data()).state == "playing"
    assert calls == ["101"]
    assert len(coordinator._artwork_tasks) == 0
    ticks[0] += 301
    await coordinator._async_update_data()
    await next(iter(coordinator._artwork_tasks.values()))
    assert calls == ["101", "101"]


@pytest.mark.asyncio
async def test_artwork_background_tasks_are_bounded_and_cancelled_on_unload(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    client = MediaClient()
    coordinator, _, _ = setup_artwork_coordinator(module, client)
    started = []
    gate = asyncio.Event()

    async def blocked(_session, _token, item, _language):
        started.append(item.tmdb_id)
        await gate.wait()
        return "https://example.com/poster.jpg"

    monkeypatch.setattr(module, "fetch_tmdb_artwork", blocked)
    for i in range(5):
        client.now = media(str(i))
        coordinator.data = await coordinator._async_update_data()
    tasks = list(coordinator._artwork_tasks.values())
    assert len(tasks) == 4
    await asyncio.sleep(0)
    assert len(started) == 4
    coordinator.async_stop_bonjour_updates()
    await asyncio.gather(*tasks, return_exceptions=True)
    assert all(task.cancelled() for task in tasks)
    assert not coordinator._artwork_tasks
    assert not coordinator._artwork_cache


@pytest.mark.asyncio
async def test_artwork_cache_stays_bounded_to_most_recent_items(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    coordinator, _, _ = setup_artwork_coordinator(module)
    coordinator._artwork_cache = OrderedDict(
        (("movie", str(i), "de-DE"), (999999999.0, "http://example.com/old"))
        for i in range(64)
    )

    async def tmdb(_session, _token, _item, _language):
        return "http://example.com/new"

    monkeypatch.setattr(module, "fetch_tmdb_artwork", tmdb)
    coordinator.client.now = media("new")
    coordinator.data = await coordinator._async_update_data()
    await next(iter(coordinator._artwork_tasks.values()))
    assert len(coordinator._artwork_cache) == 64
    assert ("movie", "0", "de-DE") not in coordinator._artwork_cache
    assert ("movie", "new", "de-DE") in coordinator._artwork_cache


@pytest.mark.asyncio
async def test_artwork_does_not_resurrect_unavailable_entity(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    coordinator, _, applied = setup_artwork_coordinator(module)
    gate = asyncio.Event()

    async def tmdb(_session, _token, _item, _language):
        await gate.wait()
        return "http://example.com/poster.jpg"

    monkeypatch.setattr(module, "fetch_tmdb_artwork", tmdb)
    coordinator.data = await coordinator._async_update_data()
    task = next(iter(coordinator._artwork_tasks.values()))
    coordinator.last_update_success = False
    gate.set()
    await task
    assert applied == []
    assert ("movie", "101", "de-DE") in coordinator._artwork_cache


@pytest.mark.asyncio
async def test_eager_completed_tasks_never_exhaust_tmdb_slots(coordinator_module, monkeypatch):
    """Copilot #4516937685: eager tasks may finish before task registration."""
    module, _ = coordinator_module
    client = MediaClient("bad-0")
    coordinator, _, _ = setup_artwork_coordinator(module, client)
    calls = []
    ticks = [100.0]
    monkeypatch.setattr(module, "monotonic", lambda: ticks[0])

    async def immediate_failure(_session, _token, item, _language):
        calls.append(item.tmdb_id)
        return None  # No suspension: HA can eagerly finish this coroutine.

    monkeypatch.setattr(module, "fetch_tmdb_artwork", immediate_failure)
    coordinator.hass.async_create_task = lambda coro: asyncio.Task(coro, loop=asyncio.get_running_loop(), eager_start=True)

    for n in range(8):
        client.now = media(f"bad-{n}")
        coordinator.data = await coordinator._async_update_data()
        assert coordinator._artwork_tasks == {}
    assert calls == [f"bad-{n}" for n in range(8)]
    assert len(coordinator._artwork_cache) == 8

    # The cached negative result must be retryable after its TTL expires.
    ticks[0] += 301
    client.now = media("bad-0")
    coordinator.data = await coordinator._async_update_data()
    assert calls.count("bad-0") == 2
    assert coordinator._artwork_tasks == {}


@pytest.mark.asyncio
async def test_eager_immediately_raising_lookup_does_not_poison_task_registry(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    client = MediaClient("not-decimal")
    coordinator, _, _ = setup_artwork_coordinator(module, client)
    errors = []

    async def immediate_error(_session, _token, _item, _language):
        raise aiohttp.ClientError("TMDB rejected ID")

    monkeypatch.setattr(module, "fetch_tmdb_artwork", immediate_error)
    coordinator.hass.async_create_task = lambda coro: asyncio.Task(coro, loop=asyncio.get_running_loop(), eager_start=True)
    for n in range(6):
        client.now = media(f"not-decimal-{n}")
        coordinator.data = await coordinator._async_update_data()
        assert not coordinator._artwork_tasks
    assert len(coordinator._artwork_cache) == 6


@pytest.mark.asyncio
async def test_completed_callback_cannot_delete_a_newer_lookup(coordinator_module):
    module, _ = coordinator_module
    coordinator, _, _ = setup_artwork_coordinator(module)
    key = ("movie", "101", "de-DE")
    loop = asyncio.get_running_loop()
    old_task = loop.create_future()
    new_task = loop.create_future()
    coordinator._artwork_tasks[key] = new_task
    coordinator._remove_artwork_task(key, old_task)
    assert coordinator._artwork_tasks[key] is new_task
    coordinator._remove_artwork_task(key, new_task)
    assert key not in coordinator._artwork_tasks
    old_task.cancel()
    new_task.cancel()
