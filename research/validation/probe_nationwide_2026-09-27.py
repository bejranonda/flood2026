"""Nationwide source probe (2026-09-27): one polite request per candidate endpoint with an honest UA; bodies are
saved to $PROBE_OUT. Results: research/VALIDATION_2026-09-27_nationwide.md. DWR EWS and RID Telerid time out from
outside Thailand; run those through the Thai egress (D-014, public pages only). GISTDA_API_KEY is read from the
environment and must be redacted from output by the caller (see the report). Usage: python3 probe.py [name ...]"""
import json, os, socket, sys, time, urllib.request, urllib.error, urllib.parse, gzip, re
OUT = os.environ.get("PROBE_OUT", "/tmp/nationwide_probe"); os.makedirs(OUT, exist_ok=True)
UA = "BKK-FloodWatch/0.6 (+https://flood.autobahn.bot) nationwide-source-probe"
V3 = "https://api-v3.thaiwater.net/api/v1/thaiwater30"
FEWS = "https://fews2.hii.or.th/model-output/data_portal"
GK = os.environ.get("GISTDA_API_KEY", "")  # never printed
T = [
 ("v3_dam",            V3 + "/analyst/dam", None),
 ("v3_watergate_load", V3 + "/public/watergate_load", None),
 ("v3_flood_road",     V3 + "/public/flood_road", None),
 ("v3_rain7day",       V3 + "/public/rain7day_forecast", None),
 ("v3_canal_wl",       V3 + "/public/canal_waterlevel", None),
 ("v3_flow",           V3 + "/public/flow", None),
 ("v3_storm",          V3 + "/public/storm_data", None),
 ("fews_flashflood",   FEWS + "/flashflood/flashflood_report.txt", None),
 ("fews_hii_wl_meta",  FEWS + "/metadata/hii_waterlevel.csv", None),
 ("fews_rid_q_meta",   FEWS + "/metadata/rid_discharge.csv", None),
 ("fews_tide",         FEWS + "/tide_table/summary.txt", None),
 ("egat_dam",          "https://api-egatwater.egat.co.th/api/dam", None),
 ("rid_telerid",       "https://telerid.rid.go.th/restapi/main/station_list/", None),
 ("dwr_ews",           "https://ews.dwr.go.th/ews/web-service/stn", {"action": "LoadStation"}),
 ("glofas_hatyai",     "https://flood-api.open-meteo.com/v1/flood?latitude=7.0&longitude=100.47&daily=river_discharge,river_discharge_median,river_discharge_max&past_days=7&forecast_days=7", None),
 ("glofas_nongkhai",   "https://flood-api.open-meteo.com/v1/flood?latitude=17.88&longitude=102.74&daily=river_discharge,river_discharge_median,river_discharge_max&past_days=7&forecast_days=7", None),
 ("gdacs_fl_tha",      "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=FL&country=THA&fromdate=2026-08-01&todate=2026-09-27", None),
 ("google_floods_api", "https://floodforecasting.googleapis.com/v1/gauges:searchGaugesByArea", {"regionCode": "TH"}),
 ("gfm_api",           "https://api.gfm.eodc.eu/v2/", None),
 ("gistda_extent_1d",  "https://api-gateway.gistda.or.th/api/2.0/resources/gi-service/v1.0/disasters/flood-extent-1day?lat=7.0&lon=100.47&api_key=" + urllib.parse.quote(GK), None),
 ("thaiwater_net_wl",  "https://www.thaiwater.net/water/wl", None),
 ("mrc_ffw",           "https://ffw-web.mrcmekong.org/", None),
]
only = set(sys.argv[1:])
res = {}
for name, url, post in T:
    if only and name not in only: continue
    t0 = time.time(); host = urllib.parse.urlparse(url).hostname
    try: socket.gethostbyname(host); dns = "ok"
    except Exception as e: dns = "FAIL"
    try:
        data = None; hdr = {"User-Agent": UA, "Accept-Encoding": "gzip", "Accept": "application/json, text/*;q=0.8, */*;q=0.5"}
        if post is not None:
            if name == "google_floods_api":
                data = json.dumps(post).encode(); hdr["Content-Type"] = "application/json"
            else:
                data = urllib.parse.urlencode(post).encode(); hdr["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=data, headers=hdr)
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read(); code = r.status; ctype = r.headers.get("Content-Type", "")
            if r.headers.get("Content-Encoding") == "gzip": body = gzip.decompress(body)
    except urllib.error.HTTPError as e:
        body = e.read()[:4000]; code = e.code; ctype = e.headers.get("Content-Type", "")
    except Exception as e:
        body = b""; code = type(e).__name__ + ": " + str(e)[:120]; ctype = ""
    dt = round(time.time() - t0, 1)
    open(os.path.join(OUT, name + ".body"), "wb").write(body)
    res[name] = {"dns": dns, "status": code, "bytes": len(body), "s": dt, "ctype": ctype[:40]}
    print(f"{name:18} dns={dns:4} status={str(code)[:60]:60} {len(body):>9}B {dt:>5}s {ctype[:30]}", flush=True)
    time.sleep(1)
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1)
