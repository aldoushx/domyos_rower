"""Minimal FIT encoder for an indoor-rowing activity (no external dependency).

FIT is Garmin's native format and the richest one Strava/Garmin Connect read: it says
"rowing / indoor rowing" and carries calories, strokes, stroke rate, power and heart rate.
Field numbers and enum values below come from Garmin's official FIT profile and are
checked against the official decoder in the test-suite.
"""
from __future__ import annotations

import struct
from datetime import datetime, timezone

from .session import SessionRecorder, export_points

FIT_EPOCH = 631065600  # 1989-12-31T00:00:00Z as a Unix time
PROTOCOL_VERSION = 0x20
PROFILE_VERSION = 21158

# base types (code, size, invalid value)
ENUM, UINT8, UINT16, UINT32, STRING, UINT32Z = 0x00, 0x02, 0x84, 0x86, 0x07, 0x8C
_INFO = {
    ENUM: ("<B", 1, 0xFF),
    UINT8: ("<B", 1, 0xFF),
    UINT16: ("<H", 2, 0xFFFF),
    UINT32: ("<I", 4, 0xFFFFFFFF),
    UINT32Z: ("<I", 4, 0),
}

# global message numbers
FILE_ID, SESSION, LAP, RECORD, EVENT, ACTIVITY = 0, 18, 19, 20, 21, 34
# enumerations (official profile)
SPORT_ROWING, SUB_SPORT_INDOOR_ROWING = 15, 14
EVENT_TIMER, EVENT_SESSION, EVENT_LAP, EVENT_ACTIVITY = 0, 8, 9, 26
TYPE_START, TYPE_STOP, TYPE_STOP_ALL = 0, 1, 4
FILE_ACTIVITY, MANUFACTURER_DEVELOPMENT, ACTIVITY_MANUAL = 4, 255, 0

_CRC = (0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400)


