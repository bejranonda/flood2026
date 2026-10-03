"""River km (distance from the downstream end along HII's river line) for the "แม่น้ำ" tab (owner 2026-10-03: "Should we
adapt tab เจ้าพระยา? because we extended to nationwide already" → chose "แม่น้ำ tab + forecast").

Generalises scripts/build_chainage.py (Chao Phraya, 2026-09-26): the pieces of a river's MultiLineString are joined into
a graph (a piece end links to the nearest vertex of another piece within JOIN_KM) and km = shortest-path distance from
the mouth. Thai rivers flow south, east (Mun) or north (Pattani), so the mouth is chosen among the line's extreme
vertices (south, north, east, west) as the one from which the gauges' banks rise most consistently (banks get higher
upstream). Pure functions; the collector supplies HII's river_main.json and the gauges. Km is approximate (±10 km near
branches); it orders gauges and labels distance, it never interpolates water between gauges (D-019).
"""
from __future__ import annotations

import heapq
import math

JOIN_KM = 1.5    # piece ends closer than this to another piece are joined (build_chainage.py)
MAX_OFF_KM = 5.0  # a gauge farther than this from the river line is not on it (a tributary or a wrong river name)
MAX_GAP_KM = 100.0  # pieces of ONE named river still apart are bridged end to end, shortest first (reservoirs: Sirikit ~80 km)


def _km(a, b) -> float:
    return 111.2 * math.hypot(a[1] - b[1], (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2)))


def _graph(parts: list) -> tuple[list, dict]:
    nodes: list[tuple[float, float]] = []
    adj: dict[int, list[tuple[int, float]]] = {}
    piece: list[int] = []
    ends = []

    def link(a: int, b: int) -> None:
        w = _km(nodes[a], nodes[b])
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))

    for n, p in enumerate(parts):
        ids = []
        for c in p:
            nodes.append((c[0], c[1]))
            piece.append(n)
            ids.append(len(nodes) - 1)
        for a, b in zip(ids, ids[1:]):
            link(a, b)
        ends += [ids[0], ids[-1]]
    for e in ends:
        cands = [(_km(nodes[e], c), k) for k, c in enumerate(nodes) if piece[k] != piece[e]]
        if cands:
            g, k = min(cands)
            if g < JOIN_KM:
                link(e, k)
    # Bridge what is still apart, shortest gaps first (Kruskal over piece ends): rivers are drawn in loose pieces and
    # stop inside reservoirs (the Ping: 528 pieces, 15-25 km gaps across Bhumibol's lake, 2026-10-03).
    root = list(range(len(nodes)))

    def find(x: int) -> int:
        while root[x] != x:
            root[x] = root[root[x]]
            x = root[x]
        return x

    for a in adj:
        for b, _ in adj[a]:
            root[find(a)] = find(b)
    gaps = sorted((_km(nodes[a], nodes[b]), a, b) for i, a in enumerate(ends) for b in ends[i + 1:]
                  if piece[a] != piece[b] and _km(nodes[a], nodes[b]) <= MAX_GAP_KM)
    for g, a, b in gaps:
        if find(a) != find(b):
            link(a, b)
            root[find(a)] = find(b)
    return nodes, adj


def _dijkstra(adj: dict, start: int) -> dict[int, float]:
    dist = {start: 0.0}
    pq = [(0.0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e9):
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, 1e9):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    return dist


def _agree(pairs: list[tuple[float, float]]) -> float:
    """Share of gauge pairs where the one farther from the mouth also has the higher bank (1.0 = perfectly upstream)."""
    ok = n = 0
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            (k1, b1), (k2, b2) = pairs[i], pairs[j]
            if k1 == k2 or b1 == b2:
                continue
            n += 1
            ok += (k1 < k2) == (b1 < b2)
    return ok / n if n else 0.0


