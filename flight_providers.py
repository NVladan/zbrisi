"""
Flight search providers.

This module isolates all third-party flight-API integration behind a small
provider abstraction so the Flask app doesn't care *which* service answers a
search. The only provider implemented today is Travelpayouts, chosen
specifically because it pays the site owner a referral commission ("you get
rewarded for sending customers to flights"):

  * One API token gives access to the Aviasales flight-data API.
  * One `marker` (your partner ID) embedded in the outbound booking links is
    how Travelpayouts attributes - and pays you for - every booking made by a
    customer you referred. It also bundles Kiwi.com, WayAway and others under
    the same marker, so a single integration covers several affiliate programs.

Add another commission-paying provider later by subclassing `FlightProvider`
and appending it to `_PROVIDERS` in `get_active_provider()`.

Configuration is read from environment variables (see `.env.example`):
    TRAVELPAYOUTS_TOKEN   - Data API access token
    TRAVELPAYOUTS_MARKER  - Affiliate marker / partner ID (how you get paid)
    FLIGHTS_CURRENCY      - Currency for prices (default: usd)
    FLIGHTS_MARKET        - Data market / source country (default: us)
"""

import os
import re
from datetime import datetime

import requests

# --- Endpoints -------------------------------------------------------------
# Aviasales flight-data API (cheap cached fares "for dates").
_PRICES_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
# Cheapest price grouped by day, for the price calendar.
_CALENDAR_URL = "https://api.travelpayouts.com/aviasales/v3/grouped_prices"
# Free worldwide place lookup (city + airport -> IATA). No token required.
_AUTOCOMPLETE_URL = "https://autocomplete.travelpayouts.com/places2"
# Affiliate links point at the public Aviasales site, tagged with your marker.
_AVIASALES_BASE = "https://www.aviasales.com"

_HTTP_TIMEOUT = 15  # seconds

# A small IATA airline-code -> display-name map so results read nicely.
# Unknown codes simply fall back to the raw code.
_AIRLINE_NAMES = {
    "BA": "British Airways", "AF": "Air France", "LH": "Lufthansa",
    "KL": "KLM", "IB": "Iberia", "AY": "Finnair", "SK": "SAS",
    "FR": "Ryanair", "RK": "Ryanair UK", "U2": "easyJet", "VY": "Vueling",
    "W6": "Wizz Air", "W9": "Wizz Air UK", "W4": "Wizz Air Malta",
    "EW": "Eurowings", "DY": "Norwegian", "TP": "TAP Air Portugal",
    "TO": "Transavia", "HV": "Transavia", "BY": "TUI Airways", "LS": "Jet2",
    "AA": "American Airlines", "DL": "Delta", "UA": "United",
    "B6": "JetBlue", "WN": "Southwest", "AC": "Air Canada",
    "EK": "Emirates", "QR": "Qatar Airways", "TK": "Turkish Airlines",
    "EY": "Etihad", "SU": "Aeroflot", "QF": "Qantas", "SQ": "Singapore Airlines",
    "CX": "Cathay Pacific", "NH": "ANA", "JL": "Japan Airlines",
    "LX": "SWISS", "OS": "Austrian", "AZ": "ITA Airways", "PC": "Pegasus",
}


def airline_name(code):
    """Human-friendly airline name for an IATA code, falling back to the code."""
    if not code:
        return "Unknown airline"
    return _AIRLINE_NAMES.get(code.upper(), code.upper())


class ProviderError(Exception):
    """Raised when a provider call fails (network, bad token, API error)."""


class FlightProvider:
    """Base class for an affiliate flight-search provider."""

    name = "base"

    @property
    def is_configured(self):
        """True when the provider has the credentials it needs to run."""
        raise NotImplementedError

    def search(self, origin, destination, depart_date, currency=None, limit=30):
        """Return a list of normalised flight dicts (see TravelpayoutsProvider)."""
        raise NotImplementedError


