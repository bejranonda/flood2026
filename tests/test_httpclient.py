"""A host that refuses connections must cost seconds, not the worker loop (tiwrm.hii.or.th, 2026-09-30 20:32 UTC:
connect timeouts of 120 s x 3 attempts per chart request stalled the collectors)."""
import pytest
import requests

from floodwatch import httpclient


class Down:
    calls = 0

    def request(self, *a, **kw):
        Down.calls += 1
        Down.timeout = kw.get("timeout")
        raise requests.exceptions.ConnectTimeout("connect timed out")


def test_connect_timeout_is_short_and_a_dead_host_fails_fast(monkeypatch):
    monkeypatch.setattr(httpclient, "_session", Down())
    monkeypatch.setattr(httpclient.time, "sleep", lambda s: None)
    httpclient._host_down.clear()
    Down.calls = 0
    with pytest.raises(requests.exceptions.ConnectTimeout):
        httpclient.fetch("https://dead.example/a")
    assert Down.timeout[0] == httpclient.CONNECT_TIMEOUT_S <= 10  # (connect, read)
    first = Down.calls
    with pytest.raises(ConnectionError):
        httpclient.fetch("https://dead.example/b")  # same host within the cooldown: no network call at all
    assert Down.calls == first
    with pytest.raises(requests.exceptions.ConnectTimeout):
        httpclient.fetch("https://alive.example/c")  # other hosts are unaffected
    assert Down.calls > first


def test_fetch_sends_extra_headers_such_as_an_api_key(monkeypatch):
    seen = {}

    class Resp:
        status_code = 200
        headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def iter_content(self, n):
            return [b"{}"]

    class S:
        def request(self, *a, **kw):
            seen.update(kw["headers"])
            return Resp()

    monkeypatch.setattr(httpclient, "_session", S())
    httpclient._host_down.clear()
    httpclient.fetch("https://ok.example/x", headers={"API-Key": "k"})
    assert seen["API-Key"] == "k" and "BKK-FloodWatch" in seen["User-Agent"]
