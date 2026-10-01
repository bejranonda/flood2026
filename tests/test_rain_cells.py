"""Task 2 (v0.16, D-064): 0.5° Open-Meteo rain cells for gauges outside the Bangkok focus area."""
import inspect

from floodwatch import rain_cells


def test_cells_snap_to_the_nearest_half_degree():
    assert rain_cells.cell_of(16.49, 101.26) == ("g_16.5_101.5", 16.5, 101.5)  # URTU07, Loei
    assert rain_cells.cell_of(7.24, 100.74) == ("g_7.0_100.5", 7.0, 100.5)
    assert rain_cells.cell_of(16.25, 100.25)[0] == "g_16.5_100.5"  # halves round up, never banker's rounding


def test_focus_gauges_keep_the_bangkok_rain_points():
    assert rain_cells.rain_point_for(True, 13.76, 100.50) == "bkk_central"  # proven Bangkok inputs unchanged
    assert rain_cells.rain_point_for(False, 16.49, 101.26) == "g_16.5_101.5"
    assert rain_cells.rain_point_for(False, None, None) is None


def test_a_place_uses_a_bangkok_point_nearby_and_a_cell_elsewhere():
    assert rain_cells.rain_point_at(13.75, 100.52) == "bkk_central"
    assert rain_cells.rain_point_at(16.49, 101.26) == "g_16.5_101.5"


def test_all_cells_only_for_gauges_outside_focus_with_coordinates():
    st = [{"in_focus": False, "lat": 16.49, "lon": 101.26}, {"in_focus": False, "lat": 16.6, "lon": 101.4},
          {"in_focus": True, "lat": 13.7, "lon": 100.5}, {"in_focus": False, "lat": None, "lon": None}]
    assert rain_cells.all_cells(st) == {"g_16.5_101.5": (16.5, 101.5)}


def test_payload_split_handles_one_location_as_a_dict():
    # Open-Meteo answers a JSON list for several coordinates and a plain object for one (checked 2026-09-30)
    one = {"hourly": {"time": []}}
    assert rain_cells.split_payload(one, ["a"]) == [("a", one)]
    assert rain_cells.split_payload([one, one], ["a", "b"]) == [("a", one), ("b", one)]


def test_batches_of_fifty():
    assert [len(b) for b in rain_cells.batches(list(range(120)))] == [50, 50, 20]


def test_rain_readers_use_each_points_latest_issue():
    # cells refresh every 3 h, Bangkok points hourly: a global max(issue_time) would drop the cells at other hours
    assert "GROUP BY point" in rain_cells.LATEST_ISSUE
    from floodwatch import api, forecast
    for fn in (forecast.run_all, api.point_check, api.rain):
        src = inspect.getsource(fn)
        assert "SELECT max(issue_time) FROM weather_forecast)" not in src, fn.__name__


def test_cell_requests_join_coordinates_in_batches():
    from floodwatch import collectors
    cells = {f"g_{i}.0_100.0": (float(i), 100.0) for i in range(60)}
    reqs = collectors.cell_requests(cells, "https://api.open-meteo.com/v1/forecast", {"hourly": "precipitation"})
    assert [len(ids) for ids, _ in reqs] == [50, 10]
    ids, url = reqs[1]
    lats = [cells[i][0] for i in ids]  # the answer list follows the coordinate order: ids and coordinates aligned
    assert "latitude=" + "%2C".join(f"{x:.1f}" for x in lats) + "&" in url and "hourly=precipitation" in url


# --- v0.16.4 (Q42): Bangkok and its neighbours at the model's own ~8 km grid, for what people see -----------------
def test_fine_points_snap_to_the_model_grid():
    pid, lat, lon = rain_cells.fine_of(13.7563, 100.5018)
    assert pid == "f_13.7434_100.4959" and (lat, lon) == (13.7434, 100.4959)  # grid measured 2026-10-01
    assert rain_cells.fine_of(13.7563 + 0.02, 100.5018)[0] == pid  # within half a step (0.035°): same cell


def test_fine_points_cover_the_bangkok_region_gauges_only():
    st = [{"province": "กรุงเทพมหานคร", "lat": 13.75, "lon": 100.50}, {"province": "นนทบุรี", "lat": 13.91, "lon": 100.50},
          {"province": "เลย", "lat": 17.49, "lon": 101.72}]
    pts = rain_cells.fine_points(st)
    assert all(13.5 < la < 14.1 and 100.3 < lo < 100.7 for la, lo in pts.values())  # nothing near Loei
    assert rain_cells.fine_of(13.91, 100.50)[0] in pts and 6 <= len(pts) <= 40   # the 3 x 3 cells around each gauge


def test_a_place_in_bangkok_prefers_its_fine_point():
    fine = {"f_13.7434_100.4959"}
    assert rain_cells.rain_point_at(13.7563, 100.5018, fine) == "f_13.7434_100.4959"
    assert rain_cells.rain_point_at(13.7563, 100.5018) == "bkk_central"  # no fine data yet: as before
    assert rain_cells.rain_point_at(16.49, 101.26, fine) == "g_16.5_101.5"


def test_pins_and_region_lines_read_the_fine_points():
    from floodwatch import api
    assert "_fine_ids()" in inspect.getsource(api.point_check)
    regions_ = api.point_regions([{"province": "นนทบุรี", "lat": 13.91, "lon": 100.50, "code": "X"}])
    assert regions_[rain_cells.fine_of(13.91, 100.50)[0]] == "metro" and regions_[rain_cells.cell_of(13.91, 100.50)[0]] == "metro"
