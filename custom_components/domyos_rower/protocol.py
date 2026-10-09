"""Domyos rower protocol, decoded from the QZ (qdomyos-zwift) sources.

Two families exist:
* "proprietary": ISSC/Microchip UART-style service. The console must be
  initialised and polled with a 3-byte no-op frame; it answers with a
  26-byte status packet.
* FTMS: standard Fitness Machine Service, Rower Data characteristic (0x2AD1).
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

PROP_SERVICE = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
PROP_WRITE = "49535343-8841-43f4-a8d4-ecbe34729bb3"
PROP_NOTIFY = "49535343-1e4d-4bd9-ba61-23c647249616"

FTMS_SERVICE = "00001826-0000-1000-8000-00805f9b34fb"
ROWER_DATA = "00002ad1-0000-1000-8000-00805f9b34fb"
FTMS_RESISTANCE_RANGE = "00002ad6-0000-1000-8000-00805f9b34fb"
FTMS_CONTROL_POINT = "00002ad9-0000-1000-8000-00805f9b34fb"

# FTMS Control Point opcodes (same values QZ uses)
FTMS_OP_REQUEST_CONTROL = 0x00
FTMS_OP_SET_RESISTANCE = 0x04
FTMS_OP_START_RESUME = 0x07
FTMS_OP_RESPONSE = 0x80

FTMS_RESULTS = {
    0x01: "success",
    0x02: "op code not supported",
    0x03: "invalid parameter",
    0x04: "operation failed",
    0x05: "control not permitted",
}

NOOP = bytes.fromhex("f0ac9c")

# (frame, wait_for_answer) - same order as btinit_changyow(false) in QZ.
INIT_FRAMES: tuple[tuple[bytes, bool], ...] = (
    (bytes.fromhex("f0c801b9"), True),
    (bytes.fromhex("f0c9b9"), True),
    (bytes.fromhex("f0a393"), True),
    (bytes.fromhex("f0a494"), True),
    (bytes.fromhex("f0a595"), True),
    (bytes.fromhex("f0ab9b"), True),
    (bytes.fromhex("f0c403b7"), True),
    (bytes.fromhex("f0adffffffffffffffffffffffffffffffff01ff"), False),
    (bytes.fromhex("ffff8b"), True),
    (bytes.fromhex("f0cb020008ffffffffffffffffffffffffff0100"), False),
    (bytes.fromhex("0001ffffffffb6"), True),
    (bytes.fromhex("f0adffff0005ffffffffffffff0000ffffff01ff"), False),
)

_INIT_COUNT = {"full": 12, "no_bt_screen": 7, "minimal": 2, "none": 0, "passive": 0}


def init_frames(mode: str = "full") -> tuple[tuple[bytes, bool], ...]:
    """Init frames to send for `mode` (see INIT_MODES)."""
    return INIT_FRAMES[: _INIT_COUNT.get(mode, 12)]


PROP_PACKET_LEN = 26
RESISTANCE_MIN = 1
RESISTANCE_MAX = 15


def build_resistance_frames(level: int) -> tuple[bytes, bytes]:
    """Frames that set the resistance (forceResistance() in domyosrower.cpp).

    The 23-byte command is sent as 20 bytes + 3 bytes, like QZ does.
    """
    level = max(RESISTANCE_MIN, min(RESISTANCE_MAX, int(level)))
    frame = bytearray(
        [0xF0, 0xAD] + [0xFF] * 10 + [0xFF] * 5 + [0x00, 0x01, 0xFF, 0xFF, 0xFF, 0x00]
    )
    assert len(frame) == 23
    frame[10] = level
    frame[22] = sum(frame[:22]) & 0xFF  # trailing byte is a simple checksum
    return bytes(frame[:20]), bytes(frame[20:])


@dataclass(frozen=True)
class RowerData:
    """One snapshot of the rower metrics (None = unknown)."""

    cadence: float | None = None  # strokes per minute
    strokes: int | None = None
    speed_kmh: float | None = None
    pace_s500: int | None = None  # seconds per 500 m
    distance_m: float | None = None
    calories: int | None = None  # kcal
    power_w: int | None = None
    resistance: int | None = None
    heart_rate: int | None = None
    elapsed_s: int | None = None

    def merged(self, new: "RowerData") -> "RowerData":
        """Overlay the non-None fields of `new` on this snapshot."""
        changes = {
            f.name: getattr(new, f.name)
            for f in fields(new)
            if getattr(new, f.name) is not None
        }
        return replace(self, **changes)


def _pace_to_speed(pace_s500: int) -> float:
    return 1800.0 / pace_s500 if pace_s500 > 0 else 0.0


def parse_proprietary(packet: bytes) -> RowerData | None:
    """Decode the 26-byte status packet (offsets from domyosrower.cpp)."""
    if len(packet) != PROP_PACKET_LEN:
        return None

    strokes = (packet[2] << 8) | packet[3]
    raw_pace = (packet[6] << 8) | packet[7]
    cadence = packet[9]
    calories = (packet[10] << 8) | packet[11]
    resistance = packet[14] - 256 if packet[14] > 127 else packet[14]
    heart = packet[18]

    if raw_pace == 0 or raw_pace > 65000 or cadence == 0:
        speed = 0.0
        pace = None
    else:
        speed = _pace_to_speed(raw_pace)
        pace = raw_pace

    return RowerData(
        cadence=float(cadence),
        strokes=strokes,
        speed_kmh=round(speed, 2),
        pace_s500=pace,
        calories=calories,
        resistance=max(resistance, 1),
        heart_rate=heart if heart > 0 else None,
    )


class _Reader:
    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def _take(self, n: int) -> bytes:
        if self.pos + n > len(self.data):
            raise IndexError
        chunk = self.data[self.pos : self.pos + n]
        self.pos += n
        return chunk

    def u8(self) -> int:
        return self._take(1)[0]

    def u16(self) -> int:
        return int.from_bytes(self._take(2), "little")

    def s16(self) -> int:
        return int.from_bytes(self._take(2), "little", signed=True)

    def u24(self) -> int:
        return int.from_bytes(self._take(3), "little")


def parse_ftms_rower_data(data: bytes) -> RowerData | None:
    """Decode a standard FTMS Rower Data notification (0x2AD1)."""
    if len(data) < 2:
        return None
    flags = data[0] | (data[1] << 8)
    r = _Reader(data, 2)
    out: dict = {}
    try:
        if not flags & 0x0001:  # "More Data" bit is inverted in the spec
            out["cadence"] = r.u8() / 2.0
            out["strokes"] = r.u16()
        if flags & 0x0002:
            r.u8()  # average stroke rate
        if flags & 0x0004:
            out["distance_m"] = float(r.u24())
        if flags & 0x0008:
            pace = r.u16()
            if 0 < pace < 0xFFFF:
                out["pace_s500"] = pace
                out["speed_kmh"] = round(_pace_to_speed(pace), 2)
            elif pace == 0:
                out["speed_kmh"] = 0.0
        if flags & 0x0010:
            r.u16()  # average pace
        if flags & 0x0020:
            out["power_w"] = r.s16()
        if flags & 0x0040:
            r.s16()  # average power
        if flags & 0x0080:
            out["resistance"] = r.s16()
        if flags & 0x0100:
            out["calories"] = r.u16()
            r.u16()  # energy per hour
            r.u8()  # energy per minute
        if flags & 0x0200:
            hr = r.u8()
            if hr > 0:
                out["heart_rate"] = hr
        if flags & 0x0400:
            r.u8()  # metabolic equivalent
        if flags & 0x0800:
            out["elapsed_s"] = r.u16()
    except IndexError:
        pass  # truncated frame: keep what was decoded
    return RowerData(**out)


def build_ftms_set_resistance(level: float) -> bytes:
    """FTMS "Set Target Resistance Level": opcode + uint8, resolution 0.1 (QZ: level*10)."""
    return bytes([FTMS_OP_SET_RESISTANCE, max(0, min(255, int(round(level * 10))))])


def parse_ftms_response(data: bytes) -> tuple[int, int] | None:
    """Control Point indication -> (request opcode, result code)."""
    if len(data) >= 3 and data[0] == FTMS_OP_RESPONSE:
        return data[1], data[2]
    return None


def parse_resistance_range(data: bytes) -> tuple[float, float, float] | None:
    """Supported Resistance Level Range (0x2AD6) -> (min, max, step), or None.

    Spec layout is 3 x uint8 with a 0.1 resolution; 3 x uint16 is also accepted.
    """
    if len(data) == 3:
        lo, hi, inc = (b / 10.0 for b in data)
    elif len(data) == 6:
        lo, hi, inc = (int.from_bytes(data[i : i + 2], "little") / 10.0 for i in (0, 2, 4))
    else:
        return None
    if hi <= lo or hi <= 0:
        return None
    return lo, hi, inc if inc > 0 else 1.0


# ---- console screen (Domyos protocol only): QZ's updateDisplay(), once per second --------
_DISPLAY2_TEMPLATE = bytes([0xF0, 0xCD, 0x01, 0x00, 0x00, 0x01] + [0xFF] * 20 + [0x00])
_DISPLAY_TEMPLATE = bytes(
    [0xF0, 0xCB, 0x03, 0x00, 0x00, 0xFF, 0x01, 0x00, 0x00, 0x02, 0x01, 0x00, 0x00, 0x00,
     0x01, 0x00, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x00]
)


DISPLAY_OVERRIDE_RANGE = range(3, 26)  # bytes 0-2 are the header, byte 26 the checksum


def _check_overrides(overrides: dict[int, int] | None) -> dict[int, int]:
    clean: dict[int, int] = {}
    for index, value in (overrides or {}).items():
        index, value = int(index), int(value)
        if index not in DISPLAY_OVERRIDE_RANGE:
            raise ValueError(f"byte index {index} is outside 3..25")
        if not 0 <= value <= 255:
            raise ValueError(f"byte {index}: value {value} is outside 0..255")
        clean[index] = value
    return clean


# Console "workout" frames from QZ (btinit_changyow(startTape=true) and "stop tape").
CONSOLE_START_FRAMES: tuple[tuple[bytes, bool], ...] = (
    (bytes.fromhex("ffff94"), True),
    (bytes.fromhex("f0cbffffffffffffffffffffffff01001401ffff"), False),
    (bytes.fromhex("ffffffffffffbd"), True),
)
CONSOLE_STOP_FRAME = bytes.fromhex("f0c800b8")

# Numeric slots of the screen frame that are 0 in the template (3/4 = time, the rest unknown
# or used by QZ). The "numbered" probe puts each slot's own index in it so that whatever the
# console shows tells which byte feeds which field.
PROBE_NUMBERED = {7: 0, 8: 8, 11: 11, 12: 12, 13: 13, 15: 15, 16: 16, 19: 0, 20: 20}


def build_display_frames(
    elapsed_s: int,
    speed_kmh: float,
    heart_rate: float,
    strokes: float,
    calories: float,
    odometer_km: float,
    overrides: dict[int, int] | None = None,
    overrides2: dict[int, int] | None = None,
) -> tuple[bytes, bytes, bytes, bytes]:
    """Four chunks to write in order: (display2 20 B, display2 7 B, display 20 B, display 7 B).

    `overrides` / `overrides2` force raw bytes of the screen frame (`f0 cb 03`) and of the
    odometer frame (`f0 cd 01`) before the checksum: this is for mapping an unknown console.
    """
    over, over2 = _check_overrides(overrides), _check_overrides(overrides2)
    d2 = bytearray(_DISPLAY2_TEMPLATE)
    odo = int(max(odometer_km, 0) * 10) & 0xFFFF  # tenths of km
    d2[3], d2[4] = (odo >> 8) & 0xFF, odo & 0xFF
    for index, value in over2.items():
        d2[index] = value
    d2[26] = sum(d2[:26]) & 0xFF

    d = bytearray(_DISPLAY_TEMPLATE)
    elapsed_s = max(int(elapsed_s), 0)
    d[3] = (elapsed_s // 60) & 0xFF
    d[4] = (elapsed_s % 60) & 0xFF
    speed = int(max(speed_kmh, 0)) & 0xFFFF
    d[7], d[8] = (speed >> 8) & 0xFF, speed & 0xFF
    d[12] = int(max(heart_rate, 0)) & 0xFF
    # Bytes 15/16 feed the "Count" field, shown divided by 10 (probe: 0x0F10 -> 385; 27 -> 2),
    # so the total stroke count is sent x10. The Spm and Kcal fields are still unmapped.
    count = int(max(strokes, 0) * 10) & 0xFFFF
    d[15], d[16] = (count >> 8) & 0xFF, count & 0xFF
    # On the Rower 500 the "Km" field is bytes 19/20, in tenths of km (QZ puts kcal there,
    # which this console shows as distance).
    km10 = int(max(odometer_km, 0) * 10) & 0xFFFF
    d[19], d[20] = (km10 >> 8) & 0xFF, km10 & 0xFF
    for index, value in over.items():
        d[index] = value
    d[26] = sum(d[:26]) & 0xFF
    return bytes(d2[:20]), bytes(d2[20:]), bytes(d[:20]), bytes(d[20:])


def format_pace(seconds: int | None) -> str | None:
    """Pace per 500 m as mm:ss (178 -> '02:58')."""
    if seconds is None or seconds <= 0:
        return None
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"
