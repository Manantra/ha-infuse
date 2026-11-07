"""Integration regression: app background -> port change -> automatic recovery."""

import asyncio
import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest
from zeroconf import ServiceStateChange

from conftest import PACKAGE_NAME, model

SERVICE = "Apple TV Infuse Player._infuse-np._tcp.local."
HOST = "192.168.178.133"
OLD = (HOST, 59083)
NEW = (HOST, 59085)


@pytest.fixture
def coordinator_module(monkeypatch):
    """Use tiny Home Assistant test doubles to execute the real coordinator."""
    homeassistant = ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    zeroconf = ModuleType("homeassistant.components.zeroconf")
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, hass, _logger, **_kwargs):
            self.hass = hass
            self.data = None

    update_coordinator.UpdateFailed = UpdateFailed
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    for name, module in (
        ("homeassistant", homeassistant),
        ("homeassistant.components", components),
        ("homeassistant.components.zeroconf", zeroconf),
        ("homeassistant.config_entries", config_entries),
        ("homeassistant.core", core),
        ("homeassistant.helpers", helpers),
        ("homeassistant.helpers.update_coordinator", update_coordinator),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    fullname = f"{PACKAGE_NAME}.coordinator"
    sys.modules.pop(fullname, None)
    module = importlib.import_module(fullname)
    yield module, zeroconf
    sys.modules.pop(fullname, None)


class Client:
    def __init__(self, reachable_ports=None):
        self.endpoint = OLD
        self.calls = []
        self.reachable_ports = set(reachable_ports or {NEW[1]})

    async def get_now_playing(self):
        self.calls.append(self.endpoint)
        if self.endpoint[1] not in self.reachable_ports:
            raise ConnectionRefusedError("Infuse moved to another port")
        return model.Playback("idle", None, None, None)

    def update_endpoint(self, host, port):
        self.endpoint = (host, port)


class Hass:
    def async_create_task(self, coroutine):
        return asyncio.create_task(coroutine)


def make_coordinator(module, hass=None, client=None):
    entry = SimpleNamespace(
        entry_id="test", title="Apple TV Infuse Player", options={},
        data={"discovery_name": SERVICE, "host": HOST, "port": OLD[1]},
    )
    return module.InfuseCoordinator(hass or Hass(), entry, client or Client(), object(), 5)


@pytest.mark.asyncio
async def test_reconnect_when_home_assistant_cache_stays_stale(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    calls = []

    async def resolver(_hass, _service, _host, *, fresh):
        calls.append(fresh)
        return NEW if fresh else OLD

    monkeypatch.setattr(module, "async_resolve_endpoint", resolver)
    coordinator = make_coordinator(module)
    result = await coordinator._async_update_data()
    assert result.state == "idle"
    assert coordinator.client.endpoint == NEW
    assert coordinator.client.calls == [OLD, NEW]
    assert calls == [False, True]
    assert coordinator.last_resolution == "fresh"
    assert coordinator.endpoint_changes == 1
    # Once the target port has been fixed, no additional mDNS queries are needed.
    assert (await coordinator._async_update_data()).state == "idle"
    assert calls == [False, True]


@pytest.mark.asyncio
async def test_offline_does_not_spin_repeated_bonjour_queries(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    calls = []
    ticks = [100]
    monkeypatch.setattr(module, "monotonic", lambda: ticks[0])

    async def resolver(_hass, _service, _host, *, fresh):
        calls.append(fresh)
        return OLD

    monkeypatch.setattr(module, "async_resolve_endpoint", resolver)
    coordinator = make_coordinator(module)
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert calls == [False, True]
    ticks[0] += 2
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert calls == [False, True]  # throttled within 15 seconds
    ticks[0] += 16
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert calls == [False, True, False, True]
    assert coordinator.last_resolution == "no_reachable_new_endpoint"


@pytest.mark.asyncio
async def test_bonjour_event_proactively_changes_port_and_refreshes_entity(coordinator_module, monkeypatch):
    module, ha_zeroconf = coordinator_module
    observed = []

    class Browser:
        def __init__(self, zeroconf, type_, handlers):
            assert type_ == module.SERVICE_TYPE
            self.handler = handlers[0]
            self.cancelled = False
            observed.append(self)

        async def async_cancel(self):
            self.cancelled = True

    async def get_ha_instance(_hass):
        return SimpleNamespace(zeroconf=object())

    async def resolver(_hass, _service, _host, *, fresh):
        assert fresh is False
        return NEW

    monkeypatch.setattr(ha_zeroconf, "async_get_async_instance", get_ha_instance, raising=False)
    monkeypatch.setattr(module, "AsyncServiceBrowser", Browser)
    monkeypatch.setattr(module, "async_resolve_endpoint", resolver)
    coordinator = make_coordinator(module)
    refreshes = []

    async def refresh():
        refreshes.append(coordinator.client.endpoint)

    coordinator.async_request_refresh = refresh
    await coordinator.async_start_bonjour_updates()
    assert len(observed) == 1
    browser = observed[0]
    # Unrelated devices and removal announcements must not change this player.
    browser.handler(None, module.SERVICE_TYPE, "Other._infuse-np._tcp.local.", ServiceStateChange.Updated)
    browser.handler(None, module.SERVICE_TYPE, SERVICE, ServiceStateChange.Removed)
    await asyncio.sleep(0)
    assert coordinator.client.endpoint == OLD
    browser.handler(None, module.SERVICE_TYPE, SERVICE, ServiceStateChange.Updated)
    await coordinator._bonjour_task
    assert coordinator.client.endpoint == NEW
    assert refreshes == [NEW]
    assert coordinator.endpoint_changes == 1
    assert coordinator.last_resolution == "bonjour_event"
    coordinator.async_stop_bonjour_updates()
    await asyncio.sleep(0)
    assert browser.cancelled is True
    browser.handler(None, module.SERVICE_TYPE, SERVICE, ServiceStateChange.Updated)
    await asyncio.sleep(0)
    assert refreshes == [NEW]


def test_setup_loads_entities_even_while_infuse_http_is_offline():
    """Do not require an initial HTTP response just to start the mDNS watcher."""
    import ast
    from pathlib import Path

    init = Path(__file__).resolve().parents[1] / "custom_components/infuse/__init__.py"
    tree = ast.parse(init.read_text())
    setup = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry")
    calls = [node for node in ast.walk(setup) if isinstance(node, ast.Call)]
    methods = {call.func.attr for call in calls if isinstance(call.func, ast.Attribute)}
    assert "async_refresh" in methods
    assert "async_config_entry_first_refresh" not in methods
    assert "async_start_bonjour_updates" in methods
    assert "async_forward_entry_setups" in methods
