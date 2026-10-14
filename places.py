"""IATA code -> city name lookup, loaded from the prebuilt data/places.json.

Lets the app show real city names for *any* airport a fare points at (worldwide),
not just the 3-letter codes. Regenerate the data with scripts/build_places.py.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "places.json")

try:
    with open(_PATH, encoding="utf-8") as _f:
        _NAMES = json.load(_f)
except (OSError, ValueError):
    _NAMES = {}


def city_name(code):
    """English city name for an IATA code, falling back to the code itself."""
    if not code:
        return code
    return _NAMES.get(code.upper(), code)
