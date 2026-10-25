"""Workout programs: validation, runner, integration with the recording and the WebSocket API."""
from __future__ import annotations

import pytest

from custom_components.domyos_rower.const import DOMAIN
from custom_components.domyos_rower.workouts import (
    FINISHED,
    IDLE,
    PAUSED,
    RUNNING,
    WorkoutError,
    WorkoutRunner,
    default_workouts,
    flatten,
    total_seconds,
    validate_workout,
)

from test_session_export import eid, no_bluetooth, setup_entry  # noqa: F401 (fixture)

PYR = next(w for w in default_workouts() if w["id"] == "pyramides")


# --------------------------------------------------------------------------- pure logic
def test_pyramides_matches_the_old_automation():
    steps = flatten(PYR)
    assert total_seconds(PYR) == 81 * 60 and len(steps) == 36
    assert steps[:5] == [(240, 8), (120, 10), (60, 15), (120, 10), (240, 8)]


def test_runner_advances_only_while_rowing_and_finishes():
    r = WorkoutRunner()
    assert r.start(PYR) and r.state == PAUSED and r.pending_level == 8
    r.mark_applied()
    assert r.pending_level is None
    for _ in range(239):
        r.tick(1.0, True)
    assert r.state == RUNNING and r.level == 8 and r.step_remaining == 1
    r.tick(1.0, True)
    assert r.level == 10 and r.pending_level == 10          # step change
    r.mark_applied()
    for _ in range(300):                                   # user stops rowing: paused, no progress
        r.tick(1.0, False)
    assert r.state == PAUSED and r.elapsed == 240.0 and r.level == 10
    r.tick(1.0, True)
    assert r.state == RUNNING and r.elapsed == 241.0
    r.tick(10_000.0, True)
    assert r.state == FINISHED and r.pending_level is None
    r.stop()
    assert r.state == IDLE and r.attributes() == {}


def test_attributes_describe_the_step():
    r = WorkoutRunner()
    r.start(PYR)
    r.tick(100.0, True)
    a = r.attributes()
    assert a["workout"] == "Pyramides" and a["step"] == 1 and a["steps_total"] == 36
    assert a["level"] == 8 and a["next_level"] == 10 and a["step_remaining_s"] == 140
    assert a["elapsed_s"] == 100 and a["total_s"] == 4860


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda w: w.update(name="  "), "nom"),
        (lambda w: w.update(name="Aucun"), "réservé"),
        (lambda w: w.update(blocks=[]), "au moins un palier"),
        (lambda w: w["blocks"][0].update(repeat=0), "Répétition"),
        (lambda w: w["blocks"][0].update(steps=[]), "au moins un palier"),
        (lambda w: w["blocks"][0]["steps"][0].update(seconds=1), "Durée"),
        (lambda w: w["blocks"][0]["steps"][0].update(seconds="abc"), "Durée"),
        (lambda w: w["blocks"][0]["steps"][0].update(level=0), "Niveau"),
        (lambda w: w["blocks"][0]["steps"][0].update(level=99), "Niveau"),
        (lambda w: w.update(end_level=40), "fin"),
        (lambda w: w["blocks"][0].update(repeat=99, steps=[{"seconds": 14400, "level": 8}]), "trop long"),
    ],
)
def test_validation_rejects_bad_workouts(mutate, message):
    import copy

    w = copy.deepcopy(PYR)
    mutate(w)
    with pytest.raises(WorkoutError, match=message):
        validate_workout(w)


def test_validation_cleans_and_generates_an_id():
    w = validate_workout({"name": " Test ", "blocks": [{"steps": [{"seconds": "60", "level": 7.4}]}], "junk": 1})
    assert w["name"] == "Test" and w["id"] and w["end_level"] == 1
    assert w["blocks"] == [{"repeat": 1, "steps": [{"seconds": 60, "level": 7}]}]
    assert "junk" not in w


