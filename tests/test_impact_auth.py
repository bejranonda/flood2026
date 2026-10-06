"""/impact access (owner 2026-10-05: "One shared password in the app"; D-099): constant-time password check, a signed
HttpOnly session cookie bound to the password, and a limit on failed tries."""
import json
import types

import pytest
from fastapi import HTTPException

from floodwatch import api, impact_auth

SECRET, PW = "s" * 64, "correct horse"


def test_a_session_token_is_valid_until_it_expires_and_only_for_this_password():
    tok = impact_auth.make_token(SECRET, PW, exp=1000)
    assert impact_auth.check_token(tok, SECRET, PW, now=999)
    assert not impact_auth.check_token(tok, SECRET, PW, now=1001)            # expired
    assert not impact_auth.check_token(tok, SECRET, "new password", now=10)  # a new password logs everyone out
    assert not impact_auth.check_token(tok.replace("1000", "9999"), SECRET, PW, now=10)  # tampered expiry
    assert not impact_auth.check_token("garbage", SECRET, PW, now=10) and not impact_auth.check_token(None, SECRET, PW, now=10)


def test_failed_logins_are_limited_per_client():
    lim = impact_auth.LoginLimiter(max_failures=5, window_s=900)
    for _ in range(5):
        assert lim.allowed("c1", now=100)
        lim.fail("c1", now=100)
    assert not lim.allowed("c1", now=200) and lim.allowed("c2", now=200)
    assert lim.allowed("c1", now=100 + 901)  # the window passed


def test_password_check_is_exact():
    assert impact_auth.password_ok("pass-long", "pass-long") and not impact_auth.password_ok("pass", "pass-long")
    assert not impact_auth.password_ok("", "") and not impact_auth.password_ok("x", "")  # not set up: nobody gets in


class Req:
    def __init__(self, cookie=None):
        self.cookies = {"fw_impact": cookie} if cookie else {}
        self.headers = {"cf-connecting-ip": "203.0.113.9"}
        self.client = types.SimpleNamespace(host="127.0.0.1")


def test_endpoints_need_the_session_and_say_when_not_set_up(monkeypatch):
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    monkeypatch.setattr(api, "_impact_state", lambda: {"case": "kaeng-krachan", "points": [], "dam": {}, "validation": {}})
    with pytest.raises(HTTPException) as e:
        api.impact_board(Req())
    assert e.value.status_code == 401
    bad = api.impact_login(api.ImpactLogin(password="wrong"), Req())
    assert bad.status_code == 401
    ok = api.impact_login(api.ImpactLogin(password=PW), Req())
    cookie = ok.headers["set-cookie"]
    assert ok.status_code == 200 and "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie.replace("Strict", "strict")
    token = cookie.split("fw_impact=")[1].split(";")[0]
    assert json.loads(api.impact_board(Req(token)).body)["case"] == "kaeng-krachan"
    monkeypatch.setattr(api, "_impact_conf", lambda: ("", SECRET))
    with pytest.raises(HTTPException) as e:
        api.impact_board(Req(token))
    assert e.value.status_code == 503


def test_the_whatif_is_refused_until_the_replay_passes_and_templates_need_the_session(monkeypatch):
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    state = {"case": "kaeng-krachan", "dam": {"released_mcm": 10.8}, "diversion_default": 63.0, "points": [],
             "validation": {"whatif_ready": False}}
    monkeypatch.setattr(api, "_impact_state", lambda: state)
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    with pytest.raises(HTTPException) as e:
        api.impact_whatif(Req(tok), release_mcm=20.0, diversion_cms=None)
    assert e.value.status_code == 409  # not credible yet: the board explains why
    state["validation"]["whatif_ready"] = True
    assert json.loads(api.impact_whatif(Req(tok), release_mcm=20.0, diversion_cms=None).body)["release_mcm"] == 20.0
    csv = api.impact_template(Req(tok), "diversion_dam")
    assert csv.status_code == 200 and "datetime_ict" in csv.body.decode() and "gate_opening_m" in csv.body.decode()
    with pytest.raises(HTTPException):
        api.impact_template(Req(), "diversion_dam")
    with pytest.raises(HTTPException):
        api.impact_template(Req(tok), "../etc/passwd")


class PageReq:
    headers = {"host": "flood.autobahn.bot"}


