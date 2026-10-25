"""Real Home Assistant tests: config flow and options flow."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.domyos_rower.const import DOMAIN
from custom_components.domyos_rower.coordinator import DomyosRowerCoordinator

ADDR = "FC:6E:C4:46:1F:19"
LIST = "custom_components.domyos_rower.config_flow.async_discovered_service_info"
SETUP = "custom_components.domyos_rower.async_setup_entry"


@pytest.fixture(autouse=True)
def no_bluetooth(hass):
    hass.config.components.update({"bluetooth", "bluetooth_adapters"})
    with patch.object(DomyosRowerCoordinator, "async_start", lambda self: None):
        yield


def discovery():
    device = BLEDevice(ADDR, "Domyos-ROW-0136", {}, rssi=-70)
    adv = AdvertisementData(
        local_name="Domyos-ROW-0136", manufacturer_data={}, service_data={},
        service_uuids=["00001826-0000-1000-8000-00805f9b34fb"], rssi=-70, tx_power=None, platform_data=(),
    )
    return BluetoothServiceInfoBleak.from_device_and_advertisement_data(device, adv, "local", 0.0, True)


async def start_user_flow(hass):
    with patch(LIST, return_value=[SimpleNamespace(address=ADDR, name="Domyos-ROW-0136")]):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["step_id"] == "user"
        return await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ADDRESS: ADDR})


async def test_user_flow_creates_entry(hass):
    result = await start_user_flow(hass)
    # no more optional step: the entry is created straight away
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADDRESS: ADDR, CONF_NAME: "Domyos-ROW-0136"}


async def test_bluetooth_discovery_flow(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_BLUETOOTH}, data=discovery()
    )
    assert result["step_id"] == "bluetooth_confirm"
    with patch(SETUP, return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Domyos-ROW-0136"


async def make_entry(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_ADDRESS: ADDR, CONF_NAME: "Domyos-ROW-0136"}, unique_id=ADDR)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_options_flow_folder_and_reload(hass, tmp_path):
    entry = await make_entry(hass)
    before = hass.data[DOMAIN][entry.entry_id]
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    keys = {str(k) for k in result["data_schema"].schema}
    assert {"output_dir", "gpx_latitude", "gpx_longitude", "setup_garmin"} <= keys
    assert "sport_type" not in keys and "remove_garmin" not in keys

    # a folder that cannot be created is refused
    blocker = tmp_path / "file"
    blocker.write_text("x")
    bad = await hass.config_entries.options.async_configure(
        result["flow_id"], {"output_dir": str(blocker / "sub"), "gpx_latitude": 48.0, "gpx_longitude": 2.0}
    )
    assert bad["type"] is FlowResultType.FORM and bad["errors"] == {"output_dir": "cannot_write"}

    good = await hass.config_entries.options.async_configure(
        result["flow_id"], {"output_dir": str(tmp_path / "out"), "gpx_latitude": 48.0, "gpx_longitude": 2.0}
    )
    assert good["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["output_dir"] == str(tmp_path / "out")
    assert (tmp_path / "out").is_dir()
    assert hass.data[DOMAIN][entry.entry_id] is not before              # options change reloads the entry
