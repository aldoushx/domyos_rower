"""Domyos Rower integration (Bluetooth, works through HA Bluetooth proxies)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

SERVICE_DISPLAY_PROBE = "display_probe"
SERVICE_CONSOLE_WORKOUT = "console_workout"

# Bytes are given as {"16": 30}: YAML/JSON keys are strings.
_BYTES = vol.Schema({vol.Coerce(int): vol.All(vol.Coerce(int), vol.Range(min=0, max=255))})
DISPLAY_PROBE_SCHEMA = vol.Schema(
    {
        vol.Optional("preset", default="none"): vol.In(["none", "numbered"]),
        vol.Optional("values"): _BYTES,
        vol.Optional("odometer_values"): _BYTES,
        vol.Optional("duration", default=30): vol.All(vol.Coerce(float), vol.Range(min=1, max=120)),
    }
)
CONSOLE_WORKOUT_SCHEMA = vol.Schema({vol.Required("action"): vol.In(["start", "stop"])})


def _coordinators(hass: HomeAssistant) -> list[DomyosRowerCoordinator]:
    found = [c for c in hass.data.get(DOMAIN, {}).values() if isinstance(c, DomyosRowerCoordinator)]
    if not found:
        raise ServiceValidationError("Aucun rameur Domyos n'est configuré.")
    return found


def _register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_DISPLAY_PROBE):
        return

    async def display_probe(call: ServiceCall) -> None:
        for coordinator in _coordinators(hass):
            coordinator.async_probe_display(
                call.data.get("values"),
                call.data.get("odometer_values"),
                call.data["preset"],
                call.data["duration"],
            )

    async def console_workout(call: ServiceCall) -> None:
        for coordinator in _coordinators(hass):
            coordinator.async_console_workout(call.data["action"])

    hass.services.async_register(DOMAIN, SERVICE_DISPLAY_PROBE, display_probe, DISPLAY_PROBE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CONSOLE_WORKOUT, console_workout, CONSOLE_WORKOUT_SCHEMA)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DomyosRowerCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data.get(CONF_NAME, "Domyos Rower")
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()
    _register_services(hass)

    # Reload only when the *options* change (refreshed Strava tokens also update the entry).
    seen_options = dict(entry.options)

    async def _options_updated(hass: HomeAssistant, updated: ConfigEntry) -> None:
        nonlocal seen_options
        if dict(updated.options) != seen_options:
            seen_options = dict(updated.options)
            await hass.config_entries.async_reload(updated.entry_id)

    entry.async_on_unload(entry.add_update_listener(_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: DomyosRowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_DISPLAY_PROBE)
            hass.services.async_remove(DOMAIN, SERVICE_CONSOLE_WORKOUT)
    return unloaded
