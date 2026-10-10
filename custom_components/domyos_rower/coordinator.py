"""Keeps a BLE connection to the rower through Home Assistant's Bluetooth stack.

Because it uses HA's Bluetooth manager, the connection transparently goes
through an ESPHome Bluetooth proxy (which must run with `active: true`).

Two protocols are supported, picked from the GATT services (same rule as QZ):
* Domyos proprietary service present -> proprietary protocol;
* otherwise FTMS: subscribe to every notify/indicate characteristic of the FTMS
  service, then write "Start/Resume" to the Control Point (what QZ does for
  DOMYOS-ROW-xxxx rowers), which is what makes the console stream its data.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
import logging
import os
import time
import zlib

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth, persistent_notification
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ACK_TIMEOUT,
    CONF_GPX_LAT,
    CONF_GPX_LON,
    CONF_OUTPUT_DIR,
    CONF_SPORT_TYPE,
    CONF_STRAVA,
    DEFAULT_SPORT_TYPE,
    DISTANCE_SCALE_MAX,
    DISTANCE_SCALE_MIN,
    DOMAIN,
    EVENT_SESSION_SAVED,
    FTMS_CMD_TIMEOUT,
    FTMS_STROKE_IDLE,
    POLL_INTERVAL,
    PROP_NO_DATA_TIMEOUT,
    MIN_GOOD_SESSION,
    RETRY_DELAYS,
    SAMPLE_INTERVAL,
    SAMPLE_TOLERANCE,
    STALE_TIMEOUT,
    STATUS_CONNECTED,
    STATUS_CONNECTING,
    STATUS_DISABLED,
    STATUS_ERROR,
    STATUS_WAITING,
)
from .protocol import (
    FTMS_CONTROL_POINT,
    FTMS_OP_REQUEST_CONTROL,
    FTMS_OP_START_RESUME,
    FTMS_RESISTANCE_RANGE,
    FTMS_RESULTS,
    FTMS_SERVICE,
    INIT_FRAMES,
    NOOP,
    PROP_NOTIFY,
    PROP_SERVICE,
    PROP_WRITE,
    RESISTANCE_MAX,
    RESISTANCE_MIN,
    ROWER_DATA,
    RowerData,
    build_ftms_set_resistance,
    build_resistance_frames,
    parse_ftms_response,
    parse_ftms_rower_data,
    parse_proprietary,
    parse_resistance_range,
)

from .fit import build_fit
from .session import SessionRecorder, build_gpx, build_tcx, file_stem
from .strava import StravaClient, StravaError

_LOGGER = logging.getLogger(__name__)


def default_output_dir(hass: HomeAssistant) -> str:
    """/media/domyos_rower when a writable /media exists (HA OS, Supervised), else <config>/domyos_rower."""
    if os.path.isdir("/media") and os.access("/media", os.W_OK):
        return "/media/domyos_rower"
    return hass.config.path("domyos_rower")


def _write_files(folder: str, stem: str, tcx: str, gpx: str, fit: bytes) -> dict[str, str]:
    os.makedirs(folder, exist_ok=True)
    paths = {ext: os.path.join(folder, f"{stem}.{ext}") for ext in ("tcx", "gpx", "fit")}
    with open(paths["tcx"], "w", encoding="utf-8") as fh:
        fh.write(tcx)
    with open(paths["gpx"], "w", encoding="utf-8") as fh:
        fh.write(gpx)
    with open(paths["fit"], "wb") as fh:
        fh.write(fit)
    return paths


def _err_text(err: BaseException) -> str:
    return f"{type(err).__name__}: {err}" if str(err) else type(err).__name__


class DomyosRowerCoordinator:
    """Push-style coordinator: BLE notifications -> listeners."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, address: str, name: str
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.address = address
        self.name = name

        self.data = RowerData()
        self.connected = False
        self.enabled = True  # lets the user free the rower for a phone/QZ
        self.mode: str | None = None  # "proprietary" or "ftms"

        # diagnostics
        self.status = STATUS_WAITING
        self.last_error: str | None = None
        self.services: list[str] = []
        self._last_logged_error: str | None = None
        self.last_operation: str | None = None  # BLE step in progress when it last failed
        self.failures = 0  # consecutive failed sessions (drives the retry back-off)
        self._op: str | None = None
        self._session_connected = False

        self._listeners: set[Callable[[], None]] = set()
        self._task: asyncio.Task | None = None
        self._cancel_adv: Callable[[], None] | None = None
        self._advert_event = asyncio.Event()
        self._wake_event = asyncio.Event()
        self._answer_event = asyncio.Event()
        self._last_packet = 0.0

        # Domyos proprietary state
        self._distance_m = 0.0
        self._last_t: float | None = None
        self._last_strokes: int | None = None
        self._got_packet = False

        # FTMS state
        self._ftms_cp = None  # Control Point characteristic object
        self._cp_event = asyncio.Event()
        self._cp_expected: int | None = None
        self._cp_response: tuple[int, int] | None = None
        self._ftms_strokes: int | None = None
        self._ftms_stroke_t = 0.0

        # session recording (switch) and export (files at the end, Strava on demand)
        self.recorder: SessionRecorder | None = None
        self.recording = False
        self.last_session: dict | None = None
        self.strava_busy = False
        self._rec_mono = 0.0
        self._next_sample_mono = float("-inf")
        self._strava_obj: StravaClient | None = None
        self._store: Store = Store(hass, 1, f"{DOMAIN}_session_{entry.entry_id}")

        # distance calibration (multiplier applied to distance and what derives from it)
        self.distance_scale = 1.0

        # values the rower doesn't send are derived here, like QZ does
        self._rower_sends_power = False
        self._rower_sends_elapsed = False
        self._seen_strokes: int | None = None
        self._last_stroke_change = float("-inf")
        self._active_time = 0.0
        self._tick_t = 0.0

        # resistance control
        self.resistance_range: tuple[float, float, float] = (
            float(RESISTANCE_MIN),
            float(RESISTANCE_MAX),
            1.0,
        )
        self.resistance_range_known = False
        self._pending_resistance: float | None = None
        self._expected_resistance: float | None = None
        self._expected_until = 0.0
        self._commanded_resistance: float | None = None

    # ------------------------------------------------------------ calibration
    @property
    def view(self) -> RowerData:
        """Rower data with the distance calibration applied.

        Scaled: distance, speed, pace (inverse) and the power derived from the pace.
        Untouched: strokes, cadence, calories, resistance, heart rate, time, and a power
        value that the rower itself sends.
        """
        k = self.distance_scale
        d = self.data
        if k == 1.0:
            return d
        pace = round(d.pace_s500 / k) if d.pace_s500 else d.pace_s500
        power = d.power_w if self._rower_sends_power else self._power_from_pace(pace, d.cadence)
        return replace(
            d,
            distance_m=round(d.distance_m * k, 1) if d.distance_m is not None else None,
            speed_kmh=round(d.speed_kmh * k, 2) if d.speed_kmh is not None else None,
            pace_s500=pace,
            power_w=power,
        )

    @callback
    def async_set_distance_scale(self, value: float) -> None:
        self.distance_scale = round(
            max(DISTANCE_SCALE_MIN, min(DISTANCE_SCALE_MAX, float(value))), 3
        )
        self._push()

    # ------------------------------------------------------------ derived values
    @property
    def power_is_calculated(self) -> bool:
        return not self._rower_sends_power

    @staticmethod
    def _power_from_pace(pace_s500: int | None, cadence: float | None) -> int:
        """Concept2 formula, as in QZ: watts = 2.8 * (500 / pace_s_per_500m)^3."""
        if not pace_s500 or pace_s500 <= 0 or not cadence:
            return 0
        return max(0, round(2.8 * (500.0 / pace_s500) ** 3))

    def _note_strokes(self, strokes: int | None, now: float) -> None:
        if strokes is None:
            return
        if self._seen_strokes is not None:
            if strokes < self._seen_strokes:  # the console started a new workout
                self._active_time = 0.0
            if strokes != self._seen_strokes:
                self._last_stroke_change = now
        self._seen_strokes = strokes

    def _tick_derived(self, now: float) -> None:
        """Workout timer: counts while strokes keep coming (rower sends no elapsed time)."""
        dt = min(max(now - self._tick_t, 0.0), 1.0)
        self._tick_t = now
        self._sample(now)
        if self._rower_sends_elapsed:
            return
        if now - self._last_stroke_change <= FTMS_STROKE_IDLE:
            self._active_time += dt
        elapsed = int(self._active_time)
        if self.data.elapsed_s != elapsed:
            self.data = replace(self.data, elapsed_s=elapsed)
            self._push()

    # ------------------------------------------------------------ session recording
    def _opt(self, key: str, default=None):
        value = self.entry.options.get(key)
        return default if value in (None, "") else value

    @property
    def has_session(self) -> bool:
        return self.recorder is not None and len(self.recorder.samples) >= 2

    @property
    def strava_configured(self) -> bool:
        return bool(self.entry.data.get(CONF_STRAVA, {}).get("refresh_token"))

    async def async_load(self) -> None:
        """Restore the last recorded session (so the buttons keep working after a restart)."""
        data = await self._store.async_load()
        if data and data.get("session"):
            self.recorder = SessionRecorder.from_dict(data["session"])
            self.last_session = data.get("info")

    def _store_data(self) -> dict:
        return {
            "session": self.recorder.to_dict() if self.recorder else None,
            "info": self.last_session,
        }

    @callback
    def _sample(self, now: float) -> None:
        if not (self.recording and self.connected and self.recorder):
            return
        if now + SAMPLE_TOLERANCE < self._next_sample_mono:
            return
        # Fixed 1 Hz schedule (not "1 s after the previous tick") so ticks of ~0.3 s don't stretch it.
        base = now if self._next_sample_mono == float("-inf") else self._next_sample_mono
        self._next_sample_mono = base + SAMPLE_INTERVAL
        if self._next_sample_mono < now:  # fell behind (e.g. event loop stalled): don't burst
            self._next_sample_mono = now + SAMPLE_INTERVAL
        d = self.view
        self.recorder.add(
            now - self._rec_mono,
            distance_m=d.distance_m,
            speed_kmh=d.speed_kmh,
            cadence=d.cadence,
            power_w=d.power_w,
            heart_rate=d.heart_rate,
            calories=d.calories,
            resistance=d.resistance,
            strokes=d.strokes,
        )
        self._store.async_delay_save(self._store_data, 30)
        self._push()

    async def async_start_recording(self) -> None:
        if self.recording:
            return
        self.recorder = SessionRecorder(dt_util.utcnow())
        self._rec_mono = time.monotonic()
        self._next_sample_mono = float("-inf")
        self._active_time = 0.0  # the workout timer starts with the recording
        self.recording = True
        _LOGGER.info("%s: session recording started", self.address)
        self._push()

    async def async_stop_recording(self) -> None:
        """Stop and, like QZ would at the end of a workout, write the TCX and GPX files."""
        if not self.recording:
            return
        self.recording = False
        self._push()
        if not self.has_session:
            _LOGGER.info("%s: recording stopped with no data, nothing exported", self.address)
            persistent_notification.async_create(
                self.hass,
                "La séance enregistrée est vide (le rameur n'était pas connecté ou il n'y a eu "
                "aucune donnée), aucun fichier n'a été créé.",
                title="Domyos Rower",
                notification_id=f"{DOMAIN}_{self.address}_empty",
            )
            return
        try:
            await self.async_generate_files()
        except HomeAssistantError as err:
            persistent_notification.async_create(
                self.hass,
                f"Impossible de créer les fichiers de la séance : {err}. "
                "La séance reste en mémoire : corrige le dossier dans les options puis utilise "
                "le bouton « Générer les fichiers ».",
                title="Domyos Rower",
                notification_id=f"{DOMAIN}_{self.address}_files",
            )

    def _session_texts(self) -> tuple[str, str, str]:
        assert self.recorder is not None
        start_local = dt_util.as_local(self.recorder.start)
        name = f"Rameur Domyos – {start_local:%d/%m/%Y %H:%M}"
        summ = self.recorder.summary()
        notes = (
            f"Séance enregistrée avec Home Assistant : {summ['strokes']} coups, "
            f"cadence moyenne {summ['avg_cadence']:g} coups/min, {summ['calories']} kcal."
        )
        if self.power_is_calculated:
            notes += " Puissance estimée à partir de l'allure (formule du Concept2)."
        if self.distance_scale != 1.0:
            notes += f" Distance étalonnée (x{self.distance_scale:g})."
        return name, notes, file_stem(start_local)

    async def async_generate_files(self) -> dict:
        """Write <stem>.tcx, .gpx and .fit in the export folder. Never uploads anything."""
        if not self.has_session:
            raise HomeAssistantError("Aucune séance enregistrée à exporter.")
        if self.recording:
            raise HomeAssistantError("Arrête l'enregistrement avant de générer les fichiers.")
        rec = self.recorder
        assert rec is not None
        name, notes, stem = self._session_texts()
        folder = self._opt(CONF_OUTPUT_DIR) or await self.hass.async_add_executor_job(
            default_output_dir, self.hass
        )
        lat = float(self._opt(CONF_GPX_LAT, self.hass.config.latitude))
        lon = float(self._opt(CONF_GPX_LON, self.hass.config.longitude))
        tcx = build_tcx(rec, notes)
        gpx = build_gpx(rec, name, lat, lon)
        offset = dt_util.as_local(rec.start).utcoffset()
        fit = build_fit(
            rec,
            serial=zlib.crc32(self.address.encode()) & 0xFFFFFFFF,
            utc_offset_s=int(offset.total_seconds()) if offset else 0,
        )
        try:
            paths = await self.hass.async_add_executor_job(
                _write_files, folder, stem, tcx, gpx, fit
            )
        except OSError as err:
            raise HomeAssistantError(f"écriture impossible dans « {folder} » ({err})") from err

        summary = rec.summary()
        previous_strava = (
            (self.last_session or {}).get("strava")
            if (self.last_session or {}).get("start") == rec.start.isoformat()
            else None
        )
        self.last_session = {
            "start": rec.start.isoformat(),
            "name": name,
            "folder": folder,
            "files": paths,
            "summary": summary,
            "strava": previous_strava,
        }
        await self._store.async_save(self._store_data())
        self.hass.bus.async_fire(
            EVENT_SESSION_SAVED,
            {
                "entry_id": self.entry.entry_id,
                "address": self.address,
                "device": self.name,
                "start": rec.start.isoformat(),
                "folder": folder,
                "tcx": paths["tcx"],
                "gpx": paths["gpx"],
                "fit": paths["fit"],
                **{k: summary.get(k) for k in ("duration_s", "distance_m", "calories", "strokes")},
            },
        )
        _LOGGER.info("%s: session files written: %s", self.address, paths)
        self._push()
        return self.last_session

    def _strava_client(self) -> StravaClient:
        if self._strava_obj is None:
            conf = self.entry.data[CONF_STRAVA]

            async def save(tokens: dict) -> None:
                self.hass.config_entries.async_update_entry(
                    self.entry,
                    data={**self.entry.data, CONF_STRAVA: {**self.entry.data[CONF_STRAVA], **tokens}},
                )

            self._strava_obj = StravaClient(
                async_get_clientsession(self.hass),
                conf["client_id"],
                conf["client_secret"],
                tokens=conf,
                token_saved=save,
            )
        return self._strava_obj

    async def async_upload_strava(self) -> dict:
        """Manual only: send the last recorded session to Strava (TCX)."""
        if not self.strava_configured:
            raise HomeAssistantError("Strava n'est pas configuré pour cet appareil.")
        if not self.has_session or self.recording:
            raise HomeAssistantError("Aucune séance terminée à envoyer.")
        if self.strava_busy:
            raise HomeAssistantError("Un envoi vers Strava est déjà en cours.")
        rec = self.recorder
        assert rec is not None
        name, notes, stem = self._session_texts()
        info = self.last_session or {}
        self.strava_busy = True
        self._push()
        try:
            result = await self._strava_client().upload_activity(
                build_tcx(rec, notes).encode("utf-8"),
                f"{stem}.tcx",
                name=name,
                description=notes,
                sport_type=self._opt(CONF_SPORT_TYPE, DEFAULT_SPORT_TYPE),
                external_id=stem,
            )
        except StravaError as err:
            info["strava"] = {"status": "error", "error": str(err)}
            self.last_session = info
            persistent_notification.async_create(
                self.hass,
                f"L'envoi vers Strava a échoué : {err}",
                title="Domyos Rower",
                notification_id=f"{DOMAIN}_{self.address}_strava",
            )
            raise HomeAssistantError(f"Envoi Strava impossible : {err}") from err
        finally:
            self.strava_busy = False
            self._push()
        info["strava"] = {"status": "uploaded", "uploaded_at": dt_util.utcnow().isoformat(), **result}
        self.last_session = info
        await self._store.async_save(self._store_data())
        persistent_notification.async_dismiss(self.hass, f"{DOMAIN}_{self.address}_strava")
        self._push()
        return result

    # ------------------------------------------------------------ resistance
    @property
    def can_set_resistance(self) -> bool:
        if not self.connected:
            return False
        return self.mode == "proprietary" or (
            self.mode == "ftms" and self._ftms_cp is not None
        )

    @property
    def resistance_target(self) -> float | None:
        """What the number entity shows: the request until the console confirms it."""
        if self._pending_resistance is not None:
            return self._pending_resistance
        if self._expected_resistance is not None:
            return self._expected_resistance
        if self.data.resistance is not None:
            return self.data.resistance
        return self._commanded_resistance

    @callback
    def async_set_resistance(self, level: float) -> None:
        """Queue a resistance change; the session loop sends it (writes stay serialized)."""
        if not self.can_set_resistance:
            raise HomeAssistantError(
                "Resistance can only be changed while the rower is connected."
            )
        lo, hi, step = self.resistance_range
        level = max(lo, min(hi, float(level)))
        if self.mode == "proprietary":
            level = int(round(level))
        elif step > 0:
            level = round(lo + round((level - lo) / step) * step, 1)
        self._pending_resistance = level
        self._push()

    def _check_expected(self, now: float) -> None:
        if self._expected_resistance is None:
            return
        res = self.data.resistance
        if (res is not None and abs(res - self._expected_resistance) < 0.5) or (
            now > self._expected_until
        ):
            self._expected_resistance = None

    async def _send_pending_resistance(self, client) -> None:
        if self._pending_resistance is None:
            return
        level, self._pending_resistance = self._pending_resistance, None
        self._step(f"set resistance {level}")
        if self.mode == "proprietary":
            first, second = build_resistance_frames(int(level))
            _LOGGER.debug("%s: setting resistance %s (Domyos)", self.address, level)
            await self._write(client, first, False)
            await self._write(client, second, False)
        else:
            payload = build_ftms_set_resistance(level)
            result = await self._ftms_command(client, payload, ensure_control=True)
            _LOGGER.debug(
                "%s: setting resistance %s (FTMS %s) -> %s",
                self.address, level, payload.hex(" "), self._result_text(result),
            )
            if result not in (None, 0x01):
                _LOGGER.warning(
                    "%s: rower refused resistance %s: %s",
                    self.address, level, self._result_text(result),
                )
                self._push()
                return
        self._step("streaming")
        self._commanded_resistance = level
        self._expected_resistance = level
        self._expected_until = time.monotonic() + 3.0
        self._push()

    # ------------------------------------------------------------ listeners
    @callback
    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(update)

        @callback
        def remove() -> None:
            self._listeners.discard(update)

        return remove

    @callback
    def _push(self) -> None:
        for update in list(self._listeners):
            update()

    def _step(self, op: str | None) -> None:
        """Remember which BLE step is running, so a failure can say where it happened."""
        self._op = op

    @callback
    def _set_connected(self, value: bool) -> None:
        if self.connected != value:
            self.connected = value
            if value:
                self._session_connected = True
                self.status = STATUS_CONNECTED
                self.last_error = None
            else:
                self.mode = None
                self._ftms_cp = None
            self._push()

    @callback
    def _set_status(self, status: str, error: str | None = None) -> None:
        changed = status != self.status or (error is not None and error != self.last_error)
        self.status = status
        if error is not None:
            self.last_error = error
        if changed:
            self._push()

    @callback
    def async_set_enabled(self, value: bool) -> None:
        self.enabled = value
        if not value:
            self._set_status(STATUS_DISABLED)
        self._wake_event.set()
        self._advert_event.set()
        self._push()

    # ------------------------------------------------------------ lifecycle
    @callback
    def async_start(self) -> None:
        self._cancel_adv = bluetooth.async_register_callback(
            self.hass,
            self._async_on_advert,
            BluetoothCallbackMatcher(address=self.address, connectable=True),
            BluetoothScanningMode.ACTIVE,
        )
        self._task = self.entry.async_create_background_task(
            self.hass, self._run(), f"{DOMAIN}_{self.address}"
        )

    async def async_stop(self) -> None:
        if self._cancel_adv:
            self._cancel_adv()
            self._cancel_adv = None
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    @callback
    def _async_on_advert(
        self, service_info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        self._advert_event.set()

    def _current_ble_device(self):
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    def _log_failure(self, text: str) -> None:
        """WARNING the first time an error shows up, DEBUG while it repeats."""
        if text != self._last_logged_error:
            self._last_logged_error = text
            _LOGGER.warning("%s: %s", self.address, text)
        else:
            _LOGGER.debug("%s: %s (repeated)", self.address, text)

    # ------------------------------------------------------------ main loop
    async def _run(self) -> None:
        while True:
            if not self.enabled:
                self._set_status(STATUS_DISABLED)
                self._wake_event.clear()
                await self._wake_event.wait()
                continue

            ble_device = self._current_ble_device()
            if ble_device is None:
                # The rower sleeps (no advertising) until someone pulls the handle.
                self._set_status(STATUS_WAITING)
                self._advert_event.clear()
                await self._advert_event.wait()
                continue

            started = time.monotonic()
            self._session_connected = False
            self._step("connect")
            self._set_status(STATUS_CONNECTING)
            try:
                await self._session(ble_device)
            except asyncio.CancelledError:
                raise
            except (BleakError, TimeoutError, OSError) as err:
                self.last_operation = self._op
                text = f"{_err_text(err)} (during: {self._op})"
                self._set_status(STATUS_ERROR, text)
                self._log_failure(f"connection/communication error: {text}")
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error with %s", self.address)
                self.last_operation = self._op
                self._set_status(STATUS_ERROR, f"unexpected error: {_err_text(err)}")
            duration = time.monotonic() - started
            was_connected = self._session_connected
            self._set_connected(False)
            if self.status != STATUS_ERROR:
                self._set_status(STATUS_WAITING)

            # A real, held connection resets the back-off (a link lost mid-workout is
            # retried quickly); repeated failures space the attempts out.
            if was_connected and duration >= MIN_GOOD_SESSION:
                self.failures = 0
            else:
                self.failures += 1
            delay = RETRY_DELAYS[min(self.failures, len(RETRY_DELAYS) - 1)]
            _LOGGER.info(
                "%s: session ended after %.1f s (connected=%s, last step: %s); retrying in %.0f s",
                self.address, duration, was_connected, self._op, delay,
            )
            self._push()

            with suppress(TimeoutError):
                await asyncio.wait_for(self._wake_event.wait(), delay)
            self._wake_event.clear()

    def _on_disconnected(self, _client) -> None:
        _LOGGER.info("%s: disconnected", self.address)
        self._set_connected(False)

    async def _session(self, ble_device) -> None:
        _LOGGER.info("%s: connecting (via %s)", self.address, getattr(ble_device, "details", "?"))
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self.name,
            self._on_disconnected,
            max_attempts=1,  # our own loop retries, with back-off
            ble_device_callback=self._current_ble_device,
        )
        self._reset_session()
        self._step("read services")
        try:
            services = client.services
            self.services = sorted(s.uuid for s in services)
            _LOGGER.info("%s: connected, services: %s", self.address, self.services)
            has_prop = services.get_service(PROP_SERVICE) is not None
            has_ftms = services.get_service(FTMS_SERVICE) is not None
            if has_prop:
                self.mode = "proprietary"
                answered = await self._run_proprietary(client)
                if not answered and has_ftms and client.is_connected and self.enabled:
                    _LOGGER.warning(
                        "%s: Domyos protocol got no answer, falling back to FTMS", self.address
                    )
                    self._set_connected(False)
                    self.mode = "ftms"
                    await self._run_ftms(client)
            elif has_ftms:
                self.mode = "ftms"
                await self._run_ftms(client)
            else:
                text = f"no Domyos/FTMS service, found: {self.services}"
                self._set_status(STATUS_ERROR, text)
                self._log_failure(text)
        finally:
            with suppress(BleakError, TimeoutError, OSError):
                await client.disconnect()

    def _reset_session(self) -> None:
        self.data = RowerData()
        self._distance_m = 0.0
        self._last_t = None
        self._last_strokes = None
        self._got_packet = False
        self._last_packet = time.monotonic()
        self._pending_resistance = None
        self._expected_resistance = None
        self._commanded_resistance = None
        self._ftms_cp = None
        self._ftms_strokes = None
        self._ftms_stroke_t = time.monotonic()
        self._rower_sends_power = False
        self._rower_sends_elapsed = False
        self._seen_strokes = None
        self._last_stroke_change = float("-inf")
        self._active_time = 0.0
        self._tick_t = time.monotonic()
        self._last_logged_error = None

    # ------------------------------------------------------------ FTMS
    @staticmethod
    def _result_text(result: int | None) -> str:
        if result is None:
            return "no indication from the rower"
        return FTMS_RESULTS.get(result, f"result {result:#04x}")

    async def _ftms_command(self, client, payload: bytes, ensure_control: bool = False) -> int | None:
        """Write to the Control Point and return the FTMS result code (None = no answer)."""

        async def once(data: bytes) -> int | None:
            self._cp_expected = data[0]
            self._cp_response = None
            self._cp_event.clear()
            await client.write_gatt_char(self._ftms_cp, data, response=True)
            with suppress(TimeoutError):
                await asyncio.wait_for(self._cp_event.wait(), FTMS_CMD_TIMEOUT)
            return self._cp_response[1] if self._cp_response else None

        result = await once(payload)
        if ensure_control and result == 0x05:  # control not permitted -> ask for control
            _LOGGER.debug("%s: requesting control then retrying", self.address)
            await once(bytes([FTMS_OP_REQUEST_CONTROL]))
            result = await once(payload)
        return result

    def _on_ftms_cp(self, payload: bytes) -> None:
        parsed = parse_ftms_response(payload)
        _LOGGER.debug("%s: control point indication %s", self.address, payload.hex(" "))
        if parsed and parsed[0] == self._cp_expected:
            self._cp_response = parsed
            self._cp_event.set()

    def _on_ftms_other(self, uuid: str, payload: bytes) -> None:
        _LOGGER.debug("%s: %s -> %s", self.address, uuid, payload.hex(" "))

    def _make_ftms_handler(self, uuid: str):
        def handler(_char, payload: bytearray) -> None:
            data = bytes(payload)
            if uuid == ROWER_DATA:
                self._on_ftms_data(data)
            elif uuid == FTMS_CONTROL_POINT:
                self._on_ftms_cp(data)
            else:
                self._on_ftms_other(uuid, data)

        return handler

    async def _run_ftms(self, client) -> None:
        service = client.services.get_service(FTMS_SERVICE)
        chars = list(service.characteristics)
        _LOGGER.info(
            "%s: FTMS characteristics: %s",
            self.address,
            {
                c.uuid[4:8]: f"handle {getattr(c, 'handle', '?')} {'/'.join(c.properties)}"
                for c in chars
            },
        )

        self._ftms_cp = next(
            (c for c in chars if c.uuid == FTMS_CONTROL_POINT and "write" in c.properties),
            None,
        )

        # Like QZ: subscribe to every notify/indicate characteristic of the FTMS service.
        subscribed = []
        for char in chars:
            if "notify" not in char.properties and "indicate" not in char.properties:
                continue
            try:
                self._step(f"subscribe {char.uuid[4:8]} (handle {getattr(char, 'handle', '?')})")
                await client.start_notify(char, self._make_ftms_handler(char.uuid))
                subscribed.append(char.uuid[4:8])
            except (BleakError, TimeoutError, OSError) as err:
                if char.uuid == ROWER_DATA:
                    raise
                _LOGGER.warning(
                    "%s: could not subscribe to %s: %s", self.address, char.uuid[4:8], _err_text(err)
                )
        _LOGGER.info("%s: subscribed to %s", self.address, subscribed)

        # Optional: the machine's resistance range, so the slider has the right bounds.
        range_char = next((c for c in chars if c.uuid == FTMS_RESISTANCE_RANGE), None)
        if range_char is not None and "read" in range_char.properties:
            try:
                self._step("read resistance range")
                raw = bytes(await client.read_gatt_char(range_char))
                parsed = parse_resistance_range(raw)
                _LOGGER.info("%s: resistance range raw=%s -> %s", self.address, raw.hex(" "), parsed)
                if parsed:
                    self.resistance_range = parsed
                    self.resistance_range_known = True
            except (BleakError, TimeoutError, OSError) as err:
                _LOGGER.debug("%s: cannot read resistance range: %s", self.address, _err_text(err))

        # Like QZ for DOMYOS-ROW-xxxx: "Start or Resume" lets the console stream its data.
        if self._ftms_cp is not None:
            self._step(
                f"write Start/Resume (handle {getattr(self._ftms_cp, 'handle', '?')})"
            )
            result = await self._ftms_command(
                client, bytes([FTMS_OP_START_RESUME]), ensure_control=True
            )
            _LOGGER.info("%s: Start/Resume -> %s", self.address, self._result_text(result))
        else:
            _LOGGER.warning("%s: no FTMS Control Point, read-only mode", self.address)

        self._ftms_stroke_t = time.monotonic()
        self._step("streaming")
        self._set_connected(True)
        while client.is_connected and self.enabled:
            await self._send_pending_resistance(client)
            self._ftms_idle_check()
            self._tick_derived(time.monotonic())
            await asyncio.sleep(POLL_INTERVAL)

    def _ftms_idle_check(self) -> None:
        """No new stroke for a few seconds: the rower isn't moving (same rule as QZ)."""
        now = time.monotonic()
        d = self.data
        if now - self._ftms_stroke_t > FTMS_STROKE_IDLE and (
            d.cadence or d.speed_kmh or d.power_w
        ):
            self.data = replace(
                d,
                cadence=0.0 if d.cadence is not None else None,
                speed_kmh=0.0 if d.speed_kmh is not None else None,
                power_w=0 if d.power_w is not None else None,
                pace_s500=None,
            )
            self._push()

    def _on_ftms_data(self, payload: bytes) -> None:
        parsed = parse_ftms_rower_data(payload)
        if parsed is None:
            return
        now = time.monotonic()
        if parsed.strokes is not None and parsed.strokes != self._ftms_strokes:
            self._ftms_strokes = parsed.strokes
            self._ftms_stroke_t = now
        self._note_strokes(parsed.strokes, now)
        if parsed.power_w is not None:
            self._rower_sends_power = True
        if parsed.elapsed_s is not None:
            self._rower_sends_elapsed = True
        self.data = self.data.merged(parsed)
        if not self._rower_sends_power:
            self.data = replace(
                self.data,
                power_w=self._power_from_pace(self.data.pace_s500, self.data.cadence),
            )
        self._last_packet = now
        self._check_expected(now)
        self._ftms_idle_check()
        self._push()

    # ------------------------------------------------------------ Domyos proprietary
    async def _write(self, client, data: bytes, wait_answer: bool) -> None:
        self._answer_event.clear()
        await client.write_gatt_char(PROP_WRITE, data, response=True)
        if wait_answer:
            with suppress(TimeoutError):
                await asyncio.wait_for(self._answer_event.wait(), ACK_TIMEOUT)

    async def _run_proprietary(self, client) -> bool:
        """Returns True if the console answered with status packets, False if silent."""
        self._step("subscribe domyos")
        await client.start_notify(PROP_NOTIFY, self._on_proprietary)
        _LOGGER.info("%s: Domyos protocol, sending init sequence", self.address)
        for i, (frame, wait_answer) in enumerate(INIT_FRAMES, 1):
            self._step(f"domyos init frame {i}/{len(INIT_FRAMES)}")
            await self._write(client, frame, wait_answer)
        self._step("domyos polling")

        started = time.monotonic()
        self._last_packet = started
        while client.is_connected and self.enabled:
            await self._write(client, NOOP, False)
            await self._send_pending_resistance(client)
            self._tick_derived(time.monotonic())
            await asyncio.sleep(POLL_INTERVAL)
            now = time.monotonic()
            if not self._got_packet and now - started > PROP_NO_DATA_TIMEOUT:
                _LOGGER.warning("%s: no valid Domyos status packet after init", self.address)
                return False
            if self._got_packet and now - self._last_packet > STALE_TIMEOUT:
                _LOGGER.info("%s: no status packet for %s s, closing", self.address, STALE_TIMEOUT)
                return True
        return self._got_packet

    def _on_proprietary(self, _char, payload: bytearray) -> None:
        packet = bytes(payload)
        self._answer_event.set()
        parsed = parse_proprietary(packet)
        if parsed is None:
            _LOGGER.debug(
                "%s: ignored packet (%d bytes): %s", self.address, len(packet), packet.hex(" ")
            )
            return

        now = time.monotonic()
        # New workout on the console (stroke counter went back down): restart distance.
        if self._last_strokes is not None and parsed.strokes < self._last_strokes:
            self._distance_m = 0.0
        self._last_strokes = parsed.strokes
        if self._last_t is not None and parsed.speed_kmh:
            self._distance_m += parsed.speed_kmh / 3.6 * (now - self._last_t)
        self._last_t = now
        self._last_packet = now
        self._got_packet = True

        self._note_strokes(parsed.strokes, now)
        self.data = replace(
            parsed,
            distance_m=round(self._distance_m, 1),
            power_w=self._power_from_pace(parsed.pace_s500, parsed.cadence),
            elapsed_s=self.data.elapsed_s,
        )
        self._check_expected(now)
        self._set_connected(True)
        self._push()