def chainage(feature: dict, gauges: list[dict]) -> dict:
    """{"mouth": [lon, lat], "agree": share of concordant gauge pairs, "stations": {code: {"km", "off_km"}}}."""
    geom = feature.get("geometry") or {}
    parts = geom.get("coordinates") or []
    if geom.get("type") == "LineString":
        parts = [parts]
    parts = [p for p in parts if len(p) >= 2]
    if not parts:
        return {"mouth": None, "agree": 0.0, "stations": {}}
    nodes, adj = _graph(parts)
    near = {}
    for g in gauges:
        if g.get("lat") is None or g.get("lon") is None:
            continue
        off, k = min((_km((g["lon"], g["lat"]), c), k) for k, c in enumerate(nodes))
        if off <= MAX_OFF_KM:
            near[g["code"]] = (k, off, g.get("bank_msl"))
    cands = {min(range(len(nodes)), key=lambda k: nodes[k][1]), max(range(len(nodes)), key=lambda k: nodes[k][1]),
             max(range(len(nodes)), key=lambda k: nodes[k][0]), min(range(len(nodes)), key=lambda k: nodes[k][0])}
    best = None
    for start in sorted(cands, key=lambda k: nodes[k][1]):  # ties: the southern end (most Thai rivers flow south)
        dist = _dijkstra(adj, start)
        pairs = [(dist[k], b) for k, _, b in near.values() if b is not None and k in dist]
        score = _agree(pairs)
        if best is None or score > best[0]:
            best = (score, start, dist)
    score, start, dist = best
    return {"mouth": list(nodes[start]), "agree": round(score, 3),
            "stations": {c: {"km": round(dist[k], 1), "up": round(dist[k], 1), "off_km": round(off, 2)}
                         for c, (k, off, _) in near.items() if k in dist}}


def order(stations: list[dict], km: dict[str, dict]) -> list[dict]:
    """The profile's stations with a river km, upstream first (as /api/profile always returned them)."""
    up = lambda v: v["up"] if v.get("up") is not None else (v.get("km") or 0.0)  # km-only entries (stored before v0.20.1)
    return sorted((s for s in stations if s["code"] in km), key=lambda s: -up(km[s["code"]]))


MIN_GAUGES = 3  # a chain needs three gauges (2026-10-03: 8 left out three quarters of the gauges; 3 gives ~62 waterways)
POLDER_REGIONS = ("bkk", "metro")  # canals here are pumped and gated: no upstream/downstream (point.POLDER_REGIONS, D-070)


def has_view(river: str, gauges: list[dict]) -> bool:
    """A natural waterway gets a river view; Bangkok-region canals do not. Outside the polders "คลอง" often names a
    natural river (คลองอู่ตะเภา, คลองจันทบุรี), so a canal is excluded only when most of its gauges are in กทม./ปริมณฑล."""
    from floodwatch import point, regions
    if point.water_body({"river": river, "code": gauges[0].get("code", "")}) == "river":
        return True
    regs = [regions.region_of(g.get("province")) for g in gauges]
    if not any(regs):  # where it is unknown it may be a polder canal: no view (คลองหกวา, 2026-10-03)
        return False
    return sum(r in POLDER_REGIONS for r in regs) * 2 < len(gauges)


def profile(rows: list[dict], river: str, km: dict[str, dict]) -> list[dict]:
    """The "แม่น้ำ" tab for one river: its gauges upstream first, each with `chainage_km` (None without an HII line).
    BMA gauges never join an HII/RID river chain (levels differ 0.3-0.6 m, KI-217); they stay in the list and the map."""
    mine = [r for r in rows if r.get("river") == river and r.get("agency") != "BMA"]
    return [{**s, "chainage_km": km[s["code"]].get("km")} for s in order(mine, km)]


def river_km(features: list[dict], stations: list[dict], min_gauges: int = MIN_GAUGES) -> dict:
    """{river: {"mouth", "agree", "stations": {code: {"km", "up"}}}} for every waterway with a view (has_view) and >=
    min_gauges non-BMA gauges with a bank (weekly, hii_geo). With an HII line: km along it (chainage). Without one: the
    order of the banks (they rise upstream on 73-100 % of gauge pairs where both are known, 2026-10-03), no km."""
    lines: dict[str, list] = {}
    for f in features:
        g = f.get("geometry") or {}
        parts = g.get("coordinates") or []
        lines.setdefault((f.get("properties") or {}).get("STR_NAMT"), []).extend(parts if g.get("type") == "MultiLineString" else [parts])
    by: dict[str, list] = {}
    for s in stations:
        if s.get("river") and s.get("agency") != "BMA" and s.get("bank_msl") is not None:
            by.setdefault(s["river"], []).append(s)
    out = {}
    for r, gs in by.items():
        if len(gs) < min_gauges or not has_view(r, gs):
            continue
        if lines.get(r):
            out[r] = chainage({"geometry": {"type": "MultiLineString", "coordinates": lines[r]}}, gs)
        else:
            out[r] = {"mouth": None, "agree": None,
                      "stations": {g["code"]: {"km": None, "up": float(g["bank_msl"])} for g in gs}}
    return out
