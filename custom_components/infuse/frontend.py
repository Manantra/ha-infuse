"""Serve both bundled Lovelace cards and register one versioned resource.

The cards are intentionally delivered by the Infuse integration, not installed
as a second HACS plugin. Legacy resources are left untouched for safe migration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_DIRECTORY = Path(__file__).parent / "www"
CARD_FILENAME = "infuse-dashboard-cards.js"
CARD_BASE_URL = f"/api/{DOMAIN}/cards"
CARD_PATH = f"{CARD_BASE_URL}/{CARD_FILENAME}"

# These URLs have historically been installed by HACS/Marketplace or by hand.
# Never overwrite/delete an entry maintained by another integration or HACS.
LEGACY_RESOURCE_PREFIXES = (
    "/hacsfiles/ha-infuse-cards/",
    "/local/community/ha-infuse-cards/",
    "/local/community/infuse-dashboard-cards/",
)
LEGACY_RESOURCE_PATHS = frozenset({
    "/local/infuse-now-playing-card.js",
    "/local/infuse-household-card.js",
    "/local/infuse-dashboard-cards.js",
})


def _is_legacy_card_resource(url: str) -> bool:
    """Recognize only our old card URLs; unrelated Lovelace resources survive."""
    path = urlsplit(url).path.casefold()
    return path in LEGACY_RESOURCE_PATHS or path.startswith(LEGACY_RESOURCE_PREFIXES)


async def async_register_dashboard_cards(hass: HomeAssistant) -> None:
    """Expose local assets, then register/update the resource in storage mode.

    Lovelace's resource storage may be lazy-loaded. Calling async_get_info()
    first avoids losing the user's existing resource list on HA versions where
    async_create_item() did not itself force the storage collection to load.
    """
    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_BASE_URL, str(CARD_DIRECTORY), False),
        ])
    except RuntimeError:
        # Multiple integration setups or reloads can register the same path.
        _LOGGER.debug("Infuse dashboard cards path already registered")
    except (OSError, ValueError) as exc:
        _LOGGER.warning("Unable to serve bundled Infuse dashboard cards: %s", exc)
        return

    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.warning("Lovelace is not loaded; add %s manually as a module resource", CARD_PATH)
        return
    if getattr(lovelace, "resource_mode", "storage") != "storage":
        _LOGGER.info(
            "Lovelace resources use YAML; add %s as a module resource in configuration.yaml",
            CARD_PATH,
        )
        return

    resources = lovelace.resources
    try:
        # Important: do not call async_items() on an unloaded collection.
        await resources.async_get_info()
        registered = list(resources.async_items())
        bundle = [r for r in registered if urlsplit(r.get("url", "")).path == CARD_PATH]
        legacy = [r for r in registered if _is_legacy_card_resource(r.get("url", ""))]

        if legacy:
            _LOGGER.warning(
                "Legacy Infuse dashboard card resource(s) detected; uninstall the separate "
                "cards plugin or remove old /local/ card resource entries, then reload "
                "the Infuse integration to activate the bundled card. Existing dashboards "
                "and card configuration are preserved."
            )
            # Never install a duplicate module on a frontend still loading an
            # older copy. Migration is controlled by the user/HACS.
            if not bundle:
                return

        integration = await async_get_integration(hass, DOMAIN)
        version = integration.version
        desired_url = f"{CARD_PATH}?v={version}"
        if bundle:
            existing = bundle[0]
            if existing["url"] != desired_url or existing.get("type") != "module":
                await resources.async_update_item(
                    existing["id"], {"url": desired_url, "res_type": "module"},
                )
            return

        await resources.async_create_item({"url": desired_url, "res_type": "module"})
        _LOGGER.info("Registered bundled Infuse dashboard cards %s", version)
    except (HomeAssistantError, KeyError, RuntimeError, ValueError) as exc:
        # A resource registration issue must not prevent native Infuse entities
        # or automations from loading.
        _LOGGER.warning("Unable to register Infuse dashboard cards: %s", exc)
