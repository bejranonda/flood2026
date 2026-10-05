"""Q55 (D-097): the Flood Hub archive is backfilled once (a year of daily forecasts per point; the API serves it and it
equals what we stored live, 320/320 — research/2026-10-04_floodhub_input.log)."""
import contextlib
import datetime as dt

from floodwatch import collectors


def test_backfill_asks_for_a_year_per_point_in_small_chunks_and_stores_the_steps(monkeypatch):
    calls, stored = [], []
    payload = {"forecasts": {"g1": {"forecasts": [{"issuedTime": "2025-10-05T14:00:00Z", "forecastRanges": [
        {"forecastStartTime": "2025-10-05T00:00:00Z", "forecastEndTime": "2025-10-06T00:00:00Z", "value": 12.5}]}]}}}

    def fake(method, path, body=None, params=None):
        calls.append(dict(params or []) if params else {}); calls[-1]["_ids"] = [v for k, v in (params or []) if k == "gaugeIds"]
        return payload

    class Cur:
        def executemany(self, sql, rows):
            stored.extend(rows)

    class Conn:
        def cursor(self):
            return contextlib.nullcontext(Cur())
        def execute(self, sql, *a):
            class R:
                def fetchall(self_inner):
                    return [{"gauge_id": f"g{i}"} for i in range(1, 8)]
            return R()
        def commit(self):
            pass

    monkeypatch.setattr(collectors, "_gfh", fake)
    monkeypatch.setattr(collectors.db, "connect", contextlib.contextmanager(lambda: (yield Conn())))
    import types
    monkeypatch.setattr(collectors, "settings", types.SimpleNamespace(google_flood_api_key="k"))
    n = collectors.google_floodhub_backfill(days=366)
    since = dt.datetime.fromisoformat(calls[0]["issuedTimeStart"].replace("Z", "+00:00"))
    assert 365 <= (dt.datetime.now(dt.timezone.utc) - since).days <= 366
    assert all(len(c["_ids"]) <= 5 for c in calls) and sum(len(c["_ids"]) for c in calls) == 7
    assert n == len(stored) and stored[0]["value"] == 12.5
