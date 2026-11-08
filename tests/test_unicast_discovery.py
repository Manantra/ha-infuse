"""DNS-SD unicast packet parsing and safety boundaries (no network access)."""

import struct

import pytest

from conftest import PACKAGE_NAME
from importlib import import_module

unicast = import_module(f"{PACKAGE_NAME}.unicast_discovery")
NAME = "Apple TV Infuse Player._infuse-np._tcp.local."
TARGET = b"\x0aWohnzimmer\x05local\x00"


def reply(port=59086, *, rr_name=None, flags=0x8400, answer_type=33, rdata=None):
    """RFC 1035 DNS message with compressed answer-name pointer."""
    question = unicast._encode_service_name(NAME) + struct.pack("!HH", 33, 0x8001)
    rdata = rdata if rdata is not None else struct.pack("!HHH", 0, 0, port) + TARGET
    answer = (rr_name if rr_name is not None else b"\xc0\x0c") + struct.pack(
        "!HHIH", answer_type, 1, 120, len(rdata)
    ) + rdata
    return struct.pack("!HHHHHH", 0, flags, 1, 1, 0, 0) + question + answer


def test_parse_realistic_srv_reply():
    assert unicast.parse_srv_port(reply(), NAME) == 59086


def test_reject_wrong_service_or_non_srv_answer():
    assert unicast.parse_srv_port(reply(), "Other._infuse-np._tcp.local.") is None
    assert unicast.parse_srv_port(reply(answer_type=16), NAME) is None
    assert unicast.parse_srv_port(reply(port=0), NAME) is None


@pytest.mark.parametrize("packet", [
    b"", b"\x00" * 12, b"not-a-dns-response", reply()[:20],
    reply(flags=0x0400), reply(rr_name=b"\xc0\xff"),
    reply(rr_name=b"\xc0\x0c")[:-1],
    reply(rdata=struct.pack("!HHH", 0, 0, 59086)),
])
def test_reject_malformed_or_untrusted_dns_packets(packet):
    assert unicast.parse_srv_port(packet, NAME) is None


def test_unicode_and_label_length_checks():
    assert b"Infuse" in unicast._encode_service_name(NAME)
    with pytest.raises(ValueError):
        unicast._encode_service_name("a" * 64 + "._infuse-np._tcp.local.")


@pytest.mark.asyncio
async def test_do_not_query_external_or_unknown_hosts(monkeypatch):
    """Reject invalid devices before allocating any UDP socket."""
    called = []
    monkeypatch.setattr(unicast.socket, "socket", lambda *args: called.append(args))
    assert await unicast.async_resolve_unicast(NAME, "example.com") is None
    assert await unicast.async_resolve_unicast(NAME, "2001:db8::1") is None
    assert await unicast.async_resolve_unicast("unrelated._tcp.local.", "192.168.178.133") is None
    assert called == []


def ptr_response(instance: str, *, owner: str = "_infuse-np._tcp.local.", rr_type: int = 12, flags: int = 0x8400) -> bytes:
    import struct
    service = unicast._encode_dns_name(owner)
    target = unicast._encode_service_name(instance)
    question = service + struct.pack('!HH', 12, 0x8001)
    rr = service + struct.pack('!HHIH', rr_type, 1, 120, len(target)) + target
    return struct.pack('!HHHHHH', 0, flags, 1, 1, 0, 0) + question + rr


def test_ptr_discovery_only_accepts_named_infuse_services():
    instance = 'Apple TV._infuse-np._tcp.local.'
    service = '_infuse-np._tcp.local.'
    assert unicast.parse_ptr_services(ptr_response(instance), service) == (instance,)
    assert unicast.parse_ptr_services(ptr_response(instance, rr_type=16), service) == ()
    assert unicast.parse_ptr_services(ptr_response(instance, owner='_http._tcp.local.'), service) == ()
    assert unicast.parse_ptr_services(ptr_response('Another._http._tcp.local.'), service) == ()
    assert unicast.parse_ptr_services(ptr_response(instance, flags=0), service) == ()
    assert unicast.parse_ptr_services(ptr_response(instance)[:-1], service) == ()
    assert unicast.parse_ptr_services(b'garbage', service) == ()
    assert unicast.parse_ptr_services(b'Z' * 5000, service) == ()


@pytest.mark.asyncio
async def test_ptr_discovery_rejects_nonpaired_addresses_without_opening_socket(monkeypatch):
    touched = []
    monkeypatch.setattr(unicast.socket, 'socket', lambda *args: touched.append(args))
    assert await unicast.async_discover_unicast_services('example.com') == ()
    assert await unicast.async_discover_unicast_services('2001:db8::1234') == ()
    assert not touched
