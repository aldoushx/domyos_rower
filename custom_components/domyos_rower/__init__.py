"""Domyos Rower integration (Bluetooth, works through HA Bluetooth proxies)."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .websocket import async_register_websocket

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)
CARD_URL = f"/{DOMAIN}/domyos-rower-card.js"
_CARD_FLAG = f"{DOMAIN}_card_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and load it in the frontend (once)."""
    if hass.data.get(_CARD_FLAG) or getattr(hass, "http", None) is None:
        return
    hass.data[_CARD_FLAG] = True
    try:
        import json

        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig

        folder = Path(__file__).parent / "frontend"
        version = json.loads((Path(__file__).parent / "manifest.json").read_text())["version"]
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(folder / "domyos-rower-card.js"), False)]
        )
        add_extra_js_url(hass, f"{CARD_URL}?v={version}")
    except Exception as err:  # noqa: BLE001 - the card is optional, never block the integration
        _LOGGER.warning("Impossible d'enregistrer la carte Lovelace Domyos Rower : %s", err)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _async_register_card(hass)
    async_register_websocket(hass)
    coordinator = DomyosRowerCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data.get(CONF_NAME, "Domyos Rower")
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_load()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.async_start()

    # Reload only when the *options* change (refreshed Garmin tokens also update the entry).
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
            hass.data.pop(DOMAIN)
    return unloaded
