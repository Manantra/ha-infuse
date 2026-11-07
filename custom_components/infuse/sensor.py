"""Small, useful sensor set; avoid duplicating media player attributes."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import InfuseCoordinator
from .entity import InfuseEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator: InfuseCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InfuseSensor(coordinator, entry, key) for key in ("progress", "remaining", "latency")])


class InfuseSensor(InfuseEntity, SensorEntity):
    """Progress, remaining minutes and optional diagnostic latency."""

    def __init__(self, coordinator: InfuseCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator, entry, key)
        self._key = key
        self._attr_translation_key = key
        if key == "progress":
            self._attr_native_unit_of_measurement = "%"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:progress-clock"
        elif key == "remaining":
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_icon = "mdi:timer-sand"
        else:
            self._attr_native_unit_of_measurement = "ms"
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False
            self._attr_icon = "mdi:lan-connect"

    @property
    def native_value(self) -> float | int | None:
        data = self.coordinator.data
        if not data:
            return None
        if self._key == "progress":
            return data.progress
        if self._key == "remaining":
            return round(data.remaining_seconds / 60, 1) if data.remaining_seconds is not None else None
        return data.latency_ms
