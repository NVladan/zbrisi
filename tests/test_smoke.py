"""Smoke tests for Zbriši — routing, i18n, SEO and search.

Default language is Serbian (at /), English lives under /en/.
Search/route tests force demo mode (no network) for determinism.
Run:  python -m pytest -q
"""
import pytest

import app as appmod
import places


@pytest.fixture
def client():
    appmod.app.config.update(TESTING=True)
    return appmod.app.test_client()


@pytest.fixture
def demo(monkeypatch):
    """Force the deterministic, network-free demo provider."""
    monkeypatch.setattr(appmod, "FLIGHT_PROVIDER", None)
    yield


# --- pages & i18n ----------------------------------------------------------
def test_home_default_is_serbian(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Otkrij".encode() in r.data           # Serbian hero headline


def test_home_english_under_en(client):
    r = client.get("/en/")
    assert r.status_code == 200
    assert b"Chase the" in r.data


def test_hreflang_present(client):
    html = client.get("/").data
    assert b'hreflang="en"' in html
    assert b'hreflang="x-default"' in html


def test_route_page_english(client):
    r = client.get("/en/flights/BEG/BCN")
    assert r.status_code == 200
    assert b"Cheap flights from Belgrade to Barcelona" in r.data
    assert b"FAQPage" in r.data                   # JSON-LD present


def test_route_page_serbian_declension(client):
    r = client.get("/flights/BEG/BCN")            # root = Serbian
    assert r.status_code == 200
    assert "iz Beograda za Barselonu".encode() in r.data


def test_hub_and_privacy(client):
    assert client.get("/flights").status_code == 200
    assert client.get("/privacy").status_code == 200
    assert client.get("/en/privacy").status_code == 200


def test_unknown_route_is_branded_404(client):
    r = client.get("/flights/ZZZ/BCN")
    assert r.status_code == 404
    assert b"404" in r.data


# --- SEO plumbing ----------------------------------------------------------
def test_sitemap(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert b"/flights/BEG/BCN" in r.data
    assert b'hreflang="en"' in r.data


def test_robots_disallows_search(client):
    r = client.get("/robots.txt")
    assert b"Disallow: /search" in r.data
    assert b"Sitemap:" in r.data


def test_og_tags(client):
    html = client.get("/").data
    assert b'property="og:image"' in html
    assert b"og-image.png" in html
    assert b'name="twitter:card"' in html


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


# --- search (hermetic via demo provider) -----------------------------------
def test_search_oneway_english(client, demo):
    r = client.post("/en/search", data={"departure_location": "Belgrade",
                                        "approx_date": "2026-07-15"})
    assert r.status_code == 200
    assert b"Cheapest one-ways" in r.data
    assert b'content="noindex,follow"' in r.data  # results must not be indexed


def test_search_shows_city_names(client, demo):
    r = client.post("/en/search", data={"departure_location": "Belgrade",
                                        "approx_date": "2026-07-15"})
    # demo arrivals are VIE/BCN/BER/AMS -> city names must render, not just codes
    assert b"Vienna" in r.data or b"Barcelona" in r.data


def test_search_roundtrip_english(client, demo):
    r = client.post("/en/search", data={"departure_location": "Belgrade",
                                        "destination_location": "Vienna",
                                        "approx_date": "2026-07-15",
                                        "return_date": "2026-07-25",
                                        "trip_type": "roundtrip"})
    assert r.status_code == 200
    assert b"Cheapest round trips" in r.data
    assert b"Round trip" in r.data


def test_search_roundtrip_default_serbian(client, demo):
    r = client.post("/search", data={"departure_location": "Beograd",
                                     "destination_location": "Vienna",
                                     "approx_date": "2026-07-15",
                                     "return_date": "2026-07-25",
                                     "trip_type": "roundtrip"})
    assert r.status_code == 200
    assert "Najjeftinije povratne karte".encode() in r.data


def test_missing_fields_redirects(client):
    r = client.post("/search", data={"departure_location": "", "approx_date": ""})
    assert r.status_code == 302


# --- resolvers / lookups ---------------------------------------------------
def test_autocomplete_local_match(client):
    data = client.get("/autocomplete?query=Beog").get_json()
    assert any(item["code"] == "BEG" for item in data)


def test_resolver_serbian_names():
    assert appmod.get_airport_code("Beograd") == "BEG"
    assert appmod.get_airport_code("Sarajevo") == "SJJ"
    assert appmod.get_airport_code("JFK") == "JFK"


def test_places_lookup():
    assert places.city_name("FMM") == "Memmingen"
    assert places.city_name("MIL") == "Milan"
    assert places.city_name("ZZZZ") == "ZZZZ"     # unknown -> code


# --- SEO expansion: city pages, guides, structured data -------------------
def test_city_page(client):
    r = client.get("/flights/BEG")
    assert r.status_code == 200
    assert "Beograd".encode() in r.data
    assert b"BreadcrumbList" in r.data


def test_city_page_unknown_404(client):
    assert client.get("/flights/ZZZ").status_code == 404


def test_guides_index(client):
    r = client.get("/guides")
    assert r.status_code == 200
    assert "Vodi".encode() in r.data              # "Vodiči"


def test_guide_article(client):
    r = client.get("/guides/jeftino-iz-beograda")
    assert r.status_code == 200
    assert "Beograd".encode() in r.data
    assert b'"@type": "Article"' in r.data


def test_guide_unknown_404(client):
    assert client.get("/guides/nope-not-real").status_code == 404


def test_sitemap_has_city_guides_lastmod(client):
    data = client.get("/sitemap.xml").data
    assert b"/flights/BEG<" in data               # city page loc
    assert b"/guides/" in data
    assert b"<lastmod>" in data


def test_website_jsonld(client):
    data = client.get("/").data
    assert b'"@type": "WebSite"' in data
    assert b"SearchAction" in data


def test_format_time_parsing():
    from flight_providers import _format_time
    assert _format_time("2026-07-24T18:50:00+02:00") == "18:50"
    assert _format_time(None) is None


def test_next_month_format():
    import re as _re
    assert _re.match(r"^\d{4}-\d{2}$", appmod._next_month_str())


def test_anywhere_search_renders_without_calendar(client, demo):
    r = client.post("/en/search", data={"departure_location": "Belgrade",
                                        "approx_date": "2026-07-15"})
    assert r.status_code == 200


def test_anywhere_explorer_renders(client, demo):
    r = client.get("/en/anywhere")
    assert r.status_code == 200
    assert b"budget" in r.data.lower()            # explorer copy present
    assert b"dealGrid" in r.data                  # the deals grid
    # demo arrivals are VIE/BCN/BER/AMS -> destination posters render
    assert b"Vienna" in r.data or b"Barcelona" in r.data


def test_anywhere_explorer_serbian(client, demo):
    r = client.get("/anywhere")                   # root = Serbian
    assert r.status_code == 200
    assert "Istraživač budžeta".encode() in r.data


def test_anywhere_budget_filter(client, demo):
    # A budget filters the initial slider cap without 500-ing.
    r = client.get("/en/anywhere?from=Belgrade&budget=60")
    assert r.status_code == 200
    assert b"bxRange" in r.data


def test_anywhere_in_sitemap(client):
    data = client.get("/sitemap.xml").data
    assert b"/anywhere<" in data


def test_anywhere_deals_helper_dedups_cheapest(monkeypatch):
    # _anywhere_deals keeps the cheapest fare per destination, sorted by price.
    fake = [
        {"arrival": "VIE", "price": 80, "date": "2026-07-02"},
        {"arrival": "VIE", "price": 45, "date": "2026-07-09"},   # cheaper VIE
        {"arrival": "BCN", "price": 60, "date": "2026-07-05"},
    ]

    class _P:
        def search(self, *a, **k):
            return list(fake)

    monkeypatch.setattr(appmod, "FLIGHT_PROVIDER", _P())
    appmod._ROUTE_CACHE.clear()
    deals = appmod._anywhere_deals("BEG", "eur")
    assert [d["arrival"] for d in deals] == ["VIE", "BCN"]   # sorted cheapest-first
    assert deals[0]["price"] == 45                            # cheapest VIE kept
    appmod._ROUTE_CACHE.clear()


def test_price_context_helper():
    flights = [{"price": 10}, {"price": 22}, {"price": 24}, {"price": 40}]
    appmod._annotate_price_context(flights)           # avg = 24, great <= 20.4
    assert flights[0]["context"] == "great"           # 10
    assert flights[1]["context"] == "below"           # 22 (< 24, > 20.4)
    assert flights[2]["context"] is None              # 24 (>= avg)
    assert flights[3]["context"] is None              # 40
    # too few fares -> left untouched (no badge noise)
    few = [{"price": 5}, {"price": 9}]
    appmod._annotate_price_context(few)
    assert "context" not in few[0]


def test_route_facts_helper():
    flights = [
        {"airline": "Wizz Air", "price": 19, "transfers": 0, "date": "2026-07-02"},
        {"airline": "Ryanair", "price": 31, "transfers": 1, "date": "2026-07-10"},
    ]
    f = appmod._route_facts(flights, "eur")
    assert f["price_min"] == 19 and f["price_max"] == 31
    assert "Wizz Air" in f["airlines"]
    assert f["has_direct"] is True
    assert appmod._route_facts([], "eur") is None
