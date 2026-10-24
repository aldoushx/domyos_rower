"""Workout programs: a list of resistance steps played while the rower is used.

A workout is stored as JSON-friendly dicts::

    {"id": "a1b2c3d4", "name": "Pyramides", "end_level": 1,
     "blocks": [{"repeat": 9, "steps": [{"seconds": 240, "level": 8}, ...]}]}

The runner counts time only while the user rows (it pauses when the strokes stop) and says which
resistance level should be active; the coordinator applies it. A level typed by hand is simply
replaced when the next step starts.
"""
from __future__ import annotations

import uuid
from bisect import bisect_right
from typing import Any

MAX_NAME = 60
MAX_BLOCKS = 20
MAX_REPEAT = 99
MAX_STEPS = 50
MIN_STEP_S = 5
MAX_STEP_S = 4 * 3600
MAX_TOTAL_S = 6 * 3600
MAX_WORKOUTS = 50

IDLE = "idle"
PAUSED = "paused"
RUNNING = "running"
FINISHED = "finished"
RUNNER_STATES = [IDLE, PAUSED, RUNNING, FINISHED]

NO_WORKOUT = "Aucun"  # label of the select entity when no workout is chosen


class WorkoutError(ValueError):
    """The workout sent by the editor is not valid."""


def _int(value: Any, what: str) -> int:
    try:
        if isinstance(value, bool):
            raise TypeError
        number = float(value)
    except (TypeError, ValueError):
        raise WorkoutError(f"{what} invalide") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise WorkoutError(f"{what} invalide")
    return int(round(number))


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def validate_workout(raw: Any, lo: int = 1, hi: int = 16) -> dict:
    """Return a clean copy of ``raw`` or raise WorkoutError (the editor shows the message)."""
    if not isinstance(raw, dict):
        raise WorkoutError("Entraînement invalide")
    name = str(raw.get("name") or "").strip()
    if not name:
        raise WorkoutError("Donne un nom à l'entraînement")
    if len(name) > MAX_NAME:
        raise WorkoutError(f"Nom trop long ({MAX_NAME} caractères maximum)")
    if name == NO_WORKOUT:
        raise WorkoutError(f"« {NO_WORKOUT} » est un nom réservé")
    end_level = _int(raw.get("end_level", lo), "Niveau de fin")
    if not lo <= end_level <= hi:
        raise WorkoutError(f"Niveau de fin entre {lo} et {hi}")
    blocks_raw = raw.get("blocks")
    if not isinstance(blocks_raw, list) or not blocks_raw:
        raise WorkoutError("Ajoute au moins un palier")
    if len(blocks_raw) > MAX_BLOCKS:
        raise WorkoutError(f"{MAX_BLOCKS} blocs maximum")
    blocks = []
    total = 0
    for b in blocks_raw:
        if not isinstance(b, dict):
            raise WorkoutError("Bloc invalide")
        repeat = _int(b.get("repeat", 1), "Répétition")
        if not 1 <= repeat <= MAX_REPEAT:
            raise WorkoutError(f"Répétition entre 1 et {MAX_REPEAT}")
        steps_raw = b.get("steps")
        if not isinstance(steps_raw, list) or not steps_raw:
            raise WorkoutError("Chaque bloc a besoin d'au moins un palier")
        if len(steps_raw) > MAX_STEPS:
            raise WorkoutError(f"{MAX_STEPS} paliers maximum par bloc")
        steps = []
        for s in steps_raw:
            if not isinstance(s, dict):
                raise WorkoutError("Palier invalide")
            seconds = _int(s.get("seconds"), "Durée")
            if not MIN_STEP_S <= seconds <= MAX_STEP_S:
                raise WorkoutError(f"Durée d'un palier entre {MIN_STEP_S} s et {MAX_STEP_S // 3600} h")
            level = _int(s.get("level"), "Niveau")
            if not lo <= level <= hi:
                raise WorkoutError(f"Niveau entre {lo} et {hi}")
            steps.append({"seconds": seconds, "level": level})
        total += repeat * sum(s["seconds"] for s in steps)
        blocks.append({"repeat": repeat, "steps": steps})
    if total > MAX_TOTAL_S:
        raise WorkoutError("Entraînement trop long (6 h maximum)")
    wid = str(raw.get("id") or "") or new_id()
    return {"id": wid, "name": name, "end_level": end_level, "blocks": blocks}


