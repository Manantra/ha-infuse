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

        async def async_set_unique_id(self, unique_id):
            self._set_unique_id = unique_id
            return None

        def _get_reconfigure_entry(self):
            return self._test_reconfigure_entry

        def _abort_if_unique_id_mismatch(self):
            self._unique_id_checked = True

        def async_update_and_abort(self, entry, *, data):
            self._updated_existing_entry = True
            entry.data = data
            return {"type": "abort", "reason": "reconfigure_successful", "data": data}

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


@pytest.mark.asyncio
async def test_reconfigure_uses_existing_entry_without_resetting_identity_or_options(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="the-same-device", unique_id="manual:192.168.1.2:59001",
        data={"host": "192.168.1.2", "port": 59001, "extra_setting": "preserved"},
        options={"tmdb_token": "kept-private", "poll_interval": 10},
    )
    flow._test_reconfigure_entry = entry
    form = await flow.async_step_reconfigure()
    assert form["step_id"] == "reconfigure"
    assert form["data_schema"]({})["host"] == "192.168.1.2"
    assert form["data_schema"]({})["port"] == 59001

    async def validates(host, port):
        assert (host, port) == ("192.168.1.5", 59005)
        return None

    monkeypatch.setattr(flow, "_test_connection", validates)
    response = await flow.async_step_reconfigure({"host": "192.168.1.5", "port": 59005})
    assert response["reason"] == "reconfigure_successful"
    assert flow._updated_existing_entry is True
    assert flow._unique_id_checked is True
    assert flow._set_unique_id == "manual:192.168.1.2:59001"
    assert entry.data == {"host": "192.168.1.5", "port": 59005, "extra_setting": "preserved"}
    assert entry.options["tmdb_token"] == "kept-private"


@pytest.mark.asyncio
async def test_reconfigure_clears_stale_bonjour_name_on_host_change(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="original", unique_id="service:original._infuse-np._tcp.local.",
        data={"host": "192.168.1.2", "port": 59001,
              "discovery_name": "original._infuse-np._tcp.local."}, options={},
    )
    flow._test_reconfigure_entry = entry

    async def success(*_):
        return None
    monkeypatch.setattr(flow, "_test_connection", success)
    response = await flow.async_step_reconfigure({"host": "192.168.1.3", "port": 59003})
    assert response["type"] == "abort"
    assert "discovery_name" not in entry.data
    assert entry.unique_id == "service:original._infuse-np._tcp.local."


@pytest.mark.asyncio
async def test_reconfigure_preserves_bonjour_name_for_same_host_new_port(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="original", unique_id="service:original._infuse-np._tcp.local.",
        data={"host": "192.168.1.2", "port": 59001,
              "discovery_name": "original._infuse-np._tcp.local."}, options={},
    )
    flow._test_reconfigure_entry = entry

    async def success(*_):
        return None
    monkeypatch.setattr(flow, "_test_connection", success)
    await flow.async_step_reconfigure({"host": "192.168.1.2", "port": 59010})
    assert entry.data["discovery_name"] == "original._infuse-np._tcp.local."


@pytest.mark.asyncio
async def test_reconfigure_refuses_other_entries_and_unreachable_target(flow_module, monkeypatch):
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(entry_id="one", unique_id="manual:1", data={"host": "one", "port": 1234}, options={})
    flow._test_reconfigure_entry = entry
    flow._async_current_entries = lambda: [entry, SimpleNamespace(
        entry_id="two", data={"host": "other", "port": 5678},
    )]
    calls = []

    async def validate(*args):
        calls.append(args)
        return "cannot_connect"

    monkeypatch.setattr(flow, "_test_connection", validate)
    duplicate = await flow.async_step_reconfigure({"host": "other", "port": 5678})
    assert duplicate["errors"]["base"] == "already_configured"
    assert calls == []
    unreachable = await flow.async_step_reconfigure({"host": "test", "port": 5678})
    assert unreachable["errors"]["base"] == "cannot_connect"
    assert calls == [("test", 5678)]
    invalid = await flow.async_step_reconfigure({"host": "http://example.com", "port": 5678})
    assert invalid["errors"]["base"] == "invalid_host"
    assert not hasattr(flow, "_updated_existing_entry")


def test_reconfigure_translations_present_and_same_api_fields():
    import json
    from pathlib import Path
    base = Path(__file__).resolve().parents[1] / "custom_components/infuse"
    for rel in ("strings.json", "translations/de.json", "translations/en.json"):
        config = json.loads((base / rel).read_text())["config"]
        assert set(config["step"]["reconfigure"]["data"]) == {"host", "port"}
        assert config["error"]["already_configured"]


