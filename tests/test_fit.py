"""The FIT file is decoded by Garmin's official SDK; field numbers are checked against its profile."""
import io
from datetime import datetime, timezone

import fitparse
from garmin_fit_sdk import Decoder, Profile, Stream

from custom_components.domyos_rower import fit as F
from custom_components.domyos_rower.session import SessionRecorder


def make_session():
    rec = SessionRecorder(datetime(2026, 10, 3, 18, 11, 8, tzinfo=timezone.utc))
    dist = cal = 0.0
    strokes = 0
    for t in range(0, 601):
        rowing = not (240 <= t < 250)
        spd = 10.11 if rowing else 0
        dist += spd / 3.6
        strokes += 1 if (rowing and t % 2 == 0) else 0
        cal += 0.2 if rowing else 0
        rec.add(t, distance_m=dist, speed_kmh=spd, cadence=29 if rowing else 0, power_w=62 if rowing else 0,
                heart_rate=(130 + t // 20) if t > 30 else None, calories=cal, resistance=4, strokes=strokes)
    return rec


def decode(data):
    decoder = Decoder(Stream.from_bytes_io(io.BytesIO(data)))
    assert decoder.is_fit() and decoder.check_integrity()           # header + CRC are valid
    return Decoder(Stream.from_bytes_io(io.BytesIO(data))).read(enable_crc_check=True)


def test_official_decoder_reads_an_indoor_rowing_activity():
    rec = make_session()
    msgs, errors = decode(F.build_fit(rec, serial=42, utc_offset_s=7200))
    assert errors == []
    assert {k: len(v) for k, v in msgs.items()} == {
        "file_id_mesgs": 1, "event_mesgs": 2, "record_mesgs": 601,
        "lap_mesgs": 1, "session_mesgs": 1, "activity_mesgs": 1,
    }
    ses, lap = msgs["session_mesgs"][0], msgs["lap_mesgs"][0]
    for m in (ses, lap):
        assert m["sport"] == "rowing" and m["sub_sport"] == "indoor_rowing"
        assert m["total_calories"] == 118 and m["total_distance"] == 1659.7
    assert ses["total_elapsed_time"] == 600.0 and ses["total_timer_time"] == 590.0   # pause excluded
    assert ses["total_strokes"] == 296 and ses["avg_power"] == 62 and ses["max_heart_rate"] == 160
    assert ses["avg_cadence"] == 29 and ses["avg_speed"] == 2.808 and ses["num_laps"] == 1
    r = msgs["record_mesgs"][60]
    assert (r["power"], r["heart_rate"], r["cadence"], r["resistance"], r["calories"]) == (62, 133, 29, 4, 12)
    assert r["distance"] == 171.3 and r["speed"] == 2.808
    assert "heart_rate" not in msgs["record_mesgs"][5]               # no belt yet -> field absent, not 0
    fid = msgs["file_id_mesgs"][0]
    assert fid["type"] == "activity" and fid["serial_number"] == 42 and fid["product_name"] == "Domyos Rower (HA)"
    act = msgs["activity_mesgs"][0]
    assert act["local_timestamp"] - (act["timestamp"].timestamp() - F.FIT_EPOCH) == 7200   # local time offset


def test_second_independent_decoder_agrees():
    ff = fitparse.FitFile(io.BytesIO(F.build_fit(make_session())))
    ff.parse()
    ses = next(iter(ff.get_messages("session")))
    assert {f.name: f.value for f in ses}["total_cycles"] == 296
    assert sum(1 for _ in ff.get_messages("record")) == 601


def test_field_numbers_match_garmin_profile():
    """Every (message, field, type) the encoder writes exists in the official profile."""
    msgs = Profile["messages"]
    expected = {
        F.RECORD: {253: "uint32", 5: "uint32", 6: "uint16", 7: "uint16", 3: "uint8", 4: "uint8", 10: "uint8", 33: "uint16"},
        F.LAP: {254: "uint16", 253: "uint32", 2: "uint32", 7: "uint32", 8: "uint32", 9: "uint32", 10: "uint32",
                11: "uint16", 13: "uint16", 14: "uint16", 15: "uint8", 16: "uint8", 17: "uint8", 18: "uint8",
                19: "uint16", 20: "uint16"},
        F.SESSION: {254: "uint16", 253: "uint32", 2: "uint32", 7: "uint32", 8: "uint32", 9: "uint32", 10: "uint32",
                    11: "uint16", 14: "uint16", 15: "uint16", 16: "uint8", 17: "uint8", 18: "uint8", 19: "uint8",
                    20: "uint16", 21: "uint16", 25: "uint16", 26: "uint16"},
        F.ACTIVITY: {253: "uint32", 0: "uint32", 1: "uint16", 5: "uint32"},
    }
    sizes = {"uint8": 1, "uint16": 2, "uint32": 4}
    for gnum, fields in expected.items():
        profile = msgs[gnum]["fields"]
        for num, kind in fields.items():
            field = profile[num]
            base = {"date_time": "uint32", "local_date_time": "uint32", "message_index": "uint16"}.get(field["type"], field["type"])
            assert base == kind and sizes[kind], (gnum, num, field["type"], kind)
    assert Profile["types"]["sport"][F.SPORT_ROWING] == "rowing"
    assert Profile["types"]["sub_sport"][F.SUB_SPORT_INDOOR_ROWING] == "indoor_rowing"
    assert Profile["types"]["event"][F.EVENT_SESSION] == "session" and Profile["types"]["event"][F.EVENT_LAP] == "lap"


def test_crc_reference_vector():
    assert F.crc16(b"") == 0 and F.crc16(b"\x0e\x20") != 0
    data = F.build_fit(make_session())
    assert F.crc16(data[:-2]) == int.from_bytes(data[-2:], "little")
