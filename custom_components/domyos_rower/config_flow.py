"""Config flow: Bluetooth discovery, then an optional Strava link; options for the export."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_GPX_LAT,
    CONF_GPX_LON,
    CONF_OUTPUT_DIR,
    CONF_PROTOCOL,
    CONF_SPORT_TYPE,
    CONF_STRAVA,
    DEFAULT_SPORT_TYPE,
    DOMAIN,
    PROTOCOL_AUTO,
    PROTOCOLS,
    SPORT_TYPES,
)
from .coordinator import default_output_dir
from .strava import StravaAuthError, StravaClient, StravaError, authorize_url, extract_code

_LOGGER = logging.getLogger(__name__)

CONF_SETUP_STRAVA = "setup_strava"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"


class DomyosRowerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._devices: dict[str, str] = {}
        self._device: dict[str, str] = {}
        self._strava: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "DomyosRowerOptionsFlow":
        return DomyosRowerOptionsFlow()

    # ------------------------------------------------------------ device
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        if user_input is not None:
            self._device = {
                CONF_ADDRESS: self._discovery.address,
                CONF_NAME: self._discovery.name,
            }
            return await self.async_step_strava_ask()
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery.name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            name = self._devices.get(address, "Domyos Rower").split(" (")[0]
            self._device = {CONF_ADDRESS: address, CONF_NAME: name}
            return await self.async_step_strava_ask()

        current = self._async_current_ids()
        for info in async_discovered_service_info(self.hass, True):
            if info.address in current:
                continue
            if (info.name or "").upper().startswith("DOMYOS-ROW"):
                self._devices[info.address] = f"{info.name} ({info.address})"

        if not self._devices:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(self._devices)}),
        )

    # ------------------------------------------------------------ optional Strava
    def _create_entry(self) -> ConfigFlowResult:
        data: dict[str, Any] = dict(self._device)
        if self._strava:
            data[CONF_STRAVA] = self._strava
        return self.async_create_entry(title=self._device[CONF_NAME], data=data)

    async def async_step_strava_ask(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input.get(CONF_SETUP_STRAVA):
                return await self.async_step_strava_app()
            return self._create_entry()
        return self.async_show_form(
            step_id="strava_ask",
            data_schema=vol.Schema({vol.Required(CONF_SETUP_STRAVA, default=False): bool}),
        )

    async def async_step_strava_app(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = user_input[CONF_CLIENT_ID].strip()
            client_secret = user_input[CONF_CLIENT_SECRET].strip()
            if not client_id.isdigit():
                errors[CONF_CLIENT_ID] = "invalid_client_id"
            elif not client_secret:
                errors[CONF_CLIENT_SECRET] = "invalid_client_secret"
            else:
                self._strava = {"client_id": client_id, "client_secret": client_secret}
                return await self.async_step_strava_code()
        return self.async_show_form(
            step_id="strava_app",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID, default=self._strava.get("client_id", "")): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                }
            ),
            errors=errors,
        )

    async def async_step_strava_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = StravaClient(
                async_get_clientsession(self.hass),
                self._strava["client_id"],
                self._strava["client_secret"],
            )
            try:
                tokens = await client.exchange_code(extract_code(user_input["code"]))
            except StravaAuthError:
                errors["base"] = "strava_auth_failed"
            except StravaError:
                errors["base"] = "strava_cannot_connect"
            else:
                self._strava = {**self._strava, **tokens}
                return self._create_entry()
        return self.async_show_form(
            step_id="strava_code",
            data_schema=vol.Schema({vol.Required("code"): str}),
            description_placeholders={"url": authorize_url(self._strava["client_id"])},
            errors=errors,
        )


class DomyosRowerOptionsFlow(OptionsFlow):
    """Where the TCX/GPX files go, Strava activity type, placeholder GPX position."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        opts = self.config_entry.options
        if user_input is not None:
            folder = (user_input.get(CONF_OUTPUT_DIR) or "").strip()
            if folder:
                try:
                    await self.hass.async_add_executor_job(_check_writable, folder)
                except OSError:
                    errors[CONF_OUTPUT_DIR] = "cannot_write"
            if not errors:
                return self.async_create_entry(data={**user_input, CONF_OUTPUT_DIR: folder})

        default_dir = opts.get(CONF_OUTPUT_DIR) or await self.hass.async_add_executor_job(
            default_output_dir, self.hass
        )
        schema: dict[Any, Any] = {
            vol.Optional(
                CONF_PROTOCOL, default=opts.get(CONF_PROTOCOL, PROTOCOL_AUTO)
            ): SelectSelector(
                SelectSelectorConfig(options=PROTOCOLS, translation_key="protocol", mode="list")
            ),
            vol.Optional(CONF_OUTPUT_DIR, default=default_dir): str,
            vol.Optional(
                CONF_GPX_LAT, default=opts.get(CONF_GPX_LAT, self.hass.config.latitude)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_GPX_LON, default=opts.get(CONF_GPX_LON, self.hass.config.longitude)
            ): vol.Coerce(float),
        }
        if CONF_STRAVA in self.config_entry.data:
            schema[
                vol.Optional(CONF_SPORT_TYPE, default=opts.get(CONF_SPORT_TYPE, DEFAULT_SPORT_TYPE))
            ] = vol.In(SPORT_TYPES)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )


def _check_writable(folder: str) -> None:
    import os

    os.makedirs(folder, exist_ok=True)
    probe = os.path.join(folder, ".write_test")
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write("ok")
    os.remove(probe)