@pytest.mark.asyncio
async def test_old_bonjour_announcement_cannot_undo_manual_reconfigure(flow_module):
    """Do not silently rebind a reconfigured entry back to the old Apple TV."""
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="existing", unique_id="service:original._infuse-np._tcp.local.",
        data={"host": "192.168.1.3", "port": 59003},
    )
    called = []
    async def existing_id(uid):
        called.append(uid)
        return entry
    flow.async_set_unique_id = existing_id
    flow._abort_if_unique_id_configured = lambda **kwargs: pytest.fail(
        "Stale discovery must never update a manually reconfigured host"
    )
    result = await flow.async_step_zeroconf(SimpleNamespace(
        host="192.168.1.2", port=59001,
        name="Original._infuse-np._tcp.local.",
    ))
    assert result == {"type": "abort", "reason": "already_configured"}
    assert entry.data == {"host": "192.168.1.3", "port": 59003}
    assert called == ["service:original._infuse-np._tcp.local."]


@pytest.mark.asyncio
async def test_bonjour_discovery_no_longer_schedules_duplicate_reload(flow_module):
    """HA's existing entry listener handles a single reload on endpoint update."""
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="existing", unique_id="service:original._infuse-np._tcp.local.",
        data={"host": "192.168.1.2", "port": 59001,
              "discovery_name": "Original._infuse-np._tcp.local."},
    )
    async def existing_id(uid):
        return entry
    flow.async_set_unique_id = existing_id
    captured = {}
    def abort_if_configured(**kwargs):
        captured.update(kwargs)
        # Real HA throws AbortFlow here when a configured entry exists.
        raise RuntimeError("already_configured")
    flow._abort_if_unique_id_configured = abort_if_configured
    with pytest.raises(RuntimeError, match="already_configured"):
        await flow.async_step_zeroconf(SimpleNamespace(
            host="192.168.1.2", port=59004,
            name="Original._infuse-np._tcp.local.",
        ))
    assert captured["updates"] == {"host": "192.168.1.2", "port": 59004}
    assert captured["reload_on_update"] is False


@pytest.mark.asyncio
async def test_reconfigure_rejects_live_port_claimed_by_recovered_player(flow_module, monkeypatch):
    """Copilot #4516937607: persisted old port may differ from active port."""
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="tv-a", unique_id="manual:192.168.1.4:59001",
        data={"host": "192.168.1.4", "port": 59001}, options={"tmdb_token": "secret"},
    )
    other = SimpleNamespace(entry_id="tv-b", data={"host": "192.168.1.5", "port": 59002})
    flow._test_reconfigure_entry = entry
    flow._async_current_entries = lambda: [entry, other]
    flow.hass = SimpleNamespace(data={"infuse": {
        "tv-a": SimpleNamespace(client=SimpleNamespace(endpoint=("192.168.1.4", 59001))),
        "tv-b": SimpleNamespace(client=SimpleNamespace(endpoint=("192.168.1.5", 59099))),
    }})
    calls = []

    async def validate(host, port):
        calls.append((host, port))
        return None

    monkeypatch.setattr(flow, "_test_connection", validate)
    result = await flow.async_step_reconfigure({"host": "192.168.1.5", "port": 59099})
    assert result["type"] == "form"
    assert result["errors"]["base"] == "already_configured"
    assert calls == []  # reject even before probing the duplicate endpoint
    assert entry.data == {"host": "192.168.1.4", "port": 59001}
    assert entry.options["tmdb_token"] == "secret"

    # The selected device may be reconfigured to its *own* active endpoint.
    result = await flow.async_step_reconfigure({"host": "192.168.1.4", "port": 59001})
    assert result["type"] == "abort"
    assert calls == [("192.168.1.4", 59001)]


@pytest.mark.asyncio
async def test_reconfigure_checks_live_duplicates_after_async_probe(flow_module, monkeypatch):
    """Another coordinator can change ports while the validation awaits HTTP."""
    flow = flow_module.InfuseConfigFlow()
    entry = SimpleNamespace(
        entry_id="tv-a", unique_id="manual:192.168.1.4:59001",
        data={"host": "192.168.1.4", "port": 59001}, options={},
    )
    other = SimpleNamespace(entry_id="tv-b", data={"host": "192.168.1.5", "port": 59002})
    live_b = SimpleNamespace(client=SimpleNamespace(endpoint=("192.168.1.5", 59002)))
    flow._test_reconfigure_entry = entry
    flow._async_current_entries = lambda: [entry, other]
    flow.hass = SimpleNamespace(data={"infuse": {"tv-b": live_b}})

    async def validate(_host, _port):
        # Simulate an automatic Bonjour recovery during the HTTP probe.
        live_b.client.endpoint = ("192.168.1.5", 59099)
        return None

    monkeypatch.setattr(flow, "_test_connection", validate)
    result = await flow.async_step_reconfigure({"host": "192.168.1.5", "port": 59099})
    assert result["type"] == "form"
    assert result["errors"]["base"] == "already_configured"
    assert entry.data == {"host": "192.168.1.4", "port": 59001}
