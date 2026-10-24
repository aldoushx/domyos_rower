"""WebSocket API used by the Lovelace card to list, edit and choose workouts."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .coordinator import DomyosRowerCoordinator
from .workouts import WorkoutError

_FLAG = f"{DOMAIN}_ws_registered"


def _coordinator(hass: HomeAssistant, msg: dict) -> DomyosRowerCoordinator | None:
    coordinators = hass.data.get(DOMAIN, {})
    if msg.get("entry_id"):
        return coordinators.get(msg["entry_id"])
    return next(iter(coordinators.values()), None)


def _snapshot(coord: DomyosRowerCoordinator) -> dict[str, Any]:
    lo, hi = coord._level_bounds()
    return {
        "workouts": coord.workouts,
        "selected": coord.selected_workout,
        "level_range": [lo, hi],
        "state": coord.workout_runner.state,
        "attributes": coord.workout_runner.attributes(),
    }


def _with_coordinator(handler):
    async def wrapper(hass: HomeAssistant, connection, msg: dict) -> None:
        coord = _coordinator(hass, msg)
        if coord is None:
            connection.send_error(msg["id"], "not_found", "Aucun rameur configuré")
            return
        try:
            result = await handler(coord, msg)
        except WorkoutError as err:
            connection.send_error(msg["id"], "invalid_workout", str(err))
            return
        connection.send_result(msg["id"], result)

    return wrapper


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/workouts", vol.Optional("entry_id"): str}
)
@websocket_api.async_response
@_with_coordinator
async def ws_list(coord: DomyosRowerCoordinator, msg: dict) -> dict:
    return _snapshot(coord)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/workouts/save",
        vol.Required("workout"): dict,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_coordinator
async def ws_save(coord: DomyosRowerCoordinator, msg: dict) -> dict:
    saved = await coord.async_save_workout(msg["workout"])
    return {**_snapshot(coord), "saved": saved}


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/workouts/delete",
        vol.Required("workout_id"): str,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_coordinator
async def ws_delete(coord: DomyosRowerCoordinator, msg: dict) -> dict:
    await coord.async_delete_workout(msg["workout_id"])
    return _snapshot(coord)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/workouts/select",
        vol.Required("workout_id"): vol.Any(str, None),
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
@_with_coordinator
async def ws_select(coord: DomyosRowerCoordinator, msg: dict) -> dict:
    await coord.async_select_workout(msg["workout_id"])
    return _snapshot(coord)


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    if hass.data.get(_FLAG):
        return
    hass.data[_FLAG] = True
    for command in (ws_list, ws_save, ws_delete, ws_select):
        websocket_api.async_register_command(hass, command)
