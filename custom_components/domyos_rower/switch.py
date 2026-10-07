"""Switch to free the rower for another Bluetooth client (phone, QZ...)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DomyosRowerConnectionSwitch(coordinator),
            DomyosRowerRecordingSwitch(coordinator),
            DomyosRowerDisplaySwitch(coordinator),
        ]
    )


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


class DomyosRowerRecordingSwitch(DomyosRowerEntity, SwitchEntity):
    """On = recording the session; off = stop, the TCX and GPX files are written."""

    _attr_icon = "mdi:record-rec"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "recording")

    @property
    def is_on(self) -> bool:
        return self.coordinator.recording

    @property
    def extra_state_attributes(self) -> dict:
        rec = self.coordinator.recorder
        return {
            "samples": len(rec.samples) if rec else 0,
            "started": rec.start.isoformat() if rec and self.coordinator.recording else None,
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_start_recording()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_stop_recording()


class DomyosRowerDisplaySwitch(DomyosRowerEntity, SwitchEntity, RestoreEntity):
    """Experimental: write the workout values on the console screen (Domyos protocol only)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:monitor-dashboard"

    def __init__(self, coordinator: DomyosRowerCoordinator) -> None:
        super().__init__(coordinator, "console_display")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state == "on":
            self.coordinator.async_set_console_display(True)

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.console_display

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "protocol": self.coordinator.mode,
            "has_effect": self.coordinator.mode == "proprietary",
        }

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.async_set_console_display(True)

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.async_set_console_display(False)
