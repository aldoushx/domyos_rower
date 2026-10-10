"""Config flow: Bluetooth discovery; options for the export folder and the optional Garmin link."""
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
from homeassistant.requirements import async_process_requirements
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    CONF_GARMIN,
    CONF_GPX_LAT,
    CONF_GPX_LON,
    CONF_OUTPUT_DIR,
    DOMAIN,
)
from .coordinator import default_output_dir
from . import garmin

_LOGGER = logging.getLogger(__name__)

CONF_SETUP_GARMIN = "setup_garmin"
CONF_REMOVE_GARMIN = "remove_garmin"
CONF_GARMIN_EMAIL = "email"
CONF_GARMIN_PASSWORD = "password"
CONF_GARMIN_CODE = "code"
CONF_CLIENT_SECRET = "client_secret"


class DomyosRowerConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._devices: dict[str, str] = {}
        self._device: dict[str, str] = {}

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
            return self._create_entry()
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
            return self._create_entry()

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

    def _create_entry(self) -> ConfigFlowResult:
        return self.async_create_entry(title=self._device[CONF_NAME], data=dict(self._device))


class DomyosRowerOptionsFlow(OptionsFlow):
    """Export folder, placeholder GPX position, optional Garmin link."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}
        self._garmin_api: Any = None
        self._garmin_email = ""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        opts = self.config_entry.options
        linked = bool(self.config_entry.data.get(CONF_GARMIN, {}).get("tokens"))
        if user_input is not None:
            user_input = dict(user_input)
            setup_garmin = user_input.pop(CONF_SETUP_GARMIN, False)
            remove_garmin = user_input.pop(CONF_REMOVE_GARMIN, False)
            folder = (user_input.get(CONF_OUTPUT_DIR) or "").strip()
            if folder:
                try:
                    await self.hass.async_add_executor_job(_check_writable, folder)
                except OSError:
                    errors[CONF_OUTPUT_DIR] = "cannot_write"
            if not errors:
                self._options = {**user_input, CONF_OUTPUT_DIR: folder}
                if linked and not remove_garmin and not setup_garmin:
                    self._options[CONF_GARMIN] = opts.get(CONF_GARMIN, True)
                if remove_garmin and linked:
                    data = {k: v for k, v in self.config_entry.data.items() if k != CONF_GARMIN}
                    self.hass.config_entries.async_update_entry(self.config_entry, data=data)
                    return self.async_create_entry(data=self._options)
                if setup_garmin:
                    return await self.async_step_garmin()
                return self.async_create_entry(data=self._options)

        default_dir = opts.get(CONF_OUTPUT_DIR) or await self.hass.async_add_executor_job(
            default_output_dir, self.hass
        )
        schema: dict[Any, Any] = {
            vol.Optional(CONF_OUTPUT_DIR, default=default_dir): str,
            vol.Optional(
                CONF_GPX_LAT, default=opts.get(CONF_GPX_LAT, self.hass.config.latitude)
            ): vol.Coerce(float),
            vol.Optional(
                CONF_GPX_LON, default=opts.get(CONF_GPX_LON, self.hass.config.longitude)
            ): vol.Coerce(float),
        }
        schema[vol.Optional(CONF_SETUP_GARMIN, default=False)] = bool
        if linked:
            schema[vol.Optional(CONF_REMOVE_GARMIN, default=False)] = bool
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )

    # ------------------------------------------------------------ optional Garmin Connect
    async def async_step_garmin(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_GARMIN_EMAIL].strip()
            try:
                await async_process_requirements(self.hass, DOMAIN, [garmin.GARMIN_REQUIREMENT])
                api, needs_mfa = await self.hass.async_add_executor_job(
                    garmin.start_login, email, user_input[CONF_GARMIN_PASSWORD]
                )
            except garmin.GarminAuthError:
                errors["base"] = "garmin_auth_failed"
            except garmin.GarminError:
                errors["base"] = "garmin_cannot_connect"
            except Exception:  # noqa: BLE001 - requirement install failure etc.
                errors["base"] = "garmin_cannot_connect"
            else:
                self._garmin_email = email
                self._garmin_api = api
                if needs_mfa:
                    return await self.async_step_garmin_mfa()
                return await self._finish_garmin()
        return self.async_show_form(
            step_id="garmin",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GARMIN_EMAIL, default=self._garmin_email): str,
                    vol.Required(CONF_GARMIN_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_garmin_mfa(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    garmin.finish_mfa, self._garmin_api, user_input[CONF_GARMIN_CODE]
                )
            except garmin.GarminAuthError:
                errors["base"] = "garmin_mfa_failed"
            except garmin.GarminError:
                errors["base"] = "garmin_cannot_connect"
            else:
                return await self._finish_garmin()
        return self.async_show_form(
            step_id="garmin_mfa",
            data_schema=vol.Schema({vol.Required(CONF_GARMIN_CODE): str}),
            errors=errors,
        )

    async def _finish_garmin(self) -> ConfigFlowResult:
        tokens = await self.hass.async_add_executor_job(garmin.dump_tokens, self._garmin_api)
        self._garmin_api = None  # the password never leaves the library object, and is dropped here
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_GARMIN: {"email": self._garmin_email, "tokens": tokens},
            },
        )
        # the "garmin" option changes so the entry reloads and the upload button appears
        self._options[CONF_GARMIN] = self._garmin_email
        return self.async_create_entry(data=self._options)


def _check_writable(folder: str) -> None:
    import os

    os.makedirs(folder, exist_ok=True)
    probe = os.path.join(folder, ".write_test")
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write("ok")
    os.remove(probe)
