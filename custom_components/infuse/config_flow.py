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
from .const import (
    CONF_CLEAR_TMDB_TOKEN, CONF_DISCOVERY_NAME, CONF_HOST, CONF_LANGUAGE,
    CONF_NAME, CONF_POLL_INTERVAL, CONF_PORT, CONF_TMDB_TOKEN,
    DEFAULT_LANGUAGE, DEFAULT_POLL_INTERVAL, DOMAIN,
)
from .model import InfuseInvalidResponse


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
                    )
        port_key = (
            vol.Required(CONF_PORT, default=user_input[CONF_PORT])
            if user_input and CONF_PORT in user_input else vol.Required(CONF_PORT)
        )
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): cv.string,
            port_key: vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Required(CONF_NAME, default=(user_input or {}).get(CONF_NAME, "Infuse")): cv.string,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

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
        await self.async_set_unique_id(f"service:{discovery_info.name.lower()}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})
        self.context["title_placeholders"] = {"name": name}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict | None = None) -> FlowResult:
        if not self._discovered:
            return self.async_abort(reason="not_supported")
        errors: dict[str, str] = {}
        if user_input is not None:
            info = self._discovered
            error = await self._test_connection(info[CONF_HOST], info[CONF_PORT])
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(title=info[CONF_NAME], data=info)
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}), errors=errors)

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
            elif user_input.get(CONF_TMDB_TOKEN):
                options[CONF_TMDB_TOKEN] = user_input[CONF_TMDB_TOKEN].strip()
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
        return self.async_show_form(step_id="init", data_schema=schema)
