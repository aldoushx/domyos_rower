"""Domyos Rower integration (Bluetooth, works through HA Bluetooth proxies)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator

PLATFORMS = [Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DomyosRowerCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data.get(CONF_NAME, "Domyos Rower")
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: DomyosRowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