def test_impact_mode_is_the_main_app_with_one_more_tab_and_the_public_page_is_unchanged():
    # owner 2026-10-05: "In impact page we need similar map and functions to main page but add the risk and impacts as
    # additional tab" → chose "Main app + ผลกระทบ tab" (D-100)
    page, home = api.impact_page(PageReq()), api.index(PageReq())
    html, pub = page.body.decode(), home.body.decode()
    assert 'data-tab="impact"' in html and 'id="view-impact"' in html and "/static/impact.js" in html
    assert "/static/app.js" in html and "leaflet" in html and 'data-tab="watch"' in html  # the whole main app
    assert 'name="robots" content="noindex' in html and 'data-mode="impact"' in html
    assert 'data-tab="impact"' not in pub and "/static/impact.js" not in pub and "impact.css" not in pub
    assert "noindex" in page.headers.get("x-robots-tag", "") and page.headers.get("x-frame-options") == "DENY"
    csp = page.headers.get("content-security-policy", "")
    script = csp.split("script-src")[1].split(";")[0]
    assert "'self'" in script and "https://unpkg.com" in script and "unsafe-inline" not in script  # no inline script
    assert "frame-ancestors 'none'" in csp and "connect-src 'self'" in csp
    import types as _t
    robots = api.robots(_t.SimpleNamespace(headers={"host": "flood.autobahn.bot"}, url=_t.SimpleNamespace(hostname="flood.autobahn.bot"))).body.decode()
    assert "Disallow: /impact" in robots and "Disallow: /api/impact" in robots


def test_the_main_app_lets_one_more_tab_plug_in_without_changing_its_own_tabs():
    from pathlib import Path
    web = Path(api.__file__).resolve().parents[3] / "web"
    app, js = (web / "app.js").read_text(), (web / "impact.js").read_text()
    assert "window.FW_TABS" in app and 'new CustomEvent("fw:map"' in app  # the two hooks, nothing else
    assert "FW_TABS" in js and "fw:map" in js
    assert not (web / "impact.html").exists()  # the standalone shell is gone: one app, two modes
    assert "style=" not in js and "const agency = (a) => esc(" in js  # outside strings escaped; styles by class
    # the scenarios (D-101) reuse the app's own ✨ card and bottom sheet, so engineers meet the patterns residents know
    assert 'id="imp-sc"' in js and "bindAskUrl(sec," in js and "askHTML()" in js and 'getElementById("sheet")' in js
    assert "ยังไม่ผ่านการทดสอบ" in js and "chartSvg(" in js and "imp-custom" in js
    # v0.30 (owner: "just click and see … not read so long"): the app's grammar — chips, one ★ card, one-line rows, a river
    # strip whose nodes open the station's own sheet, ⓘ toasts (.conf-badge) and one ℹ️ collapsible for the rest
    assert 'class="chips imp-chips-num"' in js and "imp-hero" in js and "imp-row" in js and "imp-strip" in js
    assert "showDetail(b.dataset.code)" in js and 'class="conf-badge' in js and '<details class="imp-info">' in js
    assert "whatifHtml" not in js  # the disabled what-if card is gone (the custom plan does the same)
    # v0.31 (owner: "too much info each card"): the dams list is the station list — group headers with ⓘ, two-line rows
    # with one badge, the forecast in the app's words ("อีก N ชม." → "อีก 7 วัน"), row and ◆ open the same sheet
    assert "wgrp-h" in js and '<li class="item s-' in js and 'class="badge b-' in js and "อีก 7 วัน" in js
    assert "openDamSheet(i, false)" in js and "bindPopup" not in js
    assert "Math.round(p7)" in js  # the arrow follows the two percentages on the row, never "↗ 94 %" beside "94 %"
    # E-7D-DOWN: plans name the downstream model they used; a tested one shows its error, not "untested"
    assert "cmp.downstream" in js and "🟠 ท้ายน้ำ ±" in js and "st.river7" in js
    assert "ใช้ในแบบจำลองน้ำไหลเข้า" in js  # D-104: the plan's inflow can run on the tested rain model; the page says so
    # owner 2026-10-06: a plan's day on the map — the river by its nearest gauge, said to be no flood area (D-019)
    assert "st.river_reaches" in js and "colorReaches(" in js and "ไม่ใช่พื้นที่น้ำท่วม" in js and "data-day" in js
    assert "drawOnwr(" in js and "ที่มา: สทนช." in js and "ไม่ใช่ผลของแผนระบาย" in js  # ONWR's layers: dated, credited, not ours


