"""Real HA smoke: integration setup and entity lifecycle with a mocked Infuse API."""

from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import aiohttp
import pytest
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import STATE_IDLE, STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.infuse.model import Playback
from custom_components.infuse.diagnostics import async_get_config_entry_diagnostics


@pytest.mark.asyncio
async def test_real_home_assistant_setup_and_unload_without_device(hass):
    """No Apple TV needed; use real config-entry and entity machinery."""
    entry = MockConfigEntry(
        domain="infuse", title="Infuse Test TV",
        unique_id="manual:127.0.0.1:59999",
        data={"host": "127.0.0.1", "port": 59999},
        options={},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.infuse.api.InfuseClient.get_now_playing",
            new_callable=AsyncMock, return_value=Playback("idle", None, None, None),
        ),
        patch(
            "custom_components.infuse.coordinator.InfuseCoordinator.async_start_bonjour_updates",
            new_callable=AsyncMock,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinators = hass.data.get("infuse", {})
        assert entry.entry_id in coordinators
        assert coordinators[entry.entry_id].last_update_success is True
        registry = er.async_get(hass)
        entity_ids = [
            entity.entity_id for entity in registry.entities.values()
            if entity.config_entry_id == entry.entry_id
        ]
        assert any(eid.startswith("media_player.") for eid in entity_ids)
        assert any(eid.startswith("sensor.") for eid in entity_ids)
        for entity_id in entity_ids:
            state = hass.states.get(entity_id)
            if state is not None and entity_id.startswith("media_player."):
                assert state.state == STATE_IDLE
        # These checks use real Lovelace resource storage, not a mocked list.
        lovelace = hass.data["lovelace"]
        await lovelace.resources.async_get_info()
        resource_urls = [resource["url"] for resource in lovelace.resources.async_items()]
        assert any(url.startswith("/api/infuse/cards/infuse-dashboard-cards.js?v=") for url in resource_urls)
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.entry_id not in hass.data.get("infuse", {})


@pytest.mark.asyncio
async def test_real_home_assistant_starts_offline_and_preserves_entities(hass):
    """Infuse being suspended cannot prevent the config entry loading."""
    entry = MockConfigEntry(
        domain="infuse", title="Offline TV", unique_id="manual:127.0.0.1:59998",
        data={"host": "127.0.0.1", "port": 59998}, options={},
    )
    entry.add_to_hass(hass)
    with (
        patch("custom_components.infuse.api.InfuseClient.get_now_playing",
              new_callable=AsyncMock, side_effect=aiohttp.ClientConnectionError("offline")),
        patch("custom_components.infuse.coordinator.InfuseCoordinator.async_start_bonjour_updates",
              new_callable=AsyncMock),
        patch("custom_components.infuse.coordinator.async_discover_unicast_services",
              new_callable=AsyncMock, return_value=()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.data["infuse"][entry.entry_id].last_update_success is False
        registry = er.async_get(hass)
        ids = [entity.entity_id for entity in registry.entities.values()
               if entity.config_entry_id == entry.entry_id and entity.domain == "media_player"]
        assert len(ids) == 1
        assert hass.states.get(ids[0]).state == STATE_UNAVAILABLE
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_real_home_assistant_reconfigure_preserves_device_and_options(hass):
    """Run the actual HA flow manager to catch schema/reload incompatibilities."""
    entry = MockConfigEntry(
        domain="infuse", title="Reconfigurable TV", unique_id="manual:127.0.0.1:59800",
        data={"host": "127.0.0.1", "port": 59800},
        options={"poll_interval": 10, "tmdb_token": "private-token"},
    )
    entry.add_to_hass(hass)
    with (
        patch("custom_components.infuse.api.InfuseClient.get_now_playing",
              new_callable=AsyncMock, return_value=Playback("idle", None, None, None)),
        patch("custom_components.infuse.coordinator.InfuseCoordinator.async_start_bonjour_updates",
              new_callable=AsyncMock),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        before = {
            entity.entity_id for entity in registry.entities.values()
            if entity.config_entry_id == entry.entry_id
        }
        form = await hass.config_entries.flow.async_init(
            "infuse", context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        assert form["type"] == "form"
        assert form["step_id"] == "reconfigure"
        # A second entry can be recovered on a port not present in its
        # persisted data. Reconfigure must reject its active HTTP endpoint.
        hass.data["infuse"]["other-apple-tv"] = SimpleNamespace(
            client=SimpleNamespace(endpoint=("127.0.0.1", 59801)),
        )
        duplicate = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"host": "127.0.0.1", "port": 59801},
        )
        assert duplicate["type"] == "form"
        assert duplicate["errors"]["base"] == "already_configured"
        assert entry.data["port"] == 59800
        hass.data["infuse"].pop("other-apple-tv")
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"host": "127.0.0.1", "port": 59801},
        )
        assert result["type"] == "abort"
        assert result["reason"] == "reconfigure_successful"
        await hass.async_block_till_done()
        assert entry.data["port"] == 59801
        assert entry.options["tmdb_token"] == "private-token"
        diagnostics = await async_get_config_entry_diagnostics(hass, entry)
        assert diagnostics["integration_version"] == "0.2.15"
        assert "private-token" not in str(diagnostics)
        after = {
            entity.entity_id for entity in registry.entities.values()
            if entity.config_entry_id == entry.entry_id
        }
        assert before == after
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_real_home_assistant_exposes_playback_before_tmdb_finishes(hass):
    """Actual coordinator/HA entities stay responsive while artwork is pending."""
    import asyncio
    from custom_components.infuse.model import InfuseItem

    entry = MockConfigEntry(
        domain="infuse", title="Poster TV", unique_id="manual:127.0.0.1:59802",
        data={"host": "127.0.0.1", "port": 59802},
        options={"tmdb_token": "private-token"},
    )
    entry.add_to_hass(hass)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_tmdb(_session, _token, _item, _language):
        started.set()
        await release.wait()
        return "https://image.tmdb.org/t/p/w500/real-ha.jpg"

    with (
        patch("custom_components.infuse.api.InfuseClient.get_now_playing",
              new_callable=AsyncMock,
              return_value=Playback("playing", 12, 120,
                                    InfuseItem(kind="movie", tmdb_id="123", title="Demo"))),
        patch("custom_components.infuse.coordinator.InfuseCoordinator.async_start_bonjour_updates",
              new_callable=AsyncMock),
        patch("custom_components.infuse.coordinator.fetch_tmdb_artwork",
              side_effect=slow_tmdb),
    ):
        # This must complete even though poster metadata is still blocked.
        assert await asyncio.wait_for(hass.config_entries.async_setup(entry.entry_id), timeout=3)
        assert hass.data["infuse"][entry.entry_id].data.state == "playing"
        await asyncio.wait_for(started.wait(), timeout=3)
        assert not release.is_set()
        release.set()
        await hass.async_block_till_done()
        snapshot = hass.data["infuse"][entry.entry_id].data
        assert snapshot.artwork_url.endswith("/real-ha.jpg")
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_real_home_assistant_immediate_artwork_lookup_does_not_block_future_lookups(hass):
    """Eagerly completed tasks must not occupy one of the four lookup slots."""
    from custom_components.infuse.model import InfuseItem

    entry = MockConfigEntry(
        domain="infuse", title="Eager Poster TV", unique_id="manual:127.0.0.1:59803",
        data={"host": "127.0.0.1", "port": 59803},
        options={"tmdb_token": "private-token"},
    )
    entry.add_to_hass(hass)
    responses = AsyncMock(
        return_value=Playback("playing", 10, 200,
                              InfuseItem(kind="movie", tmdb_id="nondecimal-0", title="Demo 0")),
    )

    async def immediate_no_artwork(*_args, **_kwargs):
        return None  # The coroutine never suspends.

    with (
        patch("custom_components.infuse.api.InfuseClient.get_now_playing", responses),
        patch("custom_components.infuse.coordinator.InfuseCoordinator.async_start_bonjour_updates",
              new_callable=AsyncMock),
        patch("custom_components.infuse.coordinator.fetch_tmdb_artwork",
              side_effect=immediate_no_artwork) as tmdb,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data["infuse"][entry.entry_id]
        for n in range(1, 7):
            responses.return_value = Playback(
                "playing", 10, 200,
                InfuseItem(kind="movie", tmdb_id=f"nondecimal-{n}", title=f"Demo {n}"),
            )
            await coordinator.async_refresh()
            await hass.async_block_till_done()
            assert coordinator._artwork_tasks == {}
        assert tmdb.call_count == 7  # Six extra media titles all fetched.
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.asyncio
async def test_real_ha_zeroconf_confirmation_replaces_stale_port(hass):
    """A verified direct DNS-SD SRV record beats the stale discovery port."""
    from custom_components.infuse.config_flow import InfuseConfigFlow

    flow = InfuseConfigFlow()
    flow.hass = hass
    flow.context = {}
    flow._discovered = {
        "host": "192.168.1.50",
        "port": 59095,
        "name": "Infuse Apple TV",
        "discovery_name": "Infuse Apple TV._infuse-np._tcp.local.",
    }
    seen_ports = []

    async def simulated_api(client):
        seen_ports.append(client.endpoint[1])
        if client.endpoint[1] != 59096:
            raise aiohttp.ClientConnectionError("cached port is closed")
        return Playback("idle", None, None, None)

    with (
        patch("custom_components.infuse.config_flow.async_resolve_unicast",
              new_callable=AsyncMock, return_value=("192.168.1.50", 59096)) as direct,
        patch("custom_components.infuse.config_flow.async_resolve_endpoint",
              new_callable=AsyncMock, return_value=("192.168.1.50", 59095)) as cached,
        patch("custom_components.infuse.api.InfuseClient.get_now_playing", simulated_api),
    ):
        preview = await flow.async_step_confirm()
        assert preview["description_placeholders"]["port"] == "59096"
        result = await flow.async_step_confirm({})
        assert result["type"] == "create_entry"
        assert result["data"]["port"] == 59096
        assert result["options"] == {}
        assert seen_ports == [59096]
        assert direct.await_count == 2
        cached.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_ha_confirmation_preserves_initial_port_for_fallback(hass):
    """Even after preview displays stale DNS, confirm retries original HTTP."""
    from custom_components.infuse.config_flow import InfuseConfigFlow

    flow = InfuseConfigFlow()
    flow.hass = hass
    flow.context = {}
    flow._discovered = {
        "host": "192.168.1.50", "port": 59095,
        "name": "Infuse Apple TV",
        "discovery_name": "Infuse Apple TV._infuse-np._tcp.local.",
    }
    probed = []

    async def serve_original(client):
        probed.append(client.endpoint[1])
        if client.endpoint[1] == 59096:
            raise aiohttp.ClientConnectionError("new SRV is stale")
        if client.endpoint[1] == 59095:
            return Playback("idle", None, None, None)
        raise AssertionError("Unknown port attempted")

    with (
        patch("custom_components.infuse.config_flow.async_resolve_unicast",
              new_callable=AsyncMock, return_value=("192.168.1.50", 59096)),
        patch("custom_components.infuse.config_flow.async_resolve_endpoint",
              new_callable=AsyncMock, return_value=None),
        patch("custom_components.infuse.api.InfuseClient.get_now_playing", serve_original),
    ):
        preview = await flow.async_step_confirm()
        assert preview["description_placeholders"]["port"] == "59096"
        result = await flow.async_step_confirm({})
        assert result["type"] == "create_entry"
        assert result["data"]["port"] == 59095
        assert probed == [59096, 59095]
