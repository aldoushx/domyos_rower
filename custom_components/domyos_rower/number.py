"""Resistance target (read/write) for the Domyos proprietary protocol."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([DomyosRowerResistanceNumber(hass.data[DOMAIN][entry.entry_id])])


class DomyosRowerResistanceNumber(DomyosRowerEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "resistance_target")

    @property
    def native_min_value(self) -> float:
        return self.coordinator.resistance_range[0]

    @property
    def native_max_value(self) -> float:
        return self.coordinator.resistance_range[1]

    @property
    def native_step(self) -> float:
        return self.coordinator.resistance_range[2]

    @property
    def available(self) -> bool:
        return self.coordinator.can_set_resistance

    @property
    def native_value(self) -> float | None:
        return self.coordinator.resistance_target

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_resistance(value)
