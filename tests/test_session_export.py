"""Real Home Assistant tests: recording switch, automatic files on stop, files."""
from __future__ import annotations

import os
from unittest.mock import patch

import gpxpy
from garmin_fit_sdk import Decoder, Stream
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)
from tcxreader.tcxreader import TCXReader

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.domyos_rower.const import DOMAIN, EVENT_SESSION_SAVED
from custom_components.domyos_rower.coordinator import DomyosRowerCoordinator
from custom_components.domyos_rower.protocol import RowerData

ADDR = "FC:6E:C4:46:1F:19"


@pytest.fixture(autouse=True)
def no_bluetooth(hass):
    """No radio in the tests: the BLE loop is not started."""
    hass.config.components.update({"bluetooth", "bluetooth_adapters"})
    with patch.object(DomyosRowerCoordinator, "async_start", lambda self: None):
        yield


async def setup_entry(hass, tmp_path):
    data = {CONF_ADDRESS: ADDR, CONF_NAME: "Domyos-ROW-0136"}
    entry = MockConfigEntry(
        domain=DOMAIN, data=data, options={"output_dir": str(tmp_path / "export")}, unique_id=ADDR
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry, hass.data[DOMAIN][entry.entry_id]


def eid(hass, platform, key):
    found = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{ADDR}_{key}")
    assert found, f"{platform}.{key} not registered"
    return found


async def row_session(hass, coordinator, seconds=90, moving_until=None):
    """Drive a fake workout through the real recording switch."""
    coordinator.connected = True
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": eid(hass, "switch", "recording")}, blocking=True
    )
    assert coordinator.recording
    dist = 0.0
    for t in range(1, seconds + 1):
        moving = moving_until is None or t <= moving_until
        dist += 2.81 if moving else 0.0
        coordinator.data = RowerData(
            cadence=29.0 if moving else 0.0, strokes=t // 2, speed_kmh=10.11 if moving else 0.0,
            pace_s500=178 if moving else None, distance_m=round(dist, 1), calories=t // 10,
            power_w=62 if moving else 0, resistance=4, heart_rate=120 + t // 10, elapsed_s=t,
        )
        coordinator._sample(coordinator._rec_mono + t)
    await hass.async_block_till_done()


async def stop(hass):
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": eid(hass, "switch", "recording")}, blocking=True
    )
    await hass.async_block_till_done()


