"""ONWR's water-risk platform (https://waterrisk.onwr.go.th/map, owner question 2026-10-05): what it serves without a key,
how fresh it is, and whether its 24 h flood warning adds to our gauges. Standard library only, project User-Agent,
public GETs only; the personal-data services the map also calls (SOS requests, vulnerable houses) are not touched, and the
third-party map key embedded in the site's JavaScript is not used.
Run: python3 research/2026-10-05_onwr_waterrisk_probe.py"""
import collections, gzip, json, math, struct, time, urllib.request

UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"
TILES = "https://check-water-map-service-726396821992.asia-southeast3.run.app"
API = "https://api.waterrisk.onwr.go.th/api/v1"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            b = r.read()
            return r.status, gzip.decompress(b) if r.headers.get("Content-Encoding") == "gzip" else b
    except urllib.error.HTTPError as e:
        return e.code, b""
def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7F) << s; s += 7
        if c < 0x80: return r, i

def fields(b):
    i = 0
    while i < len(b):
        k, i = varint(b, i); f, w = k >> 3, k & 7
        if w == 0: v, i = varint(b, i)
        elif w == 2: n, i = varint(b, i); v = b[i:i + n]; i += n
        elif w == 1: v = b[i:i + 8]; i += 8
        elif w == 5: v = b[i:i + 4]; i += 4
        else: raise ValueError(w)
        yield f, w, v

def packed(b):
    out, i = [], 0
    while i < len(b):
        v, i = varint(b, i); out.append(v)
    return out

def value(b):
    for f, w, v in fields(b):
        if f == 1: return v.decode("utf-8", "replace")
        if f == 2: return struct.unpack("<f", v)[0]
        if f == 3: return struct.unpack("<d", v)[0]
        if f in (4, 5): return v
        if f == 6: return (v >> 1) ^ -(v & 1)
        if f == 7: return bool(v)

def decode(data):
    if data[:2] == b"\x1f\x8b": data = gzip.decompress(data)
    layers = []
    for f, w, lb in fields(data):
        if f != 3: continue
        L = {"name": None, "keys": [], "values": [], "features": [], "extent": 4096}
        for g, w2, v in fields(lb):
            if g == 1: L["name"] = v.decode()
            elif g == 3: L["keys"].append(v.decode())
            elif g == 4: L["values"].append(value(v))
            elif g == 5: L["extent"] = v
            elif g == 2:
                F = {"id": None, "tags": [], "type": None, "geom": []}
                for h, w3, u in fields(v):
                    if h == 1: F["id"] = u
                    elif h == 2: F["tags"] = packed(u)
                    elif h == 3: F["type"] = u
                    elif h == 4: F["geom"] = packed(u)
                L["features"].append(F)
        layers.append(L)
    return layers

def props(L, F):
    t = F["tags"]
    return {L["keys"][t[i]]: L["values"][t[i + 1]] for i in range(0, len(t), 2)}



def km(a, b, c, d):
    return 6371 * 2 * math.asin(math.sqrt(math.sin(math.radians(c - a) / 2) ** 2 + math.cos(math.radians(a))
                                          * math.cos(math.radians(c)) * math.sin(math.radians(d - b) / 2) ** 2))


_, body = get(f"{TILES}/layers")
print("tile service layers (GET /layers):")
for x in json.loads(body):
    _, tj = get(f"{TILES}/tiles/{x['id']}/tilejson.json")
    print(f"  {x['id']:22s} {x['type']:8s} {x['name'][:40]:40s} data_updated {json.loads(tj or b'{}').get('data_updated')}")
    time.sleep(0.2)
_, body = get(f"{API}/dashboard")
d = json.loads(body)["data"]
fl = next(a for a in d["alerts"] if a["disaster"] == "flood")
print(f"dashboard: floodUpdatedAt {d['floodUpdatedAt']} · flood provincesAtRisk {fl['provincesAtRisk']} ({fl['statusTh']}) · riskAreas rows {len(d['riskAreas'])}")

cells = {}
for x in (49, 50):
    for y in (28, 29, 30, 31):
        st, b = get(f"{TILES}/tiles/flood-warn/6/{x}/{y}.pbf")
        if st == 200 and b[:1] != b"{":
            for L in decode(b):
                for F in L["features"]:
                    p = props(L, F)
                    cells[p["id"]] = p
        time.sleep(0.2)
print("flood-warn cells at z6 over Thailand:", len(cells), dict(sorted(collections.Counter(c["class_risk"] for c in cells.values()).items())),
      "(z6 keeps ~84 % of the cells seen at z8: a collector should read z8+)")
_, body = get("https://flood.autobahn.bot/api/stations")
j = json.loads(body)
gs = [s for s in (j if isinstance(j, list) else j.get("stations", [])) if s.get("lat") and s.get("lon")]
cent = [((c["top"] + c["bottom"]) / 2, (c["left"] + c["right"]) / 2) for c in cells.values()]


def nearest(lat, lon):
    return min((km(lat, lon, a, b) for a, b in cent if abs(a - lat) < 0.2 and abs(b - lon) < 0.2), default=1e9)


for label, sel in (("over/near bank (critical, warning)", ("critical", "warning")), ("watch", ("watch",)), ("normal", ("normal",))):
    g = [s for s in gs if s.get("status") in sel]
    dd = [nearest(s["lat"], s["lon"]) for s in g]
    print(f"our gauges {label}: {len(g)} · ONWR warning cell within 2 km {sum(v <= 2 for v in dd)}"
          f" ({100 * sum(v <= 2 for v in dd) / max(1, len(g)):.0f} %) · within 5 km {sum(v <= 5 for v in dd)}")
