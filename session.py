"""Workout session recording and TCX / GPX export.

Pure Python, no Home Assistant import: it only knows about samples and file formats.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

CREATOR_NAME = "Domyos Rower (Home Assistant)"


@dataclass
class Sample:
    t: float  # seconds since the session started
    distance_m: float  # cumulative
    speed_ms: float
    cadence: float  # strokes per minute
    power_w: int | None
    heart_rate: int | None
    calories: float  # cumulative kcal
    resistance: float | None
    strokes: int  # cumulative


class SessionRecorder:
    """Collects ~1 Hz samples. Cumulative counters survive a reset on the console."""

    def __init__(self, start: datetime | None = None) -> None:
        self.start = (start or datetime.now(timezone.utc)).astimezone(timezone.utc)
        self.samples: list[Sample] = []
        self._offset = {"distance": 0.0, "calories": 0.0, "strokes": 0.0}
        self._last_raw = {"distance": 0.0, "calories": 0.0, "strokes": 0.0}

    # -------------------------------------------------------------- recording
    def _cumulative(self, key: str, raw: float | None) -> float:
        if raw is None:
            raw = self._last_raw[key]
        last = self._last_raw[key]
        if last > 1 and raw < last * 0.5:  # the console started a new workout
            self._offset[key] += last
        self._last_raw[key] = raw
        value = raw + self._offset[key]
        if self.samples:  # never go backwards (rounding noise, calibration changes)
            previous = {
                "distance": self.samples[-1].distance_m,
                "calories": self.samples[-1].calories,
                "strokes": self.samples[-1].strokes,
            }[key]
            value = max(value, previous)
        return value

    def add(
        self,
        t: float,
        *,
        distance_m: float | None,
        speed_kmh: float | None,
        cadence: float | None,
        power_w: int | None,
        heart_rate: int | None,
        calories: float | None,
        resistance: float | None,
        strokes: int | None,
    ) -> None:
        self.samples.append(
            Sample(
                t=round(t, 2),
                distance_m=round(self._cumulative("distance", distance_m), 1),
                speed_ms=round(max(speed_kmh or 0.0, 0.0) / 3.6, 3),
                cadence=float(cadence or 0.0),
                power_w=None if power_w is None else int(power_w),
                heart_rate=int(heart_rate) if heart_rate else None,
                calories=round(self._cumulative("calories", calories), 1),
                resistance=resistance,
                strokes=int(self._cumulative("strokes", strokes)),
            )
        )

    # -------------------------------------------------------------- summary
    @property
    def duration_s(self) -> float:
        return self.samples[-1].t if self.samples else 0.0

    def summary(self) -> dict:
        s = self.samples
        if not s:
            return {"duration_s": 0, "distance_m": 0.0, "calories": 0, "strokes": 0}
        hr = [x.heart_rate for x in s if x.heart_rate]
        moving = [x for x in s if x.cadence > 0]
        pw = [x.power_w for x in moving if x.power_w is not None]
        timer = sum(
            min(b.t - a.t, 2.0) for a, b in zip(s, s[1:]) if b.cadence > 0
        )
        return {
            "duration_s": round(self.duration_s),
            "timer_s": round(timer),
            "distance_m": round(s[-1].distance_m, 1),
            "calories": round(s[-1].calories),
            "strokes": s[-1].strokes,
            "avg_speed_ms": round(sum(x.speed_ms for x in moving) / len(moving), 3) if moving else 0.0,
            "max_speed_ms": max(x.speed_ms for x in s),
            "avg_cadence": round(sum(x.cadence for x in moving) / len(moving), 1) if moving else 0.0,
            "max_cadence": max((x.cadence for x in s), default=0.0),
            "avg_hr": round(sum(hr) / len(hr)) if hr else None,
            "max_hr": max(hr) if hr else None,
            "avg_power_w": round(sum(pw) / len(pw)) if pw else None,
            "max_power_w": max(pw) if pw else None,
        }

    # -------------------------------------------------------------- persistence
    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "samples": [
                [x.t, x.distance_m, x.speed_ms, x.cadence, x.power_w, x.heart_rate,
                 x.calories, x.resistance, x.strokes]
                for x in self.samples
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionRecorder":
        rec = cls(datetime.fromisoformat(data["start"]))
        rec.samples = [Sample(*row) for row in data["samples"]]
        if rec.samples:
            last = rec.samples[-1]
            rec._last_raw = {"distance": last.distance_m, "calories": last.calories, "strokes": last.strokes}
        return rec


# ====================================================================== exporters
def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_points(session: SessionRecorder) -> list[tuple[datetime, Sample]]:
    """One point per distinct second (formats need strictly increasing times)."""
    points: list[tuple[datetime, Sample]] = []
    seen: int | None = None
    for s in session.samples:
        sec = int(round(s.t))
        if sec == seen:
            continue
        seen = sec
        points.append((session.start + timedelta(seconds=sec), s))
    return points


def build_tcx(session: SessionRecorder, notes: str = "") -> str:
    """Garmin TrainingCenterDatabase v2. Sport 'Other' (rowing isn't a TCX sport)."""
    pts = export_points(session)
    if not pts:
        raise ValueError("empty session")
    summ = session.summary()
    start = _iso(session.start)
    total_time = max(session.duration_s, 1.0)

    lap_hr = ""
    if summ.get("avg_hr"):
        lap_hr = (
            f"<AverageHeartRateBpm><Value>{summ['avg_hr']}</Value></AverageHeartRateBpm>"
            f"<MaximumHeartRateBpm><Value>{summ['max_hr']}</Value></MaximumHeartRateBpm>"
        )

    rows = []
    for when, s in pts:
        hr = f"<HeartRateBpm><Value>{s.heart_rate}</Value></HeartRateBpm>" if s.heart_rate else ""
        cad = f"<Cadence>{int(min(254, max(0, round(s.cadence))))}</Cadence>"
        watts = f"<ns3:Watts>{int(min(65535, max(0, s.power_w)))}</ns3:Watts>" if s.power_w is not None else ""
        rows.append(
            f"<Trackpoint><Time>{_iso(when)}</Time>"
            f"<DistanceMeters>{s.distance_m:.1f}</DistanceMeters>{hr}{cad}"
            f"<Extensions><ns3:TPX><ns3:Speed>{s.speed_ms:.3f}</ns3:Speed>{watts}</ns3:TPX></Extensions>"
            f"</Trackpoint>"
        )
    note = f"<Notes>{escape(notes)}</Notes>" if notes else ""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" '
        'xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 '
        'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">\n'
        f'<Activities><Activity Sport="Other"><Id>{start}</Id>'
        f'<Lap StartTime="{start}"><TotalTimeSeconds>{total_time:.1f}</TotalTimeSeconds>'
        f'<DistanceMeters>{summ["distance_m"]:.1f}</DistanceMeters>'
        f'<MaximumSpeed>{summ["max_speed_ms"]:.3f}</MaximumSpeed>'
        f'<Calories>{int(summ["calories"])}</Calories>{lap_hr}'
        f'<Intensity>Active</Intensity><TriggerMethod>Manual</TriggerMethod>'
        f'<Track>{"".join(rows)}</Track>{note}</Lap>'
        f'<Creator xsi:type="Device_t"><Name>{escape(CREATOR_NAME)}</Name><UnitId>0</UnitId>'
        f'<ProductID>0</ProductID><Version><VersionMajor>0</VersionMajor><VersionMinor>5</VersionMinor>'
        f'</Version></Creator></Activity></Activities></TrainingCenterDatabase>\n'
    )


