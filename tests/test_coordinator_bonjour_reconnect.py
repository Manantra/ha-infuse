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
            self.last_update_success = True

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

    async def no_unicast(*_args, **_kwargs):
        return None

    monkeypatch.setattr(module, "async_resolve_unicast", no_unicast)

    async def no_ptr(*_args, **_kwargs):
        return ()

    monkeypatch.setattr(module, "async_discover_unicast_services", no_ptr)
    class CandidateClient:
        def __init__(self, session, host, port):
            self.endpoint = (host, port)

        async def get_now_playing(self):
            client = module._test_original_client
            client.calls.append(self.endpoint)
            if self.endpoint[1] not in client.reachable_ports:
                raise ConnectionRefusedError("not an Infuse endpoint")
            return model.Playback("idle", None, None, None)

    monkeypatch.setattr(module, "InfuseClient", CandidateClient)
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
    chosen = client or Client()
    module._test_original_client = chosen
    return module.InfuseCoordinator(hass or Hass(), entry, chosen, object(), 5)


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

    async def resolver(_hass, service, _host, *, fresh):
        assert fresh is False
        if service == "Other._infuse-np._tcp.local.":
            return ("192.168.178.207", NEW[1])
        return NEW

    monkeypatch.setattr(ha_zeroconf, "async_get_async_instance", get_ha_instance, raising=False)
    monkeypatch.setattr(module, "AsyncServiceBrowser", Browser)
    monkeypatch.setattr(module, "async_resolve_endpoint", resolver)

    class ValidationClient:
        def __init__(self, session, host, port):
            self.endpoint = host, port

        async def get_now_playing(self):
            return model.Playback("idle", None, None, None)

    monkeypatch.setattr(module, "InfuseClient", ValidationClient)
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


@pytest.mark.asyncio
async def test_recover_via_unicast_if_ha_cache_and_fresh_multicast_stay_old(coordinator_module, monkeypatch):
    """Regression for HAOS VM with stale port 59083 and working port 59085."""
    module, _ = coordinator_module
    mdns_queries = []
    directed_queries = []

    async def stale_multicast(_hass, _service, _host, *, fresh):
        mdns_queries.append(fresh)
        return OLD

    async def direct_apple_tv(service, host):
        directed_queries.append((service, host))
        return NEW

    monkeypatch.setattr(module, "async_resolve_endpoint", stale_multicast)
    monkeypatch.setattr(module, "async_resolve_unicast", direct_apple_tv)
    coordinator = make_coordinator(module)
    snapshot = await coordinator._async_update_data()
    assert snapshot.state == "idle"
    assert coordinator.client.calls == [OLD, NEW]
    assert coordinator.client.endpoint == NEW
    assert coordinator.endpoint_changes == 1
    assert coordinator.last_resolution == "direct_unicast"
    assert mdns_queries == [False, True]
    assert directed_queries == [(SERVICE, HOST)]
    assert (await coordinator._async_update_data()).state == "idle"
    assert len(directed_queries) == 1  # no extra UDP requests after recovery


@pytest.mark.asyncio
async def test_ignore_late_stale_bonjour_event_after_unicast_recovery(coordinator_module, monkeypatch):
    """Old HA mDNS data cannot replace the working unicast-recovered port."""
    module, _ = coordinator_module
    coordinator = make_coordinator(module)
    coordinator.client.endpoint = NEW
    refreshes = []

    async def old_cache(_hass, _service, _host, *, fresh):
        return OLD

    class ValidationClient:
        def __init__(self, session, host, port):
            self.endpoint = host, port

        async def get_now_playing(self):
            raise ConnectionRefusedError("old port is not answering")

    monkeypatch.setattr(module, "async_resolve_endpoint", old_cache)
    monkeypatch.setattr(module, "InfuseClient", ValidationClient)

    async def refresh():
        refreshes.append(True)

    coordinator.async_request_refresh = refresh
    await coordinator._async_apply_bonjour_update()
    assert coordinator.client.endpoint == NEW
    assert coordinator.endpoint_changes == 0
    assert refreshes == []

