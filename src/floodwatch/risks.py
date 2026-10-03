"""The "⚠️ จับตา" tab (owner 2026-10-03: "the list of potential risks according to the water level in next 24 or 48 hr
… link to the stations or areas … with the confidence"; D-077). Pure: the API passes the station rows, rain per
province, the satellite summary and the track records (compute_records). A gauge is listed once, in its worst group;
provinces are listed for rain and satellite. Evidence for every threshold: research/2026-10-03_verify_*.py."""
from __future__ import annotations

from floodwatch import regions

RAIN_MM = 35.1         # the top strip's heavy-rain threshold (SUMMARY_RAIN_MIN_MM, KI-265)
UP_RISE_CM = 30        # upstream rose this much in 24 h: 69 % led to a >= 10 cm rise downstream (24 % without), 2026-10-03
UP_LAG_H = (3, 48)     # learned travel times inside the tab's window
BANDS = (">50%", "25-50%")  # bank-chance bands whose record is >= 1 in 10 (61 % and 12 % came true, 2026-10-03)
ORDER = ("over_bank", "may_reach", "upstream", "fast_rise", "rain", "satellite")


def _item(s: dict, **k) -> dict:
    return {"code": s["code"], "name_th": s.get("name_th") or s["code"], "province": s.get("province"),
            "region": s.get("region"), "freeboard_m": s.get("freeboard_m"), **k}


def _upstream_hit(s: dict, by: dict) -> dict | None:
    """The learned upstream gauge (fresh, travel time 3-48 h) with the biggest measured 24 h rise >= UP_RISE_CM."""
    best = None
    for u in s.get("upstream") or []:
        o = by.get(u.get("code"))
        lag = u.get("lag_h")
        if not o or o.get("stale") or lag is None or not (UP_LAG_H[0] <= lag <= UP_LAG_H[1]):
            continue
        rise = (o.get("observed24") or {}).get("change_cm")
        if rise is not None and rise >= UP_RISE_CM and (best is None or rise > best["rise_cm"]):
            best = {"code": o["code"], "name_th": o.get("name_th") or o["code"], "lag_h": lag, "rise_cm": rise}
    return best


def _group_of(s: dict, by: dict) -> tuple[str | None, dict]:
    st = s.get("status")
    b24, b48 = s.get("bank_chance24"), s.get("bank_chance48")
    if st == "critical":
        return "over_bank", {}
    if b24 in BANDS or b48 in BANDS:
        band, hours = (b24, 24) if b24 in BANDS else (b48, 48)
        return "may_reach", {"band": band, "hours": hours}
    up = _upstream_hit(s, by) if st in ("watch", "warning") else None
    if up:
        return "upstream", {"up": up}
    ch = s.get("change24") or {}
    if ch.get("level") == "strong_rise":
        return "fast_rise", {"rise_cm": round((ch.get("median") or 0) * 100)}
    return None, {}


def build(stations: list[dict], rain_by_prov: dict[str, float], sat: dict | None, records: dict | None) -> dict:
    by = {s["code"]: s for s in stations}
    groups: dict[str, list] = {k: [] for k in ORDER}
    stale = {k: 0 for k in ORDER}
    for s in stations:
        key, extra = _group_of(s, by)
        if key is None:
            continue
        if s.get("stale"):  # old data cannot say what happens next: counted, not listed
            stale[key] += 1
            continue
        groups[key].append(_item(s, **extra))
    prov: dict[str, list] = {}
    for i in groups["over_bank"]:
        prov.setdefault(i["province"] or "ไม่ทราบจังหวัด", []).append(i)
    groups["over_bank"] = [{"province": p, "region": regions.region_of(p),
                            "gauges": sorted(v, key=lambda i: i["freeboard_m"] if i["freeboard_m"] is not None else 0)}
                           for p, v in sorted(prov.items(), key=lambda x: (-len(x[1]), x[0]))]
    groups["may_reach"].sort(key=lambda i: (BANDS.index(i["band"]), i["hours"],
                                            i["freeboard_m"] if i["freeboard_m"] is not None else 9e9))
    groups["upstream"].sort(key=lambda i: -i["up"]["rise_cm"])
    groups["fast_rise"].sort(key=lambda i: -i["rise_cm"])
    groups["rain"] = [{"province": p, "region": regions.region_of(p), "mm24": round(mm, 1)}
                      for p, mm in sorted(rain_by_prov.items(), key=lambda x: -x[1]) if mm >= RAIN_MM]
    sp = (sat or {}).get("province") or {}
    groups["satellite"] = [{"province": p, "region": regions.region_of(p), "rai": int(r)}
                           for p, r in sorted(sp.items(), key=lambda x: -x[1]) if r > 0]
    return {"groups": [{"key": k, "items": groups[k], "left_stale": stale[k]} for k in ORDER if groups[k]],
            "records": records or {},
            "sat_dates": [sat["img_from"], sat["img_to"]] if sat and sat.get("img_from") else None}
