"""Single automation-friendly sensor for actively playing video."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import InfuseCoordinator
from .entity import InfuseEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: InfuseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InfuseActiveSensor(coordinator, entry)])


class InfuseActiveSensor(InfuseEntity, BinarySensorEntity):
    _attr_translation_key = "playing"
    _attr_icon = "mdi:movie-play"

    def __init__(self, coordinator: InfuseCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "playing")

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.state == "playing" if data else None
