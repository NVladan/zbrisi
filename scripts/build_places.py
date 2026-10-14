"""Build data/places.json — an IATA code -> city name lookup.

Downloads Travelpayouts' public cities + airports data and writes a compact
{code: name} map so the app can show city names (not just codes) for any fare,
offline and fast. Re-run occasionally to refresh.
"""
import json
import os
import urllib.request

BASE = "https://api.travelpayouts.com/data/en/"


def get(name):
    req = urllib.request.Request(
        BASE + name, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


cities = get("cities.json")
airports = get("airports.json")

city_name = {c["code"]: c["name"] for c in cities if c.get("code") and c.get("name")}
places = dict(city_name)
for a in airports:
    code = a.get("code")
    if not code or code in places:
        continue
    places[code] = city_name.get(a.get("city_code")) or a.get("name") or code

out = os.path.join(os.path.dirname(__file__), "..", "data", "places.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(places, f, ensure_ascii=False, separators=(",", ":"))
print(f"wrote {len(places)} places to {os.path.abspath(out)}")
