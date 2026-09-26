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


def _flag_implausible(c: psycopg.Connection, rows: list[dict[str, Any]]) -> None:
    """Apply the > bank + 3 m plausibility rule with the *stored* bank, whatever the source sent (some feeds carry
    no bank for a station, e.g. BKK003 in waterlevel_load). Flag, never delete (KI-211)."""
    from floodwatch.collectors.parsing import MAX_ABOVE_BANK_M
    codes = sorted({r["code"] for r in rows})
    since = min(r["obs_time"] for r in rows)
    c.execute("""UPDATE observation o SET quality_flag='out_of_range' FROM station s
                 WHERE s.code=o.code AND o.code = ANY(%s) AND o.obs_time >= %s AND o.quality_flag='ok'
                   AND s.bank_msl IS NOT NULL AND o.level_msl > s.bank_msl + %s""", (codes, since, MAX_ABOVE_BANK_M))


def insert_observations(c: psycopg.Connection, rows: list[dict[str, Any]]) -> int:
    """Upsert observations. Large batches (backfills: ~50k rows per station-year) go through COPY into a temp
    table, which is orders of magnitude faster than row-by-row inserts. First occurrence of a key wins."""
    if not rows:
        return 0
    cols = ("code", "obs_time", "level_msl", "discharge", "situation_level", "source", "quality_flag", "raw_ref")
    conflict = """ON CONFLICT (code, obs_time) DO UPDATE SET
                 discharge=COALESCE(observation.discharge, EXCLUDED.discharge),
                 situation_level=COALESCE(observation.situation_level, EXCLUDED.situation_level)"""
    if len(rows) < 500:
        with c.cursor() as cur:
            cur.executemany(
                f"""INSERT INTO observation ({", ".join(cols)})
                    VALUES ({", ".join(f"%({k})s" for k in cols)}) {conflict}""", rows)
        _flag_implausible(c, rows)
        return len(rows)
    seen: set = set()
    unique = []
    for r in rows:
        key = (r["code"], r["obs_time"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    with c.cursor() as cur:
        cur.execute("CREATE TEMP TABLE IF NOT EXISTS obs_stage (LIKE observation INCLUDING DEFAULTS) ON COMMIT DELETE ROWS")
        cur.execute("TRUNCATE obs_stage")
        with cur.copy(f"COPY obs_stage ({', '.join(cols)}) FROM STDIN") as cp:
            for r in unique:
                cp.write_row([r.get(k) for k in cols])
        cur.execute(f"INSERT INTO observation ({', '.join(cols)}) SELECT {', '.join(cols)} FROM obs_stage {conflict}")
    _flag_implausible(c, unique)
    return len(unique)


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


def get_state(c: psycopg.Connection, key: str) -> Any:
    row = c.execute("SELECT value FROM collector_state WHERE key=%s", (key,)).fetchone()
    return row["value"] if row else None


def set_state(c: psycopg.Connection, key: str, value: Any) -> None:
    c.execute("""INSERT INTO collector_state (key, value, updated_at) VALUES (%s, %s, now())
                 ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""", (key, Jsonb(value)))
