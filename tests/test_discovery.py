"""Resolve the newest Bonjour port, even if HA still has a stale discovery."""

import sys
from types import ModuleType

import pytest

from conftest import discovery

SERVICE = "Apple TV Infuse Player._infuse-np._tcp.local."


class FakeInfo:
    def __init__(self, port: int, ips: list[str]):
        self.port = port
        self.ips = ips

    def parsed_addresses(self):
        return self.ips


def test_discovered_address_prefers_existing_ipv4():
    info = FakeInfo(59083, ["192.168.178.133", "fe80::1"])
    assert discovery._endpoint_from_service(info, "192.168.178.133") == ("192.168.178.133", 59083)
    assert discovery._endpoint_from_service(info, "192.168.178.25") == ("192.168.178.133", 59083)


def test_unresolvable_or_invalid_service_rejected():
    assert discovery._endpoint_from_service(FakeInfo(0, ["192.168.178.133"]), None) is None
    assert discovery._endpoint_from_service(FakeInfo(59083, []), None) is None


class SharedZeroconf:
    """Stand-in for Home Assistant's shared HaAsyncZeroconf."""

    result = None
    error = None

    def __init__(self):
        self.lookups = []

    async def async_get_service_info(self, service_type, name, timeout):
        self.lookups.append((service_type, name, timeout))
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def shared_zeroconf(monkeypatch):
    """Serve a SharedZeroconf through homeassistant.components.zeroconf."""
    shared = SharedZeroconf()

    async def async_get_async_instance(_hass):
        return shared

    ha_zeroconf = ModuleType("homeassistant.components.zeroconf")
    ha_zeroconf.async_get_async_instance = async_get_async_instance
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    components.zeroconf = ha_zeroconf
    monkeypatch.setitem(sys.modules, "homeassistant", ModuleType("homeassistant"))
    monkeypatch.setitem(sys.modules, "homeassistant.components", components)
    monkeypatch.setitem(sys.modules, "homeassistant.components.zeroconf", ha_zeroconf)
    return shared


@pytest.mark.asyncio
@pytest.mark.parametrize("fresh", [False, True])
async def test_lookup_reads_updated_port_from_shared_zeroconf(shared_zeroconf, fresh):
    shared_zeroconf.result = FakeInfo(59083, ["192.168.178.133"])
    actual = await discovery.async_resolve_endpoint(None, SERVICE, "192.168.178.133", fresh=fresh)
    assert actual == ("192.168.178.133", 59083)
    # Never a private resolver: closing one inside HA stops the shared instance.
    assert shared_zeroconf.lookups == [(discovery.SERVICE_TYPE, SERVICE, 3000)]


@pytest.mark.asyncio
async def test_missing_service_does_not_invent_a_port(shared_zeroconf):
    assert await discovery.async_resolve_endpoint(None, SERVICE, fresh=True) is None
    assert await discovery.async_resolve_endpoint(None, "not-an-infuse-service", fresh=True) is None


@pytest.mark.asyncio
async def test_discovery_errors_do_not_crash_setup(shared_zeroconf):
    shared_zeroconf.error = OSError("no multicast interface")
    assert await discovery.async_resolve_endpoint(None, SERVICE, fresh=True) is None
