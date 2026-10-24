"""Workout selection: the program that starts with the session."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity
from .workouts import NO_WORKOUT, WorkoutError


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([DomyosRowerWorkoutSelect(hass.data[DOMAIN][entry.entry_id])])


class DomyosRowerWorkoutSelect(DomyosRowerEntity, SelectEntity):
    _attr_icon = "mdi:chart-areaspline"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "workout")

    @property
    def options(self) -> list[str]:
        return [NO_WORKOUT] + [w["name"] for w in self.coordinator.workouts]

    @property
    def current_option(self) -> str:
        return self.coordinator.selected_workout_name or NO_WORKOUT

    async def async_select_option(self, option: str) -> None:
        wid = next((w["id"] for w in self.coordinator.workouts if w["name"] == option), None)
        try:
            await self.coordinator.async_select_workout(wid)
        except WorkoutError as err:
            raise HomeAssistantError(str(err)) from err