def crc16(data: bytes, crc: int = 0) -> int:
    for byte in data:
        tmp = _CRC[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC[byte & 0xF]
        tmp = _CRC[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC[(byte >> 4) & 0xF]
    return crc


def fit_time(dt: datetime) -> int:
    return int(dt.astimezone(timezone.utc).timestamp()) - FIT_EPOCH


class _Writer:
    def __init__(self) -> None:
        self.buf = bytearray()
        self._defs: dict[int, list[tuple[int, int, int]]] = {}

    def define(self, local: int, global_num: int, fields: list[tuple[int, int, int]]) -> None:
        """fields: (field number, base type, size in bytes)."""
        self.buf += bytes([0x40 | local, 0, 0]) + struct.pack("<H", global_num) + bytes([len(fields)])
        for num, base, size in fields:
            self.buf += bytes([num, size, base])
        self._defs[local] = fields

    def data(self, local: int, values: list) -> None:
        self.buf.append(local)
        for (_num, base, size), value in zip(self._defs[local], values):
            if base == STRING:
                raw = (value or "").encode("utf-8")[: size - 1]
                self.buf += raw + b"\x00" * (size - len(raw))
                continue
            fmt, width, invalid = _INFO[base]
            if value is None:
                value = invalid
            else:
                value = max(0, min(int(round(value)), (1 << (8 * width)) - (2 if invalid else 1)))
            self.buf += struct.pack(fmt, value)


def build_fit(
    session: SessionRecorder,
    *,
    serial: int = 0,
    utc_offset_s: int = 0,
    product_name: str = "Domyos Rower (HA)",
) -> bytes:
    pts = export_points(session)
    if not pts:
        raise ValueError("empty session")
    summ = session.summary()
    start = fit_time(session.start)
    end = start + int(round(session.duration_s))
    elapsed_ms = int(round(session.duration_s * 1000))
    timer_ms = int(summ["timer_s"]) * 1000
    cm = lambda m: m * 100  # noqa: E731 - metres -> FIT centimetres
    mm = lambda v: v * 1000  # noqa: E731 - m/s -> mm/s

    w = _Writer()
    w.define(0, FILE_ID, [(0, ENUM, 1), (1, UINT16, 2), (2, UINT16, 2), (3, UINT32Z, 4),
                          (4, UINT32, 4), (8, STRING, 24)])
    w.data(0, [FILE_ACTIVITY, MANUFACTURER_DEVELOPMENT, 0, serial or None, start, product_name])

    w.define(1, EVENT, [(253, UINT32, 4), (0, ENUM, 1), (1, ENUM, 1), (4, UINT8, 1)])
    w.data(1, [start, EVENT_TIMER, TYPE_START, 0])

    w.define(2, RECORD, [(253, UINT32, 4), (5, UINT32, 4), (6, UINT16, 2), (7, UINT16, 2),
                         (3, UINT8, 1), (4, UINT8, 1), (10, UINT8, 1), (33, UINT16, 2)])
    for when, s in pts:
        w.data(2, [
            fit_time(when), cm(s.distance_m), mm(s.speed_ms), s.power_w,
            s.heart_rate, s.cadence, s.resistance, s.calories,
        ])

    w.data(1, [end, EVENT_TIMER, TYPE_STOP_ALL, 0])

    common = [
        (253, UINT32, 4), (2, UINT32, 4), (0, ENUM, 1), (1, ENUM, 1), (7, UINT32, 4), (8, UINT32, 4),
        (9, UINT32, 4), (10, UINT32, 4), (11, UINT16, 2),
    ]
    totals = [
        end, start, None, TYPE_STOP, elapsed_ms, timer_ms, cm(summ["distance_m"]),
        summ["strokes"], summ["calories"],
    ]
    # lap: avg/max speed 13/14, hr 15/16, cadence 17/18, power 19/20
    w.define(3, LAP, [(254, UINT16, 2)] + common + [
        (13, UINT16, 2), (14, UINT16, 2), (15, UINT8, 1), (16, UINT8, 1), (17, UINT8, 1),
        (18, UINT8, 1), (19, UINT16, 2), (20, UINT16, 2), (25, ENUM, 1), (39, ENUM, 1)])
    stats = [
        mm(summ["avg_speed_ms"]), mm(summ["max_speed_ms"]), summ["avg_hr"], summ["max_hr"],
        summ["avg_cadence"], summ["max_cadence"], summ["avg_power_w"], summ["max_power_w"],
    ]
    w.data(3, [0] + [*totals[:2], EVENT_LAP, *totals[3:]] + stats + [SPORT_ROWING, SUB_SPORT_INDOOR_ROWING])

    # session: sport 5/6, avg/max speed 14/15, hr 16/17, cadence 18/19, power 20/21, laps 25/26
    w.define(4, SESSION, [(254, UINT16, 2)] + common + [
        (5, ENUM, 1), (6, ENUM, 1), (14, UINT16, 2), (15, UINT16, 2), (16, UINT8, 1), (17, UINT8, 1),
        (18, UINT8, 1), (19, UINT8, 1), (20, UINT16, 2), (21, UINT16, 2), (25, UINT16, 2), (26, UINT16, 2)])
    w.data(4, [0] + [*totals[:2], EVENT_SESSION, *totals[3:]]
           + [SPORT_ROWING, SUB_SPORT_INDOOR_ROWING] + stats + [0, 1])

    w.define(5, ACTIVITY, [(253, UINT32, 4), (0, UINT32, 4), (1, UINT16, 2), (2, ENUM, 1),
                           (3, ENUM, 1), (4, ENUM, 1), (5, UINT32, 4)])
    w.data(5, [end, timer_ms, 1, ACTIVITY_MANUAL, EVENT_ACTIVITY, TYPE_STOP, end + utc_offset_s])

    body = bytes(w.buf)
    header = struct.pack("<BBHI4s", 14, PROTOCOL_VERSION, PROFILE_VERSION, len(body), b".FIT")
    header += struct.pack("<H", crc16(header))
    return header + body + struct.pack("<H", crc16(body, crc16(header)))
