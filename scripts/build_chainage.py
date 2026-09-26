"""Build river chainage (km from the mouth) for Chao Phraya gauges from HII's river centreline (D-019, D-023).

Source: https://tiwrm.hii.or.th/thaiwater_l5/public/resources/json/river/river_main.json (the river layer of the
HII warning map; 93 named rivers, CRS84, ~100 m vertex precision). The Chao Phraya is a MultiLineString of 24
pieces including side branches, so pieces are joined into a graph (endpoints linked to the nearest vertex of
another piece within 1.5 km) and chainage = shortest-path distance from the southernmost vertex (the mouth).
Check (2026-09-26): mouth -> Nakhon Sawan = 373.5 km (commonly cited river length: ~372 km).

Usage: python3 scripts/build_chainage.py stations.csv > src/floodwatch/data/chaophraya_chainage.json
stations.csv lines: code|lat|lon   (e.g. from: SELECT code, lat, lon FROM station WHERE river='แม่น้ำเจ้าพระยา')
"""
from __future__ import annotations

import heapq
import json
import math
import sys
import urllib.request

URL = "https://tiwrm.hii.or.th/thaiwater_l5/public/resources/json/river/river_main.json"
UA = "BKK-FloodWatch/0.2 (+https://flood.autobahn.bot)"


def km(a, b) -> float:
    return 111.2 * math.hypot(a[1] - b[1], (a[0] - b[0]) * math.cos(math.radians((a[1] + b[1]) / 2)))


def main(path: str) -> None:
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    geo = json.load(urllib.request.urlopen(req, timeout=60))
    feat = next(f for f in geo["features"] if f["properties"].get("STR_NAMT") == "แม่น้ำเจ้าพระยา")
    parts = [p for p in feat["geometry"]["coordinates"] if len(p) >= 2]
    nodes: list[tuple[float, float]] = []
    adj: dict[int, list[tuple[int, float]]] = {}

    def link(a: int, b: int) -> None:
        w = km(nodes[a], nodes[b])
        adj.setdefault(a, []).append((b, w))
        adj.setdefault(b, []).append((a, w))

    ends = []
    piece: list[int] = []
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
        cands = [(km(nodes[e], c), k) for k, c in enumerate(nodes) if piece[k] != piece[e]]
        g, k = min(cands)
        if g < 1.5:
            link(e, k)
    mouth = min(range(len(nodes)), key=lambda k: nodes[k][1])
    dist = {mouth: 0.0}
    pq = [(0.0, mouth)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, 1e9):
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, 1e9):
                dist[v] = d + w
                heapq.heappush(pq, (d + w, v))
    out = {}
    for line in open(path):
        code, lat, lon = line.strip().split("|")
        off, ch = min((km((float(lon), float(lat)), nodes[k]), dist[k]) for k in dist)
        out[code] = {"chainage_km": round(ch, 1), "offset_km": round(off, 2)}
    json.dump({"source": URL, "method": "graph shortest path from the mouth; see script docstring",
               "mouth_to_northernmost_km": round(dist[max(dist, key=lambda k: nodes[k][1])], 1), "stations": out}, sys.stdout, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