@pytest.mark.asyncio
async def test_manual_entry_recovers_after_foreground_by_targeted_ptr(coordinator_module, monkeypatch):
    """Manual installs have no original Bonjour name, but now recover automatically."""
    module, _ = coordinator_module
    manual = make_coordinator(module)
    manual.entry.data.pop("discovery_name")
    manual._service_name = None
    names = []
    directed = []

    async def ptr(host):
        names.append(host)
        return (SERVICE,)

    async def resolve(name, host):
        directed.append((name, host))
        return NEW

    monkeypatch.setattr(module, "async_discover_unicast_services", ptr)
    monkeypatch.setattr(module, "async_resolve_unicast", resolve)
    result = await manual._async_update_data()
    assert result.state == "idle"
    assert manual.client.endpoint == NEW
    assert manual._service_name == SERVICE
    assert manual.last_resolution == "direct_ptr_unicast"
    assert names == [HOST]
    assert directed == [(SERVICE, HOST)]
    assert manual.client.calls == [OLD, NEW]


@pytest.mark.asyncio
async def test_different_service_name_after_foreground_is_recovered(coordinator_module, monkeypatch):
    """If Bonjour re-registers a renamed service, accept only the same verified device."""
    module, _ = coordinator_module
    coordinator = make_coordinator(module)
    renamed = "Infuse re-opened._infuse-np._tcp.local."
    queried = []

    async def stale_endpoint(_hass, name, _host, *, fresh):
        queried.append((name, fresh))
        return OLD

    async def ptr(host):
        assert host == HOST
        return (renamed,)

    async def direct(name, host):
        assert host == HOST
        return NEW if name == renamed else OLD

    monkeypatch.setattr(module, "async_resolve_endpoint", stale_endpoint)
    monkeypatch.setattr(module, "async_discover_unicast_services", ptr)
    monkeypatch.setattr(module, "async_resolve_unicast", direct)
    assert (await coordinator._async_update_data()).state == "idle"
    assert coordinator.client.endpoint == NEW
    assert coordinator._service_name == renamed
    assert coordinator.last_resolution == "direct_ptr_unicast"
    assert queried == [(SERVICE, False), (SERVICE, True)]


@pytest.mark.asyncio
async def test_failed_dns_candidates_never_replace_current_endpoint(coordinator_module, monkeypatch):
    """Stale service records must not overwrite a valid saved endpoint."""
    module, _ = coordinator_module
    coordinator = make_coordinator(module)
    unreachable = (HOST, 59900)
    mdns = []

    async def stale(_hass, _service, _host, *, fresh):
        mdns.append(fresh)
        return unreachable

    async def unicast(_name, _host):
        return (HOST, 59901)

    monkeypatch.setattr(module, "async_resolve_endpoint", stale)
    monkeypatch.setattr(module, "async_resolve_unicast", unicast)
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.client.endpoint == OLD
    assert coordinator.endpoint_changes == 0
    assert coordinator.last_resolution == "no_reachable_new_endpoint"
    assert mdns == [False, True]
    assert coordinator.client.calls == [OLD, unreachable, (HOST, 59901)]


@pytest.mark.asyncio
async def test_bonjour_watcher_tracks_new_name_for_manual_device(coordinator_module, monkeypatch):
    module, ha_zeroconf = coordinator_module
    manual = make_coordinator(module)
    manual.entry.data.pop("discovery_name")
    manual._service_name = None
    registered = []

    class Browser:
        def __init__(self, instance, type_, handlers):
            assert type_ == module.SERVICE_TYPE
            registered.append(handlers[0])

    async def aiozc(_hass):
        return SimpleNamespace(zeroconf=object())

    async def resolve(_hass, _service, _host, *, fresh):
        return NEW

    monkeypatch.setattr(module, "AsyncServiceBrowser", Browser)
    monkeypatch.setattr(ha_zeroconf, "async_get_async_instance", aiozc, raising=False)
    monkeypatch.setattr(module, "async_resolve_endpoint", resolve)
    refreshes = []

    async def refresh():
        refreshes.append(manual.client.endpoint)

    manual.async_request_refresh = refresh
    await manual.async_start_bonjour_updates()
    assert len(registered) == 1
    registered[0](None, module.SERVICE_TYPE, SERVICE, ServiceStateChange.Added)
    await manual._bonjour_task
    assert manual.client.endpoint == NEW
    assert manual.last_resolution == "bonjour_event"
    assert manual._service_name == SERVICE
    assert refreshes == [NEW]