# --------------------------------------------------------------------------- files at the end
async def test_stop_writes_fit_tcx_and_gpx_and_never_uploads(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    events = async_capture_events(hass, EVENT_SESSION_SAVED)

    await row_session(hass, c, 90)
    sw = hass.states.get(eid(hass, "switch", "recording"))
    assert sw.state == "on" and sw.attributes["samples"] == 90
    # while recording: export buttons are unavailable
    assert hass.states.get(eid(hass, "button", "generate_files")).state == "unavailable"
    assert not os.path.exists(tmp_path / "export")          # nothing written until the end

    await stop(hass)

    files = sorted(os.listdir(tmp_path / "export"))
    assert [f.rsplit(".", 1)[1] for f in files] == ["fit", "gpx", "tcx"], files
    tcx_path = tmp_path / "export" / files[2]
    r = TCXReader().read(str(tcx_path), only_gps=False)
    assert len(r.trackpoints) == 90 and abs(r.distance - 252.9) < 1 and r.hr_max == 129
    g = gpxpy.parse(open(tmp_path / "export" / files[1]))
    assert len(g.tracks[0].segments[0].points) == 90 and g.tracks[0].type == "rowing"
    # FIT: decoded by Garmin's official decoder
    fit_msgs, fit_errors = Decoder(Stream.from_file(str(tmp_path / "export" / files[0]))).read()
    assert not fit_errors
    ses = fit_msgs["session_mesgs"][0]
    assert ses["sport"] == "rowing" and ses["sub_sport"] == "indoor_rowing" and ses["total_calories"] == 9
    assert ses["total_strokes"] == 45 and len(fit_msgs["record_mesgs"]) == 90

    # event for other integrations / automations
    assert len(events) == 1
    ev = events[0].data
    assert ev["fit"].endswith(".fit") and ev["tcx"].endswith(".tcx") and ev["gpx"].endswith(".gpx") and ev["folder"] == str(tmp_path / "export")
    assert ev["distance_m"] == pytest.approx(252.9, abs=0.2) and ev["duration_s"] == 90

    # last-session sensor
    last = hass.states.get(eid(hass, "sensor", "last_session"))
    assert last.state != "unknown" and last.attributes["tcx_file"] == ev["tcx"]
    assert last.attributes["fit_file"] == ev["fit"] and last.attributes["active_time_s"] == 89
    assert last.attributes["garmin_status"] == "not sent"

    # buttons are available now
    assert hass.states.get(eid(hass, "button", "generate_files")).state != "unavailable"
    assert not c.recording


async def test_regenerate_button_and_guard_while_recording(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    await row_session(hass, c, 30)
    with pytest.raises(HomeAssistantError):                    # can't export a running session
        await c.async_generate_files()
    await stop(hass)
    folder = tmp_path / "export"
    for f in os.listdir(folder):
        os.remove(folder / f)
    await hass.services.async_call(
        "button", "press", {"entity_id": eid(hass, "button", "generate_files")}, blocking=True
    )
    assert len(os.listdir(folder)) == 3                         # files recreated from the session in memory


async def test_no_garmin_button_when_not_linked(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    assert er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{ADDR}_upload_garmin") is None


async def test_empty_recording_creates_nothing(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": eid(hass, "switch", "recording")}, blocking=True
    )
    await stop(hass)
    assert not os.path.exists(tmp_path / "export")
    assert not c.has_session


async def test_gap_while_disconnected_and_console_reset(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    await row_session(hass, c, 40)
    c.connected = False                                         # BLE drops: no samples, wall clock keeps going
    for t in range(41, 51):
        c._sample(c._rec_mono + t)
    c.connected = True
    c.data = RowerData(cadence=29.0, strokes=1, speed_kmh=10.0, pace_s500=180, distance_m=3.0, calories=0, resistance=4)
    c._sample(c._rec_mono + 51)                                 # console counters restarted from 0
    await stop(hass)
    s = c.recorder.summary()
    assert s["duration_s"] == 51 and s["distance_m"] > 110      # distance kept growing across the reset
    assert len(c.recorder.samples) == 41


# --------------------------------------------------------------------------- Strava, manual only
async def test_last_session_survives_restart(hass, tmp_path, hass_storage):
    entry, c = await setup_entry(hass, tmp_path)
    await row_session(hass, c, 45)
    await stop(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    c2 = hass.data[DOMAIN][entry.entry_id]
    assert c2 is not c and c2.has_session and c2.last_session["summary"]["duration_s"] == 45


async def test_sampling_stays_at_one_hertz_with_real_tick_rate(hass, tmp_path):
    """The BLE loop ticks every ~0.3 s: samples must still be ~1 per second, never bursts or gaps."""
    entry, c = await setup_entry(hass, tmp_path)
    c.connected = True
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": eid(hass, "switch", "recording")}, blocking=True
    )
    c.data = RowerData(cadence=29.0, strokes=1, speed_kmh=10.0, pace_s500=180, distance_m=1.0)
    for i in range(1, 334):                              # 100 s of 0.3 s ticks
        c._sample(c._rec_mono + i * 0.3)
    times = [s.t for s in c.recorder.samples]
    assert 99 <= len(times) <= 101, len(times)
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert max(gaps) <= 1.31 and min(gaps) >= 0.89, (min(gaps), max(gaps))
    c._sample(c._rec_mono + 5000.0)                      # a long stall must not produce a burst
    c._sample(c._rec_mono + 5000.1)
    assert len(c.recorder.samples) == len(times) + 1
