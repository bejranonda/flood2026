"""E-7D-IN-LONG, the merge: the change that passed (KF_ec on days 3–7 where persistence is served,
research/2026-10-06_e7d_inflow_long_narrow.log) into src/floodwatch/data/reservoir_inflow7.json without touching any served
model horizon. Existing dams: a persistence horizon chosen for KF_ec takes the built model; the ECMWF scales learned on
the 2025 wet season go under scale_by_source["ec"] (the served 4-model scales stay). New dams: an entry whose other
horizons are persistence with the 2026 scored bands. Run: python3 research/2026-10-06_e7d_inflow_long_merge.py"""
import json

PATH = "src/floodwatch/data/reservoir_inflow7.json"
cur = json.load(open(PATH))
b = json.loads(next(l for l in open("research/2026-10-06_e7d_inflow_long_build.log") if l.startswith("BUILD_JSON "))[len("BUILD_JSON "):])
added, new_dams = 0, 0
for dam_id, e in b.items():
    kf = {h: v for h, v in e["horizons"].items() if v.get("use") == "KF_ec"}
    if not kf:
        continue
    ec_scale = {"ecmwf_ifs025": e["scale"]["ecmwf_ifs025"]}
    if dam_id in cur:
        d = cur[dam_id]
        for h, v in kf.items():
            if (d["horizons"].get(h) or {}).get("use", "persistence") == "persistence":
                d["horizons"][h] = v
                added += 1
        d.setdefault("scale_by_source", {})["ec"] = ec_scale
        d["source"] = d.get("source", "") + " · KF_ec on days 3–7 where persistence was served: research/2026-10-06_e7d_inflow_long_build.py"
    else:
        hz = {}
        for h in map(str, range(1, 8)):
            hz[h] = kf.get(h) or {"use": "persistence", "family": None, "band_persist": e["persist_bands"][h]}
        cur[dam_id] = {"dam_id": int(dam_id), "name_th": e["name_th"], "family": "KF_ec", "models": ["ecmwf_ifs025"],
                       "scale": ec_scale, "scale_by_source": {"ec": ec_scale}, "horizons": hz,
                       "test_from": e["test_from"], "test_to": e["test_to"], "test_days": e["test_days"], "choose_days": e["choose_days"],
                       "points": e["points"], "loss_by_month": e["loss_by_month"],
                       "source": "research/2026-10-06_e7d_inflow_long_build.py S+KF_ec@3 (E-7D-IN-LONG; chosen on the 2025 wet season, scored on 2026)"}
        added += len(kf)
        new_dams += 1
json.dump(cur, open(PATH, "w"), ensure_ascii=False, indent=1)
print(f"dams in the file: {len(cur)} (new {new_dams}) · KF_ec horizons added: {added}")
