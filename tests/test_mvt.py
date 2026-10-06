"""A dependency-free Mapbox Vector Tile reader for ONWR's flood layers (owner 2026-10-06: ONWR's layers on the impact map).
The tile here is encoded by the test itself (protobuf by hand), so no third-party data sits in the repository."""
import math

from floodwatch import mvt


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _field(num: int, wire: int, payload: bytes) -> bytes:
    key = _varint((num << 3) | wire)
    return key + (_varint(len(payload)) + payload if wire == 2 else payload)


def _packed(nums) -> bytes:
    return b"".join(_varint(n) for n in nums)


def _zz(n: int) -> int:
    return (n << 1) ^ (n >> 31)


def _tile():
    # one layer "flood_warn", extent 4096, one polygon feature: a square 0..2048 in tile coordinates, class_risk 3
    geom = [(1 << 3) | 1, _zz(0), _zz(0),            # MoveTo 1: (0, 0)
            (3 << 3) | 2, _zz(2048), _zz(0), _zz(0), _zz(2048), _zz(-2048), _zz(0),  # LineTo 3
            (1 << 3) | 7]                             # ClosePath
    feature = _field(1, 0, _varint(7)) + _field(2, 2, _packed([0, 0, 1, 1])) + _field(3, 0, _varint(3)) + _field(4, 2, _packed(geom))
    values = _field(4, 2, _field(4, 0, _varint(3))) + _field(4, 2, _field(1, 2, "ปกติ".encode()))
    layer = (_field(15, 0, _varint(2)) + _field(1, 2, b"flood_warn") + _field(2, 2, feature) +
             _field(3, 2, b"class_risk") + _field(3, 2, b"name") + values + _field(5, 0, _varint(4096)))
    return _field(3, 2, layer)


def test_a_tile_decodes_to_layers_features_properties_and_rings():
    layers = mvt.decode(_tile())
    f = layers["flood_warn"]["features"][0]
    assert layers["flood_warn"]["extent"] == 4096 and f["id"] == 7 and f["type"] == 3
    assert f["properties"] == {"class_risk": 3, "name": "ปกติ"}
    assert f["rings"] == [[(0, 0), (2048, 0), (2048, 2048), (0, 2048), (0, 0)]]


def test_tile_coordinates_become_latitude_and_longitude():
    z, x, y = 10, 796, 474
    lat, lon = mvt.to_latlon(0, 0, z, x, y, 4096)  # the tile's north-west corner
    n = 2 ** z
    assert abs(lon - (x / n * 360 - 180)) < 1e-9
    assert abs(lat - math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))) < 1e-9
    assert mvt.tiles_for_bbox(12.6, 99.3, 13.3, 100.1, 10) == [(x_, y_) for x_ in range(794, 797) for y_ in range(473, 476)]


def test_an_empty_or_broken_tile_is_no_features():
    assert mvt.decode(b"") == {}


def test_onwr_layers_reads_each_layers_tiles_with_its_update_time_and_skips_empty_tiles():
    import json as _json
    from floodwatch import collectors

    class R:
        def __init__(self, status, body):
            self.status, self.body = status, body
    calls = []

    def get(url):
        calls.append(url)
        if url.endswith("tilejson.json"):
            return R(200, _json.dumps({"data_updated": "2026-10-06T05:16:21+00:00"}).encode())
        if "/flood-warn/10/795/474.pbf" in url:
            return R(200, _tile())
        return R(404, b"")
    out = collectors.onwr_layers((12.6, 99.3, 13.3, 100.1), get=get)
    assert set(out) == set(collectors.ONWR_LAYERS) and out["flood-warn"]["updated"] == "2026-10-06T05:16:21+00:00"
    f = out["flood-warn"]["features"]
    assert len(f) == 1 and f[0]["cls"] == 3
    lat, lon = mvt.to_latlon(0, 0, 10, 795, 474)
    assert f[0]["rings"][0][0] == [round(lat, 5), round(lon, 5)]
    assert out["flood-forecast-d1"]["features"] == [] and sum(1 for u in calls if u.endswith(".pbf")) == 9 * len(collectors.ONWR_LAYERS)
