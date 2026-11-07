"""A configured Infuse device can recover when its Bonjour port changes."""

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest

from conftest import PACKAGE_NAME, model


@pytest.mark.asyncio
async def test_coordinator_recovers_from_new_bonjour_port(monkeypatch):
    """A failed poll must retry the updated endpoint without changing device identity."""
    homeassistant = ModuleType("homeassistant")
    homeassistant.__path__ = []
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = object
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    ha_zeroconf = ModuleType("homeassistant.components.zeroconf")
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, _item):
            return cls

        def __init__(self, hass, logger, **kwargs):
            self.hass = hass
            self.data = None

    update_coordinator.UpdateFailed = UpdateFailed
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    for name, mod in (
        ("homeassistant", homeassistant),
        ("homeassistant.components", components),
        ("homeassistant.components.zeroconf", ha_zeroconf),
        ("homeassistant.config_entries", config_entries),
        ("homeassistant.core", core),
        ("homeassistant.helpers", helpers),
        ("homeassistant.helpers.update_coordinator", update_coordinator),
    ):
        monkeypatch.setitem(sys.modules, name, mod)

    # Ensure the test imports a coordinator with the lightweight HA stand-ins.
    module_name = f"{PACKAGE_NAME}.coordinator"
    sys.modules.pop(module_name, None)
    coordinator_module = importlib.import_module(module_name)

    class Client:
        def __init__(self):
            self.endpoint = ("192.168.178.133", 59078)
            self.calls = []

        async def get_now_playing(self):
            self.calls.append(self.endpoint)
            if self.endpoint[1] == 59078:
                raise ConnectionRefusedError("old Bonjour port")
            return model.Playback(state="idle", position=None, duration=None, item=None)

        def update_endpoint(self, host, port):
            self.endpoint = (host, port)

    lookups = []

    async def resolve(hass, name, host, *, fresh):
        lookups.append((name, host, fresh))
        return (host, 59083)

    monkeypatch.setattr(coordinator_module, "async_resolve_endpoint", resolve)
    client = Client()
    entry = SimpleNamespace(
        entry_id="test_entry",
        title="Apple TV Infuse Player",
        options={},
        data={"discovery_name": "Apple TV Infuse Player._infuse-np._tcp.local."},
    )
    instance = coordinator_module.InfuseCoordinator(object(), entry, client, object(), 5)
    playback = await instance._async_update_data()
    assert playback.state == "idle"
    assert client.endpoint == ("192.168.178.133", 59083)
    assert client.calls == [
        ("192.168.178.133", 59078),
        ("192.168.178.133", 59083),
    ]
    assert len(lookups) == 1 and lookups[0][2] is False
    assert instance.endpoint_changes == 1
    assert instance.last_resolution == "home_assistant"
    sys.modules.pop(module_name, None)
