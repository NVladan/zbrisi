"""Bulk-download city background photos for the destination cards.

Saves static/img/cities/<CODE>.jpg (cover-cropped, optimised). Source: Pexels
(free, commercial use allowed, no attribution required). The download/crop/query
logic lives in city_photos.py (shared with the app's on-demand fetcher); this
script is just the batch driver.

Usage:
    1. Free API key at https://www.pexels.com/api/  -> put PEXELS_API_KEY in .env
       (auto-loaded) or the shell.
    2. Modes:
       python scripts/fetch_city_images.py            # the geo.CITIES list (~50)
       python scripts/fetch_city_images.py --discover  # every city that renders
           # on /anywhere right now (cheapest per Balkan origin) — pulls live data
           # and covers worldwide destinations too
       python scripts/fetch_city_images.py MUC PRG BUD # just these IATA codes
       python scripts/fetch_city_images.py --all       # every airport in
           # places.json (~10k) — a long, resumable grind; Pexels free is ~200
           # requests/hour, so it self-throttles with backoff. Disk ~1GB.
    Flags: --force (re-download existing), --limit N (cap a run),
           --per-origin N (cheapest-N per origin in --discover; 0 = every airport),
           --sleep S (seconds between fetches; raise if Pexels returns 429).

Existing images are kept by default. Re-run anytime; it's resumable. The app also
fetches missing photos on demand at runtime (see city_photos.ensure), so this
script is mainly for pre-seeding. Requires: requests, Pillow, python-dotenv.
"""
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv

# Make the project root importable so we can reuse the canonical lists + helpers.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import geo  # noqa: E402
from city_photos import OUT_DIR, query_for, download_one  # noqa: E402

load_dotenv()


def discover_rendered_codes(limit_per_origin):
    """Frequency of every destination code that renders on /anywhere (the cheapest
    `limit_per_origin` per Balkan origin; 0 = every reachable airport), top-first."""
    import app  # lazy: pulls in the flight provider + .env
    from collections import Counter
    freq = Counter()
    for origin in geo.ORIGINS:
        try:
            deals = app._anywhere_deals(origin, "eur")
            if limit_per_origin:
                deals = deals[:limit_per_origin]
        except Exception as exc:  # noqa: BLE001
            print(f"  (discover) {origin}: {exc}")
            continue
        for f in deals:
            c = f.get("arrival")
            if c:
                freq[c] += 1
    return [c for c, _ in freq.most_common()]


def _opt(args, name, default):
    """Read --name value (or --name=value) from argv, else default."""
    for i, a in enumerate(args):
        if a == name and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return default


def main():
    args = sys.argv[1:]
    force = "--force" in args
    discover = "--discover" in args
    all_airports = "--all" in args
    limit = int(_opt(args, "--limit", "0"))             # 0 = no cap
    per_origin = int(_opt(args, "--per-origin", "60"))  # matches ANYWHERE_MAX_CARDS
    pause = float(_opt(args, "--sleep", "0.5"))         # throttle (Cloudflare burst)
    # Positional args are explicit IATA codes (3 letters); this also stops flag
    # values like the "0" in "--per-origin 0" from being read as a city code.
    only = [a.upper() for a in args if re.fullmatch(r"[A-Za-z]{3}", a)]

    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        sys.exit("Set PEXELS_API_KEY first (in .env or the shell; free key at "
                 "https://www.pexels.com/api/).")
    os.makedirs(OUT_DIR, exist_ok=True)

    if only:
        codes = only
    elif all_airports:
        import places
        codes = sorted(places._NAMES.keys())
        print(f"Fetching photos for ALL {len(codes)} known airports (places.json). "
              f"This is a long, throttle-bound grind — it's resumable, so just re-run "
              f"if it stops.")
    elif discover:
        print(f"Discovering destinations on /anywhere "
              f"({'every airport' if per_origin == 0 else 'top %d' % per_origin} per origin)…")
        codes = discover_rendered_codes(per_origin)
        print(f"  {len(codes)} distinct destinations appear.")
    else:
        codes = list(geo.CITIES.keys())

    todo = [c for c in codes
            if force or not os.path.exists(os.path.join(OUT_DIR, f"{c}.jpg"))]
    skipped = len(codes) - len(todo)
    if limit:
        todo = todo[:limit]

    ok = fail = 0
    i = 0
    cooldown = 30
    while i < len(todo):
        code = todo[i]
        try:
            if download_one(code, key):
                ok += 1
                print(f"  {code}: {query_for(code)} -> {code}.jpg")
            else:
                print(f"  {code}: no usable photo for '{query_for(code)}'")
            i += 1
            cooldown = 30
            time.sleep(pause)
        except requests.HTTPError as exc:
            if getattr(exc.response, "status_code", None) == 429:
                # Self-throttle: wait (escalating) and retry the SAME code, so a
                # single unattended run grinds through everything.
                print(f"  {code}: HTTP 429 — backing off {cooldown}s, then retrying…")
                time.sleep(cooldown)
                cooldown = min(cooldown * 2, 900)
                continue
            print(f"  {code}: failed — {exc}")
            fail += 1
            i += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  {code}: failed — {exc}")
            fail += 1
            i += 1
    remaining = len(todo) - ok - fail
    tail = f"  {remaining} still to go." if remaining else ""
    print(f"Done: {ok} saved, {fail} failed, {skipped} kept "
          f"(already present) in static/img/cities/.{tail}")


if __name__ == "__main__":
    main()
