"""Villages and อำเภอ along each gauge's reach of the Phetchaburi River, for the impact tab's plans (owner 2026-10-06: "River
km + places", villages + อำเภอ because OpenStreetMap has no ตำบล boundaries here; D-110). Reads the case state read-only,
samples each reach every ~1 km, asks Nominatim's reverse geocoder (zoom 14, Thai, the project User-Agent, one call per
1.5 s; data © OpenStreetMap contributors, ODbL) and writes src/floodwatch/data/kk_reach_places.json. A reach where fewer
than 80 % of samples name a village keeps its อำเภอ only. Rerun by hand when the river line or the gauges change; nothing
calls Nominatim at request time.
Run: PYTHONPATH=src python3 research/2026-10-06_kk_reach_places.py > research/2026-10-06_kk_reach_places.log"""
import datetime as dt
import json
import time
from pathlib import Path

import requests

from floodwatch import db, impact
from floodwatch.config import settings

STEP_KM = 1.0
URL = "https://nominatim.openstreetmap.org/reverse"
OUT = Path(__file__).resolve().parents[1] / "src" / "floodwatch" / "data" / "kk_reach_places.json"


def samples(line, step_km=STEP_KM):
    """The first vertex, then the next vertex each time step_km of river has been covered."""
    out, acc = [line[0]], 0.0
    for a, b in zip(line, line[1:]):
        acc += impact._km({"lat": a[0], "lon": a[1]}, {"lat": b[0], "lon": b[1]})
        if acc >= step_km:
            out.append(b)
            acc = 0.0
    return out


def strip(name):
    for p in ("อำเภอ", "เขต", "ตำบล", "จังหวัด"):
        if name and name.startswith(p) and len(name) > len(p):
            return name[len(p):].strip()
    return name or None


def main():
    with db.connect_readonly() as c:
        st = db.get_state(c, impact.state_key("kaeng-krachan")) or {}
    reaches = st.get("river_reaches") or []
    if not reaches:
        raise SystemExit("no river_reaches in the case state")
    found, cover = {}, {}
    for r in reaches:
        for lat, lon in samples(r["line"]):
            resp = requests.get(URL, params={"lat": round(lat, 4), "lon": round(lon, 4), "format": "jsonv2", "zoom": 14,
                                             "addressdetails": 1, "accept-language": "th"},
                                headers={"User-Agent": settings.user_agent}, timeout=15)
            time.sleep(1.5)
            a = ((resp.json() or {}).get("address") or {}) if resp.status_code == 200 else {}
            village = a.get("village") or a.get("hamlet") or a.get("municipality")
            amphoe = strip(a.get("county") or a.get("city_district") or a.get("suburb"))
            n = cover.setdefault(r["code"], {"samples": 0, "villages": 0})
            n["samples"] += 1
            n["villages"] += 1 if village else 0
            items = found.setdefault(r["code"], [])
            item = {"village": village, "amphoe": amphoe}
            if (village or amphoe) and item not in items:
                items.append(item)
    reaches_out = {}
    for code, items in found.items():
        n = cover[code]
        if n["samples"] and n["villages"] / n["samples"] >= 0.8:
            reaches_out[code] = [x for x in items if x["village"]]
        else:  # too few villages named: the อำเภอ only, once each
            reaches_out[code] = [{"village": None, "amphoe": a} for a in dict.fromkeys(x["amphoe"] for x in items if x["amphoe"])]
        print(f"{code}: {n['samples']} samples, {n['villages']} with a village, {len(reaches_out[code])} places")
    OUT.write_text(json.dumps({"built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                               "source": "OpenStreetMap via Nominatim reverse (zoom 14) · © OpenStreetMap contributors (ODbL)",
                               "step_km": STEP_KM, "coverage": cover, "reaches": reaches_out}, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
