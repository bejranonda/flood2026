# Impact tab: release plans as a comparison grid — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Kaeng Krachan case view of `/impact` into a comparison grid of 7-day release plans with honest
outside-the-data labels, river-km + village coverage, ONWR's layers clipped and off by default, and four on-tap AI helps,
released as v0.34.0.

**Architecture:** The engine (`scenarios.compare`) computes everything the grid shows once, on the server: per plan and
day a cell status, outside flags, km at risk and villages; the API adds the brief, the two-plan comparison and a Thai plan
parser; `web/impact.js` renders a table, colours the map from the same fields and puts ONWR's layers into the app's
existing layer box (`app.js` untouched). Villages come from a one-time OpenStreetMap build into a data file.

**Tech Stack:** Python 3.11 (FastAPI, numpy, pytest), plain JavaScript + Leaflet (no build step), CSS, Playwright (browser
check), Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-06-impact-plan-grid-design.md`

## Global Constraints

- Tests: `docker compose build worker && docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q` (the suite runs in the worker image; 461 tests pass before this plan).
- The ★ rule (`scenarios.optimal`) does not change (owner: "Label only", D-110).
- No paragraph over 160 characters in `#view-impact` or any sheet the tab opens; the ★ "why" ≤ 100 characters.
- No water drawn on land (D-019, D-105); river colours and km only.
- Margins are to each gauge's own agency's bank; never mix agencies (KI-217).
- AI: GLM only, on tap only, never decides; everything works with `AI_EXPLAIN=0` (D-022, D-068).
- The typed plan text is never logged or stored (POST body only).
- `web/app.js` and `web/index.html` do not change; `impact.js` keeps "styles by class only" and escapes every outside string with `esc`.
- Never write the `/impact` password (or anything resembling it) in code, tests, docs or commit messages; read it from `.env` only via `IMPACT_PW="$(sed -n 's/^IMPACT_PASSWORD=//p' .env)"`.
- Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S
  ```
- Release steps run one at a time, each checked (GUIDELINES §6c): tests → `git tag -a` → `git push origin main` → `git push origin v0.34.0` → `gh release create v0.34.0 --verify-tag`.
- Before every commit: `git status` (another session's files are committed separately, never folded in).
- Work on the branch `feat/impact-plan-grid` (CLAUDE.md: branch from `main`): before Task 1 run `git checkout main && git pull --ff-only && git checkout -b feat/impact-plan-grid`. Task 15 merges it into `main` with `git checkout main && git pull --ff-only && git merge --ff-only feat/impact-plan-grid` (if `main` moved, `git rebase main` on the branch first and re-run the suite) before tagging.

## Review Focus

1. **A day where no gauge has a margin** (stale feed, all `margin_m` None) must show a grey `none` cell, 0 km and the title "ไม่มีข้อมูล" — never blue. Pinned in Task 3 (`test_a_day_without_any_margin_is_none_not_ok`).
2. **An older stored ONWR copy without `bbox`**, or a layer with no features, must pass through `clip_onwr` unchanged and show a disabled row with count 0. Pinned in Task 1 (`test_stored_onwr_layers_are_clipped_to_their_box_when_served`).
3. **A typed plan above 200 ล้าน ลบ.ม./วัน** is refused, never silently clipped; Thai digits and units are read. Pinned in Task 7.
4. **A custom plan equal to an existing plan** (e.g. today's release typed again) keeps one row per role and the comparison finds the named plan, not the custom twin. Pinned in Task 4 (`test_a_custom_plan_equal_to_todays_keeps_both_rows`) and Task 8 (`test_compare_prefers_the_named_plan_over_its_custom_twin`).
5. **The session expires while the tab is open:** the brief, comparison and parse calls get 401 and the tab shows the login form, not a broken card. Pinned in Task 12 (code) and Task 13 (`session_expiry_shows_login` in the browser check).

---

### Task 1: ONWR's cells clipped to the case box (KI-318)

**Files:**
- Modify: `src/floodwatch/mvt.py` (add `ring_overlaps_bbox` after `tiles_for_bbox`)
- Modify: `src/floodwatch/collectors/__init__.py:843-876` (`onwr_layers` keeps only features inside the box)
- Modify: `src/floodwatch/impact.py` (add `clip_onwr` after `river_reaches`)
- Modify: `src/floodwatch/api/__init__.py:726-733` (`impact_case` serves the clipped copy)
- Test: `tests/test_mvt.py`, `tests/test_impact.py`, `tests/test_impact_auth.py`

**Interfaces:**
- Produces: `mvt.ring_overlaps_bbox(ring: list[list[float]], lat0, lon0, lat1, lon1) -> bool`; `impact.clip_onwr(onwr: dict | None) -> dict | None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mvt.py`:

```python
def test_a_ring_overlaps_a_box_by_its_own_bounding_box():
    box = (12.6, 99.3, 13.3, 100.1)
    inside = [[13.0, 99.9], [13.01, 99.91], [13.0, 99.92]]
    far = [[13.5, 99.8], [13.51, 99.81], [13.5, 99.82]]          # Ratchaburi town, 30+ km north of the case (KI-318)
    around = [[12.5, 99.2], [12.5, 100.2], [13.4, 100.2], [13.4, 99.2]]  # a big polygon with no vertex inside the box
    assert mvt.ring_overlaps_bbox(inside, *box) and mvt.ring_overlaps_bbox(around, *box)
    assert not mvt.ring_overlaps_bbox(far, *box) and not mvt.ring_overlaps_bbox([], *box)


def test_onwr_layers_keeps_only_features_inside_the_case_box():
    # KI-318: whole zoom-10 tiles were kept, so cells 30–56 km away (Ratchaburi) reached the Kaeng Krachan map
    from floodwatch import collectors

    class R:
        def __init__(self, status, body):
            self.status, self.body = status, body

    def get(url):
        if url.endswith("tilejson.json"):
            return R(200, b'{"data_updated": "2026-10-06T05:16:21+00:00"}')
        if "/flood-warn/10/795/474.pbf" in url or "/flood-warn/10/795/473.pbf" in url:
            return R(200, _tile())  # 474: 13.07–13.24 °N (inside); 473: 13.41–13.58 °N (outside the box)
        return R(404, b"")
    out = collectors.onwr_layers((12.6, 99.3, 13.3, 100.1), get=get)
    f = out["flood-warn"]["features"]
    assert len(f) == 1 and 13.0 < f[0]["rings"][0][0][0] < 13.3
```

Append to `tests/test_impact.py`:

```python
def test_stored_onwr_layers_are_clipped_to_their_box_when_served():
    # KI-318: copies stored before the collector clipped are clipped when served; the stored state is not changed
    near = {"cls": 2, "tb": None, "rai": None, "rings": [[[13.07, 99.94], [13.08, 99.95], [13.07, 99.96]]]}
    far = {"cls": 2, "tb": None, "rai": None, "rings": [[[13.51, 99.80], [13.52, 99.81], [13.51, 99.82]]]}
    stored = {"fetched": "2026-10-06T12:03:05+00:00", "bbox": [12.618, 99.237, 13.274, 100.043],
              "layers": {"flood-warn": {"updated": "2026-10-06T11:12:42+00:00", "features": [near, far]},
                         "flood-forecast-d3": {"updated": None, "features": []}}}
    out = impact.clip_onwr(stored)
    assert out["layers"]["flood-warn"]["features"] == [near] and out["layers"]["flood-forecast-d3"]["features"] == []
    assert len(stored["layers"]["flood-warn"]["features"]) == 2 and out["layers"]["flood-warn"]["updated"] == "2026-10-06T11:12:42+00:00"
    assert impact.clip_onwr(None) is None
    old = {"layers": {"flood-warn": {"features": [far]}}}  # an older copy without its box passes through unchanged
    assert impact.clip_onwr(old) is old
```

Append to `tests/test_impact_auth.py`:

```python
def test_the_case_endpoint_serves_onwr_cells_inside_the_case_box_only(monkeypatch):
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    far = {"cls": 2, "rings": [[[13.51, 99.80], [13.52, 99.81], [13.51, 99.82]]]}
    near = {"cls": 2, "rings": [[[13.07, 99.94], [13.08, 99.95], [13.07, 99.96]]]}
    st = {"case": "kaeng-krachan", "points": [], "onwr": {"bbox": [12.618, 99.237, 13.274, 100.043],
                                                          "layers": {"flood-warn": {"updated": None, "features": [near, far]}}}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st)
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    out = json.loads(api.impact_case(Req(tok), "kaeng-krachan").body)
    assert out["onwr"]["layers"]["flood-warn"]["features"] == [near]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_mvt.py tests/test_impact.py tests/test_impact_auth.py -k "overlaps or keeps_only or clipped or inside_the_case_box"`
Expected: FAIL — `AttributeError: module 'floodwatch.mvt' has no attribute 'ring_overlaps_bbox'` and `'impact' has no attribute 'clip_onwr'`; the collector test fails with 2 features.

- [ ] **Step 3: Implement**

In `src/floodwatch/mvt.py`, after `tiles_for_bbox`:

```python
def ring_overlaps_bbox(ring, lat0: float, lon0: float, lat1: float, lon1: float) -> bool:
    """A ring of [lat, lon] whose own bounding box overlaps the box (lat0, lon0, lat1, lon1). ONWR's cells are ≈ 1.1 km
    hexagons, so boxes overlapping is shapes overlapping to within a cell (KI-318)."""
    if not ring:
        return False
    lats = [p[0] for p in ring]
    lons = [p[1] for p in ring]
    return min(lats) <= lat1 and max(lats) >= lat0 and min(lons) <= lon1 and max(lons) >= lon0
```

In `src/floodwatch/collectors/__init__.py`, inside `onwr_layers`, replace the feature loop body:

```python
            for f in lay.get("features", []):
                p = f["properties"]
                rings = [[[round(c, 5) for c in mvt.to_latlon(px, py, ONWR_Z, x, y, lay["extent"])] for px, py in ring]
                         for ring in f["rings"]]
                if not rings or not mvt.ring_overlaps_bbox(rings[0], *bbox):  # whole tiles reach 30–56 km away (KI-318)
                    continue
                feats.append({"cls": p.get("class_risk"), "tb": p.get("TB_IDN"), "rai": p.get("flood_area"), "rings": rings})
```

In `src/floodwatch/impact.py`, after `river_reaches`:

```python
def clip_onwr(onwr: dict | None) -> dict | None:
    """ONWR's stored layers with only the features inside their own fetch box (KI-318: whole zoom-10 tiles were kept, so
    cells around Ratchaburi, 30–56 km from the Phetchaburi River, showed on the case map). Returns a copy; a copy without a
    box (stored before 2026-10-06) passes through unchanged."""
    from floodwatch import mvt
    if not onwr or not onwr.get("bbox") or not onwr.get("layers"):
        return onwr
    box = onwr["bbox"]
    layers = {lid: {**lay, "features": [f for f in lay.get("features") or []
                                        if f.get("rings") and mvt.ring_overlaps_bbox(f["rings"][0], *box)]}
              for lid, lay in onwr["layers"].items()}
    return {**onwr, "layers": layers}
