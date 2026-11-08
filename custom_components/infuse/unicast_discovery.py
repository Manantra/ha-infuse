"""Last-resort, device-targeted DNS-SD when multicast discovery is stale.

Home Assistant OS virtual machines may retain a stale Bonjour SRV record after
Infuse (re)starts on a new ephemeral HTTP port. The already paired Apple TV
responds to an ordinary unicast DNS SRV query on UDP 5353, even when fresh
multicast resolution inside Home Assistant returns no updated service.

No network scanning: this sends one targeted UDP packet to the configured
Infuse device, validates its named SRV response, and never uses an unverified
port without the caller subsequently checking the Infuse HTTP API.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import struct

_DNS_PORT = 5353
_DNS_SRV = 33
_DNS_PTR = 12
_DNS_IN = 1
_MAX_PACKET = 4096


def _encode_dns_name(name: str, *, min_labels: int = 3) -> bytes:
    """Encode DNS labels safely (including the three-label service type)."""
    labels = name.removesuffix(".").split(".")
    if len(labels) < min_labels:
        raise ValueError("not a DNS-SD service name")
    parts = []
    for label in labels:
        encoded = label.encode("utf-8")
        if not 0 < len(encoded) <= 63:
            raise ValueError("invalid DNS-SD label")
        parts.append(bytes((len(encoded),)) + encoded)
    encoded_name = b"".join(parts) + b"\x00"
    if len(encoded_name) > 255:
        raise ValueError("DNS-SD name too long")
    return encoded_name


def _encode_service_name(name: str) -> bytes:
    """Encode an exact DNS-SD instance name (not just the service type)."""
    return _encode_dns_name(name, min_labels=4)


def _read_dns_name(packet: bytes, offset: int) -> tuple[str, int]:
    """Read bounded DNS labels and compression pointers from a response."""
    labels: list[str] = []
    end_offset: int | None = None
    visited: set[int] = set()
    for _ in range(64):
        if offset >= len(packet) or offset in visited:
            raise ValueError("invalid DNS name")
        visited.add(offset)
        size = packet[offset]
        if size == 0:
            return ".".join(labels) + ".", (end_offset if end_offset is not None else offset + 1)
        if size & 0xC0 == 0xC0:
            if offset + 1 >= len(packet):
                raise ValueError("invalid DNS compression pointer")
            target = ((size & 0x3F) << 8) | packet[offset + 1]
            if target >= len(packet):
                raise ValueError("DNS pointer outside packet")
            if end_offset is None:
                end_offset = offset + 2
            offset = target
            continue
        if size & 0xC0 or size > 63 or offset + 1 + size > len(packet):
            raise ValueError("invalid DNS label")
        labels.append(packet[offset + 1:offset + 1 + size].decode("utf-8"))
        offset += 1 + size
    raise ValueError("DNS pointer chain too long")


def parse_srv_port(packet: bytes, expected_name: str) -> int | None:
    """Return port only for an exact SRV record in a valid DNS response."""
    if not 12 <= len(packet) <= _MAX_PACKET:
        return None
    msg_id, flags, questions, answers, authorities, additional = struct.unpack_from("!HHHHHH", packet)
    if msg_id != 0 or not (flags & 0x8000) or flags & 0x000F or questions > 4:
        return None
    if answers + authorities + additional > 64:
        return None
    offset = 12
    try:
        for _ in range(questions):
            _, offset = _read_dns_name(packet, offset)
            if offset + 4 > len(packet):
                return None
            offset += 4
        for _ in range(answers):
            name, offset = _read_dns_name(packet, offset)
            if offset + 10 > len(packet):
                return None
            rr_type, rr_class, ttl, rdlen = struct.unpack_from("!HHIH", packet, offset)
            offset += 10
            if offset + rdlen > len(packet):
                return None
            if name.casefold() == expected_name.casefold() and rr_type == _DNS_SRV and (rr_class & 0x7FFF) == _DNS_IN and rdlen >= 7:
                port = struct.unpack_from("!H", packet, offset + 4)[0]
                return port if 1 <= port <= 65535 else None
            offset += rdlen
    except (UnicodeDecodeError, ValueError, struct.error):
        return None
    return None


def parse_ptr_services(packet: bytes, service_type: str) -> tuple[str, ...]:
    """Read bounded DNS-SD PTR records for the Infuse service type only.

    No devices or addresses are trusted from this response: callers still
    query the known paired IP and verify GET /nowplaying before rebinding.
    """
    if not 12 <= len(packet) <= _MAX_PACKET:
        return ()
    try:
        msg_id, flags, questions, answers, authorities, additional = struct.unpack_from("!HHHHHH", packet)
        if msg_id != 0 or not (flags & 0x8000) or flags & 0x000F or questions > 4:
            return ()
        if answers + authorities + additional > 64:
            return ()
        offset = 12
        for _ in range(questions):
            _, offset = _read_dns_name(packet, offset)
            if offset + 4 > len(packet):
                return ()
            offset += 4
        names: list[str] = []
        for _ in range(answers + authorities + additional):
            owner, offset = _read_dns_name(packet, offset)
            if offset + 10 > len(packet):
                return ()
            rr_type, rr_class, _ttl, rdlen = struct.unpack_from("!HHIH", packet, offset)
            offset += 10
            end = offset + rdlen
            if end > len(packet):
                return ()
            if owner.casefold() == service_type.casefold() and rr_type == _DNS_PTR and (rr_class & 0x7FFF) == _DNS_IN:
                target, consumed = _read_dns_name(packet, offset)
                if consumed <= end and target.casefold().endswith("." + service_type.casefold()):
                    if target.casefold() not in {name.casefold() for name in names}:
                        names.append(target)
                        if len(names) >= 5:
                            return tuple(names)
            offset = end
        return tuple(names)
    except (UnicodeDecodeError, ValueError, struct.error):
        return ()


async def async_discover_unicast_services(
    host: str, *, timeout: float = 1.5,
) -> tuple[str, ...]:
    """Targeted PTR query to the *already paired* IPv4 Infuse device.

    Recovers after foregrounding even if Infuse has changed the DNS-SD
    instance name. No subnet scanning, multicast broadcast, or guessing ports.
    """
    from .discovery import SERVICE_TYPE

    try:
        if ipaddress.ip_address(host).version != 4:
            return ()
        question = _encode_dns_name(SERVICE_TYPE)
    except ValueError:
        return ()
    packet = struct.pack("!HHHHHH", 0, 0, 1, 0, 0, 0) + question + struct.pack("!HH", _DNS_PTR, 0x8000 | _DNS_IN)
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    try:
        async with asyncio.timeout(timeout):
            await loop.sock_connect(sock, (host, _DNS_PORT))
            await loop.sock_sendall(sock, packet)
            response = await loop.sock_recv(sock, _MAX_PACKET)
    except (OSError, TimeoutError):
        return ()
    finally:
        sock.close()
    return parse_ptr_services(response, SERVICE_TYPE)


async def async_resolve_unicast(
    service_name: str, host: str, *, timeout: float = 1.5,
) -> tuple[str, int] | None:
    """Ask the already-paired IPv4 device for its current Infuse SRV port."""
    from .discovery import SERVICE_TYPE

    if not service_name.casefold().endswith("." + SERVICE_TYPE):
        return None
    try:
        if ipaddress.ip_address(host).version != 4:
            return None
        # Request a unicast response (RFC 6762 QU bit) from the known device.
        question = _encode_service_name(service_name)
    except ValueError:
        return None
    packet = struct.pack("!HHHHHH", 0, 0, 1, 0, 0, 0) + question + struct.pack("!HH", _DNS_SRV, 0x8000 | _DNS_IN)
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    try:
        async with asyncio.timeout(timeout):
            await loop.sock_connect(sock, (host, _DNS_PORT))
            await loop.sock_sendall(sock, packet)
            response = await loop.sock_recv(sock, _MAX_PACKET)
    except (OSError, TimeoutError):
        return None
    finally:
        sock.close()
    port = parse_srv_port(response, service_name)
    return (host, port) if port is not None else None
