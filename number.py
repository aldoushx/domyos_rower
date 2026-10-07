"""Resistance target (read/write) for the Domyos proprietary protocol."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DISTANCE_SCALE_MAX, DISTANCE_SCALE_MIN, DOMAIN
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [DomyosRowerResistanceNumber(coordinator), DomyosRowerDistanceScaleNumber(coordinator)]
    )


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


class DomyosRowerDistanceScaleNumber(DomyosRowerEntity, RestoreNumber):
    """Calibration multiplier (1.00 = rower values as they are), kept across restarts."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = DISTANCE_SCALE_MIN
    _attr_native_max_value = DISTANCE_SCALE_MAX
    _attr_native_step = 0.01
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:ruler"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "distance_scale")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self.coordinator.async_set_distance_scale(last.native_value)

    @property
    def available(self) -> bool:
        return True  # a setting: usable even when the rower is asleep

    @property
    def native_value(self) -> float:
        return self.coordinator.distance_scale

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.async_set_distance_scale(value)
