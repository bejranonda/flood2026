#!/usr/bin/env python3
"""Re-run the evidence behind research/VALIDATION_2026-09-26.md.

Usage:  python3 research/validation/validate_research_claims.py

Needs Python 3.11+ and numpy. It makes a few polite GET requests with an honest
User-Agent and prints the results. Nothing is saved to disk. Results depend on
where you run it: several Thai government hosts block non-Thai or datacenter IPs.
Always record the host's country along with the results.
"""
from __future__ import annotations

import datetime as dt
import json
import urllib.error
import urllib.request

import numpy as np

UA = "BKK-FloodWatch-research/0.1 (+https://flood.bejranonda.com)"
TIMEOUT_S = 40

# (label, url, verdict expected at the time of the 2026-09-26 run)
ENDPOINTS = [
    ("HII waterlevel_load (careful survey)", "https://api-v3.thaiwater.net/api/v1/thaiwater30/public/waterlevel_load", "200 JSON"),
    ("HII chart XHR getGraphFirst/BKK008", "https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/BKK008", "200 JSON"),
    ("HII /v1/telemetry/station/river (Gemini draft)", "https://api-v3.thaiwater.net/v1/telemetry/station/river", "404"),
    ("api2.thaiwater.net (API_noKey-1)", "https://api2.thaiwater.net/v1/analyst/water/telemetry", "DNS fail"),
    ("open.traffy.in.th (Gemini draft)", "https://open.traffy.in.th/api/v1/tickets?type=flooding", "DNS fail"),
    ("Traffy public API (found in validation)", "https://publicapi.traffy.in.th/share/teamchadchart/search?limit=1", "201 JSON"),
    ("Open-Meteo forecast", "https://api.open-meteo.com/v1/forecast?latitude=13.7563&longitude=100.5018&hourly=precipitation", "200"),
    ("Open-Meteo ensemble", "https://ensemble-api.open-meteo.com/v1/ensemble?latitude=13.75&longitude=100.5&hourly=precipitation&models=ecmwf_ifs025", "200"),
    ("Open-Meteo flood (GloFAS)", "https://flood-api.open-meteo.com/v1/flood?latitude=14.12&longitude=100.50&daily=river_discharge", "200"),
    ("Open-Meteo elevation", "https://api.open-meteo.com/v1/elevation?latitude=13.7392,13.6780&longitude=100.4984,100.6080", "200 [4.0, 7.0]"),
    ("Navy tide PDF 2026", "https://hydro.navy.mi.th/download/Water_lever69/LLW/TT2026.pdf", "404 / bot wall"),
    ("BMA DDS portal", "https://dds.bangkok.go.th/", "reset (non-TH host)"),
    ("BMA weather/water", "http://weather.bangkok.go.th/water/CanalList.aspx", "reset (non-TH host)"),
    ("RID flood portal", "https://water.rid.go.th/flood/", "200"),
    ("GISTDA API gateway", "https://api-gateway.gistda.or.th/v2", "200 (portal)"),
    ("Copernicus GFM API", "https://api.gfm.eodc.eu/v2/", "200 (swagger)"),
    ("TMD API portal", "https://data.tmd.go.th/api/index1.php", "200 (portal)"),
]


def get(url: str) -> tuple[str, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return str(resp.status), resp.read()
    except urllib.error.HTTPError as e:
        return str(e.code), b""
    except Exception as e:  # DNS failure, connection reset, timeout
        return type(e).__name__ + ": " + str(e)[:60], b""


def probe_endpoints() -> None:
    print("## Endpoint probes")
    for label, url, expected in ENDPOINTS:
        status, body = get(url)
        print(f"- {label}: got {status} ({len(body)} B); expected {expected}")


def fetch_series(code: str) -> tuple[np.ndarray, np.ndarray]:
    """HII chart API rows: [epoch_ms_utc, level_msl, bank, ground, level_str]."""
    status, body = get(f"https://tiwrm.hii.or.th/thaiwater_l5/public/getGraphFirst/{code}")
    if status != "200":
        raise RuntimeError(f"{code}: HTTP {status}")
    rows = json.loads(body)
    t = np.array([r[0] for r in rows], float) / 1000.0
    h = np.array([np.nan if r[1] is None else float(r[1]) for r in rows])
    bad = np.isnan(h) | (h > 50) | (h < -10)  # HII uses 999999 as a missing/error sentinel
    print(f"{code}: {len(h)} rows, {int(bad.sum())} sentinel/invalid, bank={rows[-1][2]} m MSL")
    return t[~bad], h[~bad]


def tidal_signal(t: np.ndarray, h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Hourly series minus a 25 h running mean (crude tidal filter), skipping gaps > 1.5 h."""
    th = (t - t[0]) / 3600.0
    grid = np.arange(np.ceil(th[0]), th[-1], 1.0)
    hg = np.interp(grid, th, h)
    near = np.array([np.min(np.abs(th - g)) for g in grid]) <= 1.5
    w = 25
    res = hg - np.convolve(hg, np.ones(w) / w, mode="same")
    keep = near.copy()
    keep[:w] = keep[-w:] = False
    return t[0] + grid[keep] * 3600.0, res[keep]


def draft_tide(tsec: np.ndarray, cons: list[tuple[float, float, float]], sign: int) -> np.ndarray:
    """The drafts' formula: hours since 2026-01-01Z, cos(speed*t -/+ phase), no V0+u, no nodal f."""
    hours = (tsec - dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp()) / 3600.0
    return sum(a * np.cos(np.radians(s * hours + sign * p)) for s, a, p in cons)


def check_tide(code: str = "CPY015") -> None:
    print(f"\n## Tide constants vs observed tidal signal at {code}")
    t, h = fetch_series(code)
    ts, y = tidal_signal(t, h)
    g = (ts - ts[0]) / 3600.0
    speeds = {"M2": 28.9841042, "S2": 30.0, "K1": 15.0410686, "O1": 13.9430356}
    cols = [np.ones_like(g)]
    for s in speeds.values():
        cols += [np.cos(np.radians(s * g)), np.sin(np.radians(s * g))]
    x = np.array(cols).T
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    fit = x @ coef
    amps = {k: float(np.hypot(coef[1 + 2 * i], coef[2 + 2 * i])) for i, k in enumerate(speeds)}
    form = (amps["K1"] + amps["O1"]) / (amps["M2"] + amps["S2"])
    print("fitted amplitudes (m):", {k: round(v, 2) for k, v in amps.items()}, f"form factor F={form:.2f}")
    draft_a = [(28.9841042, 0.62, 125.4), (30.0, 0.28, 172.1), (15.0410686, 0.44, 210.8), (13.9430356, 0.35, 185.3)]
    draft_b = [(28.9841042, 0.85, 45.0), (30.0, 0.32, 112.0), (15.0410686, 0.58, 210.0), (13.9430356, 0.42, 185.0)]
    for name, pred in [
        ("draft A (docs JS / API_noKey-1)", draft_tide(ts, draft_a, -1)),
        ("draft B (engine constants)", draft_tide(ts, draft_b, +1)),
        ("own 4-constituent fit (in-sample)", fit),
    ]:
        corr = np.corrcoef(pred, y)[0, 1]
        rmse = float(np.sqrt(np.mean((pred - y) ** 2)))
        print(f"- {name}: corr {corr:+.2f}, RMSE {rmse:.2f} m")


if __name__ == "__main__":
    print("Run at", dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"))
    probe_endpoints()
    check_tide()
