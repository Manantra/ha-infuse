"""Reconnection diagnostics contain useful status without leaking credentials."""
import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest
from conftest import PACKAGE_NAME


@pytest.mark.asyncio
async def test_diagnostics_distinguish_missing_api_from_moved_port(monkeypatch):
    ha = ModuleType("homeassistant")
    ha.__path__ = []
    entries = ModuleType("homeassistant.config_entries")
    entries.ConfigEntry = object
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    for name,mod in (("homeassistant",ha),("homeassistant.config_entries",entries),("homeassistant.core",core)):
        monkeypatch.setitem(sys.modules,name,mod)
    module_name = f"{PACKAGE_NAME}.diagnostics"
    sys.modules.pop(module_name,None)
    module = importlib.import_module(module_name)
    entry = SimpleNamespace(
        entry_id="test",title="Living room",options={"tmdb_token":"private-secret"},
        data={"host":"192.168.178.120","port":59321,"discovery_name":"Original._infuse-np._tcp.local."},
    )
    coordinator = SimpleNamespace(
        data=None,client=SimpleNamespace(endpoint=("192.168.178.120",59326)),
        endpoint_changes=2,last_resolution="no_reachable_new_endpoint",
        recovery_attempts=19,last_connection_error="ClientConnectorError",
        last_successful_contact="2026-11-09T00:00:00+00:00",
        _service_name="New._infuse-np._tcp.local.",
        update_interval=SimpleNamespace(total_seconds=lambda:5),
        last_update_success=False,
    )
    hass = SimpleNamespace(data={"infuse":{"test":coordinator}})
    result = await module.async_get_config_entry_diagnostics(hass,entry)
    assert result["integration_version"]=="0.2.11"
    assert result["connected"] is False
    assert result["recovery_attempts"]==19
    assert result["last_connection_error"]=="ClientConnectorError"
    assert result["last_bonjour_resolution"]=="no_reachable_new_endpoint"
    assert result["service_name_changed"] is True
    assert result["active_port"]==59326
    assert result["last_successful_contact"]=="2026-11-09T00:00:00+00:00"
    assert result["tmdb_configured"] is True
    assert "private-secret" not in repr(result)
    assert "192.168.178.120" not in repr(result)
    sys.modules.pop(module_name,None)
