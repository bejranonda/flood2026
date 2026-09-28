"""bma_history must never block the worker loop (KI-239): no HII request when there is nothing to do, the daily
refresh spread over runs, and a gauge that keeps failing set aside instead of heading the queue forever."""
import pytest

from floodwatch import collectors


class _Conn:
    def __init__(self, codes):
        self.codes = codes

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *a, **k):
        codes = self.codes
        return type("R", (), {"fetchall": lambda _s: [{"code": x} for x in codes]})()

    def commit(self):
        pass


@pytest.fixture
def env(monkeypatch):
    codes = [f"WL.T{i:02d}" for i in range(50)]
    st = {"state": None, "calls": [], "fail": set()}
    monkeypatch.setattr(collectors.db, "connect", lambda: _Conn(codes))
    monkeypatch.setattr(collectors.db, "get_state", lambda c, k: st["state"])
    monkeypatch.setattr(collectors.db, "set_state", lambda c, k, v: st.update(state=v))
    monkeypatch.setattr(collectors.db, "insert_observations", lambda c, rows: len(rows))
    monkeypatch.setattr(collectors.parsing, "parse_canal_graph", lambda code, p, sha: [])
    monkeypatch.setattr(collectors.time, "sleep", lambda s: None)

    def get_json(name, url):
        st["calls"].append(name)
        if name == "hii_canal_waterlevel":
            return {"data": [{"station": {"canal_oldcode": x, "id": i}} for i, x in enumerate(codes)]}, "sha"
        if any(f"station_id={i}&" in url for i, x in enumerate(codes) if x in st["fail"]):
            raise RuntimeError("HTTP 500")
        return {"data": {}}, "sha"

    monkeypatch.setattr(collectors, "_get_json", get_json)
    return codes, st


def test_a_failing_gauge_is_set_aside_after_three_runs(env):
    codes, st = env
    st["fail"] = {codes[0]}
    for _ in range(collectors.BMA_MAX_FAILURES):
        collectors.bma_history(max_stations=5, pause_s=0)
    assert codes[0] in st["state"]["failed"] and codes[0] not in st["state"]["done"]
    collectors.bma_history(max_stations=5, pause_s=0)  # the queue moves on past it
    assert set(codes[1:5]) <= set(st["state"]["done"])


def test_daily_refresh_is_spread_over_runs_and_idle_runs_ask_nothing(env):
    codes, st = env
    st["state"] = {"done": list(codes), "missing": [], "refreshed": None}
    runs = 0
    while st["state"].get("refreshed") is None:
        st["calls"].clear()
        collectors.bma_history(pause_s=0)
        assert st["calls"].count("hii_canal_graph") <= collectors.BMA_REFRESH_PER_RUN
        runs += 1
        assert runs < 10
    assert runs == -(-len(codes) // collectors.BMA_REFRESH_PER_RUN)
    st["calls"].clear()
    assert collectors.bma_history(pause_s=0) is None and st["calls"] == []  # done for today: no request at all
