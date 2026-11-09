"""Bundled Lovelace card: versioned resource, safe migration and lazy HA storage."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from conftest import PACKAGE_NAME


@pytest.fixture
def frontend_module(monkeypatch):
    ha = ModuleType("homeassistant")
    ha.__path__ = []
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    http = ModuleType("homeassistant.components.http")
    core = ModuleType("homeassistant.core")
    loader = ModuleType("homeassistant.loader")
    exceptions = ModuleType("homeassistant.exceptions")
    exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    core.HomeAssistant = object
    http.StaticPathConfig = lambda url, path, cache: SimpleNamespace(
        url_path=url, path=path, cache_headers=cache,
    )

    async def get_integration(_hass, domain):
        assert domain == "infuse"
        return SimpleNamespace(version="0.2.12")

    loader.async_get_integration = get_integration
    for name, module in (
        ("homeassistant", ha),
        ("homeassistant.components", components),
        ("homeassistant.components.http", http),
        ("homeassistant.core", core),
        ("homeassistant.exceptions", exceptions),
        ("homeassistant.loader", loader),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    fullname = f"{PACKAGE_NAME}.frontend"
    sys.modules.pop(fullname, None)
    module = importlib.import_module(fullname)
    yield module
    sys.modules.pop(fullname, None)


class ResourceStore:
    """Intentionally lazy: async_items would lose prior data before loading."""

    def __init__(self, items=()):
        self.saved = list(items)
        self.current = []
        self.loaded = False
        self.created = []
        self.updated = []

    async def async_get_info(self):
        self.current = [dict(item) for item in self.saved]
        self.loaded = True
        return {"resources": len(self.current)}

    def async_items(self):
        assert self.loaded, "resource store must load before listing"
        return self.current

    async def async_create_item(self, item):
        assert self.loaded, "create before load could erase existing cards"
        item = {"id": f"card-{len(self.current) + 1}", "type": item["res_type"], "url": item["url"]}
        self.current.append(item)
        self.saved.append(item)
        self.created.append(item)
        return item

    async def async_update_item(self, item_id, values):
        assert self.loaded
        self.updated.append((item_id, values))
        for item in self.current:
            if item["id"] == item_id:
                item.update({"url": values["url"], "type": values["res_type"]})
                return item
        raise KeyError(item_id)


class HTTP:
    def __init__(self):
        self.registered = []
        self.error = None

    async def async_register_static_paths(self, paths):
        if self.error:
            raise self.error
        self.registered.extend(paths)


def make_hass(items=(), *, mode="storage"):
    store = ResourceStore(items)
    http = HTTP()
    return SimpleNamespace(http=http, data={"lovelace": SimpleNamespace(resource_mode=mode, resources=store)}), store


@pytest.mark.asyncio
async def test_new_install_serves_integration_file_and_registers_versioned_module(frontend_module):
    hass, resources = make_hass()
    await frontend_module.async_register_dashboard_cards(hass)
    assert len(hass.http.registered) == 1
    static = hass.http.registered[0]
    assert static.url_path == "/api/infuse/cards"
    assert static.path == str(Path(frontend_module.__file__).parent / "www")
    assert static.cache_headers is False
    assert Path(static.path, "infuse-dashboard-cards.js").is_file()
    assert resources.created == [{
        "id": "card-1", "type": "module",
        "url": "/api/infuse/cards/infuse-dashboard-cards.js?v=0.2.12",
    }]


@pytest.mark.asyncio
async def test_idempotent_registration_preserves_unrelated_user_cards(frontend_module):
    other = {"id": "other", "type": "module", "url": "/hacsfiles/different-card/ui.js?v=2"}
    hass, resources = make_hass([other])
    await frontend_module.async_register_dashboard_cards(hass)
    await frontend_module.async_register_dashboard_cards(hass)
    assert len(resources.created) == 1
    assert len(resources.current) == 2
    assert resources.current[0] == other
    assert resources.updated == []


@pytest.mark.asyncio
async def test_update_existing_bundle_url_without_adding_resource(frontend_module):
    item = {
        "id": "existing", "type": "module",
        "url": "/api/infuse/cards/infuse-dashboard-cards.js?v=0.2.10",
    }
    hass, resources = make_hass([item])
    await frontend_module.async_register_dashboard_cards(hass)
    assert resources.created == []
    assert resources.updated == [("existing", {
        "url": "/api/infuse/cards/infuse-dashboard-cards.js?v=0.2.12",
        "res_type": "module",
    })]
    assert len(resources.current) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("legacy_url", [
    "/hacsfiles/ha-infuse-cards/infuse-dashboard-cards.js?hacstag=12",
    "/local/community/ha-infuse-cards/infuse-dashboard-cards.js?v=0.1.3",
    "/local/infuse-now-playing-card.js",
    "/local/infuse-household-card.js",
    "/local/infuse-dashboard-cards.js",
])
async def test_legacy_plugin_remains_untouched_without_duplicate_resource(frontend_module, legacy_url):
    existing = {"id": "legacy", "type": "module", "url": legacy_url}
    hass, store = make_hass([existing])
    await frontend_module.async_register_dashboard_cards(hass)
    assert store.current == [existing]
    assert store.created == []
    assert store.updated == []
    assert len(hass.http.registered) == 1  # future migration needs only a reload


@pytest.mark.asyncio
async def test_after_uninstall_and_reload_bundled_cards_activate(frontend_module):
    legacy = {"id": "legacy", "type": "module", "url": "/hacsfiles/ha-infuse-cards/infuse-dashboard-cards.js"}
    hass, store = make_hass([legacy])
    await frontend_module.async_register_dashboard_cards(hass)
    store.saved = []  # uninstall/remove old resource in HA settings
    store.loaded = False
    await frontend_module.async_register_dashboard_cards(hass)
    assert len(store.current) == 1
    assert store.current[0]["url"].startswith(frontend_module.CARD_PATH)


@pytest.mark.asyncio
async def test_yaml_resource_mode_does_not_modify_resource_config(frontend_module):
    hass, store = make_hass([], mode="yaml")
    await frontend_module.async_register_dashboard_cards(hass)
    assert len(hass.http.registered) == 1
    assert not store.loaded
    assert not store.created


@pytest.mark.asyncio
async def test_no_lovelace_still_serves_files(frontend_module):
    hass, store = make_hass()
    del hass.data["lovelace"]
    await frontend_module.async_register_dashboard_cards(hass)
    assert len(hass.http.registered) == 1
    assert not store.created


@pytest.mark.asyncio
async def test_path_already_registered_can_still_manage_resource(frontend_module):
    hass, store = make_hass()
    hass.http.error = RuntimeError("already registered")
    await frontend_module.async_register_dashboard_cards(hass)
    assert len(store.created) == 1


@pytest.mark.asyncio
async def test_unserved_directory_never_creates_broken_dashboard_resource(frontend_module):
    hass, store = make_hass()
    hass.http.error = OSError("path inaccessible")
    await frontend_module.async_register_dashboard_cards(hass)
    assert store.created == []


def test_only_known_legacy_urls_are_detected(frontend_module):
    assert frontend_module._is_legacy_card_resource(
        "/hacsfiles/ha-infuse-cards/infuse-dashboard-cards.js?hacstag=33"
    )
    assert not frontend_module._is_legacy_card_resource(
        "/hacsfiles/a-different-project/infuse-dashboard-cards.js"
    )
    assert not frontend_module._is_legacy_card_resource("/local/my-other-custom-card.js")
