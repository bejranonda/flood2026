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


def test_the_impact_page_is_kept_out_of_search_engines():
    page = api.impact_page()
    assert "noindex" in page.headers.get("x-robots-tag", "") and "<title>" in page.body.decode()
    # a password page must not be framed by another site (clickjacking) and runs only its own script
    assert page.headers.get("x-frame-options") == "DENY"
    csp = page.headers.get("content-security-policy", "")
    assert "frame-ancestors 'none'" in csp and "script-src 'self'" in csp and "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    import types as _t
    robots = api.robots(_t.SimpleNamespace(headers={"host": "flood.autobahn.bot"}, url=_t.SimpleNamespace(hostname="flood.autobahn.bot"))).body.decode()
    assert "Disallow: /impact" in robots and "Disallow: /api/impact" in robots


def test_the_page_runs_no_inline_script_or_style_and_escapes_outside_text():
    from pathlib import Path
    web = Path(api.__file__).resolve().parents[3] / "web"
    html, js = (web / "impact.html").read_text(), (web / "impact.js").read_text()
    assert "<script>" not in html and "style=" not in html and "style=" not in js  # the CSP would block them
    assert "const agency = (a) => esc(" in js and "innerHTML = '<p class=\"card\">' + esc(" in js
