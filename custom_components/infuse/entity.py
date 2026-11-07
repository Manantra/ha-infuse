"""Common Home Assistant entity attributes for one Infuse endpoint."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import InfuseCoordinator


class InfuseEntity(CoordinatorEntity[InfuseCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: InfuseCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id or entry.entry_id}_{suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id or entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Firecore",
            "model": "Infuse / Now Playing API",
        }
