"""Resolve the newest Bonjour port, even if HA still has a stale discovery."""

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


@pytest.mark.asyncio
async def test_active_zeroconf_lookup_reads_updated_port(monkeypatch):
    class TemporaryZeroconf:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def async_get_service_info(self, service_type, name, timeout):
            assert service_type == discovery.SERVICE_TYPE
            assert name == SERVICE
            assert timeout == 3000
            return FakeInfo(59083, ["192.168.178.133"])

    monkeypatch.setattr(discovery, "AsyncZeroconf", TemporaryZeroconf)
    actual = await discovery.async_resolve_endpoint(None, SERVICE, "192.168.178.133", fresh=True)
    assert actual == ("192.168.178.133", 59083)


@pytest.mark.asyncio
async def test_missing_service_does_not_invent_a_port(monkeypatch):
    class MissingZeroconf:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def async_get_service_info(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(discovery, "AsyncZeroconf", MissingZeroconf)
    assert await discovery.async_resolve_endpoint(None, SERVICE, fresh=True) is None
    assert await discovery.async_resolve_endpoint(None, "not-an-infuse-service", fresh=True) is None


@pytest.mark.asyncio
async def test_discovery_errors_do_not_crash_setup(monkeypatch):
    class BrokenZeroconf:
        async def __aenter__(self):
            raise OSError("no multicast interface")

        async def __aexit__(self, *_):
            return None

    monkeypatch.setattr(discovery, "AsyncZeroconf", BrokenZeroconf)
    assert await discovery.async_resolve_endpoint(None, SERVICE, fresh=True) is None
