"""Resolve Infuse's ephemeral Bonjour HTTP endpoint.

Azeroconf discoveries can remain in a config flow after Infuse has restarted.
Always resolve the service again rather than relying on its original SRV port.
"""

from __future__ import annotations

import ipaddress
import logging

from zeroconf.asyncio import AsyncZeroconf

_LOGGER = logging.getLogger(__name__)
SERVICE_TYPE = "_infuse-np._tcp.local."


def _endpoint_from_service(info, preferred_host: str | None) -> tuple[str, int] | None:
    """Prefer the currently configured address, otherwise a usable IPv4 address."""
    if info is None or not isinstance(info.port, int) or not 1 <= info.port <= 65535:
        return None
    addresses = info.parsed_addresses()
    if preferred_host in addresses:
        host = preferred_host
    else:
        host = next(
            (address for address in addresses if ipaddress.ip_address(address).version == 4),
            None,
        )
    if not host:
        return None
    return host, info.port


async def async_resolve_endpoint(
    hass, service_name: str, preferred_host: str | None = None, *, fresh: bool = False,
) -> tuple[str, int] | None:
    """Look up an Infuse SRV record, optionally bypassing stale HA mDNS cache.

    A short-lived independent resolver is used only when an original discovery
    is being confirmed or an established connection has failed. Regular polling
    never starts a separate Bonjour instance.
    """
    if not service_name.lower().endswith("." + SERVICE_TYPE):
        return None
    try:
        if fresh:
            async with AsyncZeroconf() as aiozc:
                info = await aiozc.async_get_service_info(SERVICE_TYPE, service_name, timeout=3000)
        else:
            from homeassistant.components import zeroconf as ha_zeroconf

            aiozc = await ha_zeroconf.async_get_async_instance(hass)
            info = await aiozc.async_get_service_info(SERVICE_TYPE, service_name, timeout=3000)
    except Exception as exc:  # Network lookup must not abort the config flow
        _LOGGER.debug("Unable to resolve Infuse Bonjour service %s: %s", service_name, exc)
        return None
    return _endpoint_from_service(info, preferred_host)
