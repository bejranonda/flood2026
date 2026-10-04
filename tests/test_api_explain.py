"""The two new ✨ endpoints answer from the same snapshot as the sheet and the tab (owner 2026-10-04)."""
import json

import pytest
from fastapi import HTTPException

from floodwatch import api

body = lambda resp: json.loads(resp.body)


def test_explain_watch_reads_the_tab_snapshot_and_its_filters(monkeypatch):
    data = {"groups": [{"key": "fast_rise", "items": [{"code": "F1", "name_th": "สถานีF1", "province": "พิษณุโลก",
                                                       "region": "up", "freeboard_m": 1.0, "rise_cm": 25}]}], "records": {}}
    monkeypatch.setattr(api, "_risks_data", lambda: data)
    r = body(api.explain_watch(region="up", prov="", q="simple", part="lines"))
    assert "สถานีF1" in r["story"] and "ภาคกลาง" in r["story"] and r["lines"]
    r = body(api.explain_watch(region="south", prov="", q="simple", part="lines"))
    assert "ไม่พบ" in r["lines"][0]
    with pytest.raises(HTTPException):
        api.explain_watch(region="mars", prov="", q="simple", part="lines")


def test_explain_station_reads_the_station_row(monkeypatch):
    row = {"code": "T.13", "name_th": "บ้านบางการ้อง", "river": "แม่น้ำท่าจีน", "province": "สุพรรณบุรี", "status": "normal",
           "freeboard_m": 0.5, "observed24": None, "change24": None, "stale": False, "lat": None, "lon": None}
    monkeypatch.setattr(api, "_station_by_code", lambda code: row if code == "T.13" else None)
    r = body(api.explain_station(code="T.13", q="simple", part="lines"))
    assert r["lines"][0].startswith("📍 สถานีวัดน้ำบ้านบางการ้อง") and "บ้านบางการ้อง" in r["story"]
    with pytest.raises(HTTPException):
        api.explain_station(code="NOPE", q="simple", part="lines")
