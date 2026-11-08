"""Centralized LAN polling, optional artwork enrichment, and state events."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import logging
from time import monotonic

import aiohttp
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser

from homeassistant.components import zeroconf as ha_zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InfuseClient
from .discovery import SERVICE_TYPE, async_resolve_endpoint
from .unicast_discovery import async_discover_unicast_services, async_resolve_unicast
from .const import (
    CONF_DISCOVERY_NAME, CONF_LANGUAGE, CONF_TMDB_TOKEN, DEFAULT_LANGUAGE, DOMAIN,
    EVENT_MEDIA_CHANGED, EVENT_PLAYBACK_IDLE, EVENT_PLAYBACK_PAUSED,
    EVENT_PLAYBACK_RESUMED, EVENT_PLAYBACK_STARTED, EVENT_STATE_CHANGED,
)
from .metadata import fetch_tmdb_artwork
from .model import InfuseInvalidResponse, Playback

_LOGGER = logging.getLogger(__name__)


class InfuseCoordinator(DataUpdateCoordinator[Playback]):
    """Exactly one HTTP poll per device; all entities share its snapshot."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: InfuseClient,
        session: aiohttp.ClientSession, interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
            always_update=False,
        )
        self.entry = entry
        self.client = client
        self.session = session
        self._artwork_cache: dict[tuple[str, str, str], tuple[float, str | None]] = {}
        self._last_rediscovery = float("-inf")
        self._bonjour_browser: AsyncServiceBrowser | None = None
        self._bonjour_task = None
        self._bonjour_pending: set[str] = set()
        # Bonjour can re-register a different instance name when Infuse resumes.
        # Keep the last validated name without modifying the HA config entry.
        self._service_name: str | None = entry.data.get(CONF_DISCOVERY_NAME)
        self._unloading = False
        self.endpoint_changes = 0
        self.last_resolution = "not_attempted"
        self.recovery_attempts = 0
        self.last_connection_error: str | None = None
        self.last_successful_contact: str | None = None

    def _update_endpoint(self, endpoint: tuple[str, int]) -> bool:
        """Use the new Bonjour endpoint without resetting the HA device."""
        if endpoint == self.client.endpoint:
            return False
        previous = self.client.endpoint
        self.client.update_endpoint(*endpoint)
        self.endpoint_changes += 1
        _LOGGER.info("Infuse Bonjour endpoint changed: port %s -> %s", previous[1], endpoint[1])
        return True

    async def async_start_bonjour_updates(self) -> None:
        """Track Infuse after foregrounding, including manually added devices."""
        try:
            aiozc = await ha_zeroconf.async_get_async_instance(self.hass)
            self._bonjour_browser = AsyncServiceBrowser(
                aiozc.zeroconf, SERVICE_TYPE, handlers=[self._on_bonjour_change],
            )
        except (OSError, RuntimeError, ValueError) as exc:
            _LOGGER.debug("Cannot subscribe to Infuse Bonjour updates: %s", exc)
            self.last_resolution = "browser_unavailable"

    def _on_bonjour_change(self, zeroconf, service_type, name, state_change) -> None:
        """Browser callbacks run in the HA event loop, never in an HTTP poll."""
        if self._unloading or state_change is ServiceStateChange.Removed:
            return
        # A resumed app may advertise a new instance name. Resolve only
        # _infuse-np services, and require the original host for renamed ones.
        self._bonjour_pending.add(name)
        if self._bonjour_task is None or self._bonjour_task.done():
            self._bonjour_task = self.hass.async_create_task(self._async_apply_bonjour_update())

    async def _async_apply_bonjour_update(self) -> None:
        """Validate new Bonjour announcements before refreshing HA entities.

        Drain pending names instead of dropping notifications arriving while a
        slow DNS resolution or HTTP validation is in progress.
        """
        names = self._bonjour_pending or ({self._service_name} if self._service_name else set())
        self._bonjour_pending = set()
        while names and not self._unloading:
            for name in sorted(names):
                if self._unloading:
                    return
                endpoint = await async_resolve_endpoint(
                    self.hass, name, self.client.endpoint[0], fresh=False,
                )
                if endpoint is None:
                    continue
                # Exact service name may legitimately move to a new IP.
                # A renamed service may only be associated if its IP matches
                # the device that was already configured by the user.
                same_service = bool(
                    self._service_name and name.casefold() == self._service_name.casefold()
                )
                if not same_service and endpoint[0] != self.client.endpoint[0]:
                    continue
                if endpoint == self.client.endpoint and same_service and self.last_update_success:
                    continue
                try:
                    await InfuseClient(self.session, *endpoint).get_now_playing()
                except (aiohttp.ClientError, TimeoutError, OSError, ValueError, InfuseInvalidResponse):
                    _LOGGER.debug("Ignoring unreachable Infuse Bonjour service %s", name)
                    continue
                changed = self._update_endpoint(endpoint)
                self._service_name = name
                if not self._unloading:
                    self.last_resolution = "bonjour_event"
                    if changed or not self.last_update_success:
                        await self.async_request_refresh()
            names = self._bonjour_pending
            self._bonjour_pending = set()

    def async_stop_bonjour_updates(self) -> None:
        """Dispose of the subscription when the config entry is unloaded."""
        self._unloading = True
        if self._bonjour_task and not self._bonjour_task.done():
            self._bonjour_task.cancel()
        if self._bonjour_browser is not None:
            browser = self._bonjour_browser
            self._bonjour_browser = None
            self.hass.async_create_task(browser.async_cancel())

    async def _async_probe_endpoint(
        self, endpoint: tuple[str, int] | None, resolution: str,
        tried: set[tuple[str, int]],
    ) -> Playback | None:
        """Probe candidate independently; never replace a working endpoint with a stale one."""
        if endpoint is None or endpoint in tried:
            return None
        tried.add(endpoint)
        try:
            playback = await InfuseClient(self.session, *endpoint).get_now_playing()
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError, InfuseInvalidResponse):
            return None
        self._update_endpoint(endpoint)
        self.last_resolution = resolution
        return playback

    async def _async_recover(self, original_error: Exception) -> Playback:
        """Follow fresh Infuse registrations after background/foreground cycles.

        Start with HA cached/fresh Bonjour, then the paired host's unicast SRV.
        Finally ask that same host for PTR records in case the DNS-SD instance
        was renamed or this entry was originally configured by hand.
        """
        if monotonic() - self._last_rediscovery < 15:
            raise UpdateFailed(
                f"Unable to contact Infuse Now Playing API: {type(original_error).__name__}"
            ) from original_error
        self._last_rediscovery = monotonic()
        self.recovery_attempts += 1
        tried: set[tuple[str, int]] = {self.client.endpoint}
        host = self.client.endpoint[0]
        service = self._service_name
        if service:
            for fresh in (False, True):
                endpoint = await async_resolve_endpoint(self.hass, service, host, fresh=fresh)
                playback = await self._async_probe_endpoint(
                    endpoint, "fresh" if fresh else "home_assistant", tried,
                )
                if playback is not None:
                    return playback
            # A direct SRV query also works on HAOS installations that miss
            # multicast responses after Infuse changes its ephemeral port.
            endpoint = await async_resolve_unicast(service, host)
            playback = await self._async_probe_endpoint(endpoint, "direct_unicast", tried)
            if playback is not None:
                return playback

        # Ask *only the already paired device* if it now publishes an Infuse
        # service under another DNS-SD name. This also supports manual setup,
        # where there was never an original service name to resolve.
        for name in await async_discover_unicast_services(host):
            if self._unloading:
                break
            endpoint = await async_resolve_unicast(name, host)
            playback = await self._async_probe_endpoint(endpoint, "direct_ptr_unicast", tried)
            if playback is not None:
                self._service_name = name
                return playback
        self.last_resolution = "no_reachable_new_endpoint"
        raise UpdateFailed(
            f"Unable to contact Infuse Now Playing API: {type(original_error).__name__}"
        ) from original_error

    async def _async_update_data(self) -> Playback:
        previous = self.data
        try:
            current = await self.client.get_now_playing()
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError, InfuseInvalidResponse) as exc:
            self.last_connection_error = type(exc).__name__
            current = await self._async_recover(exc)
        else:
            # A listener can return on the original port without a new Bonjour
            # announcement after Infuse is foregrounded again.
            if self.last_connection_error is not None:
                self.last_resolution = "original_port_recovered"
        self.last_connection_error = None
        self.last_successful_contact = datetime.now(timezone.utc).isoformat(timespec="seconds")

        item = current.item
        token: str = self.entry.options.get(CONF_TMDB_TOKEN, "")
        language: str = self.entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        if item and token and item.tmdb_id:
            cache_key = (item.kind, item.tmdb_id, language)
            cached = self._artwork_cache.get(cache_key)
            if cached and cached[0] > monotonic():
                artwork = cached[1]
            else:
                try:
                    artwork = await fetch_tmdb_artwork(self.session, token, item, language)
                except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
                    _LOGGER.debug("Optional TMDB artwork lookup failed: %s", type(exc).__name__)
                    artwork = None
                    self._artwork_cache[cache_key] = (monotonic() + 300, None)
                else:
                    self._artwork_cache[cache_key] = (monotonic() + 12 * 3600, artwork)
            current = replace(current, artwork_url=artwork)

        if previous is not None:
            self._emit_events(previous, current)
        return current

    def _emit_events(self, previous: Playback, current: Playback) -> None:
        old_item = previous.item.identity if previous.item else None
        new_item = current.item.identity if current.item else None
        context = {
            "config_entry_id": self.entry.entry_id,
            "device_name": self.entry.title,
            "state": current.state,
            "title": current.item.title if current.item else None,
            "series_title": current.item.series_title if current.item else None,
            "tmdb_id": current.item.tmdb_id if current.item else None,
        }
        if old_item != new_item:
            self.hass.bus.async_fire(EVENT_MEDIA_CHANGED, context)
        if previous.state == current.state:
            return
        self.hass.bus.async_fire(
            EVENT_STATE_CHANGED,
            {**context, "previous_state": previous.state},
        )
        if current.state == "idle":
            specific = EVENT_PLAYBACK_IDLE
        elif current.state == "paused":
            specific = EVENT_PLAYBACK_PAUSED
        elif previous.state == "paused":
            specific = EVENT_PLAYBACK_RESUMED
        else:
            specific = EVENT_PLAYBACK_STARTED
        self.hass.bus.async_fire(specific, context)
