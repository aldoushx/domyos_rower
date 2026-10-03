"""Switch to free the rower for another Bluetooth client (phone, QZ...)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([DomyosRowerConnectionSwitch(hass.data[DOMAIN][entry.entry_id])])


class DomyosRowerConnectionSwitch(DomyosRowerEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "connection")

    @property
    def is_on(self) -> bool:
        return self.coordinator.enabled

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_enabled(False)
