"""Domyos Rower integration (Bluetooth, works through HA Bluetooth proxies)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DomyosRowerCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data.get(CONF_NAME, "Domyos Rower")
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()

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
    return unloaded
