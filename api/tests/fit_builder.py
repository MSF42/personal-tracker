"""A minimal FIT *encoder* for tests.

fitdecode can only read FIT, so tests build small synthetic activity files here:
file_id, developer field descriptions, sport, records, laps, session, activity.
Only what the parser needs is encoded; scales/offsets follow the FIT profile so
fitdecode decodes them to the same units a real device file would.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)

# base types: (base_type_byte, struct format)
ENUM = (0x00, "B")
UINT8 = (0x02, "B")
SINT8 = (0x01, "b")
UINT16 = (0x84, "H")
SINT32 = (0x85, "i")
UINT32 = (0x86, "I")
UINT32Z = (0x8C, "I")
BYTE = (0x0D, "B")
STRING = (0x07, "s")

_CRC_TABLE = [
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
]  # fmt: skip


def fit_crc(data: bytes, crc: int = 0) -> int:
    for byte in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def fit_time(dt: datetime) -> int:
    return int((dt - FIT_EPOCH).total_seconds())


@dataclass
class Field:
    num: int
    base: tuple[int, str]
    value: object
    size: int | None = None  # for strings / byte arrays
    dev_index: int | None = None  # developer field when set


@dataclass
class Message:
    global_num: int
    fields: list[Field]


@dataclass
class FitRecord:
    offset_s: float
    distance_m: float | None = None
    heart_rate: int | None = None
    cadence: int | None = None  # strides/min, as a device records it
    speed_mps: float | None = None
    altitude_m: float | None = None
    power: int | None = None
    lat: float | None = None
    lon: float | None = None


@dataclass
class FitLapSpec:
    start_offset_s: float
    timer_s: float
    distance_m: float
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: int | None = None
    trigger: int = 2  # distance


@dataclass
class FitSpec:
    start: datetime
    records: list[FitRecord]
    laps: list[FitLapSpec] = field(default_factory=list)
    total_distance_m: float | None = None
    timer_s: float | None = None
    elapsed_s: float | None = None
    avg_hr: int | None = None
    max_hr: int | None = None
    avg_cadence: int | None = None  # strides/min
    calories: int | None = None
    total_ascent_m: int | None = None
    avg_power: int | None = None
    sport_name: str = "Run"
    local_offset_hours: int = -4
    session_uuid: bytes | None = None
    indoor: bool | None = None
    include_session: bool = True


class _Encoder:
    def __init__(self) -> None:
        self.body = bytearray()
        self._defs: dict[tuple[int, tuple[tuple[int, int, int, int | None], ...]], int] = {}
        self._next_local = 0

    def _field_bytes(self, f: Field) -> bytes:
        base, fmt = f.base
        if fmt == "s":
            raw = str(f.value).encode() + b"\0"
            size = f.size or len(raw)
            return raw.ljust(size, b"\0")[:size]
        if base == BYTE[0] and isinstance(f.value, (bytes, bytearray)):
            size = f.size or len(f.value)
            return bytes(f.value).ljust(size, b"\0")[:size]
        return struct.pack("<" + fmt, f.value)

    def write(self, msg: Message) -> None:
        encoded = [(f, self._field_bytes(f)) for f in msg.fields]
        signature = (
            msg.global_num,
            tuple((f.num, len(b), f.base[0], f.dev_index) for f, b in encoded),
        )
        local = self._defs.get(signature)
        if local is None:
            local = self._next_local % 16
            self._next_local += 1
            self._defs[signature] = local
            normal = [(f, b) for f, b in encoded if f.dev_index is None]
            dev = [(f, b) for f, b in encoded if f.dev_index is not None]
            header = 0x40 | local | (0x20 if dev else 0)
            self.body += bytes([header, 0, 0]) + struct.pack("<H", msg.global_num)
            self.body.append(len(normal))
            for f, b in normal:
                self.body += bytes([f.num, len(b), f.base[0]])
            if dev:
                self.body.append(len(dev))
                for f, b in dev:
                    assert f.dev_index is not None
                    self.body += bytes([f.num, len(b), f.dev_index])
        self.body.append(local)
        for f, b in encoded:
            if f.dev_index is None:
                self.body += b
        for f, b in encoded:
            if f.dev_index is not None:
                self.body += b

    def finish(self) -> bytes:
        header = struct.pack("<BBHI4s", 14, 0x20, 2140, len(self.body), b".FIT")
        header += struct.pack("<H", fit_crc(header))
        data = header + bytes(self.body)
        return data + struct.pack("<H", fit_crc(data))


def _scaled(value: float, scale: float, offset: float = 0.0) -> int:
    return int(round((value + offset) * scale))


def _semicircles(deg: float) -> int:
    return int(round(deg * 2**31 / 180))


def build_fit(spec: FitSpec) -> bytes:  # noqa: C901 - straight-line encoding
    enc = _Encoder()
    start_ts = fit_time(spec.start)
    last = spec.records[-1] if spec.records else FitRecord(offset_s=0)
    end_dt = spec.start + timedelta(seconds=last.offset_s)
    end_ts = fit_time(end_dt)
    timer = spec.timer_s if spec.timer_s is not None else last.offset_s
    elapsed = spec.elapsed_s if spec.elapsed_s is not None else timer
    total_dist = (
        spec.total_distance_m if spec.total_distance_m is not None else (last.distance_m or 0.0)
    )

    enc.write(
        Message(
            0,
            [
                Field(0, ENUM, 4),  # type = activity
                Field(1, UINT16, 255),  # manufacturer = development
                Field(3, UINT32Z, 12345),
                Field(4, UINT32, start_ts),
            ],
        )
    )
    use_dev = spec.session_uuid is not None or spec.indoor is not None
    if use_dev:
        enc.write(Message(207, [Field(3, UINT8, 0), Field(1, BYTE, b"\x01" * 16, size=16)]))
        enc.write(
            Message(
                206,
                [
                    Field(0, UINT8, 0),
                    Field(1, UINT8, 0),
                    Field(2, UINT8, BYTE[0]),
                    Field(3, STRING, "SESSION UUID", size=16),
                ],
            )
        )
        enc.write(
            Message(
                206,
                [
                    Field(0, UINT8, 0),
                    Field(1, UINT8, 1),
                    Field(2, UINT8, UINT8[0]),
                    Field(3, STRING, "SESSION INDOOR", size=16),
                ],
            )
        )
    enc.write(
        Message(
            12, [Field(0, ENUM, 1), Field(1, ENUM, 0), Field(3, STRING, spec.sport_name, size=16)]
        )
    )

    for rec in spec.records:
        fields = [Field(253, UINT32, start_ts + int(rec.offset_s))]
        if rec.lat is not None and rec.lon is not None:
            fields += [
                Field(0, SINT32, _semicircles(rec.lat)),
                Field(1, SINT32, _semicircles(rec.lon)),
            ]
        if rec.distance_m is not None:
            fields.append(Field(5, UINT32, _scaled(rec.distance_m, 100)))
        if rec.heart_rate is not None:
            fields.append(Field(3, UINT8, rec.heart_rate))
        if rec.cadence is not None:
            fields.append(Field(4, UINT8, rec.cadence))
        if rec.speed_mps is not None:
            fields.append(Field(6, UINT16, _scaled(rec.speed_mps, 1000)))
        if rec.altitude_m is not None:
            fields.append(Field(2, UINT16, _scaled(rec.altitude_m, 5, 500)))
        if rec.power is not None:
            fields.append(Field(7, UINT16, rec.power))
        enc.write(Message(20, fields))

    for i, lap in enumerate(spec.laps):
        lap_start = start_ts + int(lap.start_offset_s)
        fields = [
            Field(253, UINT32, lap_start + int(lap.timer_s)),
            Field(254, UINT16, i),
            Field(2, UINT32, lap_start),
            Field(7, UINT32, _scaled(lap.timer_s, 1000)),
            Field(8, UINT32, _scaled(lap.timer_s, 1000)),
            Field(9, UINT32, _scaled(lap.distance_m, 100)),
            Field(24, ENUM, lap.trigger),
            Field(25, ENUM, 1),  # sport = running (resolves *_running_cadence subfields)
        ]
        if lap.avg_hr is not None:
            fields.append(Field(15, UINT8, lap.avg_hr))
        if lap.max_hr is not None:
            fields.append(Field(16, UINT8, lap.max_hr))
        if lap.avg_cadence is not None:
            fields.append(Field(17, UINT8, lap.avg_cadence))
        enc.write(Message(19, fields))

    if spec.include_session:
        fields = [
            Field(253, UINT32, end_ts),
            Field(254, UINT16, 0),
            Field(2, UINT32, start_ts),
            Field(5, ENUM, 1),  # sport running
            Field(6, ENUM, 0),
            Field(7, UINT32, _scaled(elapsed, 1000)),
            Field(8, UINT32, _scaled(timer, 1000)),
            Field(9, UINT32, _scaled(total_dist, 100)),
            Field(26, UINT16, len(spec.laps)),
        ]
        if spec.avg_hr is not None:
            fields.append(Field(16, UINT8, spec.avg_hr))
        if spec.max_hr is not None:
            fields.append(Field(17, UINT8, spec.max_hr))
        if spec.avg_cadence is not None:
            fields.append(Field(18, UINT8, spec.avg_cadence))
        if spec.calories is not None:
            fields.append(Field(11, UINT16, spec.calories))
        if spec.total_ascent_m is not None:
            fields.append(Field(22, UINT16, spec.total_ascent_m))
        if spec.avg_power is not None:
            fields.append(Field(20, UINT16, spec.avg_power))
        if spec.session_uuid is not None:
            fields.append(Field(0, BYTE, spec.session_uuid, size=16, dev_index=0))
        if spec.indoor is not None:
            fields.append(Field(1, UINT8, int(spec.indoor), dev_index=0))
        enc.write(Message(18, fields))

    enc.write(
        Message(
            34,
            [
                Field(253, UINT32, end_ts),
                Field(0, UINT32, _scaled(timer, 1000)),
                Field(1, UINT16, 1),
                Field(2, ENUM, 0),
                Field(5, UINT32, end_ts + spec.local_offset_hours * 3600),
            ],
        )
    )
    return enc.finish()


def simple_run(
    *,
    start: datetime = datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
    seconds: int = 720,
    distance_m: float = 2000.0,
    hr: int = 150,
    uuid_bytes: bytes | None = None,
    indoor: bool | None = None,
) -> bytes:
    """A steady run sampled every 10 s with one km lap per 1000 m."""
    records = []
    n = seconds // 10
    for i in range(n + 1):
        frac = i / n
        records.append(
            FitRecord(
                offset_s=i * 10,
                distance_m=distance_m * frac,
                heart_rate=hr + (i % 5),
                cadence=80,
                speed_mps=distance_m / seconds,
                altitude_m=300 + 10 * frac,
                power=250,
                lat=51.5 + 0.01 * frac,
                lon=-0.1,
            )
        )
    laps = []
    km = 0
    while (km + 1) * 1000 <= distance_m:
        lap_s = seconds * 1000 / distance_m
        laps.append(
            FitLapSpec(
                start_offset_s=km * lap_s, timer_s=lap_s, distance_m=1000, avg_hr=hr, avg_cadence=80
            )
        )
        km += 1
    return build_fit(
        FitSpec(
            start=start,
            records=records,
            laps=laps,
            avg_hr=hr,
            max_hr=hr + 4,
            avg_cadence=80,
            calories=170,
            total_ascent_m=10,
            avg_power=250,
            session_uuid=uuid_bytes,
            indoor=indoor,
        )
    )
