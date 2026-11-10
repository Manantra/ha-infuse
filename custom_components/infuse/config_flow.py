"""UI discovery, manual setup and user-configurable polling/artwork options."""

from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import InfuseClient
from .discovery import async_resolve_endpoint
from .const import (
    CONF_CLEAR_TMDB_TOKEN, CONF_DISCOVERY_NAME, CONF_HOST, CONF_LANGUAGE,
    CONF_NAME, CONF_POLL_INTERVAL, CONF_PORT, CONF_TMDB_TOKEN,
    DEFAULT_LANGUAGE, DEFAULT_POLL_INTERVAL, DOMAIN,
)
from .model import InfuseInvalidResponse
from .unicast_discovery import async_resolve_unicast


def _initial_artwork_options(user_input: dict) -> dict[str, str]:
    """Keep optional credentials out of connection data and empty config entries."""
    token = (user_input.get(CONF_TMDB_TOKEN) or "").strip()
    return {CONF_TMDB_TOKEN: token} if token else {}


class InfuseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up only actual Firecore Now Playing endpoints."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict | None = None

    async def _test_connection(self, host: str, port: int) -> str | None:
        try:
            client = InfuseClient(async_get_clientsession(self.hass), host, port)
            await client.get_now_playing()
        except (aiohttp.ClientError, TimeoutError, OSError):
            return "cannot_connect"
        except (InfuseInvalidResponse, ValueError, TypeError):
            return "invalid_response"
        except Exception:
            return "unknown"
        return None

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Manual fallback, especially useful when multicast is blocked."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            if not host or "/" in host or "://" in host:
                errors["base"] = "invalid_host"
            else:
                error = await self._test_connection(host, port)
                if error:
                    errors["base"] = error
                else:
                    if any(
                        current.data.get(CONF_HOST, "").lower() == host.lower()
                        and current.data.get(CONF_PORT) == port
                        for current in self._async_current_entries()
                    ):
                        return self.async_abort(reason="already_configured")
                    await self.async_set_unique_id(f"manual:{host.lower()}:{port}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_NAME].strip() or "Infuse",
                        data={CONF_HOST: host, CONF_PORT: port},
                        options=_initial_artwork_options(user_input),
                    )
        port_key = (
            vol.Required(CONF_PORT, default=user_input[CONF_PORT])
            if user_input and CONF_PORT in user_input else vol.Required(CONF_PORT)
        )
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): cv.string,
            port_key: vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(CONF_NAME, default=(user_input or {}).get(CONF_NAME, "Infuse")): cv.string,
            vol.Optional(CONF_TMDB_TOKEN): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
        })
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors,
            description_placeholders={"tmdb_api_url": "https://www.themoviedb.org/settings/api"},
        )

    async def async_step_zeroconf(self, discovery_info) -> FlowResult:
        """Auto-discover service; port is ephemeral and must come from the SRV record."""
        host = discovery_info.host
        port = discovery_info.port
        name = discovery_info.name.split("._infuse-np._tcp.")[0]
        self._discovered = {
            CONF_HOST: host, CONF_PORT: port, CONF_NAME: name,
            CONF_DISCOVERY_NAME: discovery_info.name,
        }
        if any(
            current.data.get(CONF_HOST, "").lower() == host.lower()
            and current.data.get(CONF_PORT) == port
            for current in self._async_current_entries()
        ):
            return self.async_abort(reason="already_configured")
        existing = await self.async_set_unique_id(f"service:{discovery_info.name.lower()}")
        if existing is not None and not existing.data.get(CONF_DISCOVERY_NAME):
            # A discovered entry may have been manually reconfigured to a new
            # host. A late old mDNS broadcast must never overwrite that choice.
            return self.async_abort(reason="already_configured")
        # Our config entry update listener already schedules a reload. Asking
        # HA to schedule another one is deprecated from Core 2026.12.
        self._abort_if_unique_id_configured(
            updates={CONF_HOST: host, CONF_PORT: port}, reload_on_update=False,
        )
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
        if not self._discovered:
            return self.async_abort(reason="not_supported")
        errors: dict[str, str] = {}
        info = self._discovered
        # Home Assistant can retain a stale Bonjour announcement after Infuse
        # restarts on a new ephemeral port. Ask ONLY the discovered device's
        # original host for its exact DNS-SD SRV record first. On HAOS virtual
        # machines this can be fresher than a multicast/HA cached record.
        original = info[CONF_HOST], info[CONF_PORT]
        direct = await async_resolve_unicast(info[CONF_DISCOVERY_NAME], original[0])
        fresh = None
        if direct is None:
            fresh = await async_resolve_endpoint(
                self.hass, info[CONF_DISCOVERY_NAME], original[0], fresh=True,
            )
        preferred = direct or fresh or original
        info[CONF_HOST], info[CONF_PORT] = preferred

        if user_input is not None:
            # Confirm using the current endpoint, not just a cached mDNS port.
            # If the direct record was stale too, try a fresh multicast record
            # before reporting that the API cannot be reached. Every candidate
            # must respond to GET /nowplaying before the config is created.
            error = await self._test_connection(*preferred)
            if error and direct is not None:
                fresh = await async_resolve_endpoint(
                    self.hass, info[CONF_DISCOVERY_NAME], original[0], fresh=True,
                )
                if fresh is not None and fresh != preferred:
                    fresh_error = await self._test_connection(*fresh)
                    if not fresh_error:
                        preferred = fresh
                        error = None
            if error and original not in {preferred, fresh}:
                original_error = await self._test_connection(*original)
                if not original_error:
                    preferred = original
                    error = None
            if error:
                errors["base"] = error
            else:
                info[CONF_HOST], info[CONF_PORT] = preferred
                return self.async_create_entry(
                    title=info[CONF_NAME],
                    data=info,
                    options=_initial_artwork_options(user_input),
                )
        # Step titles and descriptions use description_placeholders; the discovery
        # flow's title_placeholders only apply to the flow title in the UI.
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({
                vol.Optional(CONF_TMDB_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }),
            errors=errors,
            description_placeholders={
                "name": self._discovered[CONF_NAME],
                "host": self._discovered[CONF_HOST],
                "port": str(self._discovered[CONF_PORT]),
                "tmdb_api_url": "https://www.themoviedb.org/settings/api",
            },
        )

    def _reconfigure_endpoint_in_use(self, entry_id: str, host: str, port: int) -> bool:
        """Reject a device claimed by another entry, including a recovered port.

        Bonjour recovery updates the live client's endpoint independently of
        its saved config entry. Check both to avoid binding two entries to one
        Infuse player after a port change.
        """
        normalized_host = host.casefold()
        if any(
            current.entry_id != entry_id
            and current.data.get(CONF_HOST, "").casefold() == normalized_host
            and current.data.get(CONF_PORT) == port
            for current in self._async_current_entries()
        ):
            return True
        loaded = getattr(self.hass, "data", {}).get(DOMAIN, {})
        return any(
            other_id != entry_id
            and (endpoint := coordinator.client.endpoint)
            and endpoint[0].casefold() == normalized_host
            and endpoint[1] == port
            for other_id, coordinator in loaded.items()
        )

    async def async_step_reconfigure(self, user_input: dict | None = None) -> FlowResult:
        """Update a validated endpoint without replacing the config entry/entities.

        Keep the existing unique ID: Infuse's read-only API has no stable
        hardware identifier to derive a different one safely. On a manual
        host change, clear the former Bonjour name so it cannot redirect the
        entry back to a different Apple TV after DHCP changes.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            if not host or "/" in host or "://" in host:
                errors["base"] = "invalid_host"
            elif self._reconfigure_endpoint_in_use(entry.entry_id, host, port):
                errors["base"] = "already_configured"
            else:
                error = await self._test_connection(host, port)
                if error:
                    errors["base"] = error
                elif self._reconfigure_endpoint_in_use(entry.entry_id, host, port):
                    # Discovery may rebind another coordinator while awaiting
                    # the network validation. Check again before persisting.
                    errors["base"] = "already_configured"
                else:
                    if entry.unique_id is not None:
                        await self.async_set_unique_id(entry.unique_id)
                        self._abort_if_unique_id_mismatch()
                    data = dict(entry.data)
                    data.update({CONF_HOST: host, CONF_PORT: port})
                    if host.casefold() != entry.data[CONF_HOST].casefold():
                        data.pop(CONF_DISCOVERY_NAME, None)
                    # async_update_and_abort notifies the existing update
                    # listener which reloads the entry exactly once. Do not
                    # also call async_update_reload_and_abort (HA 2026.12).
                    return self.async_update_and_abort(entry, data=data)
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(
                CONF_HOST, entry.data[CONF_HOST],
            )): cv.string,
            vol.Required(CONF_PORT, default=(user_input or {}).get(
                CONF_PORT, entry.data[CONF_PORT],
            )): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        })
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return InfuseOptionsFlow()


class InfuseOptionsFlow(config_entries.OptionsFlow):
    """A blank password field leaves an existing TMDB token untouched."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            options = dict(self.config_entry.options)
            options[CONF_POLL_INTERVAL] = user_input[CONF_POLL_INTERVAL]
            options[CONF_LANGUAGE] = user_input[CONF_LANGUAGE]
            if user_input.get(CONF_CLEAR_TMDB_TOKEN):
                options.pop(CONF_TMDB_TOKEN, None)
            else:
                # Password fields are deliberately empty on reopen. A blank
                # or whitespace-only value must never remove a saved token.
                supplied_token = (user_input.get(CONF_TMDB_TOKEN) or "").strip()
                if supplied_token:
                    options[CONF_TMDB_TOKEN] = supplied_token
            return self.async_create_entry(title="", data=options)
        options = self.config_entry.options
        schema = vol.Schema({
            vol.Required(CONF_POLL_INTERVAL, default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)):
                vol.All(vol.Coerce(int), vol.Range(min=2, max=120)),
            vol.Required(CONF_LANGUAGE, default=options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)):
                vol.In(["de-DE", "en-US"]),
            vol.Optional(CONF_TMDB_TOKEN): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_CLEAR_TMDB_TOKEN, default=False): cv.boolean,
        })
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "tmdb_status": "✓" if bool(options.get(CONF_TMDB_TOKEN)) else "✗",
                "tmdb_api_url": "https://www.themoviedb.org/settings/api",
            },
        )
