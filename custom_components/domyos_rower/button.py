"""Buttons: regenerate the export files, send the last session to Garmin Connect (manual only)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .entity import DomyosRowerEntity


@dataclass(frozen=True, kw_only=True)
class RowerButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[DomyosRowerCoordinator], Awaitable[object]]
    available_fn: Callable[[DomyosRowerCoordinator], bool]


BUTTONS: tuple[RowerButtonDescription, ...] = (
    RowerButtonDescription(
        key="generate_files",
        icon="mdi:file-export",
        press_fn=lambda c: c.async_generate_files(),
        available_fn=lambda c: c.has_session and not c.recording,
    ),
    RowerButtonDescription(
        key="upload_garmin",
        icon="mdi:upload",
        press_fn=lambda c: c.async_upload_garmin(),
        available_fn=lambda c: (
            c.garmin_configured
            and (c.has_session or bool((c.last_session or {}).get("files")))
            and not c.recording
            and not c.garmin_busy
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DomyosRowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        DomyosRowerButton(coordinator, desc)
        for desc in BUTTONS
        # the Garmin button only exists when a Garmin account is linked
        if desc.key != "upload_garmin" or coordinator.garmin_configured
    )


class DomyosRowerButton(DomyosRowerEntity, ButtonEntity):
    entity_description: RowerButtonDescription

    def __init__(self, coordinator: DomyosRowerCoordinator, description: RowerButtonDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return self.entity_description.available_fn(self.coordinator)

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator)
