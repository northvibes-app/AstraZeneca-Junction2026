"""Download the boundaries of the wellbeing services counties and turn them into SVG paths.

Source: Statistics Finland, statistical area boundaries (generalised 1:1,000,000),
layer tilastointialueet:hyvinvointialue1000k_2025 on geo.stat.fi. This is the most
detailed generalisation the service offers; the 1:4,500,000 layer looks coarse
once the map zooms in on a single region.
The region codes in that layer (01-21, 90 Helsinki, 91 Åland) are the same codes
the pipeline uses, so shapes and figures join without a lookup table.

The result is a small .js file the map page can load straight from disk.

Run:  python3 pipeline/fetch_region_shapes.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from net import get_json      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAYER = "tilastointialueet:hyvinvointialue1000k_2025"
URL = ("https://geo.stat.fi/geoserver/tilastointialueet/wfs?service=WFS&version=2.0.0"
       f"&request=GetFeature&typeName={LAYER}&outputFormat=application/json&srsName=EPSG:3067")
MIN_ISLAND_KM2 = 1       # islands smaller than this are dropped to keep the file small


def ring_area_km2(ring):
    """Shoelace formula. Coordinates are metres in ETRS-TM35FIN."""
    total = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
    return abs(total) / 2 / 1e6


def main():
    features = get_json(URL, timeout=300)["features"]

    polygons = {}
    for f in features:
        geom = f["geometry"]
        parts = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        outer_rings = [[(p[0], p[1]) for p in part[0]] for part in parts]   # holes are not needed
        largest = max(outer_rings, key=ring_area_km2)
        keep = [r for r in outer_rings if r is largest or ring_area_km2(r) >= MIN_ISLAND_KM2]
        polygons[f["properties"]["hyvinvointialue"]] = (f["properties"]["name"], keep)

    xs = [x for _, rings in polygons.values() for ring in rings for x, _ in ring]
    ys = [y for _, rings in polygons.values() for ring in rings for _, y in ring]
    min_x, max_y = min(xs), max(ys)

    def to_svg(x, y):
        # 1 SVG unit = 1 km. North is up, so the y axis is flipped.
        # Two decimals = 10 m, fine enough for the closest zoom (City of Helsinki).
        return round((x - min_x) / 1000, 2), round((max_y - y) / 1000, 2)

    regions = []
    for code in sorted(polygons):
        name, rings = polygons[code]
        path, points = [], []
        for ring in rings:
            pts = [to_svg(x, y) for x, y in ring]
            points += pts
            path.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
        bx, by = [p[0] for p in points], [p[1] for p in points]
        regions.append({"code": code,
                        "name": name.replace(" wellbeing services county", ""),
                        "d": "".join(path),
                        "bbox": [min(bx), min(by), round(max(bx) - min(bx), 1),
                                 round(max(by) - min(by), 1)]})

    shapes = {"source": "Statistics Finland, statistical area boundaries 2025 (1:1,000,000)",
              "width": round((max(xs) - min_x) / 1000, 1),
              "height": round((max_y - min(ys)) / 1000, 1), "regions": regions}
    out = ROOT / "pipeline/reference/region_shapes.js"
    out.write_text("window.REGION_SHAPES = " + json.dumps(shapes, ensure_ascii=False) + ";\n",
                   encoding="utf-8")
    print(f"{out.name}: {len(regions)} regions, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