def flatten(workout: dict) -> list[tuple[int, int]]:
    """[(seconds, level), ...] with the repeats expanded."""
    out: list[tuple[int, int]] = []
    for block in workout["blocks"]:
        for _ in range(int(block["repeat"])):
            out.extend((int(s["seconds"]), int(s["level"])) for s in block["steps"])
    return out


def total_seconds(workout: dict) -> int:
    return sum(sec for sec, _ in flatten(workout))


def default_workouts() -> list[dict]:
    return [
        {"id": "pyramides", "name": "Pyramides", "end_level": 1, "blocks": [
            {"repeat": 9, "steps": [
                {"seconds": 240, "level": 8}, {"seconds": 120, "level": 10},
                {"seconds": 60, "level": 15}, {"seconds": 120, "level": 10}]}]},
        {"id": "intervalles", "name": "Intervalles 30/30", "end_level": 1, "blocks": [
            {"repeat": 1, "steps": [{"seconds": 300, "level": 6}]},
            {"repeat": 10, "steps": [{"seconds": 30, "level": 14}, {"seconds": 30, "level": 6}]},
            {"repeat": 1, "steps": [{"seconds": 300, "level": 5}]}]},
        {"id": "endurance", "name": "Endurance", "end_level": 1, "blocks": [
            {"repeat": 1, "steps": [{"seconds": 300, "level": 6}, {"seconds": 2400, "level": 8}]}]},
        {"id": "montee", "name": "Montée progressive", "end_level": 1, "blocks": [
            {"repeat": 1, "steps": [{"seconds": 300, "level": lvl} for lvl in range(4, 12)]}]},
    ]


class WorkoutRunner:
    """Plays a flattened workout; time advances only while the user is rowing."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.workout: dict | None = None
        self.timeline: list[tuple[int, int]] = []
        self._ends: list[int] = []
        self.total = 0
        self.elapsed = 0.0
        self.state = IDLE
        self.index = -1
        self._applied = -1

    def start(self, workout: dict) -> bool:
        self.reset()
        timeline = flatten(workout)
        if not timeline:
            return False
        self.workout = workout
        self.timeline = timeline
        acc = 0
        for sec, _ in timeline:
            acc += sec
            self._ends.append(acc)
        self.total = acc
        self.state = PAUSED  # until the first strokes
        self.index = 0
        return True

    def stop(self) -> None:
        self.reset()

    @property
    def active(self) -> bool:
        return self.state in (PAUSED, RUNNING)

    @property
    def level(self) -> int | None:
        if self.index < 0 or self.index >= len(self.timeline):
            return None
        return self.timeline[self.index][1]

    @property
    def next_level(self) -> int | None:
        nxt = self.index + 1
        return self.timeline[nxt][1] if 0 <= nxt < len(self.timeline) else None

    @property
    def step_remaining(self) -> int | None:
        if self.index < 0 or self.index >= len(self._ends):
            return None
        return max(0, int(round(self._ends[self.index] - self.elapsed)))

    @property
    def pending_level(self) -> int | None:
        """Level to send to the rower, or None when the current step was already applied."""
        if self.state not in (PAUSED, RUNNING) or self.index == self._applied:
            return None
        return self.level

    def mark_applied(self) -> None:
        self._applied = self.index

    def tick(self, dt: float, rowing: bool) -> bool:
        """Advance the clock. Returns True when something the UI shows has changed."""
        if self.state not in (PAUSED, RUNNING):
            return False
        changed = False
        if rowing:
            before = int(self.elapsed)
            self.elapsed = min(float(self.total), self.elapsed + max(dt, 0.0))
            changed = int(self.elapsed) != before
        if self.elapsed >= self.total:
            self.state = FINISHED
            self.index = len(self.timeline) - 1
            return True
        idx = bisect_right(self._ends, self.elapsed)
        if idx != self.index:
            self.index = idx
            changed = True
        state = RUNNING if rowing else PAUSED
        if state != self.state:
            self.state = state
            changed = True
        return changed

    def attributes(self) -> dict:
        if not self.workout:
            return {}
        return {
            "workout": self.workout["name"],
            "step": self.index + 1,
            "steps_total": len(self.timeline),
            "level": self.level,
            "next_level": self.next_level,
            "step_remaining_s": self.step_remaining,
            "elapsed_s": int(self.elapsed),
            "total_s": self.total,
        }
