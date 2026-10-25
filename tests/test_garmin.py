"""Garmin Connect link (options flow), manual upload button, and the garminconnect wrapper."""
from __future__ import annotations

import sys
import types
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError

from custom_components.domyos_rower import garmin
from custom_components.domyos_rower.const import DOMAIN
from custom_components.domyos_rower.coordinator import DomyosRowerCoordinator

ADDR = "FC:6E:C4:46:1F:19"
CF = "custom_components.domyos_rower.config_flow"
CO = "custom_components.domyos_rower.coordinator"


@pytest.fixture(autouse=True)
def no_bluetooth(hass):
    hass.config.components.update({"bluetooth", "bluetooth_adapters"})
    with patch.object(DomyosRowerCoordinator, "async_start", lambda self: None):
        yield


async def make_entry(hass, garmin_conf=None):
    data = {CONF_ADDRESS: ADDR, CONF_NAME: "Domyos-ROW-0136"}
    if garmin_conf:
        data["garmin"] = garmin_conf
    entry = MockConfigEntry(domain=DOMAIN, data=data, unique_id=ADDR)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def base_input(tmp_path, **extra):
    return {"output_dir": str(tmp_path), "gpx_latitude": 48.0, "gpx_longitude": 2.0, **extra}


async def test_link_without_mfa(hass, tmp_path):
    entry = await make_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], base_input(tmp_path, setup_garmin=True)
    )
    assert result["step_id"] == "garmin"
    with patch(f"{CF}.async_process_requirements"), patch.object(
        garmin, "start_login", return_value=(object(), False)
    ) as start, patch.object(garmin, "dump_tokens", return_value='{"di_token": "T"}'):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"email": " me@x.fr ", "password": "pw"}
        )
    start.assert_called_once_with("me@x.fr", "pw")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.data["garmin"] == {"email": "me@x.fr", "tokens": '{"di_token": "T"}'}
    assert "pw" not in str(entry.data) and "pw" not in str(entry.options)      # password never stored
    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.garmin_configured and entry.options["garmin"] == "me@x.fr"


async def test_link_with_mfa_and_errors(hass, tmp_path):
    entry = await make_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], base_input(tmp_path, setup_garmin=True)
    )
    with patch(f"{CF}.async_process_requirements"), patch.object(
        garmin, "start_login", side_effect=garmin.GarminAuthError("no")
    ):
        bad = await hass.config_entries.options.async_configure(
            result["flow_id"], {"email": "a@b.c", "password": "x"}
        )
    assert bad["type"] is FlowResultType.FORM and bad["errors"] == {"base": "garmin_auth_failed"}

    with patch(f"{CF}.async_process_requirements"), patch.object(
        garmin, "start_login", return_value=(object(), True)
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"email": "a@b.c", "password": "x"}
        )
    assert result["step_id"] == "garmin_mfa"
    with patch.object(garmin, "finish_mfa", side_effect=garmin.GarminAuthError("code")):
        bad = await hass.config_entries.options.async_configure(result["flow_id"], {"code": "000000"})
    assert bad["errors"] == {"base": "garmin_mfa_failed"}
    with patch.object(garmin, "finish_mfa") as fin, patch.object(
        garmin, "dump_tokens", return_value='{"di_token": "M"}'
    ):
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"code": "123456"})
    fin.assert_called_once()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.data["garmin"]["tokens"] == '{"di_token": "M"}'


async def test_remove_link(hass, tmp_path):
    entry = await make_entry(hass, {"email": "a@b.c", "tokens": "{}"})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "remove_garmin" in {str(k) for k in result["data_schema"].schema}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], base_input(tmp_path, remove_garmin=True)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "garmin" not in entry.data


async def test_upload_button_flow(hass, tmp_path):
    entry = await make_entry(hass, {"email": "a@b.c", "tokens": "OLD"})
    co: DomyosRowerCoordinator = hass.data[DOMAIN][entry.entry_id]
    fit = tmp_path / "s.fit"
    fit.write_bytes(b"FIT")
    co.last_session = {"start": "x", "files": {"fit": str(fit)}}
    with patch(f"{CO}.async_process_requirements"), patch.object(
        garmin, "upload_file", return_value=({"activity_id": 5}, "NEW")
    ) as up:
        result = await co.async_upload_garmin()
    up.assert_called_once_with("OLD", str(fit))
    assert result == {"activity_id": 5}
    assert entry.data["garmin"]["tokens"] == "NEW"                                  # refreshed tokens kept
    assert co.last_session["garmin"]["status"] == "uploaded" and co.last_session["garmin"]["activity_id"] == 5
    assert not co.garmin_busy

    with patch(f"{CO}.async_process_requirements"), patch.object(
        garmin, "upload_file", side_effect=garmin.GarminError("déjà importée")
    ):
        with pytest.raises(HomeAssistantError, match="déjà importée"):
            await co.async_upload_garmin()
    assert co.last_session["garmin"]["status"] == "error" and not co.garmin_busy


async def test_upload_refused_without_config_or_session(hass):
    entry = await make_entry(hass)
    co = hass.data[DOMAIN][entry.entry_id]
    with pytest.raises(HomeAssistantError):
        await co.async_upload_garmin()
    entry2 = await make_entry_other(hass)
    co2 = hass.data[DOMAIN][entry2.entry_id]
    with pytest.raises(HomeAssistantError, match="Aucune séance"):
        await co2.async_upload_garmin()


async def make_entry_other(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ADDRESS: "AA:BB:CC:DD:EE:FF", CONF_NAME: "x", "garmin": {"email": "a", "tokens": "T"}},
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# ---------------------------------------------------------------- the wrapper, with a fake library
class _AuthErr(Exception): ...
class _TooMany(Exception): ...


def fake_lib(upload_result=None, upload_exc=None, login_exc=None):
    mod = types.ModuleType("garminconnect")
    mod.GarminConnectAuthenticationError = _AuthErr
    mod.GarminConnectTooManyRequestsError = _TooMany

    class Client:
        def dumps(self):
            return "REFRESHED"

    class Garmin:
        def __init__(self, *a, **k):
            self.client = Client()

        def login(self, tokenstore=None):
            if login_exc:
                raise login_exc
            return None, None

        def upload_activity(self, path):
            if upload_exc:
                raise upload_exc
            return upload_result

    mod.Garmin = Garmin
    return mod


def test_wrapper_success_and_failures():
    ok = {"detailedImportResult": {"successes": [{"internalId": 77}], "failures": []}}
    with patch.dict(sys.modules, {"garminconnect": fake_lib(ok)}):
        assert garmin.upload_file("T", "/x.fit") == ({"activity_id": 77}, "REFRESHED")
    dup = {"detailedImportResult": {"successes": [], "failures": [{"messages": [{"content": "Duplicate Activity"}]}]}}
    with patch.dict(sys.modules, {"garminconnect": fake_lib(dup)}), pytest.raises(garmin.GarminError, match="déjà"):
        garmin.upload_file("T", "/x.fit")
    with patch.dict(sys.modules, {"garminconnect": fake_lib(upload_exc=Exception("HTTP 409"))}), pytest.raises(
        garmin.GarminError, match="déjà"
    ):
        garmin.upload_file("T", "/x.fit")
    with patch.dict(sys.modules, {"garminconnect": fake_lib(login_exc=_AuthErr())}), pytest.raises(garmin.GarminAuthError):
        garmin.upload_file("T", "/x.fit")
    with patch.dict(sys.modules, {"garminconnect": fake_lib(upload_exc=_AuthErr())}), pytest.raises(garmin.GarminAuthError):
        garmin.upload_file("T", "/x.fit")
