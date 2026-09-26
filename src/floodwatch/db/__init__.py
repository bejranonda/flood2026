"""Database access (psycopg 3). Small, explicit SQL; no ORM."""
from __future__ import annotations

import datetime as dt
from contextlib import contextmanager
from importlib import resources
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from floodwatch.config import settings


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, row_factory=dict_row, autocommit=False) as conn:
        yield conn


def init_schema() -> None:
    sql = resources.files("floodwatch.db").joinpath("schema.sql").read_text()
    with connect() as c:
        c.execute(sql)
        c.commit()


def upsert_station(c: psycopg.Connection, s: dict[str, Any]) -> None:
    prev = c.execute("SELECT bank_msl, ground_msl, lat, lon FROM station WHERE code=%s", (s["code"],)).fetchone()
    c.execute(
        """INSERT INTO station (code, hii_id, name_th, name_en, lat, lon, bank_msl, ground_msl, critical_msl,
                                agency, province, amphoe, river, basin, in_focus, updated_at)
           VALUES (%(code)s, %(hii_id)s, %(name_th)s, %(name_en)s, %(lat)s, %(lon)s, %(bank_msl)s, %(ground_msl)s,
                   %(critical_msl)s, %(agency)s, %(province)s, %(amphoe)s, %(river)s, %(basin)s, %(in_focus)s, now())
           ON CONFLICT (code) DO UPDATE SET
             hii_id=COALESCE(EXCLUDED.hii_id, station.hii_id), name_th=COALESCE(EXCLUDED.name_th, station.name_th),
             name_en=COALESCE(EXCLUDED.name_en, station.name_en), lat=COALESCE(EXCLUDED.lat, station.lat),
             lon=COALESCE(EXCLUDED.lon, station.lon), bank_msl=COALESCE(EXCLUDED.bank_msl, station.bank_msl),
             ground_msl=COALESCE(EXCLUDED.ground_msl, station.ground_msl),
             critical_msl=COALESCE(EXCLUDED.critical_msl, station.critical_msl),
             agency=COALESCE(EXCLUDED.agency, station.agency), province=COALESCE(EXCLUDED.province, station.province),
             amphoe=COALESCE(EXCLUDED.amphoe, station.amphoe), river=COALESCE(EXCLUDED.river, station.river),
             basin=COALESCE(EXCLUDED.basin, station.basin), in_focus=station.in_focus OR EXCLUDED.in_focus,
             updated_at=now()""",
        s,
    )
    changed = prev is None or any(
        s.get(k) is not None and prev[k] != s.get(k) for k in ("bank_msl", "ground_msl", "lat", "lon"))
    if changed:
        c.execute(
            """INSERT INTO station_version (code, bank_msl, ground_msl, lat, lon, source)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (s["code"], s.get("bank_msl"), s.get("ground_msl"), s.get("lat"), s.get("lon"), s.get("meta_source", "hii")),
        )


def insert_observations(c: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    with c.cursor() as cur:
        cur.executemany(
            """INSERT INTO observation (code, obs_time, level_msl, discharge, situation_level, source, quality_flag, raw_ref)
               VALUES (%(code)s, %(obs_time)s, %(level_msl)s, %(discharge)s, %(situation_level)s, %(source)s,
                       %(quality_flag)s, %(raw_ref)s)
               ON CONFLICT (code, obs_time) DO UPDATE SET
                 discharge=COALESCE(observation.discharge, EXCLUDED.discharge),
                 situation_level=COALESCE(observation.situation_level, EXCLUDED.situation_level)""",
            rows,
        )
    return len(rows)


def record_health(source: str, ok: bool, error: str | None = None, data_time: dt.datetime | None = None) -> None:
    with connect() as c:
        if ok:
            c.execute(
                """INSERT INTO source_health (source, last_success, consecutive_failures, last_data_time)
                   VALUES (%s, now(), 0, %s)
                   ON CONFLICT (source) DO UPDATE SET last_success=now(), consecutive_failures=0,
                     last_data_time=COALESCE(EXCLUDED.last_data_time, source_health.last_data_time)""",
                (source, data_time),
            )
        else:
            c.execute(
                """INSERT INTO source_health (source, last_error, last_error_msg, consecutive_failures)
                   VALUES (%s, now(), %s, 1)
                   ON CONFLICT (source) DO UPDATE SET last_error=now(), last_error_msg=EXCLUDED.last_error_msg,
                     consecutive_failures=source_health.consecutive_failures+1""",
                (source, (error or "")[:500]),
            )
        c.commit()


def save_forecast(code: str, issue_time: dt.datetime, version: str, payload: dict[str, Any]) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO forecast_run (code, issue_time, version, payload) VALUES (%s,%s,%s,%s)
               ON CONFLICT (code, issue_time) DO UPDATE SET payload=EXCLUDED.payload, version=EXCLUDED.version""",
            (code, issue_time, version, Jsonb(payload)),
        )
        c.commit()