```

In `src/floodwatch/api/__init__.py`, replace the body of `impact_case` after the 404 check:

```python
    st = _impact_state(impact.state_key(case_id))
    if st.get("onwr"):
        st = {**st, "onwr": impact.clip_onwr(st["onwr"])}  # copies stored before the collector clipped (KI-318)
    return JSONResponse(st, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_mvt.py tests/test_impact.py tests/test_impact_auth.py`
Expected: PASS (all tests in the three files).

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/mvt.py src/floodwatch/collectors/__init__.py src/floodwatch/impact.py src/floodwatch/api/__init__.py tests/test_mvt.py tests/test_impact.py tests/test_impact_auth.py
git commit -m "impact: ONWR's cells clipped to the case box (KI-318) — whole zoom-10 tiles had put Ratchaburi's cells, 30–56 km away, on the Kaeng Krachan map; stored copies are clipped when served" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 2: A goal has a "best" plan only where plans differ; "ห่างตลิ่งมากสุด"

**Files:**
- Modify: `src/floodwatch/scenarios.py:17-19` (EFFECT_TH), `:95-103` (`best_for`)
- Test: `tests/test_scenarios.py`

**Interfaces:**
- Produces: `scenarios.best_for(rows) -> dict[str, str | None]` (a key's value is None when the plans do not differ on it); `scenarios.TOL`.

- [ ] **Step 1: Write the failing test and update the old assertion**

In `tests/test_scenarios.py`, in `test_best_for_each_effect_and_the_stated_optimal_rule_are_explainable`, replace

```python
    assert best["city"] == "ramp" and best["worst"] == "ramp" and best["warning"] == "ramp" and best["water"] in ("more", "ramp")
```

with

```python
    assert best["city"] == "ramp" and best["worst"] == "ramp" and best["warning"] == "ramp"
    assert best["water"] is None  # both end at 690: no plan keeps more water (D-110)
```

Append:

```python
def test_a_goal_has_a_best_plan_only_when_the_plans_differ_on_it():
    # D-110: "ท่วมรวมน้อยสุด" and "ไม่มีจุดใดล้นหนัก" were awarded to 9.5 while no plan overtopped and every margin was > 2 m
    rows = [_row("a", worst_margin_min=2.11, city_margin_min=2.13, storage_end=715.0, ramp_max=0.0),
            _row("b", worst_margin_min=2.13, city_margin_min=2.13, storage_end=723.0, ramp_max=1.13),
            _row("c", worst_margin_min=0.18, city_margin_min=1.73, storage_end=639.0, ramp_max=10.87)]
    best = sc.best_for(rows)
    assert best["total"] is None  # nothing overtops anywhere
    assert best["worst"] == "b" and best["water"] == "b" and best["warning"] == "a" and best["city"] in ("a", "b")
    same = [_row("x", storage_end=700.0), _row("y", storage_end=700.4)]
    assert sc.best_for(same)["water"] is None and sc.best_for(same)["city"] is None
    assert sc.EFFECT_TH["worst"] == "ห่างตลิ่งมากสุด"
```

- [ ] **Step 2: Run to verify it fails**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_scenarios.py -k "best"`
Expected: FAIL — `best["total"]` is `"a"` and `EFFECT_TH["worst"]` is `"ไม่มีจุดใดล้นหนัก"`.

- [ ] **Step 3: Implement**

In `src/floodwatch/scenarios.py` change the `worst` entry of `EFFECT_TH`:

```python
EFFECT_TH = {"city": "ปกป้องตัวเมือง", "worst": "ห่างตลิ่งมากสุด", "total": "ท่วมรวมน้อยสุด", "dam": "ความปลอดภัยเขื่อน",
             "curve": "กลับใต้เส้นควบคุมเร็ว", "water": "เก็บน้ำไว้ใช้", "warning": "เตือนล่วงหน้าได้"}
```

Replace `best_for` with:

```python
# a goal has a "best" plan only when the plans differ on it by more than this (D-110: "ท่วมรวมน้อยสุด" was awarded while no
# plan overtopped anywhere): m for margins, ล้าน ลบ.ม. for storage, ล้าน ลบ.ม./วัน for the daily change
TOL = {"city": 0.05, "worst": 0.05, "dam": 1.0, "water": 1.0, "warning": 0.1}


def _spread(effects: list[dict], key: str) -> float:
    vals = [e[key] for e in effects if e.get(key) is not None]
    return (max(vals) - min(vals)) if len(vals) >= 2 else 0.0


def _differs(rows: list[dict], k: str) -> bool:
    e = [r["effects"] for r in rows]
    if len(e) < 2:
        return False
    if k == "total":
        return max(x["overtop_sum"] for x in e) > 0 and _spread(e, "overtop_sum") > 0.01
    if k == "dam":
        return _spread(e, "storage_peak") > TOL["dam"] or len({x["days_above_normal"] for x in e}) > 1
    if k == "curve":
        return len({99 if x["under_curve_day"] is None else x["under_curve_day"] for x in e}) > 1 or _spread(e, "storage_end") > TOL["water"]
    key = {"city": "city_margin_min", "worst": "worst_margin_min", "water": "storage_end", "warning": "ramp_max"}[k]
    return _spread(e, key) > TOL[k]


def best_for(rows: list[dict]) -> dict:
    """The best plan per goal, or None for a goal the plans do not differ on (D-110)."""
    none = lambda v, big: big if v is None else v
    keys = {"city": lambda e: (-none(e["city_margin_min"], -1e9),),
            "worst": lambda e: (-none(e["worst_margin_min"], -1e9),),
            "total": lambda e: (e["overtop_sum"], -none(e["worst_margin_min"], -1e9)),
            "dam": lambda e: (e["storage_peak"], e["days_above_normal"]),
            "curve": lambda e: (none(e["under_curve_day"], 99), e["storage_end"]),
            "water": lambda e: (-e["storage_end"],),
            "warning": lambda e: (e["ramp_max"], -none(e["worst_margin_min"], -1e9))}
    return {k: (_key(rows, fn) if _differs(rows, k) else None) for k, fn in keys.items()}
```

- [ ] **Step 4: Run to verify it passes**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_scenarios.py tests/test_impact_auth.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/scenarios.py tests/test_scenarios.py
git commit -m "scenarios: a goal names a best plan only where the plans differ on it; 'ห่างตลิ่งมากสุด' says what the goal measures (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 3: Day cells, outside detail and short labels (pure functions)

**Files:**
- Modify: `src/floodwatch/scenarios.py` (add after `_req_txt`)
- Test: `tests/test_scenarios.py`

**Interfaces:**
- Produces:
  - `scenarios.gauge_status(margin: float | None, req: float | None) -> str` ∈ {"over", "near", "ok", "none"}
  - `scenarios.day_cells(down: dict, margin_req: dict | None, reach_km: dict | None = None, days: int = 7) -> list[dict]` — each `{"status", "outside", "km", "codes", "worst_code", "worst_margin", "worst_req"}`; stamps `row["status"]` on every downstream row it reads.
  - `scenarios.outside_detail(down: dict, points: list[dict]) -> list[dict]` — each `{"code", "days" (1-based), "flow_max", "qmax"}`.
  - `scenarios.short_label(plan: dict) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scenarios.py`:

```python
def test_a_day_cell_is_the_worst_gauge_with_outside_and_km_and_rows_carry_their_status():
    b18 = {"margin_m": 0.18, "outside": True}
    down = {"B.18": [b18, dict(b18)],
            "B.10": [{"margin_m": 5.0, "outside": False}, {"margin_m": 0.1, "outside": False}],
            "B.16": [{"margin_m": None, "outside": False}, {"margin_m": -0.2, "outside": True}]}
    req = {"B.18": [0.08, 0.1], "B.10": [0.12, 0.22], "B.16": 0.3}
    cells = sc.day_cells(down, req, {"B.18": 62.4, "B.10": 45.8, "B.16": 11.4}, days=2)
    assert cells[0] == {"status": "ok", "outside": True, "km": 0.0, "codes": [], "worst_code": "B.18", "worst_margin": 0.18,
                        "worst_req": 0.08}
    assert cells[1]["status"] == "over" and cells[1]["codes"] == ["B.10", "B.16"] and cells[1]["km"] == 57.2
    assert cells[1]["worst_code"] == "B.16" and cells[1]["outside"] is True
    assert down["B.10"][1]["status"] == "near" and down["B.16"][0]["status"] == "none" and down["B.18"][0]["status"] == "ok"


def test_a_day_without_any_margin_is_none_not_ok():
    # Review Focus 1: a stale feed (every margin None) is grey "none" with 0 km, never blue
    cells = sc.day_cells({"B.10": [{"margin_m": None}], "B.16": [{"margin_m": None}]}, {"B.10": [0.1]}, {"B.10": 45.8}, days=1)
    assert cells == [{"status": "none", "outside": False, "km": 0.0, "codes": [], "worst_code": None, "worst_margin": None,
                      "worst_req": None}]


def test_outside_detail_names_each_gauge_its_days_its_highest_flow_and_the_ratings_range():
    from test_impact import STATE
    down = sc.daily_downstream(STATE, [21.6] * 7, diversion_cms=63.0)
    det = {o["code"]: o for o in sc.outside_detail(down, STATE["points"])}
    assert det["B.18"]["days"] == [1, 2, 3, 4, 5, 6, 7] and det["B.18"]["qmax"] == 150.0 and det["B.18"]["flow_max"] > 260
    assert det["B.10"]["days"] == [2, 3, 4, 5, 6, 7]
    assert "B.16" not in det  # 205 m³/s < the 300 its rating has seen
    # the city gauge reads B.16's flow (its rating_from), as impact.whatif does
    assert det["B.15"]["days"] == [3, 4, 5, 6, 7] and abs(det["B.15"]["flow_max"] - max(r["flow_cms"] for r in down["B.16"])) < 0.2


def test_short_labels_for_the_grid():
    assert sc.short_label({"kind": "hold", "release": [10.63] * 7}) == "10.6 วันนี้"
    assert sc.short_label({"kind": "constant", "release": [21.5] * 7}) == "21.5 คงที่"
    assert sc.short_label({"kind": "ramp", "release": [22.0, 18.67, 15.33, 12.0, 8.67, 5.33, 2.0]}) == "22→2 ทยอย"
    assert sc.short_label({"kind": "front", "release": [6.0] * 3 + [12.0] * 4}) == "6→12 สองช่วง"
    assert sc.short_label({"kind": "custom", "release": [12.5] * 7}) == "กำหนดเอง 12.5"
    assert sc.short_label({"kind": "custom", "release": [12.0, 13, 14, 15, 16, 17, 18.5]}) == "กำหนดเอง 12→18.5"
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_scenarios.py -k "day_cell or without_any_margin or outside_detail or short_labels"`
Expected: FAIL — `AttributeError: module 'floodwatch.scenarios' has no attribute 'day_cells'`.

- [ ] **Step 3: Implement**

In `src/floodwatch/scenarios.py`, after `_req_txt`:

```python
RANK = {"none": 0, "ok": 1, "near": 2, "over": 3}


def gauge_status(margin: float | None, req: float | None) -> str:
    """One gauge on one day (D-110): 'over' its bank, 'near' it (closer than that day's tested error), 'ok', or 'none'."""
    if margin is None:
        return "none"
    if margin < 0:
        return "over"
    if req is not None and margin < req:
        return "near"
    return "ok"


def _req(margin_req: dict | None, code: str, d: int) -> float | None:
    v = (margin_req or {}).get(code)
    if isinstance(v, (list, tuple)):
        return v[d] if d < len(v) else None
    return v


def day_cells(down: dict, margin_req: dict | None, reach_km: dict | None = None, days: int = DAYS) -> list[dict]:
    """The grid's cells for one plan (D-110), computed once here: per day the worst gauge's status, whether any gauge runs
    beyond its rating's data, the km of river whose nearest gauge is near or over its bank, those gauges, and the worst
    gauge with its margin and that day's tested error (the cell's title). Stamps each downstream row's own `status`, so the
    map and the sheet read the same rule."""
    out = []
    for d in range(days):
        worst, codes, outside = None, [], False
        for code, rows in down.items():
            if d >= len(rows):
                continue
            r = rows[d]
            req = _req(margin_req, code, d)
            s = gauge_status(r.get("margin_m"), req)
            r["status"] = s
            outside = outside or bool(r.get("outside"))
            if s in ("near", "over"):
                codes.append(code)
            if s != "none" and (worst is None or RANK[s] > RANK[worst[0]]
                                or (RANK[s] == RANK[worst[0]] and r["margin_m"] < worst[2])):
                worst = (s, code, r["margin_m"], req)
        out.append({"status": worst[0] if worst else "none", "outside": outside,
                    "km": round(sum((reach_km or {}).get(c, 0.0) for c in codes), 1), "codes": codes,
                    "worst_code": worst[1] if worst else None, "worst_margin": round(worst[2], 3) if worst else None,
                    "worst_req": worst[3] if worst else None})
    return out


def outside_detail(down: dict, points: list[dict]) -> list[dict]:
    """Every gauge a plan runs beyond its rating's data (D-110, KI-319): the days (1-based), the plan's highest flow on those
    days (m³/s; a city gauge reads its rating_from gauge's flow, as impact.whatif does) and the highest flow in the
    rating's data (qmax)."""
    by = {p["code"]: p for p in points}
    out = []
    for code, rows in down.items():
        days = [d + 1 for d, r in enumerate(rows) if r.get("outside")]
        if not days:
            continue
        src = (by.get(code) or {}).get("rating_from")
        flows = []
        for d in days:
            f = rows[d - 1].get("flow_cms")
            if f is None and src in down and d - 1 < len(down[src]):
                f = down[src][d - 1].get("flow_cms")
            if f is not None:
                flows.append(f)
        qmax = ((by.get(code) or {}).get("rating") or {}).get("qmax")
        out.append({"code": code, "days": days, "flow_max": round(max(flows), 1) if flows else None,
                    "qmax": round(qmax, 1) if qmax is not None else None})
    return out


def _c(x: float) -> str:
    """22.0 → '22', 10.5 → '10.5' (a short label; the sheet carries the full words)."""
    return f"{x:.1f}".rstrip("0").rstrip(".")


def short_label(plan: dict) -> str:
    """The grid's plan label (D-110): '21.5 คงที่', '10.6 วันนี้', '22→2 ทยอย', '6→12 สองช่วง', 'กำหนดเอง 12→18.5'."""
    r, kind = plan["release"], plan.get("kind")
    flat = len(set(r)) == 1
    if kind == "hold":
        return f"{r[0]:.1f} วันนี้"
    if kind == "custom":
        return "กำหนดเอง " + (f"{r[0]:.1f}" if flat else f"{_c(r[0])}→{_c(r[-1])}")
    if flat:
        return f"{r[0]:.1f} คงที่"
    return f"{_c(r[0])}→{_c(r[-1])} " + ("ทยอย" if kind == "ramp" else "สองช่วง")
```

- [ ] **Step 4: Run to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_scenarios.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/scenarios.py tests/test_scenarios.py
git commit -m "scenarios: day cells (worst gauge, outside the data, km at risk), outside detail per gauge, short plan labels — one rule on the server for the grid, the map and the sheet (D-110, KI-319)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 4: The comparison carries the grid (ladder, roles, labels, days, outside, customs)

**Files:**
- Modify: `src/floodwatch/scenarios.py:201-270` (`compare`), add `RUNG` and `ladder_ids` before `compare`
- Modify: `src/floodwatch/api/__init__.py:736-778` (`_impact_compare` parses up to three plans; `release` max_length 400 on both endpoints)
- Test: `tests/test_scenarios.py`, `tests/test_impact_auth.py`

**Interfaces:**
- Consumes: `day_cells`, `outside_detail`, `short_label`, `best_for` (Tasks 2–3).
- Produces: `scenarios.compare(..., customs: list[list[float]] | None = None, ...)` (replaces `custom=`). Every plan in `cmp["plans"]` gains `roles: list[str]` (⊆ star, today, custom, pick, ladder), `label`, `days`, `km_max`, `km_days`, `outside_detail`, `outside_any`; rows whose only role is `ladder` drop `level` and `overflow` from their downstream rows. Top level gains `ladder: [ids]`, `picks: [ids]`, `reach_km`, `places`. `scenarios.ladder_ids(rows, max_release, step=RUNG) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scenarios.py`:

```python
def test_the_comparison_carries_the_grid_ladder_roles_labels_days_and_outside_flags():
    st = _r7_state()
    st["reach_km"] = {"B.18": 62.4, "B.10": 45.8, "B.16": 11.4, "B.15": 21.0}
    st["places"] = {"B.10": [{"village": "บ้านท่าโล้", "amphoe": "ท่ายาง"}]}
    cmp = sc.compare(st, inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0,
                     customs=[[12.0] * 7, [20.0] * 7])
    by = {p["id"]: p for p in cmp["plans"]}
    assert [by[i]["release"][0] for i in cmp["ladder"]] == [float(x) for x in range(0, 25, 2)]  # 0, 2 … 24
    assert all("ladder" in by[i]["roles"] for i in cmp["ladder"])
    star = by[cmp["optimal"]["id"]]
    assert "star" in star["roles"] and star["label"] and len(star["days"]) == 7
    assert {"status", "outside", "km", "codes"} <= set(star["days"][0])
    customs = [p for p in cmp["plans"] if p["kind"] == "custom"]
    assert [p["release"][0] for p in customs] == [12.0, 20.0] and all("custom" in p["roles"] for p in customs)
    big = next(p for p in customs if p["release"][0] == 20.0)
    assert big["outside_any"] and big["outside_detail"][0]["code"] == "B.18"  # ≈ 231 m³/s + local > 150 seen
    assert cmp["places"]["B.10"][0]["village"] == "บ้านท่าโล้" and cmp["reach_km"]["B.18"] == 62.4
    assert all(p["downstream"]["B.10"][0].get("status") for p in cmp["plans"])
    only = [p for p in cmp["plans"] if p["roles"] == ["ladder"]]
    assert only and "level" not in only[0]["downstream"]["B.10"][0]  # ladder rungs travel light
    assert set(cmp["picks"]) <= set(by) and all("pick" in by[i]["roles"] for i in cmp["picks"])
    import json as _j
    assert len(_j.dumps(cmp, ensure_ascii=False)) < 150_000


def test_a_custom_plan_equal_to_todays_keeps_both_rows():
    # Review Focus 4: today's release typed again is a custom row beside the hold row, not a replacement
    cmp = sc.compare(_r7_state(), inflow_today=10.3, upper=[600.0] * 7, lower=[200.0] * 7, normal=710.0, max_release=24.0,
                     customs=[[10.8] * 7])
    kinds = [p["kind"] for p in cmp["plans"] if p["release"] == [10.8] * 7]
    assert sorted(kinds) == ["custom", "hold"]
```

In `tests/test_impact_auth.py`, append:

```python
def test_scenarios_take_up_to_three_custom_plans(monkeypatch):
    from test_impact import STATE
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    st = {**STATE, "case": "kaeng-krachan", "built_at": "2026-10-05T12:00:00+00:00", "validation": {"whatif_ready": False},
          "dam": {**STATE["dam"], "storage_mcm": 725.85, "inflow_mcm": 10.33},
          "scenario_inputs": {"curves7": {"upper": [593.0] * 7, "lower": [204.0] * 7, "dates": ["2026-10-%02d" % d for d in range(6, 13)]},
                              "normal_mcm": 710.0, "max_mcm": 900.0, "release_cap": 25.0, "release_max_seen": 24.36}}
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st)
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    three = ";".join(",".join([str(v)] * 7) for v in (12, 14, 16))
    out = json.loads(api.impact_scenarios(Req(tok), "kaeng-krachan", release=three, diversion_cms=None).body)
    assert sorted(p["release"][0] for p in out["plans"] if p["kind"] == "custom") == [12.0, 14.0, 16.0]
    with pytest.raises(HTTPException) as e:
        api.impact_scenarios(Req(tok), "kaeng-krachan", release=three + ";" + ",".join(["18"] * 7), diversion_cms=None)
    assert e.value.status_code == 422
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_scenarios.py tests/test_impact_auth.py -k "grid_ladder or equal_to_todays or three_custom"`
Expected: FAIL — `TypeError: compare() got an unexpected keyword argument 'customs'`.

- [ ] **Step 3: Implement**

In `src/floodwatch/scenarios.py`, before `compare`:

```python
RUNG = 2.0  # the release ladder's step (ล้าน ลบ.ม./วัน): 0, 2, 4 … up to the search cap (D-110)


def ladder_ids(rows: list[dict], max_release: float, step: float = RUNG) -> list[str]:
    """The ids of the constant plans at 0, step, 2·step … ≤ max_release; today's 'hold' stands in when it sits on a rung."""
    out = []
    for k in range(int(max_release // step) + 1):
        r = round(k * step, 2)
        row = next((x for x in rows if x["kind"] in ("constant", "hold") and len(set(x["release"])) == 1
                    and abs(x["release"][0] - r) < 1e-9), None)
        if row:
            out.append(row["id"])
    return out
```

In `compare`, change the signature parameter `custom: list[float] | None = None` to `customs: list[list[float]] | None = None`, and replace

```python
    if custom:
        plans.append({"kind": "custom", "release": [round(float(x), 2) for x in custom]})
```

with

```python
    for c in customs or []:  # up to three of the session's own plans, newest first (D-110)
        plans.append({"kind": "custom", "release": [round(float(x), 2) for x in c]})
```

Replace the block from `show_ids = …` to the end of its `for` loop (the one that builds `show`) with:

```python
    rung_ids = ladder_ids(rows, max_release)
    pick_ids = list(dict.fromkeys(v for v in best.values() if v))
    show_ids = [r["id"] for r in rows if r["kind"] in ("hold", "custom")] + [opt["id"]] + pick_ids + rung_ids
    reach_km = state.get("reach_km") or {}
    seen, show = set(), []
    for rid in show_ids:
        if not rid or rid in seen:
            continue
        seen.add(rid)
        r = next(x for x in rows if x["id"] == rid)
        roles = (["star"] if rid == opt["id"] else []) + (["today"] if r["kind"] == "hold" else []) + \
                (["custom"] if r["kind"] == "custom" else []) + (["pick"] if rid in pick_ids else []) + \
                (["ladder"] if rid in rung_ids else [])
        cells = day_cells(r["downstream"], margin_req, reach_km, days)
        detail = outside_detail(r["downstream"], state["points"])
        down = r["downstream"] if roles != ["ladder"] else {  # ladder rungs travel light: margins, flows, flags
            c: [{k: v for k, v in x.items() if k not in ("level", "overflow")} for x in xs] for c, xs in r["downstream"].items()}
        km = [d["km"] for d in cells]
        show.append({**r, "downstream": down, "roles": roles, "label": short_label(r), "days": cells,
                     "km_max": max(km, default=0.0), "km_days": [d + 1 for d, k in enumerate(km) if k > 0],
                     "outside_detail": detail, "outside_any": bool(detail),
                     "best_for": [k for k in EFFECT_KEYS if best[k] == rid], "optimal": rid == opt["id"],
                     "feasible": any(f["id"] == rid for f in feas)})
```

In the returned dict, after `"plans": show,` add:

```python
            "ladder": rung_ids, "picks": pick_ids, "reach_km": reach_km, "places": state.get("places") or {},
```

In `src/floodwatch/api/__init__.py`, in `_impact_compare`, replace the `custom = None … 422` block with:

```python
    customs = None
    if release:
        customs = []
        for part in release.split(";"):
            try:
                vals = [float(x) for x in part.split(",")]
            except ValueError:
                raise HTTPException(422, "release: 7 numbers, ล้าน ลบ.ม./วัน")
            if len(vals) != 7 or any(not (0 <= x <= 200) for x in vals):
                raise HTTPException(422, "release: 7 numbers between 0 and 200")
            customs.append(vals)
        if len(customs) > 3:
            raise HTTPException(422, "release: at most 3 plans")
```

and in `build()` pass `customs=customs` instead of `custom=custom`. On `impact_scenarios` and `impact_explain` change `release: str | None = Query(None, max_length=200)` to `max_length=400`.

- [ ] **Step 4: Run to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_scenarios.py tests/test_impact_auth.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/scenarios.py src/floodwatch/api/__init__.py tests/test_scenarios.py tests/test_impact_auth.py
git commit -m "scenarios: the comparison carries the grid — a release ladder (every 2 ล้าน ลบ.ม./วัน), roles, short labels, day cells, outside detail, up to three own plans (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 5: River km per reach and villages along it

**Files:**
- Create: `research/2026-10-06_kk_reach_places.py` (+ its `.log` when run)
- Create: `src/floodwatch/data/kk_reach_places.json` (written by the script)
- Modify: `src/floodwatch/impact.py` (imports; `CASES["kaeng-krachan"]["places_file"]`; `reach_km`, `reach_places`; `build_state` adds `reach_km`, `places`)
- Test: `tests/test_impact.py`

**Interfaces:**
- Produces: `impact.reach_km(reaches: list[dict]) -> dict[str, float]`; `impact.reach_places(case: str) -> dict[str, list[dict]]`; case state keys `reach_km`, `places` (read by `scenarios.compare` via `state.get`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_impact.py`:

```python
def test_each_gauges_reach_has_its_river_length_in_km():
    line = [[[13.0, 99.0 + 0.01 * k] for k in range(26)]]  # ~1.08 km per step along 13°N
    pts = [{"code": "A", "lat": 13.0, "lon": 99.02}, {"code": "B", "lat": 13.0, "lon": 99.11}]
    km = impact.reach_km(impact.river_reaches(line, pts, max_km=10.0))
    assert set(km) == {"A", "B"} and 7.0 < km["A"] < 8.0 and 13.5 < km["B"] < 14.5  # 7 and 13 steps of ~1.08 km
    assert impact.reach_km([]) == {}


def test_villages_along_each_reach_come_from_the_built_file_and_a_case_without_one_has_none():
    places = impact.reach_places("kaeng-krachan")
    assert set(places) <= {"B.18", "B.10", "B.16", "B.15", "PCH001"} and places
    for code, items in places.items():
        assert items and all(set(x) == {"village", "amphoe"} for x in items)
        assert all(not (x["amphoe"] or "").startswith("อำเภอ") for x in items)  # the prefix is stripped
    assert impact.reach_places("no-such-case") == {}
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_impact.py -k "reach_has or villages_along"`
Expected: FAIL — `AttributeError: module 'floodwatch.impact' has no attribute 'reach_km'`.

- [ ] **Step 3: Implement the loader and km**

In `src/floodwatch/impact.py` add to the imports at the top:

```python
import json
from pathlib import Path
```

In `CASES["kaeng-krachan"]` add the key `"places_file": "kk_reach_places.json",`.

After `clip_onwr`:

```python
def reach_km(reaches: list[dict]) -> dict:
    """km of river in each gauge's reach (the pieces river_reaches gives it), for a plan's 'km near the bank' (D-110)."""
    tot: dict = {}
    for r in reaches or []:
        line = r.get("line") or []
        tot[r["code"]] = tot.get(r["code"], 0.0) + sum(
            _km({"lat": a[0], "lon": a[1]}, {"lat": b[0], "lon": b[1]}) for a, b in zip(line, line[1:]))
    return {c: round(v, 1) for c, v in tot.items()}


PLACES_DIR = Path(__file__).parent / "data"


def reach_places(case: str) -> dict:
    """Villages and อำเภอ along each gauge's reach (OpenStreetMap via Nominatim, built once by
    research/2026-10-06_kk_reach_places.py; D-110): {code: [{"village", "amphoe"}]}; {} when the case has no file."""
    name = (CASES.get(case) or {}).get("places_file")
    if not name:
        return {}
    try:
        return json.loads((PLACES_DIR / name).read_text(encoding="utf-8")).get("reaches") or {}
    except (OSError, ValueError):
        return {}
```

In `build_state`'s returned dict replace `"river_reaches": river_reaches(rl, points),` with:

```python
            "river_reaches": (rr := river_reaches(rl, points)), "reach_km": reach_km(rr), "places": reach_places(case),
```

- [ ] **Step 4: Write the build script**

Create `research/2026-10-06_kk_reach_places.py`:

```python
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
```

- [ ] **Step 5: Run the build (≈ 150 calls, ≈ 4 minutes)**

Run: `cd /root/flood2026 && PYTHONPATH=src python3 research/2026-10-06_kk_reach_places.py > research/2026-10-06_kk_reach_places.log 2>&1; tail -8 research/2026-10-06_kk_reach_places.log`
Expected: one line per reach code (B.18, B.10, B.16, B.15, PCH001) with sample counts and `wrote …/kk_reach_places.json`. Open the JSON and check that village names are Thai and amphoe names carry no "อำเภอ" prefix. If the host cannot reach the database read-only (`db.connect_readonly` fails outside the containers), run it inside the worker image instead: `docker compose run --rm --no-deps -v "$PWD:/repo" -w /repo -e PYTHONPATH=src worker python research/2026-10-06_kk_reach_places.py > research/2026-10-06_kk_reach_places.log 2>&1`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q tests/test_impact.py tests/test_research_quota.py`
Expected: PASS (the research guard passes: the script does not call Open-Meteo).

- [ ] **Step 7: Commit**

```bash
git add src/floodwatch/impact.py tests/test_impact.py research/2026-10-06_kk_reach_places.py research/2026-10-06_kk_reach_places.log src/floodwatch/data/kk_reach_places.json
git commit -m "impact: river km per gauge's reach and the villages along it (OpenStreetMap, built once into a data file; D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 6: The executive brief, the two-plan comparison and the officials' voice

**Files:**
- Modify: `src/floodwatch/explain.py` (QUESTIONS gets `brief` and `compare`; `prompt`/`gist` take `system` and `checker`; new `OFFICIAL`, `ITEM_MAX`, `day_range`, `outside_short`, `check_item`, `brief`, `compare_lines`, `retell_items`)
- Test: `tests/test_explain_more.py`

**Interfaces:**
- Consumes: plan fields from Task 4 (`label`, `days`, `km_max`, `outside_detail`, `outside_any`).
- Produces: `explain.brief(cmp) -> list[str]`; `explain.compare_lines(cmp, a: dict, b: dict) -> tuple[list[str], str]`; `explain.retell_items(lines, system=OFFICIAL) -> list[str | None]`; `explain.gist(q, lines, story=None, system=None, checker=None)`; `explain.check_item(text, own) -> list[str]`; `explain.OFFICIAL`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_explain_more.py`:

```python
def _grid_cmp():
    from test_scenarios import _r7_state
    from floodwatch import scenarios as sc
    st = _r7_state()
    st["dam"].update({"name_th": "แก่งกระจาน", "dam_date": "2026-10-06", "storage_mcm": 725.0, "storage_pct": 102.1, "inflow_mcm": 10.3})
    st["reach_km"] = {"B.18": 62.4, "B.10": 45.8, "B.16": 11.4, "B.15": 21.0}
    cmp = sc.compare(st, inflow_today=10.3, upper=[593.0] * 7, lower=[204.0] * 7, normal=710.0, max_release=24.0, customs=[[20.0] * 7])
    cmp.update({"dam": st["dam"], "built_at": "2026-10-06T12:06:24+00:00"})
    return cmp


def test_the_brief_is_short_bullets_with_the_engines_numbers_and_the_outside_label():
    from floodwatch import explain
    cmp = _grid_cmp()
    lines = explain.brief(cmp)
    assert 4 <= len(lines) <= 8 and all(len(x) <= explain.ITEM_MAX for x in lines)
    text = "\n".join(lines)
    assert text.startswith("สถานการณ์:") and "แก่งกระจาน" in text and "725" in text
    assert any(x.startswith(("★ แผนตามเกณฑ์:", "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์")) for x in lines)
    assert any(x.startswith("ทางเลือก") for x in lines) and "ไม่ใช่ประกาศทางการ" in lines[-1]
    star = next(p for p in cmp["plans"] if p["optimal"])
    if star["outside_any"]:
        assert any(x.startswith("⚠ นอกช่วงข้อมูล") and "เคยวัดสูงสุด" in x for x in lines)
    assert "ปลอดภัย" not in text and "ควร" not in text


def test_two_plans_are_compared_by_their_differences_without_a_verdict():
    from floodwatch import explain
    cmp = _grid_cmp()
    star = next(p for p in cmp["plans"] if p["optimal"])
    hold = next(p for p in cmp["plans"] if p["kind"] == "hold")
    lines, story = explain.compare_lines(cmp, hold, star)
    assert lines[0] == f"{hold['label']} เทียบกับ {star['label']}" and any(x.startswith("อ่างวันที่ 7:") for x in lines)
    assert not set(explain._NUM.findall(story)) - set(explain._NUM.findall("\n".join(lines)))  # the story adds no number
    assert "ดีกว่า" not in story and "ปลอดภัย" not in story


def test_ai_items_replace_only_the_lines_they_retell_faithfully(monkeypatch):
    from floodwatch import ai, explain
    explain._cache.clear()
    monkeypatch.setenv("AI_EXPLAIN", "1")
    lines = ["สถานการณ์: อ่างเขื่อนแก่งกระจาน 725 ล้าน ลบ.ม. (102 %)", "ข้อมูล ชป. 2026-10-06 · ไม่ใช่ประกาศทางการ"]
    monkeypatch.setattr(ai, "run", lambda *a, **k: "1) ขณะนี้อ่างเขื่อนแก่งกระจานมีน้ำ 725 ล้าน ลบ.ม. หรือ 102 %\n2) ข้อมูล ชป. 2026-10-07 ปลอดภัย")
    got = explain.retell_items(lines)
    assert got[0] and "725" in got[0] and got[1] is None  # item 2 added a date and a verdict: the rule line stays
    monkeypatch.setenv("AI_EXPLAIN", "0")
    explain._cache.clear()
    assert explain.retell_items(lines) == [None, None]


def test_station_codes_in_the_rule_line_do_not_make_an_ai_line_foreign():
    from floodwatch import explain
    own = "ห่างตลิ่งต่ำสุด 1.73 ม. (PCH001)"
    assert explain.check_item("จุดที่ห่างตลิ่งน้อยที่สุดคือ PCH001 ที่ 1.73 ม.", own) == []
    assert "not Thai" in explain.check_item("lowest margin at PCH001 1.73", own)
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_explain_more.py -k "brief or compared or ai_items or station_codes"`
Expected: FAIL — `AttributeError: module 'floodwatch.explain' has no attribute 'brief'`.

- [ ] **Step 3: Implement**

In `src/floodwatch/explain.py`:

1. Add to `QUESTIONS`: `"brief": "สรุปเสนอผู้บริหาร", "compare": "เทียบสองแผน"`.

2. Change `prompt` and `gist` signatures and bodies:

```python
def prompt(q: str, lines: list[str], story: str | None = None, system: str | None = None) -> tuple[list[dict], str]:
    """The GLM messages for a retelling, and the rule text it is checked against (one place for app and validation)."""
    rule = "\n".join(([f"บทสรุป: {story}"] if story else []) + lines)
    return ([{"role": "system", "content": system or SYSTEM},
             {"role": "user", "content": f"คำถามของผู้ใช้: {QUESTIONS.get(q, q)}\nข้อมูล:\n{rule}"}], rule)
```

and in `gist`: signature `def gist(q: str, lines: list[str], story: str | None = None, system: str | None = None, checker=None) -> str | None:`, `messages, rule = prompt(q, lines, story, system)`, and replace `if not check(text, rule):` with `if not (checker or check)(text, rule):`.

3. After `gist`, before the impact section, add:

```python
# --- impact tab for officials: the executive brief and the two-plan comparison (D-110) --------------------------------
OFFICIAL = ("คุณช่วยเรียบเรียงข้อมูลการระบายน้ำจากเขื่อนให้เจ้าหน้าที่และผู้บริหารอ่าน ภาษาทางการที่กระชับ เป็นกลาง ชัดเจน "
            "ใช้เฉพาะข้อมูลที่ให้ ห้ามเพิ่มหรือเปลี่ยนตัวเลข ห้ามเพิ่มข้อมูลใหม่ ห้ามแนะนำ ห้ามตัดสินใจแทน ห้ามบอกว่าแผนใดดีกว่า "
            "ห้ามใช้คำว่า ปลอดภัย ไม่ท่วม แน่นอน ควร อันตราย วิกฤต ตอบเป็นภาษาไทยเท่านั้น ไม่ใส่อีโมจิ ไม่ต้องใส่ครับ ค่ะ หรือคะ "
            "ตอบเฉพาะข้อความ")
ITEM_MAX = 160  # characters in one brief bullet (GUIDELINES §6c-9: no paragraph over 160)


def check_item(text: str, own: str) -> list[str]:
    """`check` for officials' lines: Latin letters are allowed when they are the station codes of the rule line itself."""
    issues = check(text, own)
    if "not Thai" in issues and all(w in own for w in re.findall(r"[A-Za-z]{3,}", text)):
        issues.remove("not Thai")
    return issues


def day_range(days: list[int]) -> str:
    """[1, 2, 3, 5] → '1–3, 5'."""
    out, start, prev = [], None, None
    for d in sorted(days):
        if start is None:
            start = prev = d
        elif d == prev + 1:
            prev = d
        else:
            out.append(f"{start}–{prev}" if prev > start else f"{start}")
            start = prev = d
    if start is not None:
        out.append(f"{start}–{prev}" if prev > start else f"{start}")
    return ", ".join(out)


def outside_short(p: dict) -> str:
    """'B.18 256/143, B.10 192/86 ลบ.ม./วิ (แผน/เคยวัดสูงสุด)' — the outside label in one short line (D-110)."""
    parts = [f"{o['code']} {o['flow_max']:.0f}/{o['qmax']:.0f}" for o in p.get("outside_detail") or []
             if o.get("flow_max") is not None and o.get("qmax") is not None]
    return ", ".join(parts) + " ลบ.ม./วิ (แผน/เคยวัดสูงสุด)" if parts else ""


def _m(x) -> str:
    return "–" if x is None else f"{x:.2f}"


def _plan_facts(p: dict) -> str:
    e = p["effects"]
    worst = min((d for d in p.get("days") or [] if d.get("worst_margin") is not None), key=lambda d: d["worst_margin"], default=None)
    km = p.get("km_max") or 0
    return (f"อ่างวันที่ 7 {e['storage_end']:.0f} · ห่างตลิ่งต่ำสุด {_m(e.get('worst_margin_min'))} ม."
            + (f" ({worst['worst_code']})" if worst else "") + (f" · ใกล้/เกินตลิ่ง {km:.0f} กม." if km else ""))


def _ict(iso: str | None) -> str:
    from floodwatch.impact import TH_MONTHS
    if not iso:
        return "–"
    t = dt.datetime.fromisoformat(iso).astimezone(dt.timezone(dt.timedelta(hours=7)))
    return f"{t.day} {TH_MONTHS[t.month - 1]} {t:%H:%M} น."


def brief(cmp: dict) -> list[str]:
    """The executive brief (owner 2026-10-06: plain bullets, copyable; D-110): situation, the ★ by the stated rule, today's
    plan and one more alternative, what is outside the river data, the downstream model's limit, the data time. Numbers
    from the engine only; the ★ is the rule's, never advice."""
    from floodwatch.scenarios import EFFECT_KEYS, EFFECT_TH
    dam = cmp.get("dam") or {}
    name = f"เขื่อน{dam.get('name_th') or ''}"
    plans = cmp.get("plans") or []
    by = {p["id"]: p for p in plans}
    star = next((p for p in plans if p.get("optimal")), None)
    hold = next((p for p in plans if p.get("kind") == "hold"), None)
    st0, rel, inf = dam.get("storage_mcm"), dam.get("released_mcm"), dam.get("inflow_mcm")
    up0 = (cmp.get("upper") or [None])[0]
    lines = []
    if st0 is not None:
        pos = ("" if up0 is None else f" เหนือเส้นควบคุมบน {st0 - up0:.0f}" if st0 > up0 else f" ต่ำกว่าเส้นควบคุมบน {up0 - st0:.0f}")
        lines.append(f"สถานการณ์: อ่าง{name} {st0:.0f} ล้าน ลบ.ม." + (f" ({dam['storage_pct']:.0f} %)" if dam.get("storage_pct") is not None else "")
                     + pos + (f" · ระบาย {rel:.1f} · ไหลเข้า {inf:.1f} ล้าน ลบ.ม./วัน" if rel is not None and inf is not None else ""))
    opt = cmp.get("optimal") or {}
    if star:
        lines.append(("★ แผนตามเกณฑ์: " if opt.get("constraints_met") else "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์ ใกล้เคียงที่สุด: ")
                     + f"{star.get('label') or plan_words(star)} → {_plan_facts(star)}")
    if hold and hold is not star:
        lines.append(f"ทางเลือก (คงเท่าวันนี้): {hold.get('label') or plan_words(hold)} → {_plan_facts(hold)}")
    alt, goal = None, None
    for k in EFFECT_KEYS:
        p = by.get((cmp.get("best_for") or {}).get(k))
        if p and p is not star and p is not hold:
            alt, goal = p, k
            break
    if alt:
        lines.append(f"ทางเลือก ({EFFECT_TH[goal]}): {alt.get('label') or plan_words(alt)} → {_plan_facts(alt)}")
    for p in (star, hold, alt):
        if p and p.get("outside_any"):
            lines.append(f"⚠ นอกช่วงข้อมูล ({p.get('label') or plan_words(p)}): {outside_short(p)}")
    ds = cmp.get("downstream") or {}
    mae = ds.get("mae_cm") or {}
    d1 = max((v[0] for v in mae.values() if v and v[0] is not None), default=None)
    d7 = max((v[-1] for v in mae.values() if v and v[-1] is not None), default=None)
    lines.append(f"ข้อจำกัด: ระดับท้ายน้ำทดสอบย้อนหลังแล้ว คลาดเคลื่อนเฉลี่ย ±{d1}–{d7} ซม. (วันที่ 1–7) ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์"
                 if ds.get("method") == "hybrid" and d1 is not None and d7 is not None
                 else "ข้อจำกัด: ระดับท้ายน้ำยังไม่ผ่านการทดสอบย้อนหลัง ใช้เทียบระหว่างแผนเท่านั้น")
    lines.append(f"ข้อมูล ชป. {dam.get('dam_date') or '–'} · คำนวณ {_ict(cmp.get('built_at'))} · ไม่ใช่ประกาศทางการ")
    return lines


def compare_lines(cmp: dict, a: dict, b: dict) -> tuple[list[str], str]:
    """Plan a against plan b (D-110: '✨ เทียบกับแผน ★'): the differences the engine computed, no verdict."""
    ea, eb = a["effects"], b["effects"]
    la, lb = a.get("label") or plan_words(a), b.get("label") or plan_words(b)
    diff = ea["storage_end"] - eb["storage_end"]
    lines = [f"{la} เทียบกับ {lb}",
             f"อ่างวันที่ 7: {ea['storage_end']:.0f} เทียบ {eb['storage_end']:.0f} ล้าน ลบ.ม. (ต่างกัน {diff:+.0f})",
             f"ห่างตลิ่งต่ำสุด: {_m(ea.get('worst_margin_min'))} เทียบ {_m(eb.get('worst_margin_min'))} ม.",
             f"แม่น้ำใกล้/เกินตลิ่งมากสุด: {a.get('km_max') or 0:.0f} เทียบ {b.get('km_max') or 0:.0f} กม.",
             f"เปลี่ยนอัตราระบายวันละไม่เกิน: {ea['ramp_max']:.1f} เทียบ {eb['ramp_max']:.1f} ล้าน ลบ.ม."]
    for p, label in ((a, la), (b, lb)):
        if p.get("outside_any"):
            lines.append(f"⚠ นอกช่วงข้อมูล ({label}): {outside_short(p)}")
    story = (f"{la} เหลือน้ำในอ่างวันที่ 7 {'มากกว่า' if diff > 0 else 'น้อยกว่า'} {lb} {abs(diff):.0f} ล้าน ลบ.ม. " if abs(diff) >= 1
             else f"{la} และ {lb} เหลือน้ำในอ่างวันที่ 7 ใกล้เคียงกัน ")
    story += f"จุดที่ห่างตลิ่งน้อยที่สุด {_m(ea.get('worst_margin_min'))} เทียบ {_m(eb.get('worst_margin_min'))} ม."
    if a.get("outside_any") or b.get("outside_any"):
        story += " บางวันน้ำมากกว่าที่สถานีเคยวัดได้ ระดับท้ายน้ำของวันนั้นจึงมาจากการต่อเส้นโค้งออกไป"
    return lines, story


def retell_items(lines: list[str], system: str = OFFICIAL) -> list[str | None]:
    """GLM rewords each line in the officials' voice (D-110): one call, numbered lines back; a line is used only when it
    passes `check_item` against its own rule line and stays ≤ ITEM_MAX, else None (the rule line stays). AI off, failed or
    capped → all None."""
    if os.environ.get("AI_EXPLAIN", "1") != "1" or not lines:
        return [None] * len(lines)
    key = ("items", system, tuple(lines))
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[1] < (CACHE_H * 3600 if any(hit[0]) else 120):
            return list(hit[0])
        if _calls_today() >= DAILY_CAP:
            return [None] * len(lines)
        _count["n"] += 1
    messages = [{"role": "system", "content": system + " เขียนใหม่ทุกข้อ ข้อละหนึ่งประโยค ขึ้นต้นด้วยเลขข้อเดิม เช่น 1) …"},
                {"role": "user", "content": "\n".join(f"{k}) {t}" for k, t in enumerate(lines, 1))}]
    try:
        text = ai.run(messages, max_tokens=900, timeout=25)
    except Exception:
        text = None
    got: list[str | None] = [None] * len(lines)
    for line in (text or "").splitlines():
        m = re.match(r"\s*(\d+)\s*[).:]\s*(.+)", line)
        if not m:
            continue
        k = int(m.group(1)) - 1
        if 0 <= k < len(lines) and got[k] is None:
            t = tidy(m.group(2).strip())
            if len(t) <= ITEM_MAX and not check_item(t, lines[k]):
                got[k] = t
    with _lock:
        _cache[key] = (got, now)
    return got
```

- [ ] **Step 4: Run to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_explain_more.py tests/test_explain.py tests/test_scenarios.py tests/test_api_explain.py`
Expected: PASS (the existing ✨ tests still pass: `gist`'s defaults are unchanged).

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/explain.py tests/test_explain_more.py
git commit -m "explain: the executive brief and the two-plan comparison for officials — rules write every number, GLM may reword line by line, checked per line (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 7: Type a plan in Thai (`plan_parse.py`)

**Files:**
- Create: `src/floodwatch/plan_parse.py`
- Test: `tests/test_plan_parse.py`

**Interfaces:**
- Produces: `plan_parse.parse_rules(text: str, today: float) -> list[float] | None`; `plan_parse.parse_ai(text: str, today: float) -> list[float] | None`; `plan_parse.parse(text: str, today: float) -> tuple[list[float], str] | None` (`"rules"` or `"ai"`); `plan_parse.MAX = 200.0`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plan_parse.py`:

```python
"""Type a plan in Thai (owner 2026-10-06; D-110): rules first, GLM only when they cannot read it; 7 numbers that only fill
the boxes. Values above 200 are refused, never clipped."""
import pytest

from floodwatch import ai, plan_parse as pp

CASES = [
    ("ระบาย 15 สามวันแล้วลดเหลือ 10", [15, 15, 15, 10, 10, 10, 10]),
    ("15 ล้าน ลบ.ม./วัน 3 วันแรก แล้วเพิ่มเป็น 20", [15, 15, 15, 20, 20, 20, 20]),
    ("คงเดิม", [10.63] * 7),
    ("ระบายเท่าวันนี้", [10.63] * 7),
    ("ทยอยลดจาก 20 เป็น 8", [20, 18, 16, 14, 12, 10, 8]),
    ("ทยอยเพิ่ม 10 ถึง 16", [10, 11, 12, 13, 14, 15, 16]),
    ("12", [12] * 7),
    ("ระบาย 18 ทุกวัน", [18] * 7),
    ("10 12 14 16 18 20 22", [10, 12, 14, 16, 18, 20, 22]),
    ("๑๕ สองวันแรก แล้วเหลือ ๘", [15, 15, 8, 8, 8, 8, 8]),
    ("21.5 คงที่ 7 วัน", [21.5] * 7),
    ("10,12,14,16,18,20,22", [10, 12, 14, 16, 18, 20, 22]),
]


@pytest.mark.parametrize("text,want", CASES)
def test_the_rules_read_common_thai_phrasings(text, want):
    assert pp.parse_rules(text, today=10.63) == [float(x) for x in want]


@pytest.mark.parametrize("text", ["ระบายเยอะ ๆ", "300", "10 12 14", "", "   "])
def test_the_rules_refuse_what_they_cannot_read_and_values_above_200(text):
    assert pp.parse_rules(text, today=10.63) is None


def test_ai_reads_the_rest_and_its_answer_is_only_seven_valid_numbers(monkeypatch):
    monkeypatch.setenv("AI_EXPLAIN", "1")
    monkeypatch.setattr(ai, "run", lambda *a, **k: 'แผน: {"release": [12, 12, 14, 14, 16, 16, 16]}')
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่มทีละสองทุกสองวัน", today=10.63) == ([12.0, 12.0, 14.0, 14.0, 16.0, 16.0, 16.0], "ai")
    monkeypatch.setattr(ai, "run", lambda *a, **k: '{"release": [12, 12, 14]}')
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่ม", today=10.63) is None
    monkeypatch.setattr(ai, "run", lambda *a, **k: '{"release": [500, 12, 14, 14, 16, 16, 16]}')
    assert pp.parse("เริ่ม 500 แล้วค่อย ๆ ลด", today=10.63) is None
    monkeypatch.setattr(ai, "run", lambda *a, **k: "ขอโทษ อ่านไม่ได้")
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่ม", today=10.63) is None
    assert pp.parse("ระบาย 15 สามวันแล้วลดเหลือ 10", today=10.63)[1] == "rules"


def test_without_ai_only_the_rules_read(monkeypatch):
    monkeypatch.setenv("AI_EXPLAIN", "0")
    monkeypatch.setattr(ai, "run", lambda *a, **k: pytest.fail("AI called while off"))
    assert pp.parse("เริ่ม 12 แล้วค่อย ๆ เพิ่ม", today=10.63) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_plan_parse.py`
Expected: FAIL — `ImportError: cannot import name 'plan_parse'`.

- [ ] **Step 3: Implement**

Create `src/floodwatch/plan_parse.py`:

```python
"""Type a plan in Thai (owner 2026-10-06; D-110): seven daily releases (ล้าน ลบ.ม./วัน) from text such as
"ระบาย 15 สามวันแล้วลดเหลือ 10". Rules first; GLM only when the rules cannot read it, and its answer is only 7 numbers that
fill the boxes for the engineer to check — nothing is computed until they press คำนวณ (D-022: AI never decides). Values
above MAX are refused, never clipped. The text is never logged or stored."""
from __future__ import annotations

import json
import os
import re

DAYS = 7
MAX = 200.0  # the custom plan's own bound (the API accepts 0–200)
TH_NUM = {"หนึ่ง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5, "หก": 6, "เจ็ด": 7}
_TH_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
N = r"(\d+(?:\.\d+)?)"
UNIT = r"(?:ล้าน\s*(?:ลบ\.?\s*ม\.?)?\s*(?:/\s*วัน)?\s*)?"
CHANGE = re.compile(r"เพิ่ม|ลด|แล้ว|ทีละ|ค่อย|จากนั้น|ต่อด้วย")  # words that say the release changes over the week


def _norm(text: str) -> str:
    t = (text or "").translate(_TH_DIGITS).replace(",", " ")
    for word, n in TH_NUM.items():
        t = re.sub(word + r"(?=\s*วัน)", str(n), t)
    return re.sub(r"\s+", " ", t).strip()


def _ok(vals) -> list[float] | None:
    if vals is None or len(vals) != DAYS or any(v is None or not (0 <= v <= MAX) for v in vals):
        return None
    return [round(float(v), 2) for v in vals]


def parse_rules(text: str, today: float) -> list[float] | None:
    """Day by day (7 numbers), a ramp ("ทยอย… จาก A เป็น B"), two steps ("A N วัน(แรก) แล้ว… B"), a constant (one number),
    or today's release ("คงเดิม", "เท่าวันนี้"); else None."""
    t = _norm(text)
    if not t:
        return None
    m = re.search(r"ทยอย\S*\s*(?:จาก\s*)?" + N + r"\s*" + UNIT + r"(?:เป็น|ถึง|ไป|→|-)\s*" + N, t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return _ok([a + (b - a) * k / (DAYS - 1) for k in range(DAYS)])
    m = re.search(N + r"\s*" + UNIT + r"(\d)\s*วัน(?:แรก)?\s*(?:แล้ว|จากนั้น|ต่อด้วย)?\s*(?:ค่อย)?\s*(?:ลด|เพิ่ม)?\s*(?:ลง|ขึ้น)?\s*"
                  r"(?:เหลือ|เป็น|ไป)?\s*" + N, t)
    if m:
        a, n, b = float(m.group(1)), int(m.group(2)), float(m.group(3))
        if 1 <= n < DAYS:
            return _ok([a] * n + [b] * (DAYS - n))
    nums = [float(x) for x in re.findall(N, re.sub(r"\d+\s*วัน", " ", t))]
    if len(nums) == DAYS:
        return _ok(nums)
    if len(nums) == 1 and not CHANGE.search(t):  # "เริ่ม 12 แล้วค่อย ๆ เพิ่ม…" is not a constant 12: leave it to the AI
        return _ok([nums[0]] * DAYS)
    if not nums and re.search(r"คงเดิม|เท่าเดิม|เท่าวันนี้", t):
        return _ok([round(today, 2)] * DAYS)
    return None


SYSTEM = ("แปลงแผนการระบายน้ำจากเขื่อนที่ผู้ใช้พิมพ์ เป็นปริมาณระบายรายวัน 7 วัน หน่วยล้าน ลบ.ม./วัน "
          "ตอบเป็น JSON เท่านั้น รูปแบบ {\"release\": [ตัวเลข 7 ตัว]} ถ้าอ่านไม่ได้หรือไม่แน่ใจ ตอบ {\"release\": null} ห้ามอธิบาย")


def parse_ai(text: str, today: float) -> list[float] | None:
    """GLM reads what the rules could not; only a JSON list of 7 numbers within 0–MAX is accepted."""
    if os.environ.get("AI_EXPLAIN", "1") != "1":
        return None
    from floodwatch import ai
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"วันนี้ระบาย {today:.2f} ล้าน ลบ.ม./วัน\nแผน: {(text or '')[:200]}"}]
    try:
        out = ai.run(messages, max_tokens=120, timeout=15)
    except Exception:
        return None
    m = re.search(r"\{.*\}", out or "", re.S)
    if not m:
        return None
    try:
        vals = json.loads(m.group(0)).get("release")
        return _ok([float(v) for v in vals]) if isinstance(vals, list) else None
    except (ValueError, TypeError, AttributeError):
        return None


def parse(text: str, today: float) -> tuple[list[float], str] | None:
    """(release, "rules" | "ai") or None."""
    vals = parse_rules(text, today)
    if vals:
        return vals, "rules"
    vals = parse_ai(text, today)
    return (vals, "ai") if vals else None
```

- [ ] **Step 4: Run to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_plan_parse.py`
Expected: PASS (12 phrasings, 5 refusals, AI and no-AI paths). If a phrasing fails, fix the pattern in `parse_rules`, not the test's expected plan.

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/plan_parse.py tests/test_plan_parse.py
git commit -m "impact: type a plan in Thai — rules read common phrasings, GLM only when they cannot, 7 numbers that only fill the boxes (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 8: API — brief, comparison and the parse endpoint

**Files:**
- Modify: `src/floodwatch/api/__init__.py:781-792` (`impact_explain`), add `_plan_by_release`, `_impact_parse_limiter`, `ImpactParse`, `impact_parse`
- Test: `tests/test_impact_auth.py`

**Interfaces:**
- Consumes: `explain.brief`, `explain.compare_lines`, `explain.retell_items`, `explain.gist(..., system, checker)`, `explain.OFFICIAL`, `explain.check_item` (Task 6); `plan_parse.parse` (Task 7).
- Produces: `GET /api/impact/case/{id}/explain?q=brief` → `{"q", "lines", "ai"}`; `…&part=gist` → `{"items": [str | None]}`. `GET …/explain?q=compare&a=<7>&b=<7>` → `{"q", "question", "story", "lines", "ai"}`; `…&part=gist` → `{"gist"}`. `POST /api/impact/case/{id}/parse` `{"text"}` → `{"release": [7], "by"}` | 422 | 429. Python: `api.impact_explain(request, case_id, release, diversion_cms, part, q, a=None, b=None)`, `api.impact_parse(request, case_id, body: ImpactParse)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_impact_auth.py`:

```python
def _explain_state():
    from test_scenarios import _r7_state
    st = {**_r7_state(), "case": "kaeng-krachan", "built_at": "2026-10-06T12:06:24+00:00", "validation": {"whatif_ready": False},
          "scenario_inputs": {"curves7": {"upper": [593.0] * 7, "lower": [204.0] * 7, "dates": ["2026-10-%02d" % d for d in range(7, 14)]},
                              "normal_mcm": 710.0, "max_mcm": 900.0, "release_cap": 24.0, "release_max_seen": 24.36}}
    st["dam"] = {**st["dam"], "name_th": "แก่งกระจาน", "dam_date": "2026-10-06", "storage_mcm": 725.0, "storage_pct": 102.1, "inflow_mcm": 10.3}
    return st


def test_brief_and_compare_need_login_and_carry_the_engines_lines(monkeypatch):
    monkeypatch.setenv("AI_EXPLAIN", "0")
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    st = _explain_state()
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st if key == "impact_kaeng_krachan" else {})
    with pytest.raises(HTTPException) as e:
        api.impact_explain(Req(), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="brief")
    assert e.value.status_code == 401
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    out = json.loads(api.impact_explain(Req(tok), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="brief").body)
    assert out["q"] == "brief" and out["lines"][0].startswith("สถานการณ์:") and out["ai"] is False
    items = json.loads(api.impact_explain(Req(tok), "kaeng-krachan", release=None, diversion_cms=None, part="gist", q="brief").body)
    assert items["items"] == [None] * len(out["lines"])  # AI off: every rule line stays
    a, b = ",".join(["10.8"] * 7), ",".join(["14"] * 7)
    c = json.loads(api.impact_explain(Req(tok), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="compare", a=a, b=b).body)
    assert c["q"] == "compare" and c["lines"][0].endswith("14.0 คงที่") and c["story"]
    with pytest.raises(HTTPException) as e:
        api.impact_explain(Req(tok), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="compare", a=a, b=None)
    assert e.value.status_code == 422


def test_compare_prefers_the_named_plan_over_its_custom_twin(monkeypatch):
    # Review Focus 4: today's release compared with itself is named "วันนี้", not "กำหนดเอง"
    monkeypatch.setenv("AI_EXPLAIN", "0")
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    st = _explain_state()
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": st if key == "impact_kaeng_krachan" else {})
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    today = ",".join(["10.8"] * 7)
    c = json.loads(api.impact_explain(Req(tok), "kaeng-krachan", release=None, diversion_cms=None, part=None, q="compare",
                                      a=today, b=",".join(["16"] * 7)).body)
    assert c["lines"][0].startswith("10.8 วันนี้")


def test_typed_plans_need_login_fill_seven_numbers_and_are_never_logged(monkeypatch, caplog):
    import logging
    monkeypatch.setenv("AI_EXPLAIN", "0")
    monkeypatch.setattr(api, "_impact_conf", lambda: (PW, SECRET))
    monkeypatch.setattr(api, "_impact_state", lambda key="impact_kaeng_krachan": {"dam": {"released_mcm": 10.63}})
    with pytest.raises(HTTPException) as e:
        api.impact_parse(Req(), "kaeng-krachan", api.ImpactParse(text="12"))
    assert e.value.status_code == 401
    tok = impact_auth.make_token(SECRET, PW, exp=4102444800)
    caplog.set_level(logging.DEBUG)
    out = json.loads(api.impact_parse(Req(tok), "kaeng-krachan", api.ImpactParse(text="ระบาย 15 สามวันแล้วลดเหลือ 10")).body)
    assert out == {"release": [15.0, 15.0, 15.0, 10.0, 10.0, 10.0, 10.0], "by": "rules"}
    assert "สามวัน" not in caplog.text
    with pytest.raises(HTTPException) as e:
        api.impact_parse(Req(tok), "kaeng-krachan", api.ImpactParse(text="ระบายเยอะ ๆ"))
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e:
        api.impact_parse(Req(tok), "no-such-case", api.ImpactParse(text="12"))
    assert e.value.status_code == 404
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose build worker && docker compose run --rm --no-deps worker pytest -q tests/test_impact_auth.py -k "brief_and_compare or custom_twin or typed_plans"`
Expected: FAIL — `TypeError: impact_explain() got an unexpected keyword argument 'a'` and `AttributeError: module 'floodwatch.api' has no attribute 'ImpactParse'`.

- [ ] **Step 3: Implement**

In `src/floodwatch/api/__init__.py`, replace `impact_explain` with:

```python
def _plan_by_release(cmp: dict, s: str) -> dict:
    """The plan with these 7 releases, the named one (★, today, a pick, a rung) before its custom twin (D-110)."""
    vals = [round(float(x), 2) for x in s.split(",")]
    same = [p for p in cmp.get("plans") or [] if p["release"] == vals]
    if not same:
        raise HTTPException(422, "plan not in the comparison")
    return next((p for p in same if p["kind"] != "custom"), same[0])


@app.get("/api/impact/case/{case_id}/explain", include_in_schema=False)
def impact_explain(request: Request, case_id: str, release: str | None = Query(None, max_length=400),
                   diversion_cms: float | None = Query(None, ge=0, le=2000), part: str | None = Query(None, max_length=8),
                   q: str | None = Query(None, max_length=16), a: str | None = Query(None, max_length=120),
                   b: str | None = Query(None, max_length=120)):
    """✨ for the scenarios (D-068, D-110): q=simple the story (GLM may retell it), q=brief the executive bullets (GLM may
    reword each, checked per line), q=compare plan a against plan b (7 releases each). The rules write every number; the
    AI never decides."""
    _impact_require(request)
    ai_on = os.environ.get("AI_EXPLAIN", "1") == "1" and ai.available()
    nostore = {"Cache-Control": "no-store"}
    if q == "brief":
        lines = explain.brief(_impact_compare(case_id, release, diversion_cms))
        if part == "gist":
            return JSONResponse({"items": explain.retell_items(lines)}, headers=nostore)
        return JSONResponse({"q": "brief", "question": explain.QUESTIONS["brief"], "lines": lines, "ai": ai_on}, headers=nostore)
    if q == "compare":
        if not a or not b:
            raise HTTPException(422, "a and b: 7 numbers each")
        cmp = _impact_compare(case_id, a + ";" + b, diversion_cms)  # both as rows of the same engine run
        lines, story = explain.compare_lines(cmp, _plan_by_release(cmp, a), _plan_by_release(cmp, b))
        if part == "gist":
            return JSONResponse({"gist": explain.gist("compare", lines, story, system=explain.OFFICIAL, checker=explain.check_item)},
                                headers=nostore)
        return JSONResponse({"q": "compare", "question": explain.QUESTIONS["compare"], "story": story, "lines": lines, "ai": ai_on},
                            headers=nostore)
    cmp = _impact_compare(case_id, release, diversion_cms)
    lines, story = explain.scenarios(cmp)
    if part == "gist":
        return JSONResponse({"gist": explain.gist("simple", lines, story)}, headers=nostore)
    return JSONResponse({"q": "simple", "question": explain.QUESTIONS["simple"], "story": story, "lines": lines, "ai": ai_on},
                        headers=nostore)


_impact_parse_limiter = impact_auth.LoginLimiter(max_failures=30, window_s=900)  # counts every try here


class ImpactParse(BaseModel):
    text: str = Field(..., min_length=1, max_length=200)


@app.post("/api/impact/case/{case_id}/parse", include_in_schema=False)
def impact_parse(request: Request, case_id: str, body: ImpactParse):
    """'Type a plan in Thai' (D-110): rules first, GLM only when they cannot read it; 7 numbers that only fill the boxes.
    The text arrives in the body (never in a URL or the access log) and is never logged or stored."""
    _impact_require(request)
    from floodwatch import impact, plan_parse
    if case_id not in impact.CASES:
        raise HTTPException(404, "unknown case")
    who = _client_hash(request)
    if not _impact_parse_limiter.allowed(who):
        return JSONResponse({"ok": False, "error": "too many tries, wait 15 minutes"}, status_code=429)
    _impact_parse_limiter.fail(who)
    today = float(((_impact_state(impact.state_key(case_id)).get("dam") or {}).get("released_mcm")) or 0.0)
    got = plan_parse.parse(body.text, today)
    if not got:
        raise HTTPException(422, "อ่านแผนนี้ไม่ได้")
    return JSONResponse({"release": got[0], "by": got[1]}, headers={"Cache-Control": "no-store"})
```

The existing `test_scenario_explain_needs_login_and_returns_the_story_and_lines` keeps passing (`q="simple"`).

- [ ] **Step 4: Run to verify they pass**

Run: `docker compose build worker && docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q`
Expected: the whole suite passes (461 + the new tests).

- [ ] **Step 5: Commit**

```bash
git add src/floodwatch/api/__init__.py tests/test_impact_auth.py
git commit -m "api: the executive brief, the two-plan comparison and a typed plan for /impact (login, POST body, 30 tries per 15 min; D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 9: The comparison grid in the case view (`impact.js`, `impact.css`)

**Files:**
- Modify: `web/impact.js` — `state` (line 30); `logout` (93–101); `renderCase` (276–298); `colorReaches` (424–445); the scenarios block (457–550: `EFFECT_TH`, `planWords` kept, `loadScenarios`, `scenariosHtml`; remove `heroCard` and `planRow`); `matrixHtml` (552–557)
- Modify: `web/impact.css` (append the grid block)
- Test: browser check in Task 13 (this task is UI; it is exercised after the deploy in Task 14). Syntax check here.

**Interfaces:**
- Consumes: the plan fields from Task 4 and `places` / `reach_km`.
- Produces (used by Tasks 10–12): `state.customs` (list of 7-number arrays, newest first, ≤ 3), `state.selPlan`, `state.day`; `customParam() -> string` ("release=…" or ""); `worstDay(p) -> int`; `dayRange(days) -> string`; `outsideText(p) -> string`; `villagesText(cmp, code) -> string`; `shortWhy(p) -> string`; `EFFECT_TH`, `EFFECT_ICON`; `bindGrid(sec, cmp, st)`; `aiMenuHtml()` (defined in Task 12; until then a stub returning `""`).

- [ ] **Step 1: State and logout**

Replace line 30:

```js
  const state = { authed: false, cases: [], dams: null, sel: "dams", kase: {}, loadedAt: 0, notice: "", customs: [], selPlan: null, day: null };
```

In `logout`, after `state.authed = false; state.dams = null; state.kase = {}; state.sel = "dams";` add:

```js
    state.customs = []; state.selPlan = null; state.day = null;
```

- [ ] **Step 2: The map follows the case on desktop**

In `renderCase`, replace

```js
    drawCase(st);
    loadScenarios(st, body, null);
```

with

```js
    drawCase(st);
    if (!narrow()) showCaseOnMap(st, false);  // the map follows the case, as a dam row pans it (D-110)
    loadScenarios(st, body);
```

- [ ] **Step 3: Replace the scenarios block**

Replace from `const EFFECT_TH = {` through the end of `planRow` (lines 458–550) with:

```js
  const EFFECT_TH = { city: "ปกป้องตัวเมือง", worst: "ห่างตลิ่งมากสุด", total: "ท่วมรวมน้อยสุด", dam: "ความปลอดภัยเขื่อน",
    curve: "กลับใต้เส้นควบคุมเร็ว", water: "เก็บน้ำไว้ใช้", warning: "เตือนล่วงหน้าได้" };
  const EFFECT_ICON = { city: "🏙️", worst: "🌊", total: "📏", dam: "🏞️", curve: "📉", water: "💧", warning: "⏱" };
  const CELL_TH = { ok: "รับน้ำได้", near: "ห่างตลิ่งน้อยกว่าความคลาดเคลื่อน", over: "เกินตลิ่ง", none: "ไม่มีข้อมูล" };
  const EFFECT_ROWS = [["city", "ห่างตลิ่งในเมืองต่ำสุด (ม.)", (e) => num(e.city_margin_min, 2)],
    ["worst", "ห่างตลิ่งต่ำสุดทุกจุด (ม.)", (e) => num(e.worst_margin_min, 2)],
    ["total", "เกินตลิ่งรวม (ม.·จุด·วัน)", (e) => num(e.overtop_sum, 2)],
    ["dam", "ปริมาตรสูงสุด (ล้าน ลบ.ม.) · วันเหนือปกติ", (e) => num(e.storage_peak, 0) + " · " + num(e.days_above_normal, 0)],
    ["curve", "กลับใต้เส้นควบคุมบน", (e) => (e.under_curve_day ? "วันที่ " + num(e.under_curve_day, 0) : "ไม่ใน 7 วัน")],
    ["water", "ปริมาตรวันที่ 7 (ล้าน ลบ.ม.)", (e) => num(e.storage_end, 0)],
    ["warning", "เปลี่ยนอัตราวันละไม่เกิน (ล้าน ลบ.ม.)", (e) => num(e.ramp_max, 1)]];

  function planWords(p) {
    const r = p.release, same = r.every((x) => x === r[0]);
    if (p.kind === "hold" || p.kind === "constant" || same) return num(r[0], 1) + " ล้าน ลบ.ม./วัน คงที่ 7 วัน" + (p.kind === "hold" ? " (เท่าวันนี้)" : "");
    if (p.kind === "ramp") return "ทยอย" + (r[6] > r[0] ? "เพิ่ม" : "ลด") + "จาก " + num(r[0], 1) + " เป็น " + num(r[6], 1) + " ล้าน ลบ.ม./วัน ใน 7 วัน";
    if (p.kind === "front") { const k = r.findIndex((x, i) => i > 0 && x !== r[0]); return num(r[0], 1) + " ล้าน ลบ.ม./วัน " + num(k, 0) + " วันแรก แล้ว " + num(r[k], 1); }
    return "รายวัน " + r.map((x) => num(x, 1)).join(", ") + " ล้าน ลบ.ม./วัน";
  }

  const RANK = { none: 0, ok: 1, near: 2, over: 3 };
  const worstDay = (p) => (p.days || []).reduce((b, d, i, a) => (RANK[d.status] > RANK[a[b].status] ||
    (RANK[d.status] === RANK[a[b].status] && (d.worst_margin == null ? 1e9 : d.worst_margin) < (a[b].worst_margin == null ? 1e9 : a[b].worst_margin)) ? i : b), 0);
  function dayRange(days) {  // [1,2,3,5] → "1–3, 5"
    const out = []; let s = null, p = null;
    for (const d of [...days].sort((x, y) => x - y)) {
      if (s === null) { s = p = d; } else if (d === p + 1) { p = d; } else { out.push(p > s ? s + "–" + p : String(s)); s = p = d; }
    }
    if (s !== null) out.push(p > s ? s + "–" + p : String(s));
    return out.join(", ");
  }
  const outsideText = (p) => "นอกช่วงข้อมูล: " + (p.outside_detail || []).map((o) => o.code + " " + num(o.flow_max, 0) +
    " ลบ.ม./วิ (เคยวัดสูงสุด " + num(o.qmax, 0) + ") วันที่ " + dayRange(o.days)).join(" · ");
  function villagesText(cmp, code) {  // "ริมแม่น้ำ B.16: บ้าน…, บ้าน… และอีก 3 (อ.บ้านลาด)" — at most 4 names (no long paragraph)
    const v = (cmp.places || {})[code] || [];
    if (!v.length) return "";
    const names = v.map((x) => x.village).filter(Boolean), amph = [...new Set(v.map((x) => x.amphoe).filter(Boolean))];
    return "ริมแม่น้ำ " + code + ": " + (names.length ? names.slice(0, 4).join(", ") + (names.length > 4 ? " และอีก " + (names.length - 4) : "") : "") +
      (amph.length ? " (อ." + amph.join(", อ.") + ")" : "");
  }
  const shortWhy = (p) => (p.effects.under_curve_day ? "กลับใต้เส้นควบคุมวันที่ " + num(p.effects.under_curve_day, 0) : "ลดอ่างได้มากสุด") +
    " ทุกจุดห่างตลิ่งเกินความคลาดเคลื่อน";
  const customParam = () => (state.customs.length ? "release=" + encodeURIComponent(state.customs.map((c) => c.join(",")).join(";")) : "");

  async function loadScenarios(st, body) {
    const sec = $("#imp-sc", body);
    if (!sec) return;
    sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="muted">กำลังคำนวณ…</p>';
    const qp = customParam();
    let r;
    try { r = await api("/api/impact/case/" + encodeURIComponent(st.case) + "/scenarios" + (qp ? "?" + qp : "")); }
    catch (e) { sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="imp-err">เชื่อมต่อไม่ได้</p>'; return; }
    if (r.status === 401) { state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
    if (r.status === 503) { sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="muted">ยังไม่พร้อม: ต้องมีเส้นควบคุม น้ำไหลเข้า และปริมาตรปกติของวันนี้ (คำนวณใหม่ทุกชั่วโมง)</p>'; return; }
    if (!r.ok) { sec.innerHTML = '<h3>แผนระบาย 7 วันข้างหน้า</h3><p class="imp-err">คำนวณไม่ได้ (' + r.status + ")</p>"; return; }
    const cmp = await r.json();
    state.cmp = cmp;
    sec.innerHTML = scenariosHtml(cmp);
    bindGrid(sec, cmp, st);
  }

  const cmRange = (v) => (Array.isArray(v) ? num(v[0], 0) + "→" + num(v[v.length - 1], 0) : num(v, 0));
  function redPill(cmp) {  // the downstream model the plans used: tested per day (E-7D-DOWN) or the untested what-if
    const ds = cmp.downstream || {};
    if (ds.method === "hybrid") {
      const m = ds.mae_cm || {}, k = ds.keep_cm || {};
      const d1 = Math.max(...Object.values(m).map((v) => v[0] || 0)), d7 = Math.max(...Object.values(m).map((v) => v[v.length - 1] || 0));
      const tip = "ระดับท้ายน้ำ 7 วัน: B.18 ตาม rating curve เทียบระดับวันนี้ · จุดอื่น = ระดับวันนี้ + การตอบสนองต่อการระบายที่เรียนรู้ (ไม่ติดลบ)" +
        " · ทดสอบย้อนหลัง " + (ds.window ? day(ds.window[0]) + "–" + day(ds.window[1]) : "") + " (แต่ละเดือนใช้ค่าที่เรียนจากเดือนอื่น)" +
        " · คลาดเคลื่อนเฉลี่ยวันที่ 1→7 (ซม.): " + Object.keys(m).map((c) => c + " " + cmRange(m[c]) + " (คงระดับวันนี้ " + cmRange(k[c]) + ")").join(", ") +
        " · แผนต้องห่างตลิ่งมากกว่าค่านี้ในแต่ละวัน — ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์";
      return '<button type="button" class="conf-badge imp-text" title="' + esc(tip) + '" aria-label="ความคลาดเคลื่อนท้ายน้ำ">🟠 ท้ายน้ำ ±' + num(d1, 0) + "–" + num(d7, 0) + " ซม.</button>";
    }
    return '<button type="button" class="conf-badge imp-red" title="ระดับท้ายน้ำจาก rating curve + เวลาเดินทาง ยังไม่ผ่านการทดสอบย้อนหลัง (ความคลาดเคลื่อน ' +
      Object.entries(cmp.margin_req || {}).map(([c, m]) => esc(c) + " " + (Array.isArray(m) ? cmRange(m.map((x) => x * 100)) : num(m * 100, 0)) + " ซม.").join(", ") +
      ') — ใช้เทียบระหว่างแผน ไม่ใช่ค่าพยากรณ์">🔴 ท้ายน้ำยังไม่ผ่านการทดสอบ</button>';
  }

  function gridPlans(cmp) {  // ★, today, the engine's picks, the session's own plans; the ladder apart (D-110)
    const by = Object.fromEntries(cmp.plans.map((p) => [p.id, p]));
    const star = by[(cmp.optimal || {}).id], hold = cmp.plans.find((p) => p.kind === "hold");
    const picks = (cmp.picks || []).map((id) => by[id]).filter((p) => p && p !== star && p !== hold);
    const customs = cmp.plans.filter((p) => p.kind === "custom");
    const seen = new Set(), rows = [];
    for (const p of [star, hold, ...picks, ...customs]) if (p && !seen.has(p.id)) { seen.add(p.id); rows.push(p); }
    return { rows, ladder: (cmp.ladder || []).map((id) => by[id]).filter(Boolean), star };
  }

  function cellTitle(d, i) {
    return "วันที่ " + (i + 1) + ": " + CELL_TH[d.status] + (d.worst_code ? " · " + d.worst_code + " ห่างตลิ่ง " + num(d.worst_margin, 2) + " ม." +
      (d.worst_req != null ? " (คลาดเคลื่อน ±" + num(d.worst_req, 2) + ")" : "") : "") + (d.outside ? " · ⚠ นอกช่วงข้อมูล" : "") +
      (d.km ? " · แม่น้ำ " + num(d.km, 0) + " กม." : "");
  }

  function gridRow(p, isStar) {
    const e = p.effects, worst = e.worst_margin_min;
    const icons = (p.best_for || []).map((k) => '<span class="imp-gi" title="' + esc("เหมาะกับ" + EFFECT_TH[k]) + '" aria-label="' +
      esc("เหมาะกับ" + EFFECT_TH[k]) + '">' + EFFECT_ICON[k] + "</span>").join("");
    const out = p.outside_any ? '<span class="imp-out" title="' + esc(outsideText(p)) + '" aria-label="นอกช่วงข้อมูล">⚠</span>' : "";
    const cells = (p.days || []).map((d, i) => '<td class="imp-c imp-c-' + d.status + (d.outside ? " imp-c-x" : "") +
      (state.day === i ? " imp-dsel" : "") + '" data-day="' + i + '" title="' + esc(cellTitle(d, i)) + '"><span></span></td>').join("");
    return '<tr class="imp-gr' + (p.feasible ? "" : " imp-infeasible") + (p.kind === "custom" ? " imp-custom-row" : "") +
      (state.selPlan === p.id ? " imp-sel" : "") + '" data-plan="' + esc(p.id) + '" tabindex="0">' +
      '<th scope="row"><span class="imp-gl">' + (isStar ? "★ " : "") + esc(p.label) + "</span>" + icons + out +
      '<small class="imp-km-sub">' + (p.km_max ? num(p.km_max, 0) + " กม." : "") + "</small></th>" + cells +
      "<td>" + num(e.storage_end, 0) + "</td><td" + (worst != null && worst < 0 ? ' class="imp-neg"' : "") + ">" + num(worst, 2) + "</td>" +
      '<td class="imp-col-km">' + num(p.km_max || 0, 0) + "</td>" +
      '<td><button type="button" class="imp-open" aria-label="' + esc("รายละเอียด " + p.label) + '">›</button></td></tr>';
  }

  function scenariosHtml(cmp) {
    const { rows, ladder, star } = gridPlans(cmp);
    const opt = cmp.optimal || {};
    const head = '<thead><tr><th scope="col">แผน <small>ล้าน ลบ.ม./วัน</small></th>' +
      [0, 1, 2, 3, 4, 5, 6].map((i) => '<th scope="col" class="imp-dh' + (state.day === i ? " imp-dsel" : "") + '"><button type="button" data-dayh="' + i +
        '" aria-label="' + esc("วันที่ " + (i + 1) + " " + dayShort(cmp.dates ? cmp.dates[i] : null) + " บนแผนที่") + '">' + (i + 1) + "</button></th>").join("") +
      '<th scope="col">อ่าง<small>วันที่ 7</small></th><th scope="col">ห่างตลิ่ง<small>ม.</small></th><th scope="col" class="imp-col-km">กม.</th>' +
      '<th scope="col"><span class="imp-sr">เปิด</span></th></tr></thead>';
    const lad = ladder.length ? '<tbody><tr class="imp-ladder-t"><td colspan="12"><button type="button" class="imp-ladder-btn" aria-expanded="false">▸ ระบายคงที่ทุกระดับ (' +
      num(ladder[0].release[0], 0) + "–" + num(ladder[ladder.length - 1].release[0], 0) + ")</button></td></tr></tbody>" +
      '<tbody class="imp-ladder" hidden>' + ladder.map((p) => gridRow(p, star && p.id === star.id)).join("") + "</tbody>" : "";
    const why = !star ? esc(opt.reason || "ยังไม่มีแผนให้เปรียบเทียบ")
      : opt.constraints_met ? "★ ตามเกณฑ์: " + esc(shortWhy(star)) : "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์ — ★ คือแผนที่ใกล้เคียงที่สุด";
    return '<h3>แผนระบาย 7 วันข้างหน้า ' + redPill(cmp) + "</h3>" +
      '<div class="imp-scroll"><table class="imp-grid">' + head + "<tbody>" + rows.map((p) => gridRow(p, star && p.id === star.id)).join("") + "</tbody>" + lad + "</table></div>" +
      '<p class="imp-key"><span class="imp-k imp-c-ok"></span>รับน้ำได้ <span class="imp-k imp-c-near"></span>ใกล้ตลิ่ง <span class="imp-k imp-c-over"></span>เกินตลิ่ง ' +
      '<span class="imp-k imp-c-ok imp-c-x"></span>นอกช่วงข้อมูล ' +
      info("สีของวัน = สถานีที่ห่างตลิ่งน้อยที่สุดในวันนั้น: น้ำเงิน รับน้ำได้ · ส้ม ห่างตลิ่งน้อยกว่าความคลาดเคลื่อนที่ทดสอบของวันนั้น · แดง เกินตลิ่ง · " +
        "ลาย = มีสถานีที่น้ำมากกว่าที่เคยวัดได้ (ระดับจากการต่อเส้นโค้งออกไป) · อ่าง = ปริมาตรวันที่ 7 (ล้าน ลบ.ม.) · ห่างตลิ่ง = ต่ำสุดทุกจุดทุกวัน (ม.) · " +
        "กม. = แม่น้ำช่วงที่สถานีใกล้หรือเกินตลิ่ง มากที่สุดในวันใดวันหนึ่ง · แตะเลขวันเพื่อดูวันนั้นบนแผนที่", "วิธีอ่านตาราง") + "</p>" +
      '<p class="imp-why">' + why + " " + info((opt.rule || "") + " · " + (opt.reason || "") + " · เข้าเกณฑ์ " + num(cmp.feasible, 0) +
        " จาก " + num(cmp.candidates, 0) + " แผน", "เกณฑ์ของ ★") + "</p>" +
      '<div class="imp-actions"><button type="button" class="btn" id="imp-custom-btn">➕ ลองแผนเอง</button>' + aiMenuHtml() + "</div>";
  }

  function bindGrid(sec, cmp, st) {
    const by = Object.fromEntries(cmp.plans.map((p) => [p.id, p]));
    const select = (id) => {
      if (!by[id]) return;
      state.selPlan = id;
      sec.querySelectorAll(".imp-gr").forEach((tr) => tr.classList.toggle("imp-sel", tr.dataset.plan === id));
      colorReaches(cmp, by[id], state.day != null ? state.day : worstDay(by[id]));
    };
    sec.querySelectorAll(".imp-gr").forEach((tr) => {
      const id = tr.dataset.plan;
      tr.addEventListener("click", (e) => {
        if (e.target.closest(".conf-badge, .imp-out, .imp-gi")) return;
        if (e.target.closest(".imp-open") || narrow()) { openPlanSheet(cmp, id); return; }
        select(id);
      });
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter") openPlanSheet(cmp, id); });
    });
    sec.querySelectorAll("[data-dayh]").forEach((b) => b.addEventListener("click", () => {
      const d = Number(b.dataset.dayh);
      state.day = state.day === d ? null : d;  // a second click on the same day goes back to each plan's worst day
      sec.querySelectorAll(".imp-dh").forEach((th, i) => th.classList.toggle("imp-dsel", i === state.day));
      sec.querySelectorAll(".imp-c").forEach((td) => td.classList.toggle("imp-dsel", Number(td.dataset.day) === state.day));
      select(state.selPlan && by[state.selPlan] ? state.selPlan : (cmp.optimal || {}).id);
    }));
    const lb = $(".imp-ladder-btn", sec);
    if (lb) lb.addEventListener("click", () => {
      const tb = $(".imp-ladder", sec), open = tb.hidden;
      tb.hidden = !open;
      lb.setAttribute("aria-expanded", String(open));
      lb.textContent = (open ? "▾" : "▸") + lb.textContent.slice(1);
    });
    $("#imp-custom-btn", sec).addEventListener("click", () => openCustomSheet(st, sec.closest("#imp-body"), cmp));
    bindAi(sec, st);
    select(state.selPlan && by[state.selPlan] ? state.selPlan : (cmp.optimal || {}).id);  // the map shows the ★ until a row is picked
  }

  // AI entry points (Task 12 replaces these two stubs)
  function aiMenuHtml() { return ""; }
  function bindAi() { /* Task 12 */ }
```

Replace `matrixHtml` with (ladder-only rungs stay out of the matrix):

```js
  function matrixHtml(cmp) {
    const plans = cmp.plans.filter((p) => !(p.roles && p.roles.length === 1 && p.roles[0] === "ladder"));
    return '<div class="imp-scroll"><table><thead><tr><th scope="col">ผล</th>' +
      plans.map((p) => '<th scope="col">' + (p.optimal ? "★ " : "") + esc(planWords(p)) + "</th>").join("") + "</tr></thead><tbody>" +
      EFFECT_ROWS.map(([k, label2, fmt]) => '<tr><th scope="row">' + label2 + "</th>" + plans.map((p) => "<td" + (cmp.best_for[k] === p.id ? ' class="imp-best"' : "") + ">" + fmt(p.effects) + "</td>").join("") + "</tr>").join("") +
      "</tbody></table></div>" + scenarioNotes(cmp);
  }
```

- [ ] **Step 4: The map colours read the server's status, dash outside days, list villages**

Replace `colorReaches` with:

```js
  function colorReaches(cmp, p, d) {
    if (!mapRef || !p || !p.downstream) return;
    for (const [code, lines] of Object.entries(reachLayers)) {
      const row = (p.downstream[code] || [])[d] || {};
      const k = row.status || "none", m = row.margin_m, rq = cmp.margin_req ? cmp.margin_req[code] : null;
      const req = Array.isArray(rq) ? rq[d] : rq;
      const vill = k === "near" || k === "over" ? villagesText(cmp, code) : "";
      const tip = esc(code) + " วันที่ " + (d + 1) + ": " + (m == null ? "ไม่มีข้อมูล" : m < 0 ? "เกินตลิ่ง " + num(-m, 2) + " ม." : "ห่างตลิ่ง " + num(m, 2) + " ม.") +
        (req != null ? " (คลาดเคลื่อน ±" + num(req, 2) + ")" : "") + (row.outside ? " · ⚠ นอกช่วงข้อมูล" : "") + (vill ? "<br>" + esc(vill) : "");
      for (const l of lines) { l.setStyle({ color: REACH[k], dashArray: row.outside ? "8 6" : null }); l.setTooltipContent(tip); }
    }
    if (reachLegend) reachLegend.remove();
    reachLegend = L.control({ position: "topright" });
    reachLegend.onAdd = () => {
      const div = L.DomUtil.create("div", "imp-reach-legend");
      div.innerHTML = "<b>" + esc(p.label || planWords(p)) + " · วันที่ " + (d + 1) + "</b><br>" +
        '<span class="lg lg-over">━</span> เกินตลิ่ง <span class="lg lg-near">━</span> ใกล้ตลิ่ง <span class="lg lg-ok">━</span> รับน้ำได้ ' +
        '<span class="lg lg-x">┅</span> นอกช่วงข้อมูล<br><small>สีแม่น้ำ = ห่างตลิ่งของสถานีที่ใกล้ที่สุด (ไม่เกิน 10 กม.) ไม่ใช่พื้นที่น้ำท่วม</small>';
      return div;
    };
    reachLegend.addTo(mapRef);
  }
```

- [ ] **Step 5: CSS**

Append to `web/impact.css`:

```css
/* v0.34 (D-110): release plans as a comparison grid — one row per plan, a 7-day strip of the worst gauge, hatched where a
   gauge runs beyond its rating's data; the map follows the selected row and day */
#view-impact .imp-grid { border-collapse: collapse; width: 100%; font-size: 14px; font-variant-numeric: tabular-nums; }
#view-impact .imp-grid th, #view-impact .imp-grid td { padding: 6px 3px; border-bottom: 1px solid var(--line); text-align: right; white-space: nowrap; }
#view-impact .imp-grid tbody th { text-align: left; font-weight: 600; white-space: normal; min-width: 96px; }
#view-impact .imp-grid thead th { font-size: 12px; color: var(--muted); font-weight: 600; min-width: 0; vertical-align: bottom; }
#view-impact .imp-grid thead th small { display: block; font-weight: 400; }
#view-impact .imp-gr { cursor: pointer; }
#view-impact .imp-gr:hover, #view-impact .imp-gr:focus { background: #f3f6fa; outline: none; }
#view-impact .imp-gr.imp-sel { background: #e8f0fb; box-shadow: inset 4px 0 0 var(--accent); }
#view-impact .imp-gr.imp-infeasible .imp-gl { color: var(--muted); }
#view-impact .imp-gr.imp-custom-row .imp-gl { color: var(--accent); }
#view-impact .imp-c { text-align: center; padding: 6px 1px; }
.imp-c span, .imp-k { display: inline-block; width: 16px; height: 16px; border-radius: 3px; vertical-align: middle; background-color: var(--unknown); }
.imp-c-ok span, .imp-k.imp-c-ok { background-color: var(--normal); }
.imp-c-near span, .imp-k.imp-c-near { background-color: var(--warning); }
.imp-c-over span, .imp-k.imp-c-over { background-color: var(--critical); }
.imp-c-x span, .imp-k.imp-c-x, td.imp-c-x { background-image: repeating-linear-gradient(45deg, rgba(255, 255, 255, .8) 0 2px, transparent 2px 5px); }
#view-impact .imp-c.imp-dsel span { outline: 2px solid var(--ink); outline-offset: 1px; }
#view-impact .imp-dh button { font: inherit; font-size: 12px; font-weight: 700; color: var(--muted); background: none; border: 1px solid var(--line);
  border-radius: 6px; min-width: 24px; min-height: 30px; cursor: pointer; padding: 0; }
#view-impact .imp-dh.imp-dsel button { color: #fff; background: #0d3b66; border-color: #0d3b66; }
#view-impact .imp-gi { font-size: 13px; margin-left: 3px; cursor: help; }
#view-impact .imp-out { color: var(--warning); font-weight: 700; margin-left: 3px; cursor: help; }
#view-impact .imp-open { font: inherit; font-size: 20px; line-height: 1; color: var(--muted); background: none; border: 0; min-width: 28px; min-height: 32px; cursor: pointer; }
#view-impact .imp-ladder-btn { font: inherit; font-size: 13px; font-weight: 600; color: var(--accent); background: none; border: 0; padding: 6px 0; min-height: 36px; cursor: pointer; }
#view-impact .imp-key { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; font-size: 12px; color: var(--muted); margin: 6px 0 2px; }
#view-impact .imp-why { font-size: 14px; margin: 4px 0 6px; }
#view-impact .imp-km-sub { display: none; font-weight: 400; color: var(--muted); font-size: 12px; }
.imp-sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.imp-reach-legend .lg-x { color: #1565c0; letter-spacing: -1px; }
@media (max-width: 420px) {
  #view-impact .imp-col-km { display: none; }
  #view-impact .imp-km-sub { display: block; }
  .imp-c span, .imp-k { width: 13px; height: 13px; }
  #view-impact .imp-grid tbody th { min-width: 84px; }
}
```

- [ ] **Step 6: Syntax check**

Run: `node --check web/impact.js && echo OK`
Expected: `OK`. (`openPlanSheet` and `openCustomSheet` still exist from before; Tasks 10 and 12 replace them.)

- [ ] **Step 7: Commit**

```bash
git add web/impact.js web/impact.css
git commit -m "impact tab: release plans as a comparison grid — ★, today, picks with goal icons, own plans, a release ladder; a 7-day strip per plan hatched outside the data; a day header and a selected row colour the river; the map follows the case (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 10: The plan sheet — river grid, coverage, outside line, compare

**Files:**
- Modify: `web/impact.js` — replace `openPlanSheet` (623–659); add `riverGridHtml`, `coverageHtml`, `outsideNote`, `askBox`
- Modify: `web/impact.css` (append the sheet block)

**Interfaces:**
- Consumes: `worstDay`, `dayRange`, `outsideText`, `villagesText`, `shortWhy`, `EFFECT_TH`, `colorReaches`, `showCaseOnMap`, `chartSvg`, `dayShort`, `info`, `openSheet` (existing/Task 9); app.js globals `bindAskUrl`, `fillStory` markup classes (`.ai-btn`, `.story`, `.story-body`, `.story-speak`).
- Produces: `askBox(label, heading) -> string` (also used in Task 12).

- [ ] **Step 1: Replace `openPlanSheet` and add helpers**

```js
  function askBox(label, heading) {  // the ✨ story card's markup (app.js bindAskUrl/fillStory), with our own words
    return '<div class="imp-ask"><button type="button" class="ai-btn" aria-expanded="false">' + esc(label) + "</button>" +
      '<div class="story" hidden><div class="story-h"><span>' + esc(heading) + '</span><button type="button" class="story-speak" title="ฟังเสียงอ่าน" aria-label="ฟังเสียงสรุป">🔊 ฟังเสียง</button></div>' +
      '<div class="story-body" aria-live="polite"></div></div></div>';
  }

  function outsideNote(st) {  // the ⓘ behind every outside label; the largest release on record comes from the state
    const ys = ((st && st.dam && st.dam.yearly_max) || []).filter((y) => y.max_mcm != null);
    const big = ys.reduce((b, y) => (!b || y.max_mcm > b.max_mcm ? y : b), null);
    return "นอกช่วงข้อมูล = น้ำที่สถานีมากกว่าที่เคยวัดได้ในข้อมูลที่ใช้หา rating curve ระดับวันนั้นจึงมาจากการต่อเส้นโค้งออกไป · " +
      "แบบจำลองท้ายน้ำเรียนจากช่วงที่เขื่อนทดน้ำเพชรรับการเปลี่ยนแปลงของการระบายไว้ น้ำที่เกินความจุคลองจะลงแม่น้ำ ระดับจริงจึงอาจสูงกว่าที่แสดง" +
      (big ? " · การระบายสูงสุดที่มีบันทึก " + num(big.max_mcm, 1) + " ล้าน ลบ.ม./วัน (" + day(big.date) + ") — สสน. ไม่มีข้อมูลระดับแม่น้ำปีนั้นให้ตรวจสอบ" : "");
  }

  function riverGridHtml(cmp, p, sel) {  // 5 gauges × 7 days: each cell the server's status, the margin in m, hatched outside
    const codes = Object.keys(p.downstream || {});
    const head = '<thead><tr><th scope="col">สถานี</th>' + p.release.map((r, i) => '<th scope="col">' + (i + 1) + "</th>").join("") + "</tr></thead>";
    const body = codes.map((c) => '<tr><th scope="row">' + esc(c) + "</th>" + p.downstream[c].map((r, i) => {
      const rq = cmp.margin_req ? cmp.margin_req[c] : null, req = Array.isArray(rq) ? rq[i] : rq;
      return '<td class="imp-m imp-rc-' + (r.status || "none") + (r.outside ? " imp-c-x" : "") + (i === sel ? " imp-dsel" : "") + '" data-day="' + i + '" title="' +
        esc(c + " วันที่ " + (i + 1) + ": " + CELL_TH[r.status || "none"] + (req != null ? " · คลาดเคลื่อน ±" + num(req, 2) : "") + (r.outside ? " · ⚠ นอกช่วงข้อมูล" : "")) +
        '">' + num(r.margin_m, 2) + "</td>";
    }).join("") + "</tr>").join("");
    return '<div class="imp-scroll"><table class="imp-rgrid">' + head + "<tbody>" + body + "</tbody></table></div>";
  }

  function coverageHtml(cmp, p) {  // river km near or over the bank, and the villages along those stretches (D-110)
    const days = (p.days || []).map((d, i) => [d, i]).filter(([d]) => d.km > 0);
    if (!days.length) return '<p class="imp-cover">🌊 ไม่มีช่วงใดของแม่น้ำใกล้ตลิ่งใน 7 วัน</p>';
    const codes = [...new Set(days.flatMap(([d]) => d.codes || []))];
    const vill = codes.map((c) => villagesText(cmp, c)).filter(Boolean);
    return '<p class="imp-cover">🌊 แม่น้ำใกล้/เกินตลิ่ง วันที่ ' + dayRange(days.map(([, i]) => i + 1)) + " ราว " + num(Math.max(...days.map(([d]) => d.km)), 0) +
      " กม. (" + codes.map(esc).join(", ") + ") " + info("กม. = ความยาวแม่น้ำช่วงที่สถานีที่ใกล้ที่สุด (ไม่เกิน 10 กม.) ใกล้หรือเกินตลิ่งในวันนั้น — " +
        "สถานีเดียวแทนทั้งช่วง จึงเป็นค่าหยาบ · หมู่บ้าน: © OpenStreetMap contributors · ไม่ใช่พื้นที่น้ำท่วม", "กม. และหมู่บ้าน") + "</p>" +
      (vill.length ? '<ul class="imp-cover-v">' + vill.map((v) => "<li>" + esc(v) + "</li>").join("") + "</ul>" : "");
  }

  function openPlanSheet(cmp, id) {
    const p = cmp.plans.find((x) => x.id === id);
    if (!p) return;
    const opt = cmp.optimal || {}, isStar = p.id === opt.id, e = p.effects;
    const kst = state.kase[state.sel];
    const sub = isStar ? (opt.constraints_met ? "★ ตามเกณฑ์ · " + shortWhy(p) : "⚠️ ยังไม่มีแผนที่เข้าเกณฑ์ — ใกล้เคียงที่สุด")
      : ((p.best_for || []).map((k) => "เหมาะกับ" + EFFECT_TH[k]).join(" · ") || (p.feasible ? "เข้าเกณฑ์" : "ไม่เข้าเกณฑ์"));
    let d0 = state.day != null ? state.day : worstDay(p);
    const daysBar = '<div class="chips imp-days" role="group" aria-label="วันบนแผนที่">' + p.release.map((r, i) =>
      '<button type="button" class="chip' + (i === d0 ? " on" : "") + '" data-day="' + i + '">' + (i + 1) + "</button>").join("") +
      '</div><p class="muted imp-small">สีแม่น้ำตามวันที่เลือก · ไม่ใช่พื้นที่น้ำท่วม</p>';
    const resRows = p.release.map((r, i) => '<tr><th scope="row">' + esc(dayShort(cmp.dates ? cmp.dates[i] : null)) + "</th><td>" + num(r, 1) + "</td><td>" +
      num(p.storage[i], 0) + " <small>(" + num(p.storage_low[i], 0) + "–" + num(p.storage_high[i], 0) + ")</small></td><td" +
      (p.storage[i] > cmp.upper[i] ? "" : ' class="imp-best"') + ">" + (p.storage[i] > cmp.upper[i] ? "+" : "") + num(p.storage[i] - cmp.upper[i], 0) + "</td></tr>").join("");
    const units = "ล้าน ลบ.ม./วัน · อ่างเป็นค่ากลาง (ช่วง = น้ำไหลเข้าต่ำ–สูง) · เทียบเส้นบน = ปริมาตร − เส้นควบคุมบนของวันนั้น · ห่างตลิ่ง = ตลิ่งของหน่วยงานผู้วัด − ระดับ · " +
      ((cmp.downstream || {}).method === "hybrid" ? "ท้ายน้ำทดสอบย้อนหลังแล้ว คลาดเคลื่อนรายวัน" : "ท้ายน้ำยังไม่ผ่านการทดสอบย้อนหลัง") +
      " · วันเหนือปริมาตรปกติ " + num(e.days_above_normal, 0) + " · เกินตลิ่งรวม " + num(e.overtop_sum, 2);
    const other = isStar ? cmp.plans.find((x) => x.kind === "hold") : cmp.plans.find((x) => x.id === opt.id);
    const cmpBox = other && other.id !== p.id ? askBox(isStar ? "✨ เทียบกับคงระบายเท่าวันนี้" : "✨ เทียบกับแผน ★", "✨ เทียบสองแผน") : "";
    openSheet("<h2>" + (isStar ? "★ " : "") + esc(planWords(p)) + (p.outside_any ? ' <span class="imp-out" title="' + esc(outsideText(p)) + '">⚠</span>' : "") + "</h2>" +
      '<p class="muted imp-sub">' + esc(sub) + " " + info(isStar ? (opt.reason || "") + " · " + (opt.rule || "") : planWords(p), "ที่มาของแผน") + "</p>" +
      daysBar + chartSvg(p, cmp) +
      '<div class="imp-scroll"><table><thead><tr><th scope="col">วัน</th><th scope="col">ระบาย</th><th scope="col">อ่าง (ช่วง)</th><th scope="col">เทียบเส้นบน</th></tr></thead><tbody>' +
      resRows + "</tbody></table></div>" +
      '<h3 class="imp-h3">ห่างตลิ่ง (ม.) <small>ตลิ่งของหน่วยงานผู้วัด</small> ' + info(units, "หน่วยและสมมติฐาน") + "</h3>" + riverGridHtml(cmp, p, d0) +
      coverageHtml(cmp, p) +
      (p.outside_any ? '<p class="imp-outline">⚠ นอกช่วงข้อมูล ' + info(outsideNote(kst), "นอกช่วงข้อมูลคืออะไร") + '</p><ul class="imp-out-list">' +
        (p.outside_detail || []).map((o) => "<li>" + esc(o.code + " " + num(o.flow_max, 0) + " ลบ.ม./วิ (เคยวัดสูงสุด " + num(o.qmax, 0) + ") วันที่ " +
          dayRange(o.days)) + "</li>").join("") + "</ul>" : "") +  // one gauge a line: five gauges in one paragraph ran past 160 characters
      '<div class="imp-actions">' + cmpBox + (narrow() ? '<button type="button" class="btn" data-map-plan="1">🗺️ ดูบนแผนที่</button>' : "") + "</div>", (box) => {
      const pick = (d) => {
        d0 = d;
        box.querySelectorAll(".imp-days [data-day]").forEach((x) => x.classList.toggle("on", Number(x.dataset.day) === d));
        box.querySelectorAll(".imp-rgrid td").forEach((td) => td.classList.toggle("imp-dsel", Number(td.dataset.day) === d));
        colorReaches(cmp, p, d);
      };
      box.querySelectorAll(".imp-days [data-day]").forEach((b) => b.addEventListener("click", () => pick(Number(b.dataset.day))));
      const mp = box.querySelector("[data-map-plan]");
      if (mp) mp.addEventListener("click", () => { document.getElementById("sheet").hidden = true; if (kst) showCaseOnMap(kst); else setTab("map"); });
      if (cmpBox && typeof bindAskUrl === "function") {
        bindAskUrl(box, "/api/impact/case/" + encodeURIComponent(st0(kst)) + "/explain?q=compare&a=" + encodeURIComponent(p.release.join(",")) +
          "&b=" + encodeURIComponent(other.release.join(",")));
      }
      pick(d0);
      if (kst && !narrow()) showCaseOnMap(kst, false);  // desktop: the coloured river beside the sheet
    });
  }
  const st0 = (kst) => (kst && kst.case) || state.sel;
```

- [ ] **Step 2: CSS**

Append to `web/impact.css`:

```css
/* v0.34: the plan sheet — the river as gauges × days of margins, the coverage line, the outside line (D-110) */
.imp-sheet .imp-sub { margin: 0 0 6px; }
.imp-sheet .imp-rgrid { border-collapse: separate; border-spacing: 2px; width: 100%; font-size: 13px; font-variant-numeric: tabular-nums; }
.imp-sheet .imp-rgrid th, .imp-sheet .imp-rgrid td { padding: 4px 2px; border: 0; text-align: center; }
.imp-sheet .imp-rgrid tbody th { text-align: left; font-weight: 600; }
.imp-sheet .imp-rgrid td.imp-m { color: #fff; font-weight: 600; border-radius: 4px; min-width: 36px; }
.imp-sheet .imp-rc-ok { background-color: var(--normal); } .imp-sheet .imp-rc-near { background-color: var(--warning); }
.imp-sheet .imp-rc-over { background-color: var(--critical); } .imp-sheet .imp-rc-none { background-color: var(--unknown); }
.imp-sheet .imp-rgrid td.imp-dsel { outline: 2px solid var(--ink); outline-offset: -1px; }
.imp-sheet .imp-cover { font-size: 14px; margin: 8px 0 2px; }
.imp-sheet .imp-cover-v { padding-left: 20px; margin: 2px 0 6px; font-size: 13px; color: var(--muted); }
.imp-sheet .imp-outline { font-size: 14px; color: #8a4b00; background: #fff4e5; border-left: 4px solid var(--warning); border-radius: 4px; padding: 6px 10px; margin: 6px 0 0; }
.imp-sheet .imp-out-list { margin: 2px 0 6px; padding-left: 24px; font-size: 13px; color: #8a4b00; }
.imp-sheet .imp-out { color: var(--warning); }
.imp-sheet .imp-ask { flex: 1 1 100%; }
```

- [ ] **Step 3: Syntax check**

Run: `node --check web/impact.js && echo OK`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add web/impact.js web/impact.css
git commit -m "impact tab: the plan sheet — the river as gauges × days of margins (hatched outside the data), km near the bank with the villages along it, the outside line, ✨ compare with the ★ (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 11: ONWR's layers in the app's one layer box, off by default

**Files:**
- Modify: `web/impact.js` — replace the ONWR block (371–418: `ONWR_LAYERS` kept, `ONWR_FILL` kept, `onwrGroups`, `onwrCtl` → `onwrBox`, `clearOnwr`, `drawOnwr`); in `logout` the `clearOnwr()` call stays
- Modify: `web/impact.css` (append the group block)

**Interfaces:**
- Consumes: the app's `details.legend.layers` (built by `app.js`, unchanged), `info`.
- Produces: `.legend.layers .imp-onwr-grp` with `input[data-onwr]` rows (asserted by Task 13).

- [ ] **Step 1: Replace the ONWR block**

```js
  // ONWR's flood layers over the case (owner 2026-10-06), dated and attributed — ONWR's areas, not results of a plan.
  // D-110: off by default, inside the app's one layer box (app.js builds it; its change handler ignores rows without
  // data-layer, so app.js stays as it is); the cells come clipped to the case box (KI-318)
  const ONWR_LAYERS = [["flood-warn", "พื้นที่เตือนวันนี้"], ["flood-forecast-d1", "คาดการณ์ +1 วัน"], ["flood-forecast-d2", "คาดการณ์ +2 วัน"],
    ["flood-forecast-d3", "คาดการณ์ +3 วัน"], ["flood-area-poly", "พื้นที่น้ำท่วมที่พบ"]];
  const ONWR_FILL = { 1: "#fdd835", 2: "#fb8c00", 3: "#e53935", obs: "#1e88e5" };
  let onwrGroups = {}, onwrBox = null;
  function clearOnwr() {
    for (const g of Object.values(onwrGroups)) g.remove();
    onwrGroups = {};
    if (onwrBox) { onwrBox.remove(); onwrBox = null; }
  }
  function drawOnwr(st) {
    clearOnwr();
    const o = st && st.onwr && st.onwr.layers;
    if (!mapRef || !o) return;
    for (const [lid, label] of ONWR_LAYERS) {
      const lay = o[lid];
      if (!lay) continue;
      const g = L.layerGroup();
      for (const f of lay.features || []) {
        const fill = lid === "flood-area-poly" ? ONWR_FILL.obs : (ONWR_FILL[f.cls] || ONWR_FILL[1]);
        L.polygon(f.rings, { stroke: false, fillColor: fill, fillOpacity: 0.45 })
          .bindTooltip("สทนช. · " + label + (f.cls ? " ระดับ " + f.cls : "") + (f.rai ? " · " + num(f.rai, 0) + " ไร่" : "") +
            (lay.updated ? " · ข้อมูล ณ " + when(lay.updated) : ""), { sticky: true }).addTo(g);
      }
      onwrGroups[lid] = g;  // not on the map until its box is ticked
    }
    // app.js adds its layer box right after announcing the map (fw:map): one tick later it is there
    if (document.querySelector(".legend.layers")) attachOnwrBox(o); else setTimeout(() => attachOnwrBox(o), 0);
  }
  function attachOnwrBox(o) {
    const box = document.querySelector(".legend.layers");
    if (!box || onwrBox || !Object.keys(onwrGroups).length) return;  // the browser check asserts the group sits in the app's box
    const div = document.createElement("div");
    div.className = "imp-onwr-grp";
    div.innerHTML = '<div class="imp-onwr-h"><b>สทนช.</b> · ไม่ขึ้นกับแผนระบาย ' +
      info("พื้นที่เตือน คาดการณ์ และพื้นที่น้ำท่วมที่พบของ สทนช. เฉพาะในกรอบของกรณีนี้ — ไม่ใช่ผลของแผนระบาย · ที่มา: สทนช.", "ชั้นข้อมูล สทนช.") + "</div>" +
      ONWR_LAYERS.filter(([lid]) => o[lid]).map(([lid, label]) => {
        const lay = o[lid], n = (lay.features || []).length;
        return '<label title="' + esc(lay.updated ? "ข้อมูล ณ " + when(lay.updated) : "") + '"><input type="checkbox" data-onwr="' + lid + '"' + (n ? "" : " disabled") + "> " +
          '<i class="sw ' + (lid === "flood-area-poly" ? "onwr-obs" : "onwr-c2") + '"></i> ' + label + ' <span class="lc">' + num(n, 0) + "</span></label>";
      }).join("") +
      '<p class="imp-onwr-key"><span class="sw onwr-c1"></span>1 <span class="sw onwr-c2"></span>2 <span class="sw onwr-c3"></span>3 ระดับความเสี่ยง</p>';
    div.addEventListener("change", (e) => {
      const lid = e.target && e.target.dataset ? e.target.dataset.onwr : null;
      const g = lid && onwrGroups[lid];
      if (!g) return;
      if (e.target.checked) g.addTo(mapRef); else g.remove();
    });
    box.appendChild(div);
    onwrBox = div;
  }
```

- [ ] **Step 2: CSS**

Append to `web/impact.css`:

```css
/* v0.34: ONWR's layers inside the app's one layer box, off by default (D-110) */
.legend.layers .imp-onwr-grp { border-top: 1px solid var(--line); margin-top: 4px; padding-top: 4px; }
.legend.layers .imp-onwr-h { font-weight: 600; white-space: nowrap; }
.legend.layers .imp-onwr-grp .sw, .legend.layers .imp-onwr-key .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin: 0 2px; vertical-align: middle; }
.legend.layers .onwr-c1 { background: #fdd835; } .legend.layers .onwr-c2 { background: #fb8c00; }
.legend.layers .onwr-c3 { background: #e53935; } .legend.layers .onwr-obs { background: #1e88e5; }
.legend.layers .imp-onwr-key { margin: 2px 0 0; color: var(--muted); }
```

- [ ] **Step 3: Syntax check**

Run: `node --check web/impact.js && echo OK && grep -c "onwrCtl" web/impact.js`
Expected: `OK` and `0` (no reference to the old control left).

- [ ] **Step 4: Commit**

```bash
git add web/impact.js web/impact.css
git commit -m "impact tab: ONWR's layers move into the app's one layer box, off by default, said not to depend on the plan (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 12: The AI menu, the executive brief and a typed plan

**Files:**
- Modify: `web/impact.js` — replace the Task 9 stubs `aiMenuHtml` / `bindAi`; add `bindBrief`, `copyText`; replace `openCustomSheet` (572–584)
- Modify: `web/impact.css` (append)

**Interfaces:**
- Consumes: `askHTML`, `bindAskUrl` (app.js), `askBox` (Task 10), `customParam` (Task 9), the endpoints from Task 8.
- Produces: `.imp-ai` (details), `.imp-brief-btn`, `.imp-brief` (ul + `.imp-copy`), `#imp-parse-text`, `#imp-parse-btn`, `#imp-parse-msg` (asserted by Task 13).

- [ ] **Step 1: Replace the stubs and add the brief**

```js
  // One ✨ entry on the case view (D-110): today's simple story and the executive brief, both on tap only (D-068)
  function aiMenuHtml() {
    return '<details class="imp-ai"><summary class="btn">✨ AI ▾</summary><div class="imp-ai-body">' +
      (typeof askHTML === "function" ? askHTML() : "") +
      '<button type="button" class="ai-btn imp-brief-btn" aria-expanded="false">📝 สรุปเสนอผู้บริหาร</button><div class="imp-brief" hidden></div></div></details>';
  }
  function bindAi(sec, st) {
    const qp = customParam();
    if (typeof bindAskUrl === "function") {
      const wrap = $(".imp-ai-body", sec);
      if (wrap) bindAskUrl(wrap, "/api/impact/case/" + encodeURIComponent(st.case) + "/explain?q=simple" + (qp ? "&" + qp : ""));
    }
    bindBrief(sec, st, qp);
  }
  function bindBrief(sec, st, qp) {
    const btn = $(".imp-brief-btn", sec), card = $(".imp-brief", sec);
    if (!btn || !card) return;
    const url = "/api/impact/case/" + encodeURIComponent(st.case) + "/explain?q=brief" + (qp ? "&" + qp : "");
    btn.addEventListener("click", async () => {
      const open = btn.getAttribute("aria-expanded") !== "true";
      btn.setAttribute("aria-expanded", String(open));
      card.hidden = !open;
      if (!open) return;
      card.innerHTML = '<p class="muted">กำลังสรุป…</p>';
      let r;
      try { r = await api(url); } catch (e) { card.innerHTML = '<p class="imp-err">สรุปไม่ได้ ลองอีกครั้ง</p>'; return; }
      if (r.status === 401) { state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
      if (!r.ok) { card.innerHTML = '<p class="imp-err">สรุปไม่ได้ (' + r.status + ")</p>"; return; }
      const data = await r.json();
      let lines = data.lines || [];
      const render = (by) => {
        card.innerHTML = "<ul>" + lines.map((l) => "<li>" + esc(l) + "</li>").join("") + "</ul>" +
          '<div class="imp-actions"><button type="button" class="btn imp-copy">📋 คัดลอก</button><span class="muted">' + esc(by) + "</span></div>";
        $(".imp-copy", card).addEventListener("click", (e) => copyText(lines.join("\n"), e.currentTarget, card));
      };
      render(data.ai ? "ตัวเลขจากระบบ · กำลังให้ AI เรียบเรียง…" : "ตัวเลขจากระบบ");
      if (!data.ai) return;
      try {
        const g = await api(url + "&part=gist");
        if (g.status === 401) { state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
        const items = g.ok ? ((await g.json()).items || []) : [];
        if (card.hidden) return;
        const n = items.filter(Boolean).length;
        lines = lines.map((l, i) => items[i] || l);
        render(n ? "✨ AI เรียบเรียง " + n + " จาก " + items.length + " ข้อ · ตัวเลขจากระบบ" : "ตัวเลขจากระบบ");
      } catch (e) { render("ตัวเลขจากระบบ"); }
    });
  }
  function copyText(text, btn, box) {
    const selectAll = () => {
      const ul = box.querySelector("ul");
      if (!ul) return;
      const rg = document.createRange(); rg.selectNodeContents(ul);
      const s = window.getSelection(); s.removeAllRanges(); s.addRange(rg);
      btn.textContent = "เลือกข้อความแล้ว กด Ctrl+C";
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(() => { btn.textContent = "✔ คัดลอกแล้ว"; }, selectAll);
    else selectAll();
  }
```

- [ ] **Step 2: Replace `openCustomSheet`**

```js
  function openCustomSheet(st, body, cmp) {
    const today = (cmp.dam || {}).released_mcm != null ? cmp.dam.released_mcm : 10;
    openSheet('<h2>ลองแผนเอง</h2><p class="muted">ล้าน ลบ.ม./วัน วันที่ 1–7 · ผลเป็นแถวในตารางแผน (เก็บได้ 3 แผน)</p>' +
      '<div class="imp-parse"><label for="imp-parse-text">พิมพ์แผนเป็นภาษาไทย</label><div class="imp-parse-row">' +
      '<input id="imp-parse-text" type="text" maxlength="200" autocomplete="off" placeholder="เช่น ระบาย 15 สามวันแล้วลดเหลือ 10">' +
      '<button type="button" class="btn" id="imp-parse-btn">อ่านแผน</button></div><p class="muted" id="imp-parse-msg" aria-live="polite"></p></div>' +
      '<form id="imp-custom" class="imp-custom">' + [1, 2, 3, 4, 5, 6, 7].map((i) => "<label>วันที่ " + i +
        '<input type="number" inputmode="decimal" step="0.1" min="0" max="200" value="' + esc(today) + '"></label>').join("") +
      '<button class="btn primary" type="submit">คำนวณ</button></form>', (box) => {
      const f = box.querySelector("#imp-custom"), msg = box.querySelector("#imp-parse-msg");
      box.querySelector("#imp-parse-btn").addEventListener("click", async () => {
        const text = box.querySelector("#imp-parse-text").value.trim();
        if (!text) return;
        msg.textContent = "กำลังอ่าน…";
        let r;
        try {
          r = await api("/api/impact/case/" + encodeURIComponent(st.case) + "/parse",
            { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
        } catch (e) { msg.textContent = "เชื่อมต่อไม่ได้"; return; }
        if (r.status === 401) { document.getElementById("sheet").hidden = true; state.authed = false; return showLogin("หมดเวลาเข้าสู่ระบบ กรุณาเข้าใหม่"); }
        if (r.status === 429) { msg.textContent = "อ่านแผนบ่อยเกินไป รอ 15 นาที"; return; }
        if (!r.ok) { msg.textContent = "อ่านแผนนี้ไม่ได้ กรอกตัวเลขเอง"; return; }
        const out = await r.json();
        f.querySelectorAll("input").forEach((inp, i) => { inp.value = out.release[i]; });
        msg.textContent = (out.by === "ai" ? "✨ AI อ่านแผนให้แล้ว" : "อ่านแผนแล้ว") + " — ตรวจตัวเลขแล้วกดคำนวณ";
      });
      f.addEventListener("submit", (e) => {
        e.preventDefault();
        document.getElementById("sheet").hidden = true;
        const plan = [...f.querySelectorAll("input")].map((i) => Number(i.value) || 0);
        state.customs = [plan].concat(state.customs.filter((c) => c.join(",") !== plan.join(","))).slice(0, 3);
        loadScenarios(st, body);
      });
    });
  }
```

- [ ] **Step 3: CSS**

Append to `web/impact.css`:

```css
/* v0.34: one ✨ entry (simple story · executive brief), the brief's bullets, a typed plan (D-110) */
#view-impact .imp-ai > summary { list-style: none; display: inline-flex; align-items: center; min-height: 38px; }
#view-impact .imp-ai > summary::-webkit-details-marker { display: none; }
#view-impact .imp-ai[open] { flex: 1 1 100%; }
#view-impact .imp-ai-body { display: grid; gap: 8px; margin-top: 8px; }
#view-impact .imp-brief ul { padding-left: 20px; margin: 4px 0; }
#view-impact .imp-brief li { font-size: 14px; margin: 3px 0; }
.imp-sheet .imp-parse label { font-size: 13px; color: var(--muted); }
.imp-sheet .imp-parse-row { display: flex; gap: 8px; margin: 4px 0; }
.imp-sheet .imp-parse-row input { flex: 1 1 auto; min-width: 0; font: inherit; padding: 8px; border: 1px solid var(--line); border-radius: 8px; min-height: 42px; }
```

- [ ] **Step 4: Syntax check**

Run: `node --check web/impact.js && echo OK`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add web/impact.js web/impact.css
git commit -m "impact tab: one ✨ entry with the simple story and the executive brief (bullets, copy), and a plan typed in Thai that fills the seven boxes (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 13: The browser check covers the grid, the sheets' text budget, ONWR's group and the AI helps

**Files:**
- Modify: `scripts/impact_tab_check.py:55-111` (the case section; the dams-list part before it and the tab/overflow/logout part after it stay)

**Interfaces:**
- Consumes: the DOM from Tasks 9–12.
- Produces: JSON keys `grid_rows`, `grid_cells`, `hatched_cells`, `ladder_rows`, `day_click_legend`, `row_select_sel`, `onwr_group_in_box`, `onwr_unchecked`, `map_follows_case`, `long_paragraphs` (view + every sheet; must be 0), `sheet_river_cells`, `coverage_line`, `brief_items`, `compare_story`, `parsed_plan`, `custom_row`, `session_expiry_shows_login`, plus the existing keys.

- [ ] **Step 1: Replace the case section**

Replace from `        # the case` through the line `        pg.screenshot(path=f"{OUT}/tab_{name}_casemap.png", full_page=False)` with:

```python
        # the case (D-110): the comparison grid, the map following the case, ONWR's group in the app's box
        pg.click('.tabs [data-tab="impact"]'); pg.wait_for_timeout(500)
        pg.click('[data-imp="kaeng-krachan"]'); pg.wait_for_selector("#imp-sc .imp-grid", timeout=40000)
        pg.wait_for_timeout(1500)
        r["case_title"] = pg.inner_text(".imp-title")
        long_p = """(sel) => [...document.querySelectorAll(sel + ' p, ' + sel + ' li')].filter(p => p.innerText.length > 160 &&
            !p.closest('details:not([open])') && !p.closest('.story')).map(p => p.innerText.slice(0, 60))"""
        r["long_paragraphs"] = {"view": pg.evaluate(long_p, "#imp-body")}
        r["chips"] = pg.locator("#imp-body .imp-chips-num .chip").count()
        r["grid_rows"] = pg.locator("#imp-sc .imp-grid > tbody:first-of-type .imp-gr").count()
        r["grid_cells"] = pg.locator("#imp-sc .imp-grid > tbody:first-of-type .imp-gr").first.locator(".imp-c").count()
        r["hatched_cells"] = pg.locator("#imp-sc .imp-c-x").count()
        r["first_screen_chars"] = pg.evaluate("document.getElementById('imp-body').innerText.length")
        r["onwr_group_in_box"] = pg.locator(".legend.layers .imp-onwr-grp").count()
        r["onwr_unchecked"] = pg.evaluate("[...document.querySelectorAll('[data-onwr]')].every(c => !c.checked)")
        r["old_onwr_ctl"] = pg.locator(".imp-onwr-ctl").count()
        if name == "desk":
            r["map_follows_case"] = pg.evaluate("(() => { const c = (window.map || map).getCenter(); return c.lat > 12.5 && c.lat < 13.4 && c.lng > 99.2 && c.lng < 100.2; })()")
            pg.locator("#imp-sc .imp-gr").nth(1).click(); pg.wait_for_timeout(500)
            r["row_select_sel"] = pg.locator("#imp-sc .imp-gr.imp-sel").count()
            pg.click('[data-dayh="2"]'); pg.wait_for_timeout(500)
            r["day_click_legend"] = "วันที่ 3" in pg.inner_text(".imp-reach-legend")
            pg.click('[data-dayh="2"]'); pg.wait_for_timeout(300)
        pg.click("#imp-sc .imp-ladder-btn"); pg.wait_for_timeout(300)
        r["ladder_rows"] = pg.locator("#imp-sc .imp-ladder .imp-gr").count()
        pg.click("#imp-sc .imp-ladder-btn"); pg.wait_for_timeout(200)
        pg.screenshot(path=f"{OUT}/tab_{name}_case_first.png", full_page=False)
        # the ★ row → its sheet: chart, reservoir table, river grid, coverage, (outside), compare
        pg.locator("#imp-sc .imp-gr").first.locator(".imp-open").click()
        pg.wait_for_selector("#sheet:not([hidden]) .imp-rgrid", timeout=8000); pg.wait_for_timeout(800)
        r["sheet_river_cells"] = pg.locator("#detail .imp-rgrid td.imp-m").count()
        r["coverage_line"] = pg.inner_text("#detail .imp-cover")[:120]
        r["plan_day_chips"] = pg.locator("#detail .imp-days [data-day]").count()
        r["long_paragraphs"]["plan_sheet"] = pg.evaluate(long_p, "#detail")
        r["reach_legend"] = pg.locator(".imp-reach-legend").count()
        pg.screenshot(path=f"{OUT}/tab_{name}_plan_sheet.png", full_page=False)
        if pg.locator("#detail .ai-btn").count():
            pg.click("#detail .ai-btn"); pg.wait_for_selector("#detail .story-text:not(.shimmer)", timeout=30000)
            r["compare_story"] = pg.inner_text("#detail .story-text")[:200]
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        # the ℹ️ sheets are the on-demand method prose (GUIDELINES §6c-9): measured and reported, not a failure
        pg.click(".imp-info summary")
        r["long_paragraphs_info"] = {}
        for k in ("val", "river", "matrix", "method", "req"):
            pg.click(f'[data-info="{k}"]'); pg.wait_for_selector("#sheet:not([hidden]) #detail h2", timeout=8000)
            r["long_paragraphs_info"][k] = len(pg.evaluate(long_p, "#detail"))
            pg.click("#detail .close"); pg.wait_for_timeout(200)
        # a chip → the dam sheet; a river node → the station's own sheet
        pg.locator("#imp-body .imp-chips-num .chip").first.click(); pg.wait_for_selector("#sheet:not([hidden]) .imp-kv", timeout=8000)
        r["dam_sheet"] = pg.inner_text("#detail h2")[:40]
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        pg.locator(".imp-strip .imp-node").nth(1).click(); pg.wait_for_selector("#sheet:not([hidden]) #detail h2", timeout=15000)
        r["station_sheet"] = pg.inner_text("#detail h2")[:40]
        pg.click("#detail .close"); pg.wait_for_timeout(300)
        # a plan typed in Thai fills the boxes; คำนวณ adds a custom row
        pg.click("#imp-custom-btn"); pg.wait_for_selector("#sheet:not([hidden]) #imp-custom", timeout=8000)
        pg.fill("#imp-parse-text", "ระบาย 15 สามวันแล้วลดเหลือ 10"); pg.click("#imp-parse-btn")
        pg.wait_for_function("document.getElementById('imp-parse-msg').innerText.includes('กดคำนวณ')", timeout=20000)
        r["parsed_plan"] = pg.eval_on_selector_all("#imp-custom input", "els => els.map(e => Number(e.value))")
        r["long_paragraphs"]["custom_sheet"] = pg.evaluate(long_p, "#detail")
        pg.click("#imp-custom button[type=submit]"); pg.wait_for_selector("#imp-sc .imp-custom-row", timeout=30000)
        r["custom_row"] = pg.locator("#imp-sc .imp-custom-row").count()
        # ✨ menu: the simple story and the executive brief (bullets + copy)
        pg.click("#imp-sc .imp-ai > summary"); pg.wait_for_timeout(300)
        pg.click("#imp-sc .imp-ai-body .ai-btn:not(.imp-brief-btn)"); pg.wait_for_selector("#imp-sc .story-text:not(.shimmer)", timeout=30000)
        r["ai_story"] = pg.inner_text("#imp-sc .story-text")[:200]
        pg.click("#imp-sc .imp-brief-btn"); pg.wait_for_selector("#imp-sc .imp-brief li", timeout=30000)
        r["brief_items"] = pg.locator("#imp-sc .imp-brief li").count()
        r["long_paragraphs"]["brief"] = pg.evaluate(long_p, "#imp-sc .imp-brief")
        pg.screenshot(path=f"{OUT}/tab_{name}_scenarios.png", full_page=False)
        pg.click("#imp-onmap"); pg.wait_for_timeout(1500)
        r["case_tooltips"] = pg.locator(".imp-tip").count()
        pg.screenshot(path=f"{OUT}/tab_{name}_casemap.png", full_page=False)
```

After the `r["overflow"] = over` and `tab_label_fits` lines, and before `pg.click("#imp-logout")`, add the session-expiry check:

```python
        # Review Focus 5: an expired session in the middle of the work shows the login form
        pg.click('.tabs [data-tab="impact"]'); pg.wait_for_timeout(500)
        ctx.clear_cookies()
        pg.click('[data-imp="dams"]'); pg.click('[data-imp="kaeng-krachan"]')
        try:
            pg.wait_for_selector("#imp-login", timeout=15000)
            r["session_expiry_shows_login"] = True
        except Exception:
            r["session_expiry_shows_login"] = False
        pg.fill("#imp-pw", os.environ["IMPACT_PW"]); pg.click("#imp-login button[type=submit]")
        pg.wait_for_selector("#imp-sc .imp-grid, .imp-dams .item", timeout=40000)  # back on the case it was showing
```

Replace the `after_logout_overlays` line with:

```python
        r["after_logout_overlays"] = pg.evaluate("document.querySelectorAll('.imp-onwr-grp, .imp-reach-legend').length")
```

At the end, before `print(json.dumps(...))`, add a pass/fail summary:

```python
fails = []
for name, r in rep.items():
    lp = r.get("long_paragraphs", {})
    if any(v for v in lp.values()):
        fails.append(f"{name}: paragraphs over 160 characters {lp}")
    for k, want in (("grid_cells", 7), ("onwr_group_in_box", 1), ("old_onwr_ctl", 0), ("ladder_rows", 13), ("sheet_river_cells", 35),
                    ("session_expiry_shows_login", True), ("after_logout_overlays", 0)):
        if r.get(k) != want:
            fails.append(f"{name}: {k} = {r.get(k)!r}, want {want!r}")
    if not r.get("onwr_unchecked"):
        fails.append(f"{name}: an ONWR layer is on by default")
    if r.get("parsed_plan") != [15, 15, 15, 10, 10, 10, 10]:
        fails.append(f"{name}: parsed_plan {r.get('parsed_plan')}")
    if name == "desk" and not (r.get("map_follows_case") and r.get("day_click_legend") and r.get("row_select_sel") == 1):
        fails.append(f"{name}: map_follows_case/day_click_legend/row_select_sel {r.get('map_follows_case')}/{r.get('day_click_legend')}/{r.get('row_select_sel')}")
    if r.get("console_errors"):
        fails.append(f"{name}: console errors {r['console_errors']}")
rep["fails"] = fails
```

(`ladder_rows` = 13 holds while the search cap is 24–25; `sheet_river_cells` = 5 gauges × 7 days.)

- [ ] **Step 2: Syntax check**

Run: `python3 -m py_compile scripts/impact_tab_check.py && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add scripts/impact_tab_check.py
git commit -m "check: the impact tab check covers the grid, the ladder, the day header, ONWR's group in the app's box, the text budget of every sheet, the brief, compare, a typed plan and an expired session (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

---

### Task 14: Deploy, rebuild the case state, validate as a first-time ONWR engineer, fix

**Files:**
- Modify (only if the validation finds problems): the files of Tasks 1–13, each fix with its own test where it is server-side.

- [ ] **Step 1: Full suite, then deploy**

Run, one at a time:

```bash
cd /root/flood2026 && git status --short && git branch --show-current   # feat/impact-plan-grid
docker compose build worker && docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q
docker compose exec -T db psql -U floodwatch -d floodwatch -At -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction'"
docker compose build app worker forecaster && docker compose up -d app worker forecaster
sleep 20; curl -s localhost:3000/api/health | python3 -m json.tool | head -20
```

Expected: all tests pass; `0` idle transactions; health `"ok"`-style output with fresh data. (KI-284: never redeploy over an open research transaction.)

- [ ] **Step 2: Rebuild the case state and ONWR's layers once, as the worker would**

```bash
docker compose exec -T worker python -c "from floodwatch import impact; s = impact.run(); print(sorted(s.get('reach_km', {}).items()), len(s.get('places', {})))"
docker compose exec -T worker python -c "from floodwatch import collectors; print(collectors.onwr_flood())"
```

Expected: five reach lengths (B.18 ≈ 62, B.10 ≈ 46, B.15 ≈ 21, B.16 ≈ 11, PCH001 ≈ 8 km) and 5 place lists; an ONWR update time.

- [ ] **Step 3: Run the browser check against production**

```bash
cd /root/flood2026 && mkdir -p /tmp/claude-0/-root-flood2026/885224ef-41e4-4223-a211-df38ac660eab/scratchpad/check && OUT_DIR=/tmp/claude-0/-root-flood2026/885224ef-41e4-4223-a211-df38ac660eab/scratchpad/check IMPACT_PW="$(sed -n 's/^IMPACT_PASSWORD=//p' .env)" timeout 600 python3 scripts/impact_tab_check.py > /tmp/claude-0/-root-flood2026/885224ef-41e4-4223-a211-df38ac660eab/scratchpad/check/report.json; python3 -c "import json; r = json.load(open('/tmp/claude-0/-root-flood2026/885224ef-41e4-4223-a211-df38ac660eab/scratchpad/check/report.json')); print(r['fails'])"
```

Expected: `[]`. For every entry in `fails`: find the cause, fix it (server-side fixes with a test first), re-run Steps 1 and 3.

- [ ] **Step 4: Look at the screenshots as a first-time ONWR engineer**

Read `tab_m390_case_first.png`, `tab_desk_case_first.png`, `tab_desk_plan_sheet.png`, `tab_m390_plan_sheet.png`, `tab_desk_scenarios.png`, `tab_desk_casemap.png` with the Read tool. Answer, and write the answers into the session notes for Task 15:
1. Can "what happens if we release 15 for 7 days?" be answered in ≤ 3 actions with no paragraph to read (➕ ลองแผนเอง → type "15" → อ่านแผน/คำนวณ → the new row)?
2. Is the ★'s ⚠ impossible to miss (row, hatched cells, sheet line)?
3. Does any ONWR shape show without being ticked? (must not)
4. Do labels fit at 390 px (no clipped text, the km under the label)?
Fix what fails; re-run Step 3.

- [ ] **Step 5: Public page regression**

Run: `timeout 1800 python3 scripts/ux_consistency.py /tmp/claude-0/-root-flood2026/885224ef-41e4-4223-a211-df38ac660eab/scratchpad/check/ux.json 6 | tail -15`
Expected: the C1–C20 summary with no new findings (KI-291 is a known intermittent).

- [ ] **Step 6: Commit any fixes**

```bash
git add -A src web tests scripts && git status --short
git commit -m "impact tab: fixes from the first-time ONWR engineer walk (D-110)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
```

(Skip the commit when nothing changed.)

---

### Task 15: Docs, version and release v0.34.0

**Files:**
- Modify: `src/floodwatch/__init__.py` and `pyproject.toml` (version 0.34.0); `CHANGELOG.md`; `docs/plan/DECISIONS.md` (D-110); `docs/KNOWN_ISSUES.md` (KI-318, KI-319 + index rows); `docs/KNOWLEDGE.md` (§28 corrected, §30 new); `docs/GUIDELINES.md` (§6c-11); `docs/APPROACH_AND_METHODS.md` (§19.27); `docs/MODELS.md` (§11 note); `docs/SOURCES.md` (§2p clipping, Nominatim/Overpass row); `docs/ARCHITECTURE.md` (endpoints, data file, layer box); `README.md`; `docs/UX_VALIDATION.md`; `docs/plan/impact-kaeng-krachan.md`; `docs/plan/PLAN.md` (impact row); `HANDOFF.md` (§3x, header, code map)

- [ ] **Step 1: Decision D-110** — append to `docs/plan/DECISIONS.md`:

```markdown
### D-110 — The impact tab's release plans as a comparison grid; outside-the-data plans labelled, not hidden (owner's exception to GUIDELINES §6c-6); ONWR's layers off by default; river km + villages; four AI helps
- **Date:** 2026-10-06 · **Status:** accepted (owner's answers, Grillme 2026-10-06; spec `docs/superpowers/specs/2026-10-06-impact-plan-grid-design.md`)
- **Context:** owner: improve the impact tab ("massive with text"), validate the flood areas ("some are far away from river"), ONWR's goals (release scenarios for 6–7 days → water level and flood coverage), users who control releases, AI may assist. Evidence: ONWR's cells were whole zoom-10 tiles (118 of 134 warning cells outside the case box, most near Ratchaburi; KI-318); the ★ plan (21.5 ≈ 249 m³/s for 7 days) ran every gauge beyond its rating's data while the engine's flag reached neither the ★ nor the page (KI-319); a 309-character paragraph; empty "best for" badges; the desktop map stayed on Bangkok.
- **Decision:** (1) **Label only** (owner, against the recommended "show, river unjudged"): the ★ rule and every number stay; "⚠ นอกช่วงข้อมูล" with each gauge's flow and the rating's highest flow appears on the row, hatched day cells, the sheet and the brief — an owner exception to GUIDELINES §6c-6 for this tab. (2) ONWR's layers clipped to the case box, off by default, inside the app's one layer box as "สทนช. · ไม่ขึ้นกับแผนระบาย". (3) Flood coverage until ONWR's maps or a LiDAR DEM: km of river near or over its bank per plan and day (reaches by nearest gauge ≤ 10 km) and the villages + อำเภอ along them (OpenStreetMap; no ตำบล boundaries there). (4) The case view is a grid: ★, today, the engine's picks (goal icons), up to three own plans, a collapsed ladder of constant releases every 2 ล้าน ลบ.ม./วัน; a 7-day strip of the worst gauge per plan; a day header and a selected row colour the river. (5) A goal names a best plan only where plans differ. (6) AI (GLM, on tap): today's ✨, an executive brief (plain bullets, copy), compare with the ★, a plan typed in Thai (rules first; 7 numbers that only fill the boxes; never logged).
- **Consequences:** ONWR's engineers compare plans at a glance and see where the river data end; the ★ may still sit outside the data by the owner's choice, so the label must stay impossible to miss. The first-time-engineer walk and the text budget are checked by `scripts/impact_tab_check.py` on every release.
- **Revisit:** when ONWR's flood maps by release level, a LiDAR DEM, เขื่อนเพชร canal flows or 2018 river records arrive (OWNER_ACTIONS FLOODMAP, DEM); or if ONWR reads the ★ as advice.
```

- [ ] **Step 2: KI-318 and KI-319** — add two sections to `docs/KNOWN_ISSUES.md` (and their rows in its summary table) with: symptom, evidence (the counts above, the live scenario numbers from `scratchpad/scen.json`: B.18 256/143, B.10 192/86, B.16 182/73 m³/s), cause (tiles not clipped; the `outside` flag computed and unused), fix (Tasks 1, 3–4, 9–10), status ✅ fixed in v0.34.0 (KI-319: "labelled; the ★ rule unchanged by the owner's choice, D-110").

- [ ] **Step 3: KNOWLEDGE** — in §28 replace "marks 176 and 161 ≈ 1.1 km cells at class 3 over the case area" with the clipped counts printed by `docker compose exec -T worker python -c "from floodwatch import db, impact; import json; c=db.connect_readonly().__enter__(); o=impact.clip_onwr(db.get_state(c,'onwr_flood_kaeng_krachan')); print({k: len(v['features']) for k,v in o['layers'].items()})"` and the note that earlier counts included whole tiles (KI-318). Add §30 "The impact tab's coverage proxy (2026-10-06)": reach lengths, OSM coverage (villages 3/3, ตำบล 1/3, no admin_level 8 in Overpass), the build file's coverage counts from `research/2026-10-06_kk_reach_places.log`, the Aug 2018 news (spillway overflow from 6 Aug 2018, five riverside districts warned — ThaiPBS, Khaosod, 🟡 news, not gauge data).

- [ ] **Step 4: GUIDELINES §6c-11** — add after §6c-10:

```markdown
### 6c-11. Lessons from the plan grid (D-110, KI-318, KI-319)
- **A flag the engine computes must reach the decision and the screen.** `outside` was computed for every plan and day and
  used nowhere; the ★ recommended a release 1.7× beyond the river data. Test that every flag a model sets is either used
  by a rule or shown.
- **Clip a tiled layer to the area it is shown for** — whole tiles carry neighbours 30–56 km away.
- **Another agency's layer is off by default where it can be misread as ours**, and sits in the app's one layer box with
  "ไม่ขึ้นกับแผน" in its title (the owner read ONWR's warning as the plan's flood area).
- **Measure sheets too:** the 160-character rule is checked in the view and in every sheet the tab opens.
- **An owner exception to a rule is written into the rule's section**, with its decision: §6c-6 ("never show an untested
  number with a warning") does not apply to the impact tab's outside-the-data plans by the owner's choice (D-110) — they
  carry the ⚠ label everywhere they appear.
```

and append to §6c-6's first bullet: " Exception (owner, D-110): the impact tab's plans beyond the river data keep their numbers with the ⚠ นอกช่วงข้อมูล label."

- [ ] **Step 5: APPROACH §19.27, MODELS §11, SOURCES, ARCHITECTURE, README, UX_VALIDATION, the pilot plan, PLAN** — write, each in its own file's style:
  - APPROACH §19.27 "Comparing plans without hiding what the data do not cover (D-110)": the day-cell rule (`gauge_status`, worst gauge, hatched when any gauge is outside), km at risk, villages, the ladder, why "label only".
  - MODELS §11 (end): "Outside the data (D-110, KI-319): a plan's day is outside when a gauge's flow exceeds its rating's highest flow (B.18 143, B.10 86, B.16 73 m³/s on 2026-10-06); the downstream gains were learned where เขื่อนเพชร absorbed release changes, so above the canals' capacity the river can rise more than the plan shows."
  - SOURCES: §2p a line "cells are clipped to the case box (KI-318)"; a row for Nominatim reverse (villages; zoom 14; 3/3 villages, 1/3 ตำบล; one-time build, 1 call per 1.5 s) and Overpass (no admin_level 8 here; 2 of 3 queries 504).
  - ARCHITECTURE: the new endpoints (`explain?q=brief|compare`, `POST …/parse`), `src/floodwatch/plan_parse.py`, `src/floodwatch/data/kk_reach_places.json`, the ONWR group inside the app's layer box.
  - README: the impact tab paragraph (grid, outside label, coverage proxy, AI helps).
  - UX_VALIDATION: the first-time ONWR engineer walk from Task 14 Step 4 (the four answers) and the check's numbers.
  - `docs/plan/impact-kaeng-krachan.md`: a "v0.34.0: the plan grid (D-110)" section.
  - PLAN: the impact row mentions v0.34.0 and D-110.

- [ ] **Step 6: Version, CHANGELOG, HANDOFF**
  - `src/floodwatch/__init__.py`: `__version__ = "0.34.0"`; `pyproject.toml`: `version = "0.34.0"`.
  - `CHANGELOG.md`: move the "Unreleased" items under `## v0.34.0 — 2026-10-06` and add this release's items (grid, labels, ONWR clipping/default, coverage proxy, AI helps, check).
  - `HANDOFF.md`: header line for v0.34.0; §3x table (owner requests → results → where, incl. the owner's "label only" choice and the improved-instructions advice given in chat); code-map additions (`plan_parse.py`, `scenarios.day_cells/outside_detail/short_label/ladder_ids`, `impact.clip_onwr/reach_km/reach_places`, `explain.brief/compare_lines/retell_items`, the data file, the research script); test count from Task 14 Step 1.

- [ ] **Step 7: Tests, commit, deploy the version, release**

Run one at a time, each checked:

```bash
cd /root/flood2026 && git status --short
docker compose build worker && docker compose run --rm --no-deps -v "$PWD/research:/app/research:ro" worker pytest -q
git add -A docs README.md CHANGELOG.md HANDOFF.md src/floodwatch/__init__.py pyproject.toml
git diff --cached | grep -ciw "$(sed -n 's/^IMPACT_PASSWORD=//p' .env)" || true   # must print 0
git commit -m "release: v0.34.0 — the impact tab's release plans as a comparison grid; outside-the-data plans labelled (owner's choice, D-110, KI-319); ONWR's cells clipped and off by default (KI-318); river km + villages; brief, compare and typed plans" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01AE3CfUkWfTj2P7tWkkua6S"
git checkout main && git pull --ff-only && git merge --ff-only feat/impact-plan-grid
docker compose build app worker forecaster && docker compose up -d app worker forecaster
sleep 20; curl -s localhost:3000/api/stats | python3 -c "import json,sys; print(json.load(sys.stdin).get('version'))"
git tag -a v0.34.0 -m "v0.34.0"
git push origin main
git push origin v0.34.0
gh release create v0.34.0 --verify-tag --title "v0.34.0 — the impact tab's plan grid" --notes-file <(sed -n '/^## v0.34.0/,/^## v0.33/p' CHANGELOG.md | head -n -1)
```

Expected: tests pass; the grep prints `0`; the version prints `0.34.0`; each push and the release succeed. Then re-run Task 14 Step 3 once more against production (validation after the release, GUIDELINES §6c-4) and record its `fails` (must be `[]`) in HANDOFF §3x.