def build_gpx(session: SessionRecorder, name: str, latitude: float, longitude: float) -> str:
    """GPX 1.1 track. GPX is a GPS format: an indoor row has no position, so every point
    uses the given placeholder coordinates. Only time, heart rate and cadence are carried."""
    pts = export_points(session)
    if not pts:
        raise ValueError("empty session")
    rows = []
    for when, s in pts:
        ext = ""
        parts = ""
        if s.heart_rate:
            parts += f"<gpxtpx:hr>{s.heart_rate}</gpxtpx:hr>"
        parts += f"<gpxtpx:cad>{int(min(254, max(0, round(s.cadence))))}</gpxtpx:cad>"
        ext = f"<extensions><gpxtpx:TrackPointExtension>{parts}</gpxtpx:TrackPointExtension></extensions>"
        rows.append(f'<trkpt lat="{latitude:.6f}" lon="{longitude:.6f}"><time>{_iso(when)}</time>{ext}</trkpt>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<gpx version="1.1" creator="{escape(CREATOR_NAME)}" '
        'xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd '
        'http://www.garmin.com/xmlschemas/TrackPointExtension/v1 '
        'http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd">\n'
        f'<metadata><name>{escape(name)}</name><time>{_iso(session.start)}</time></metadata>\n'
        f'<trk><name>{escape(name)}</name><type>rowing</type><trkseg>{"".join(rows)}</trkseg></trk>\n'
        '</gpx>\n'
    )


def file_stem(start: datetime) -> str:
    """e.g. rowing_20261003_201108, from the time zone of the datetime it is given."""
    return "rowing_" + start.strftime("%Y%m%d_%H%M%S")