def test_the_real_settings_reach_the_impact_endpoints():
    # the other tests stub _impact_conf; this one runs it (a missing import gave 500s on every endpoint)
    pw, secret = api._impact_conf()
    assert isinstance(pw, str) and isinstance(secret, str)


def test_the_replay_table_follows_the_river_and_reported_percent_is_shown_as_reported():
    from pathlib import Path
    js = (Path(api.__file__).resolve().parents[3] / "web" / "impact.js").read_text()
    assert "st.points.map((p) => p.code).filter((c) => P[c])" in js  # B.10, B.16, B.15, PCH001 — not alphabetical
    assert "ของความจุ" not in js  # the agencies' percentages are not defined the same way (RID 102 % vs EGAT 59 %)


def test_cases_dams_and_one_case_need_the_session_and_answer_from_the_hourly_state(monkeypatch):
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    states = {"impact_kaeng_krachan": {"case": "kaeng-krachan", "title": "เขื่อนแก่งกระจาน → แม่น้ำเพชรบุรี", "points": [],
                                       "built_at": "2026-10-05T12:00:00+00:00", "validation": {"whatif_ready": False}},
              "impact_dams": {"built_at": "2026-10-05T12:00:00+00:00", "dams": [{"name_th": "แก่งกระจาน", "position": "above"}]}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": states.get(key) or {})
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    for call in (lambda r: api.impact_cases(r), lambda r: api.impact_dams(r), lambda r: api.impact_case(r, "kaeng-krachan")):
        with pytest.raises(HTTPException) as e:
            call(Req())
        assert e.value.status_code == 401
    cases = json.loads(api.impact_cases(Req(tok)).body)["cases"]
    assert cases[0]["id"] == "kaeng-krachan" and cases[0]["ready"] is True and cases[0]["dam_name"] == "แก่งกระจาน"
    assert json.loads(api.impact_dams(Req(tok)).body)["dams"][0]["position"] == "above"
    assert json.loads(api.impact_case(Req(tok), "kaeng-krachan").body)["case"] == "kaeng-krachan"
    with pytest.raises(HTTPException) as e:
        api.impact_case(Req(tok), "no-such-case")
    assert e.value.status_code == 404


def test_the_tab_assets_carry_a_content_hash_so_every_change_reaches_browsers_past_the_cdn():
    import hashlib
    from pathlib import Path
    web = Path(api.__file__).resolve().parents[3] / "web"
    html = api.impact_page(PageReq()).body.decode()
    for name in ("impact.js", "impact.css"):
        h = hashlib.sha256((web / name).read_bytes()).hexdigest()[:10]
        assert f"/static/{name}?v={h}" in html, name


def test_impact_mode_sends_the_origin_as_referer_so_osm_tiles_are_not_blocked():
    # KI-300: Referrer-Policy same-origin stripped the Referer from tile requests; OSM's Thai edge answers 403 "Access
    # blocked" to referer-less browsers (osm.wiki/Blocked). The origin alone is sent: the /impact path never leaves the site.
    assert api.impact_page(PageReq()).headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_scenarios_endpoint_needs_ready_inputs_and_validates_a_custom_plan(monkeypatch):
    from test_impact import STATE
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    st = {**STATE, "case": "kaeng-krachan", "built_at": "2026-10-05T12:00:00+00:00", "validation": {"whatif_ready": False},
          "dam": {**STATE["dam"], "storage_mcm": 725.85, "inflow_mcm": 10.33},
          "scenario_inputs": {"curves7": {"upper": [593.0] * 7, "lower": [204.0] * 7, "dates": [f"2026-10-0{d}" for d in range(6, 10)] + ["2026-10-10", "2026-10-11", "2026-10-12"]},
                              "normal_mcm": 710.0, "max_mcm": 900.0, "release_cap": 25.0, "release_max_seen": 24.36}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st)
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    out = json.loads(api.impact_scenarios(Req(tok), "kaeng-krachan", release="10.8,10.8,10.8,10.8,10.8,10.8,10.8", diversion_cms=None).body)
    assert out["downstream_validated"] is False and out["candidates"] > 100 and out["plans"]
    assert any(p["kind"] == "custom" for p in out["plans"]) and any(p["kind"] == "hold" for p in out["plans"])
    assert set(out["best_for"]) == set(api.scenarios.EFFECT_KEYS) if hasattr(api, "scenarios") else True
    assert out["optimal"]["reason"]
    with pytest.raises(HTTPException) as e:
        api.impact_scenarios(Req(tok), "kaeng-krachan", release="1,2,3", diversion_cms=None)
    assert e.value.status_code == 422
    st["scenario_inputs"]["curves7"]["upper"][3] = None
    with pytest.raises(HTTPException) as e:
        api.impact_scenarios(Req(tok), "kaeng-krachan", release=None, diversion_cms=None)
    assert e.value.status_code == 503


def test_scenarios_use_the_dams_tested_7_day_inflow_and_name_the_downstream_model(monkeypatch):
    from test_impact import STATE
    from test_scenarios import _r7_state
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    st = {**_r7_state(), "case": "kaeng-krachan", "built_at": "2026-10-05T12:00:00+00:00", "validation": {"whatif_ready": False},
          "dam": {**STATE["dam"], "dam_date": "2026-10-05", "storage_mcm": 725.85, "inflow_mcm": 10.33},
          "scenario_inputs": {"curves7": {"upper": [593.0] * 7, "lower": [204.0] * 7, "dates": [f"2026-10-{d:02d}" for d in range(6, 13)]},
                              "normal_mcm": 710.0, "max_mcm": 900.0, "release_cap": 25.0, "release_max_seen": 24.36}}
    days = [{"inflow": 12.0, "inflow_lo": 11.0, "inflow_hi": 14.0, "method": "model"}] * 7
    outlook = {"dams": {"13": {"dam_date": "2026-10-05", "test": {"model": True}, "days": days}}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": outlook if key == "reservoir_outlook" else st)
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    out = json.loads(api.impact_scenarios(Req(tok), "kaeng-krachan", release=None, diversion_cms=None).body)
    assert out["inflow"]["method"] == "model" and out["inflow"]["mid"] == [12.0] * 7
    assert out["downstream"]["method"] == "hybrid" and "ทดสอบย้อนหลัง" in out["downstream_note"]
    outlook["dams"]["13"]["dam_date"] = "2026-10-04"  # yesterday's outlook for today's record: not used
    out = json.loads(api.impact_scenarios(Req(tok), "kaeng-krachan", release="10,10,10,10,10,10,10", diversion_cms=None).body)
    assert out["inflow"]["method"] == "hold"


def test_scenario_explain_needs_login_and_returns_the_story_and_lines(monkeypatch):
    from test_impact import STATE
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    st = {**STATE, "case": "kaeng-krachan", "built_at": "2026-10-05T12:00:00+00:00", "validation": {"whatif_ready": False},
          "dam": {**STATE["dam"], "name_th": "แก่งกระจาน", "dam_date": "2026-10-05", "storage_mcm": 725.85, "storage_pct": 102.2, "inflow_mcm": 10.33},
          "scenario_inputs": {"curves7": {"upper": [593.0] * 7, "lower": [204.0] * 7, "dates": ["2026-10-%02d" % d for d in range(6, 13)]},
                              "normal_mcm": 710.0, "max_mcm": 900.0, "release_cap": 25.0, "release_max_seen": 24.36}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st)
    with pytest.raises(HTTPException) as e:
        api.impact_explain(Req(), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="simple")
    assert e.value.status_code == 401
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    out = json.loads(api.impact_explain(Req(tok), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="simple").body)
    assert "แก่งกระจาน" in out["story"] and len(out["lines"]) >= 5 and "ai" in out


def test_the_case_endpoint_serves_onwr_cells_inside_the_case_box_only(monkeypatch):
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    far = {"cls": 2, "rings": [[[13.51, 99.80], [13.52, 99.81], [13.51, 99.82]]]}
    near = {"cls": 2, "rings": [[[13.07, 99.94], [13.08, 99.95], [13.07, 99.96]]]}
    st = {"case": "kaeng-krachan", "points": [], "onwr": {"bbox": [12.618, 99.237, 13.274, 100.043],
                                                          "layers": {"flood-warn": {"updated": None, "features": [near, far]}}}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st)
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    out = json.loads(api.impact_case(Req(tok), "kaeng-krachan").body)
    assert out["onwr"]["layers"]["flood-warn"]["features"] == [near]
