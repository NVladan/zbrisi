"""Build the flight-connectivity snapshot for the "browse on map" page.

For every flightable city we run one Aviasales "anywhere" search (cheapest fare
per destination) and bucket the results by country. The output is a static
snapshot the map page serves directly:

  static/map/connectivity.json      {origin_iso2: {dest_iso2: min_price_eur}}
        -> which countries light up when you click an origin, + the headline price

  static/map/routes/<ISO2>.json     {dest_iso2: [ {o,on,d,dn,p,date}, ... ]}
        -> per origin country, the concrete city->city routes to each destination
           country (cheapest first, capped), powering the drill-down panel

A destination keyed the same as the origin (dc == oc) is the country's DOMESTIC
bucket — e.g. connectivity["US"]["US"] is the cheapest within-US fare, and
routes/US.json["US"] holds the city->city domestic routes (Los Angeles -> New
York, …). The map renders this as a price tag on the origin country itself.

Country keys are ISO-3166-1 alpha-2, matching static/map/regions.geojson.
Prices are indicative (EUR), like the rest of the site — clicking a route runs a
live /search. Re-run periodically to refresh the snapshot.

The per-origin API results are cached under data/_map_cache/ so the build is
resumable (interrupt and re-run; cached origins are skipped) and re-aggregating
is free. Delete that folder to force a full refresh.

Usage:
    python scripts/build_map_connectivity.py            # full run (~3.6k origins)
    python scripts/build_map_connectivity.py --limit 50 # quick smoke test
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv  # noqa: E402
load_dotenv()
from flight_providers import get_active_provider, ProviderError  # noqa: E402

DATA = os.path.join(ROOT, "data")
CACHE_DIR = os.path.join(DATA, "_map_cache")
OUT_DIR = os.path.join(ROOT, "static", "map")
ROUTES_DIR = os.path.join(OUT_DIR, "routes")
CONNECTIVITY_OUT = os.path.join(OUT_DIR, "connectivity.json")

CURRENCY = "eur"
SEARCH_LIMIT = 1000          # max destinations per origin (Aviasales cap)
ROUTES_PER_PAIR = 20         # city->city routes kept per country pair (panel)
MAX_WORKERS = 6
RETRIES = 3

BASE = "https://api.travelpayouts.com/data/en/"


def _get_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def load_reference():
    """Return (code2country, code2name, origins) from Travelpayouts data.

    code2country: airport/city IATA -> ISO2 country
    code2name:    IATA -> display city name (from data/places.json when present)
    origins:      sorted list of flightable city codes to query
    """
    airports = _get_json(BASE + "airports.json")
    cities = _get_json(BASE + "cities.json")

    code2country = {}
    for c in cities:
        if c.get("code") and c.get("country_code"):
            code2country[c["code"]] = c["country_code"]
    for a in airports:
        if a.get("code") and a.get("country_code"):
            code2country[a["code"]] = a["country_code"]

    # Names: prefer the app's curated places.json, fall back to the raw data.
    code2name = {}
    places_path = os.path.join(DATA, "places.json")
    if os.path.exists(places_path):
        with open(places_path, encoding="utf-8") as f:
            code2name.update(json.load(f))
    for c in cities:
        code2name.setdefault(c.get("code"), c.get("name"))
    for a in airports:
        code2name.setdefault(a.get("code"), a.get("name"))

    origins = sorted({a.get("city_code") or a.get("code")
                      for a in airports if a.get("flightable")})
    origins = [o for o in origins if o]
    return code2country, code2name, origins


def fetch_origin(provider, origin):
    """Anywhere search for one origin -> [{d, p, date}], cached to disk."""
    path = os.path.join(CACHE_DIR, f"{origin}.json")
    if os.path.exists(path):
        return None  # already cached
    last_err = None
    for attempt in range(RETRIES):
        try:
            flights = provider.search(origin, None, None, currency=CURRENCY,
                                      limit=SEARCH_LIMIT, sub_id="map")
            rows = [{"d": f["arrival"], "p": round(f["price"]), "date": f.get("date")}
                    for f in flights if f.get("arrival") and f.get("price")]
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(tmp, path)
            return len(rows)
        except ProviderError as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    print(f"  ! {origin} failed: {last_err}")
    # Write an empty result so a persistent failure doesn't re-run forever.
    with open(path, "w", encoding="utf-8") as f:
        json.dump([], f)
    return 0


def crawl(origins):
    provider = get_active_provider()
    if not provider:
        sys.exit("No flight provider configured — set TRAVELPAYOUTS_TOKEN in .env")
    os.makedirs(CACHE_DIR, exist_ok=True)
    todo = [o for o in origins if not os.path.exists(os.path.join(CACHE_DIR, f"{o}.json"))]
    print(f"{len(origins)} origins, {len(todo)} to fetch "
          f"({len(origins) - len(todo)} already cached)")
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(fetch_origin, provider, o): o for o in todo}
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 100 == 0:
                print(f"  …{done}/{len(todo)} fetched")
    print("Crawl complete.")


def _trim(pairs, oc, dc, cap):
    """Keep the per-pair route list bounded (cheapest first)."""
    lst = pairs[(oc, dc)]
    if len(lst) > cap * 4:
        lst.sort(key=lambda r: r["p"])
        del lst[cap:]


def aggregate(code2country, code2name):
    """Read the per-origin cache, bucket by country, write the snapshot files."""
    connectivity = {}            # oc -> {dc -> min_price}
    pairs = {}                   # (oc, dc) -> [route rows]

    files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
    for i, fname in enumerate(files):
        origin = fname[:-5]
        oc = code2country.get(origin)
        if not oc:
            continue
        oname = code2name.get(origin) or origin
        with open(os.path.join(CACHE_DIR, fname), encoding="utf-8") as f:
            rows = json.load(f)
        for r in rows:
            dest = r["d"]
            dc = code2country.get(dest)
            # Keep domestic pairs (dc == oc) under a self-key so the map can
            # offer "flights within <country>" — drop only unknown countries and
            # trivial self-loops (same city back to itself).
            if not dc or dest == origin:
                continue
            price = r["p"]
            cm = connectivity.setdefault(oc, {})
            if dc not in cm or price < cm[dc]:
                cm[dc] = price
            key = (oc, dc)
            pairs.setdefault(key, []).append({
                "o": origin, "on": oname,
                "d": dest, "dn": code2name.get(dest) or dest,
                "p": price, "date": r.get("date"),
            })
            _trim(pairs, oc, dc, ROUTES_PER_PAIR)
        if (i + 1) % 500 == 0:
            print(f"  aggregated {i + 1}/{len(files)} origins")

    # Final write.
    os.makedirs(ROUTES_DIR, exist_ok=True)
    with open(CONNECTIVITY_OUT, "w", encoding="utf-8") as f:
        json.dump(connectivity, f, ensure_ascii=False, separators=(",", ":"))

    # Routes grouped per origin country -> one small file each.
    by_origin = {}
    for (oc, dc), lst in pairs.items():
        lst.sort(key=lambda r: r["p"])
        by_origin.setdefault(oc, {})[dc] = lst[:ROUTES_PER_PAIR]
    for oc, dests in by_origin.items():
        with open(os.path.join(ROUTES_DIR, f"{oc}.json"), "w", encoding="utf-8") as f:
            json.dump(dests, f, ensure_ascii=False, separators=(",", ":"))

    total_links = sum(len(v) for v in connectivity.values())
    print(f"\nWrote {CONNECTIVITY_OUT}: {len(connectivity)} origin countries, "
          f"{total_links} country links")
    print(f"Wrote {len(by_origin)} per-country route files to {ROUTES_DIR}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="only crawl the first N origins (smoke test)")
    ap.add_argument("--skip-crawl", action="store_true",
                    help="re-aggregate from the existing cache only")
    args = ap.parse_args()

    code2country, code2name, origins = load_reference()
    if args.limit:
        origins = origins[:args.limit]
    if not args.skip_crawl:
        crawl(origins)
    aggregate(code2country, code2name)


if __name__ == "__main__":
    main()