class TravelpayoutsProvider(FlightProvider):
    """
    Travelpayouts / Aviasales flight-data provider with affiliate monetisation.

    Every booking link returned by `search()` carries your `marker`, so a
    customer who books after clicking it is attributed to you and you earn the
    referral commission.
    """

    name = "travelpayouts"

    def __init__(self, token=None, marker=None, currency=None, market=None):
        self.token = token or os.environ.get("TRAVELPAYOUTS_TOKEN", "")
        self.marker = marker or os.environ.get("TRAVELPAYOUTS_MARKER", "")
        self.currency = (currency or os.environ.get("FLIGHTS_CURRENCY", "usd")).lower()
        self.market = (market or os.environ.get("FLIGHTS_MARKET", "us")).lower()

    @property
    def is_configured(self):
        # The token is required to fetch data. The marker is required to get
        # *paid*; we warn (in app.py) but still run without it.
        return bool(self.token)

    def affiliate_link(self, relative_or_full_link, origin=None, destination=None,
                       depart_date=None, sub_id=None, return_date=None, passengers="1"):
        """
        Turn an Aviasales `link` (or, as a fallback, a search) into a full
        affiliate URL tagged with your marker (and optional sub_id).

        The data API returns `link` like `/search/LON2207JFK1?t=...`. We prefix
        the Aviasales host and append the marker. If no link is available we
        build the canonical one-way search path `{ORIGIN}{DDMM}{DEST}1`. The
        trailing digits encode passengers ({adults}{children}{infants}); the
        sub_id lets you attribute which page/route drove a booking.
        """
        pax = passengers or "1"
        link = relative_or_full_link
        if link and pax != "1" and not link.startswith("http"):
            # The API link ends its path with a "1" passenger digit; swap it for
            # the chosen passenger string (only touch the path, never the query).
            path_part, sep, query = link.partition("?")
            link = re.sub(r"1$", pax, path_part) + sep + query
        if not link and origin and destination and depart_date:
            try:
                d = datetime.strptime(depart_date, "%Y-%m-%d")
                path = f"/search/{origin}{d.strftime('%d%m')}{destination}"
                if return_date:  # round-trip path: {O}{DDMM}{DEST}{RDDMM}{PAX}
                    r = datetime.strptime(return_date, "%Y-%m-%d")
                    path += r.strftime('%d%m')
                link = path + pax
            except (ValueError, TypeError):
                link = None
        if not link:
            return _AVIASALES_BASE  # last-resort: homepage, still marker-tagged

        url = link if link.startswith("http") else _AVIASALES_BASE + link
        params = []
        if self.marker:
            params.append(f"marker={self.marker}")
        if sub_id:
            # Keep sub_id URL-safe (letters, digits, underscore).
            safe = re.sub(r"[^A-Za-z0-9_]", "", str(sub_id))[:32]
            if safe:
                params.append(f"sub_id={safe}")
        if params:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{'&'.join(params)}"
        return url

    def search(self, origin, destination, depart_date, currency=None, limit=30,
               sub_id=None, return_date=None, round_trip=None, passengers="1"):
        """
        Query the Aviasales cheap-fares API for one-way flights.

        Args:
            origin: IATA code of the departure (required).
            destination: IATA code of the arrival, or None for "anywhere".
            depart_date: 'YYYY-MM-DD', or None for cheapest upcoming.
            sub_id: optional attribution tag added to every booking link.

        Returns a list of dicts shaped for results.html:
            airline, departure, arrival, date, price, currency, deeplink,
            transfers, flight_number.
        """
        if not self.is_configured:
            raise ProviderError("Travelpayouts token is not configured.")

        cur = (currency or self.currency).lower()
        # Round-trip is requested explicitly via round_trip; otherwise inferred
        # from a return date. A round trip with NO return date asks the API to
        # suggest the cheapest return dates itself.
        if round_trip is None:
            round_trip = bool(return_date)
        # The cached Flight Data API returns far more options when queried by
        # month than by an exact day (a specific future date often has just one
        # cached fare). The form asks for an *approximate* date, so we search the
        # whole month and return the cheapest fares across it - each labelled
        # with its own real date.
        params = {
            "origin": origin,
            "departure_at": _to_month(depart_date),
            "one_way": "false" if round_trip else "true",
            "direct": "false",
            "currency": cur,
            "market": self.market,
            "limit": limit,
            "sorting": "price",
            "token": self.token,
        }
        if round_trip and return_date:
            params["return_at"] = _to_month(return_date)
        if destination:
            params["destination"] = destination
        elif not round_trip:
            # "Anywhere" one-way search: one cheapest fare per destination.
            params["unique"] = "true"

        try:
            resp = requests.get(
                _PRICES_URL,
                params=params,
                headers={"X-Access-Token": self.token, "Accept": "application/json"},
                timeout=_HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            raise ProviderError(f"Flight API request failed: {exc}") from exc
        except ValueError as exc:
            raise ProviderError("Flight API returned invalid JSON.") from exc

        if not payload.get("success", True):
            raise ProviderError(
                payload.get("error") or "Flight API reported a failure."
            )

        flights = []
        for item in payload.get("data", []) or []:
            fare_date = _format_date(item.get("departure_at"), depart_date)
            ret_date = _format_date(item.get("return_at"), None) if item.get("return_at") else None
            flights.append({
                "airline": airline_name(item.get("airline")),
                "departure": item.get("origin", origin),
                "arrival": item.get("destination", destination or ""),
                "date": fare_date,
                "depart_time": _format_time(item.get("departure_at")),
                "duration": item.get("duration") or item.get("duration_to"),
                "return_date": ret_date,
                "price": float(item.get("price", 0) or 0),
                "currency": cur.upper(),
                "transfers": item.get("transfers", 0),
                "return_transfers": item.get("return_transfers"),
                "flight_number": item.get("flight_number"),
                "deeplink": self.affiliate_link(
                    item.get("link"),
                    origin=item.get("origin", origin),
                    destination=item.get("destination", destination),
                    depart_date=fare_date,
                    return_date=ret_date,
                    sub_id=sub_id,
                    passengers=passengers,
                ),
            })

        flights.sort(key=lambda f: f.get("price") or float("inf"))
        return flights

    def price_calendar(self, origin, destination, month, currency=None, sub_id=None):
        """
        Cheapest one-way fare per day for a route in a month.

        Returns {'YYYY-MM-DD': {'price': float, 'deeplink': str}} for the price
        calendar. Empty dict on any error (the calendar just won't render).
        """
        if not self.is_configured or not (origin and destination and month):
            return {}
        cur = (currency or self.currency).lower()
        params = {
            "origin": origin, "destination": destination,
            "departure_at": month, "group_by": "departure_at",
            "one_way": "true", "currency": cur, "market": self.market,
            "token": self.token,
        }
        try:
            resp = requests.get(
                _CALENDAR_URL, params=params,
                headers={"X-Access-Token": self.token, "Accept": "application/json"},
                timeout=_HTTP_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()
        except (requests.RequestException, ValueError):
            return {}

        out = {}
        data = payload.get("data") or {}
        if isinstance(data, dict):
            for day, info in data.items():
                price = info.get("price")
                if price is None:
                    continue
                out[day] = {
                    "price": float(price),
                    "deeplink": self.affiliate_link(
                        info.get("link"), origin=origin, destination=destination,
                        depart_date=day, sub_id=sub_id),
                }
        return out


def _to_month(depart_date):
    """Return 'YYYY-MM' for a 'YYYY-MM-DD' input (used to widen the search)."""
    if not depart_date:
        return depart_date
    try:
        return datetime.strptime(depart_date[:10], "%Y-%m-%d").strftime("%Y-%m")
    except (ValueError, TypeError):
        return depart_date[:7]


def _format_time(iso_value):
    """Extract 'HH:MM' (local departure time) from an API ISO datetime."""
    if not iso_value:
        return None
    try:
        return datetime.fromisoformat(iso_value).strftime("%H:%M")
    except (ValueError, TypeError):
        return None


def _format_date(iso_value, fallback):
    """Format an API ISO datetime ('2026-07-22T10:30:00+01:00') as 'YYYY-MM-DD'."""
    if not iso_value:
        return fallback
    try:
        # Python's fromisoformat handles the +01:00 offset on 3.11+.
        return datetime.fromisoformat(iso_value).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return iso_value[:10] if isinstance(iso_value, str) else fallback


def get_active_provider():
    """
    Return the first configured, commission-paying provider, or None.

    To add another affiliate provider, implement a FlightProvider subclass and
    insert it into this list (order = priority).
    """
    _providers = [
        TravelpayoutsProvider(),
    ]
    for provider in _providers:
        if provider.is_configured:
            return provider
    return None


def autocomplete_places(term, locale="en", limit=8):
    """
    Look up cities/airports worldwide and return [{value, label}] suggestions.

    Uses Travelpayouts' free place-autocomplete service (no token needed), so
    the search box resolves any city to an IATA code - not just a hardcoded
    handful. `value` is the IATA code (what we submit), `label` is what the
    user sees.
    """
    if not term:
        return []
    params = [
        ("locale", locale),
        ("max", str(limit)),
        ("term", term),
        ("types[]", "city"),
        ("types[]", "airport"),
    ]
    try:
        resp = requests.get(
            _AUTOCOMPLETE_URL,
            params=params,
            headers={"Accept": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        rows = resp.json()
    except (requests.RequestException, ValueError):
        return []

    suggestions = []
    for row in rows or []:
        code = row.get("code")
        if not code:
            continue
        name = row.get("name") or ""
        country = row.get("country_name") or ""
        kind = "airport" if row.get("type") == "airport" else "city"
        label_bits = [b for b in (name, country) if b]
        label = f"{', '.join(label_bits)} ({code})"
        suggestions.append({
            "value": code,      # what the form submits / resolver uses
            "label": label,     # plain-text fallback
            "name": name,       # for the rich dropdown
            "country": country,
            "code": code,
            "type": kind,       # "city" | "airport"
        })
    return suggestions