# --------------------------------------------------------------------------- in Home Assistant
async def test_workout_starts_with_recording_pauses_and_stops(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    c.connected, c.mode = True, "proprietary"
    sel = eid(hass, "select", "workout")
    assert hass.states.get(sel).state == "Aucun"
    assert "Pyramides" in hass.states.get(sel).attributes["options"]
    await hass.services.async_call("select", "select_option", {"entity_id": sel, "option": "Pyramides"}, blocking=True)
    assert c.selected_workout == "pyramides"

    status = eid(hass, "sensor", "workout_status")
    assert hass.states.get(status).state == "idle"
    await hass.services.async_call("switch", "turn_on", {"entity_id": eid(hass, "switch", "recording")}, blocking=True)
    assert c.workout_runner.state == PAUSED and c._pending_resistance == 8      # first level sent at start
    c._pending_resistance = None

    t = 1000.0
    c._wk_t = t
    for _ in range(240):                                    # 4 minutes of rowing
        t += 1.0
        c._last_stroke_change = t
        c._workout_tick(t)
    assert c.workout_runner.level == 10 and c._pending_resistance == 10
    c._pending_resistance = None

    for _ in range(60):                                     # stops rowing for a minute: paused
        t += 1.0
        c._workout_tick(t)
    await hass.async_block_till_done()
    assert hass.states.get(status).state == "paused"
    assert c.workout_runner.elapsed == 248.0   # 8 s grace after the last stroke

    c.async_set_resistance(12)                              # manual override is allowed
    assert c._pending_resistance == 12 and c.workout_runner.level == 10
    c._pending_resistance = None
    for _ in range(121):                                    # rowing again: the next step replaces it
        t += 1.0
        c._last_stroke_change = t
        c._workout_tick(t)
    assert c.workout_runner.level == 15 and c._pending_resistance == 15
    await hass.async_block_till_done()
    st = hass.states.get(status)
    assert st.state == "running" and st.attributes["step"] == 3 and st.attributes["workout"] == "Pyramides"

    c._pending_resistance = None
    await hass.services.async_call("switch", "turn_off", {"entity_id": eid(hass, "switch", "recording")}, blocking=True)
    assert c.workout_runner.state == IDLE and c._pending_resistance == 1       # end level
    await hass.async_block_till_done()
    assert hass.states.get(status).state == "idle"


async def test_no_workout_chosen_changes_nothing(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    c.connected, c.mode = True, "proprietary"
    await hass.services.async_call("switch", "turn_on", {"entity_id": eid(hass, "switch", "recording")}, blocking=True)
    assert c.workout_runner.state == IDLE and c._pending_resistance is None


async def test_level_applied_when_the_rower_connects_later(hass, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    await c.async_select_workout("endurance")
    c.connected = True                                      # recording needs a connection for samples only
    await c.async_start_recording()
    c.mode = None
    assert c.workout_runner.pending_level == 6              # not sent: no command channel yet
    c.mode = "proprietary"
    c._workout_tick(5.0)
    assert c._pending_resistance == 6 and c.workout_runner.pending_level is None


async def test_workouts_are_saved_and_survive_a_restart(hass, tmp_path, hass_storage):
    entry, c = await setup_entry(hass, tmp_path)
    saved = await c.async_save_workout({"name": "Mon test", "blocks": [{"repeat": 2, "steps": [{"seconds": 60, "level": 9}]}]})
    await c.async_select_workout(saved["id"])
    with pytest.raises(WorkoutError, match="déjà"):
        await c.async_save_workout({"name": "mon TEST", "blocks": [{"steps": [{"seconds": 60, "level": 9}]}]})
    await c.async_delete_workout("endurance")
    assert hass.states.get(eid(hass, "select", "workout")).state == "Mon test"

    from custom_components.domyos_rower.coordinator import DomyosRowerCoordinator

    c2 = DomyosRowerCoordinator(hass, entry, c.address, c.name)
    await c2.async_load()
    assert [w["name"] for w in c2.workouts] == ["Pyramides", "Intervalles 30/30", "Montée progressive", "Mon test"]
    assert c2.selected_workout == saved["id"]
    await c2.async_delete_workout(saved["id"])
    assert c2.selected_workout is None


# --------------------------------------------------------------------------- WebSocket API
async def test_websocket_list_save_select_delete(hass, hass_ws_client, tmp_path):
    entry, c = await setup_entry(hass, tmp_path)
    ws = await hass_ws_client(hass)

    await ws.send_json({"id": 1, "type": f"{DOMAIN}/workouts"})
    res = (await ws.receive_json())["result"]
    assert [w["id"] for w in res["workouts"]][0] == "pyramides" and res["level_range"] == [1, 15]

    bad = {"name": "X", "blocks": [{"repeat": 1, "steps": [{"seconds": 60, "level": 99}]}]}
    await ws.send_json({"id": 2, "type": f"{DOMAIN}/workouts/save", "workout": bad})
    err = await ws.receive_json()
    assert not err["success"] and err["error"]["code"] == "invalid_workout" and "Niveau" in err["error"]["message"]

    good = {"name": "Court", "blocks": [{"repeat": 3, "steps": [{"seconds": 30, "level": 12}, {"seconds": 30, "level": 6}]}]}
    await ws.send_json({"id": 3, "type": f"{DOMAIN}/workouts/save", "workout": good})
    res = (await ws.receive_json())["result"]
    wid = res["saved"]["id"]
    assert any(w["id"] == wid for w in res["workouts"])

    await ws.send_json({"id": 4, "type": f"{DOMAIN}/workouts/select", "workout_id": wid})
    assert (await ws.receive_json())["result"]["selected"] == wid
    await ws.send_json({"id": 5, "type": f"{DOMAIN}/workouts/select", "workout_id": None})
    assert (await ws.receive_json())["result"]["selected"] is None
    await ws.send_json({"id": 6, "type": f"{DOMAIN}/workouts/delete", "workout_id": wid})
    res = (await ws.receive_json())["result"]
    assert all(w["id"] != wid for w in res["workouts"])