@pytest.mark.asyncio
async def test_renamed_service_from_another_ip_is_ignored(coordinator_module, monkeypatch):
    module, ha_zeroconf = coordinator_module
    coordinator = make_coordinator(module)

    async def different_ip(_hass, name, _host, *, fresh):
        return ("192.168.178.248", NEW[1])

    monkeypatch.setattr(module, "async_resolve_endpoint", different_ip)
    # Original instance name can move to another address (e.g. DHCP). A
    # different instance name on a different host may not take over this entry.
    coordinator._bonjour_pending.add("Other._infuse-np._tcp.local.")
    await coordinator._async_apply_bonjour_update()
    assert coordinator.client.endpoint == OLD
    assert coordinator._service_name == SERVICE


@pytest.mark.asyncio
async def test_bonjour_events_arriving_during_resolution_are_drained(coordinator_module, monkeypatch):
    module, ha_zeroconf = coordinator_module
    coordinator = make_coordinator(module)
    first = "Another._infuse-np._tcp.local."
    second = "Renamed._infuse-np._tcp.local."
    entered = asyncio.Event()
    release = asyncio.Event()
    resolved = []

    async def resolve(_hass, name, _host, *, fresh):
        resolved.append(name)
        if name == first:
            entered.set()
            await release.wait()
            return None
        return NEW

    monkeypatch.setattr(module, "async_resolve_endpoint", resolve)
    async def refresh():
        return None

    coordinator.async_request_refresh = refresh
    coordinator._bonjour_pending.add(first)
    task = asyncio.create_task(coordinator._async_apply_bonjour_update())
    await entered.wait()
    coordinator._bonjour_pending.add(second)
    release.set()
    await task
    assert resolved == [first, second]
    assert coordinator.client.endpoint == NEW
    assert coordinator._service_name == second

@pytest.mark.asyncio
async def test_existing_http_port_recovers_when_infuse_resumes(coordinator_module):
    """A resumed app may simply reopen its original port without Bonjour."""
    module, _ = coordinator_module
    coordinator = make_coordinator(module)
    coordinator.client.reachable_ports = {OLD[1]}
    coordinator.last_connection_error = "ConnectionRefusedError"
    coordinator.last_resolution = "no_reachable_new_endpoint"
    playback = await coordinator._async_update_data()
    assert playback.state == "idle"
    assert coordinator.client.endpoint == OLD
    assert coordinator.last_resolution == "original_port_recovered"
    assert coordinator.last_connection_error is None
    assert coordinator.last_successful_contact and coordinator.last_successful_contact.endswith("+00:00")
    assert coordinator.recovery_attempts == 0


@pytest.mark.asyncio
async def test_offline_diagnostics_report_error_and_throttled_retry(coordinator_module, monkeypatch):
    module, _ = coordinator_module
    coordinator = make_coordinator(module)
    coordinator.client.reachable_ports = set()
    calls = [100]
    monkeypatch.setattr(module, "monotonic", lambda: calls[0])

    async def stale(*args, **kwargs):
        return OLD

    monkeypatch.setattr(module, "async_resolve_endpoint", stale)
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.recovery_attempts == 1
    assert coordinator.last_connection_error == "ConnectionRefusedError"
    assert coordinator.last_successful_contact is None
    calls[0] += 5
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.recovery_attempts == 1  # avoid repeated DNS storms
    calls[0] += 20
    with pytest.raises(module.UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.recovery_attempts == 2


@pytest.mark.asyncio
async def test_same_port_bonjour_reannounce_refreshes_offline_entity(coordinator_module, monkeypatch):
    """Foregrounding with an unchanged port should still wake an offline entity."""
    module, _ = coordinator_module
    coordinator = make_coordinator(module)
    coordinator.last_update_success = False
    coordinator.client.reachable_ports = {OLD[1]}

    async def original_service(_hass, _name, _host, *, fresh):
        return OLD

    monkeypatch.setattr(module, "async_resolve_endpoint", original_service)
    refreshes = []

    async def refresh():
        refreshes.append(True)

    coordinator.async_request_refresh = refresh
    coordinator._bonjour_pending.add(SERVICE)
    await coordinator._async_apply_bonjour_update()
    assert coordinator.client.endpoint == OLD
    assert coordinator._service_name == SERVICE
    assert refreshes == [True]
    assert coordinator.last_resolution == "bonjour_event"
