"""Build static/map/regions.geojson — country polygons for the "browse on map" page.

Takes the Natural Earth admin-1 (province) GeoJSON in MAPA/ and dissolves it down
to one polygon per country (keyed by ISO-3166-1 alpha-2, matching the airport data
in build_map_connectivity.py), simplifies the geometry for the browser, and keeps
only the countries that actually have a flightable airport (the user's "leave only
the regions that have airports" rule).

Pipeline:
  1. mapshaper: dissolve admin-1 -> country by `iso_a2`, simplify, clean topology.
  2. Python: drop non-flightable / disputed (-1) countries, strip properties to a
     lean {iso, name}, write the final compact GeoJSON.

Requires Node.js (mapshaper is run via `npx -y mapshaper`, no global install).

Usage:
    python scripts/build_map_regions.py
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "MAPA", "static", "regionsdisc.geojson")
OUT_DIR = os.path.join(ROOT, "static", "map")
OUT = os.path.join(OUT_DIR, "regions.geojson")
TMP = os.path.join(OUT_DIR, "_regions_dissolved.geojson")

# Simplification: % of vertices to keep. Admin-1 is high-res; countries render
# fine far lower. Lower = smaller file. ~5% gives a clean ~1-2 MB world.
SIMPLIFY_PCT = "4%"

AIRPORTS_URL = "https://api.travelpayouts.com/data/en/airports.json"


def flightable_countries():
    """ISO2 set of countries that have at least one flightable airport."""
    req = urllib.request.Request(
        AIRPORTS_URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        airports = json.load(r)
    return {a["country_code"] for a in airports
            if a.get("flightable") and a.get("country_code")}


def run_mapshaper():
    """Dissolve admin-1 -> country, simplify, clean. Writes TMP."""
    os.makedirs(OUT_DIR, exist_ok=True)
    # npx is a .cmd shim on Windows -> needs shell=True there.
    cmd = [
        "npx", "-y", "mapshaper", SRC,
        "-dissolve", "iso_a2", "copy-fields=admin",
        "-simplify", SIMPLIFY_PCT, "keep-shapes",
        "-clean",
        "-o", TMP, "format=geojson", "precision=0.001",
    ]
    print("Running mapshaper (dissolve + simplify)…")
    subprocess.run(cmd, check=True, shell=(os.name == "nt"))


def post_process(flightable):
    """Filter to flightable countries, slim properties, write OUT."""
    with open(TMP, encoding="utf-8") as f:
        data = json.load(f)

    kept = []
    dropped = []
    for feat in data.get("features", []):
        props = feat.get("properties") or {}
        iso = props.get("iso_a2")
        if not iso or iso in ("-1", "-99"):
            continue
        if iso not in flightable:
            dropped.append(iso)
            continue
        feat["properties"] = {"iso": iso, "name": props.get("admin") or iso}
        kept.append(feat)

    data["features"] = kept
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(OUT) / (1024 * 1024)
    print(f"Wrote {OUT} — {len(kept)} countries, {size_mb:.2f} MB")
    if dropped:
        print(f"  (dropped {len(dropped)} non-flightable: {', '.join(sorted(set(dropped)))})")
    os.remove(TMP)


def main():
    if not os.path.exists(SRC):
        sys.exit(f"Source not found: {SRC}")
    flightable = flightable_countries()
    print(f"{len(flightable)} flightable countries")
    run_mapshaper()
    post_process(flightable)


if __name__ == "__main__":
    main()
