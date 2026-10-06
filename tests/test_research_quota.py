"""Research calls to Open-Meteo are counted and paced by one shared ledger (owner 2026-10-06, D-108): 3,000 weighted
calls a day, at most 1,000 an hour, at least 10 s apart — the free tier is shared with the live site's rain (KI-264)."""
import json
from pathlib import Path

import pytest

from floodwatch import research_quota as Q

U = "https://previous-runs-api.open-meteo.com/v1/forecast"


def test_weight_follows_open_meteos_pricing_page():
    # "2 weeks of data with 15 weather variables will be calculated as 1.5 API calls"
    v15 = ",".join(f"v{i}" for i in range(15))
    assert Q.weight(f"{U}?latitude=13&longitude=99&hourly={v15}&start_date=2025-05-01&end_date=2025-05-14") == 1.5
    # a 214-day request with 8 variables (E-7D-IN-LONG, 2026-10-06): fewer than 10 variables still count as one
    v8 = ",".join(f"v{i}" for i in range(8))
    assert abs(Q.weight(f"{U}?latitude=13&longitude=99&hourly={v8}&start_date=2025-05-01&end_date=2025-11-30") - 214 / 14) < 1e-9
    # each location counts on its own; several models count as more variables (cautious)
    assert Q.weight(f"{U}?latitude=13,14&longitude=99,100&hourly=precipitation&forecast_days=7") == 2.0
    assert Q.weight(f"{U}?latitude=13&longitude=99&hourly={v8}&models=a,b&forecast_days=14") == 1.6


def test_weight_refuses_an_api_whose_counting_is_not_documented():
    with pytest.raises(ValueError):
        Q.weight("https://ensemble-api.open-meteo.com/v1/ensemble?latitude=13&longitude=99&hourly=precipitation")
    with pytest.raises(ValueError):
        Q.weight("https://example.org/v1/forecast?latitude=13")


class Clock:
    def __init__(self, t=1_000_000.0):
        self.t, self.slept = t, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


def test_requests_wait_ten_seconds_apart_across_runs(tmp_path):
    c = Clock()
    Q.take(1.0, path=tmp_path, now=c.now, sleep=c.sleep)
    c.t += 3
    Q.take(1.0, path=tmp_path, now=c.now, sleep=c.sleep)  # a second run reads the same ledger
    assert c.slept == [7.0]
    rows = [json.loads(x) for x in (tmp_path / Q.LEDGER).read_text().splitlines()]
    assert [r["w"] for r in rows] == [1.0, 1.0]


def test_the_hourly_budget_waits_and_the_daily_budget_stops(tmp_path):
    c = Clock()
    for _ in range(3):
        Q.take(300.0, path=tmp_path, now=c.now, sleep=c.sleep)
        c.t += 60
    t_first = c.t - 180
    Q.take(300.0, path=tmp_path, now=c.now, sleep=c.sleep)  # 1,200 > 1,000 in the hour: waits until the first leaves
    assert abs(c.t - (t_first + 3600)) < 1e-6
    for _ in range(6):  # 10 × 300 = 3,000 in the day
        c.t += 3600
        Q.take(300.0, path=tmp_path, now=c.now, sleep=c.sleep)
    with pytest.raises(Q.QuotaError, match="24 h"):
        Q.take(1.0, path=tmp_path, now=c.now, sleep=c.sleep)


def test_one_request_heavier_than_the_hourly_budget_must_be_split(tmp_path):
    with pytest.raises(Q.QuotaError, match="split"):
        Q.take(Q.HOUR_LIMIT + 1, path=tmp_path)


def test_a_run_that_cannot_see_the_shared_ledger_stops(monkeypatch, tmp_path):
    monkeypatch.delenv("FLOODWATCH_RESEARCH_DIR", raising=False)
    monkeypatch.setattr(Q, "MOUNT", tmp_path / "not-mounted")
    monkeypatch.setattr(Q, "CHECKOUT", tmp_path / "no-checkout")
    with pytest.raises(Q.QuotaError, match="mount"):
        Q.ledger_dir()
    monkeypatch.setenv("FLOODWATCH_RESEARCH_DIR", str(tmp_path / "ledger"))
    assert Q.ledger_dir() == tmp_path / "ledger"


# research scripts that fetched Open-Meteo directly before the counter existed (kept as the record of their runs)
BEFORE_THE_COUNTER = frozenset({
    "2026-10-02_glofas_outlook.py", "2026-10-05_dam_inflow_nationwide.py", "2026-10-05_e7d_down.py",
    "2026-10-05_e7d_inflow.py", "2026-10-05_kk_inflow_model.py", "2026-10-05_q58_operational.py",
    "2026-10-05_two_years_history.py", "2026-10-06_e7d_down_3y.py", "2026-10-06_e7d_down_3y_fc.py",
    "2026-10-06_e7d_inflow_long.py", "2026-10-06_e7d_long_fetch.py"})


def bypasses(paths) -> list[str]:
    """Research scripts that name Open-Meteo without going through the counter."""
    out = []
    for p in paths:
        s = p.read_text(encoding="utf-8", errors="replace")
        if "open-meteo.com" in s and "research_quota" not in s and p.name not in BEFORE_THE_COUNTER:
            out.append(p.name)
    return out


def test_the_guard_finds_a_script_that_bypasses_the_counter(tmp_path):
    (tmp_path / "2026-10-08_direct.py").write_text('URL = "https://api.open-meteo.com/v1/forecast"\n')
    (tmp_path / "2026-10-08_counted.py").write_text(
        'from floodwatch import research_quota\nURL = "https://api.open-meteo.com/v1/forecast"\n')
    assert bypasses(sorted(tmp_path.glob("*.py"))) == ["2026-10-08_direct.py"]


RESEARCH = Path(__file__).resolve().parents[1] / "research"


@pytest.mark.skipif(not RESEARCH.is_dir(), reason="research/ is not in the image: mount it (-v \"$PWD/research:/app/research:ro\")")
def test_new_research_scripts_fetch_open_meteo_through_the_counter():
    assert bypasses(sorted(RESEARCH.glob("*.py"))) == []
