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


def format_pace(seconds: int | None) -> str | None:
    """Pace per 500 m as mm:ss (178 -> '02:58')."""
    if seconds is None or seconds <= 0:
        return None
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"
