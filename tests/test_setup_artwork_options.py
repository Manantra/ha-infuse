"""Cover opt-in during initial manual and Bonjour setup, using stubbed HA APIs."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from conftest import PACKAGE_NAME


@pytest.fixture
def flow_module(monkeypatch):
    """Keep the tests dependency-light while exercising real config flow logic."""
    ha = ModuleType("homeassistant")
    ha.__path__ = []
    entries = ModuleType("homeassistant.config_entries")
    core = ModuleType("homeassistant.core")
    data_entry_flow = ModuleType("homeassistant.data_entry_flow")
    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    cv = ModuleType("homeassistant.helpers.config_validation")
    aiohttp_client = ModuleType("homeassistant.helpers.aiohttp_client")
    selectors = ModuleType("homeassistant.helpers.selector")

    class ConfigFlow:
        hass = object()  # Home Assistant injects hass; our flow does not call super().__init__.

        def __init_subclass__(cls, **_kwargs):
            return None

        def __init__(self):
            self.hass = object()
            self.context = {}

        def _async_current_entries(self):
            return []

        async def async_set_unique_id(self, _unique_id):
            return None

        def _abort_if_unique_id_configured(self, **_kwargs):
            return None

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

    class Selector:
        def __init__(self, config):
            self.config = config

        def __call__(self, value):
            return value

    entries.ConfigFlow = ConfigFlow
    entries.OptionsFlow = ConfigFlow
    entries.ConfigEntry = object
    core.callback = lambda func: func
    data_entry_flow.FlowResult = dict
    cv.string = str
    cv.boolean = bool
    aiohttp_client.async_get_clientsession = lambda hass: None
    selectors.TextSelector = Selector
    selectors.TextSelectorConfig = lambda **kwargs: SimpleNamespace(**kwargs)
    selectors.TextSelectorType = SimpleNamespace(PASSWORD="password")

    for name, module in (
        ("homeassistant", ha),
        ("homeassistant.config_entries", entries),
        ("homeassistant.core", core),
        ("homeassistant.data_entry_flow", data_entry_flow),
        ("homeassistant.helpers", helpers),
        ("homeassistant.helpers.config_validation", cv),
        ("homeassistant.helpers.aiohttp_client", aiohttp_client),
        ("homeassistant.helpers.selector", selectors),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    fullname = f"{PACKAGE_NAME}.config_flow"
    sys.modules.pop(fullname, None)
    module = importlib.import_module(fullname)
    yield module
    sys.modules.pop(fullname, None)


@pytest.mark.asyncio
async def test_manual_setup_without_token_still_works(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()

    async def succeeds(*_):
        return None

    monkeypatch.setattr(flow, "_test_connection", succeeds)
    form = await flow.async_step_user()
    assert "tmdb_token" not in form["data_schema"]({"host": "127.0.0.1", "port": 9999, "name": "Infuse"})
    result = await flow.async_step_user({"host": "127.0.0.1", "port": 9999, "name": "Infuse"})
    assert result == {"type": "create_entry", "title": "Infuse", "data": {"host": "127.0.0.1", "port": 9999}, "options": {}}


@pytest.mark.asyncio
async def test_manual_setup_saves_optional_token_in_options_only(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()

    async def succeeds(*_):
        return None

    monkeypatch.setattr(flow, "_test_connection", succeeds)
    result = await flow.async_step_user({
        "host": "127.0.0.1", "port": 9999, "name": "Infuse",
        "tmdb_token": "  my-read-access-token  ",
    })
    assert result["options"] == {"tmdb_token": "my-read-access-token"}
    assert "tmdb_token" not in result["data"]


@pytest.mark.asyncio
async def test_bonjour_confirmation_refreshes_port_and_accepts_token(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()
    flow._discovered = {
        "host": "192.168.178.133", "port": 59078,
        "name": "Apple TV Infuse Player",
        "discovery_name": "Apple TV Infuse Player._infuse-np._tcp.local.",
    }
    checked_ports = []

    async def resolves(_hass, _name, host, *, fresh):
        assert fresh is True
        return host, 59083

    async def tests(_host, port):
        checked_ports.append(port)
        return None

    monkeypatch.setattr(flow_module, "async_resolve_endpoint", resolves)
    monkeypatch.setattr(flow, "_test_connection", tests)
    form = await flow.async_step_confirm()
    assert form["description_placeholders"]["port"] == "59083"
    assert form["data_schema"]({"tmdb_token": "  secret  "})["tmdb_token"] == "  secret  "
    entry = await flow.async_step_confirm({"tmdb_token": "  secret  "})
    assert checked_ports == [59083]
    assert entry["data"]["port"] == 59083
    assert entry["options"] == {"tmdb_token": "secret"}
    assert "tmdb_token" not in entry["data"]


@pytest.mark.asyncio
async def test_bonjour_confirmation_no_token_retains_local_only_flow(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()
    flow._discovered = {"host": "127.0.0.1", "port": 5000, "name": "Infuse",
                        "discovery_name": "Infuse._infuse-np._tcp.local."}

    async def resolves(_hass, _name, host, *, fresh):
        return host, 5000

    async def tests(_host, _port):
        return None

    monkeypatch.setattr(flow_module, "async_resolve_endpoint", resolves)
    monkeypatch.setattr(flow, "_test_connection", tests)
    entry = await flow.async_step_confirm({})
    assert entry["type"] == "create_entry"
    assert entry["options"] == {}

@pytest.mark.asyncio
async def test_options_screen_identifies_stored_token_without_revealing_value(flow_module):
    options_flow = flow_module.InfuseOptionsFlow()
    options_flow.config_entry = SimpleNamespace(options={"tmdb_token": "top-secret-token"})
    form = await options_flow.async_step_init()
    assert form["description_placeholders"]["tmdb_status"] == "✓"
    assert "top-secret-token" not in repr(form)
    assert "tmdb_token" not in form["data_schema"]({"poll_interval": 5, "language": "de-DE"})


@pytest.mark.asyncio
@pytest.mark.parametrize("token_value", [None, "", "   "])
async def test_options_preserve_existing_token_when_password_field_blank(flow_module, token_value):
    options_flow = flow_module.InfuseOptionsFlow()
    options_flow.config_entry = SimpleNamespace(options={"tmdb_token": "existing-token", "language": "de-DE"})
    submission = {"poll_interval": 10, "language": "en-US", "clear_tmdb_token": False}
    if token_value is not None:
        submission["tmdb_token"] = token_value
    result = await options_flow.async_step_init(submission)
    assert result["data"]["tmdb_token"] == "existing-token"
    assert result["data"]["poll_interval"] == 10
    assert result["data"]["language"] == "en-US"


@pytest.mark.asyncio
async def test_options_replace_token_only_when_explicit_nonempty_value(flow_module):
    options_flow = flow_module.InfuseOptionsFlow()
    options_flow.config_entry = SimpleNamespace(options={"tmdb_token": "old-token"})
    result = await options_flow.async_step_init({
        "poll_interval": 5, "language": "de-DE", "tmdb_token": "  new-token  "
    })
    assert result["data"]["tmdb_token"] == "new-token"


@pytest.mark.asyncio
async def test_options_remove_token_only_with_explicit_clear_flag(flow_module):
    options_flow = flow_module.InfuseOptionsFlow()
    options_flow.config_entry = SimpleNamespace(options={"tmdb_token": "existing-token"})
    result = await options_flow.async_step_init({
        "poll_interval": 5, "language": "de-DE", "clear_tmdb_token": True,
        "tmdb_token": "unwanted-new-token",
    })
    assert "tmdb_token" not in result["data"]


@pytest.mark.asyncio
async def test_options_screen_indicates_when_no_token_exists(flow_module):
    options_flow = flow_module.InfuseOptionsFlow()
    options_flow.config_entry = SimpleNamespace(options={})
    form = await options_flow.async_step_init()
    assert form["description_placeholders"]["tmdb_status"] == "✗"
