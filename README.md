# Zbriši ✈

Cheap **one-way and round-trip** flight search for the **Balkans**, that earns an
**affiliate commission** when a visitor books through the results. Bilingual
(English + Serbian) with a programmatic-SEO surface designed to get found.

## How it makes money

Zbriši integrates [**Travelpayouts**](https://www.travelpayouts.com/) (the
Aviasales affiliate network). Every booking link carries your **`marker`**
(partner ID) plus a **`sub_id`** that records *which page* drove the click, so a
referred booking is attributed to you — at no extra cost to the traveller. One
account also covers Kiwi.com, WayAway and others under the same marker.

## What's in the box

- **Search** — one-way and round-trip, with worldwide city/airport autocomplete
  (local Balkan cities matched first, in Serbian *or* English spelling).
- **Bilingual (Serbian-first)** — Serbian at `/` (default), English at `/en/`,
  with `hreflang`, a language switcher, and proper Serbian grammar (e.g.
  *"letovi iz Beograda za Barselonu"*).
- **City names everywhere** — fares show real city names (Memmingen, Milan…),
  not just IATA codes, via a local `data/places.json` lookup.
- **Programmatic SEO** — ~290 `/flights/<from>/<to>` route pages (live fares,
  unique per-route facts, `FAQPage` JSON-LD, internal links), `/flights/<city>`
  city hubs, a `/flights` directory, a flat-file **Markdown blog** at `/guides`,
  `WebSite`/`Organization`/`BreadcrumbList`/`Article` JSON-LD, `sitemap.xml`
  (304 URLs, `hreflang` + `lastmod`) and `robots.txt`.
- **Privacy-first performance** — fonts are **self-hosted** (no Google Fonts
  request → GDPR-friendly + faster). Google Search Console verification via env.
- **Monetisation** — affiliate `marker` + per-page `sub_id` on every link.
- **Privacy & analytics** — a `/privacy` page, a consent banner, and optional
  Plausible (cookieless) / GA4 (consent-gated) analytics.
- **Production-ready** — WSGI server config, `ProxyFix`, `/health`, branded
  translated 404/500, Open Graph/Twitter share cards, `noindex` on search results.

## Quickstart

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure
cp .env.example .env          # then set TRAVELPAYOUTS_TOKEN and TRAVELPAYOUTS_MARKER

# 3. Run (development)
python app.py                 # http://localhost:5001
```

Get your **token** and **marker** at travelpayouts.com → **Programs → Aviasales →
API**. Without a token the app still runs on clearly-labelled **demo data**.

### Run like production (locally)

```bash
# Windows / cross-platform
waitress-serve --port=5001 app:app
# Linux
gunicorn app:app --workers 2 --bind 0.0.0.0:5001
```

## Deploy (Contabo VPS + Namecheap domain)

Full step-by-step in **[DEPLOY.md](DEPLOY.md)**. In short:

1. Point `zbrisi.com` at the VPS IP via Namecheap DNS (A records `@` + `www`).
2. On the VPS: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`,
   create `.env` with the token + marker.
3. Run it with the bundled **systemd** unit (`deploy/zbrisi.service`) →
   gunicorn on `127.0.0.1:8000`.
4. Put **nginx** in front (`deploy/nginx-zbrisi.conf`) and add HTTPS with
   `certbot --nginx`.
5. Submit `https://zbrisi.com/sitemap.xml` to Google Search Console.

`ProxyFix` is enabled and the nginx config forwards `X-Forwarded-*`, so
canonical/`hreflang`/sitemap URLs come out as the real public HTTPS host.

## Configuration (env vars)

| Var | Purpose |
|-----|---------|
| `TRAVELPAYOUTS_TOKEN` | Aviasales flight-data API token (live fares) |
| `TRAVELPAYOUTS_MARKER` | Affiliate marker / partner ID (**how you get paid**) |
| `FLIGHTS_CURRENCY` | Default currency (`eur`, `usd`, `gbp`, `rsd`, …) |
| `FLIGHTS_MARKET` | Data source market (country code, default `us`) |
| `PLAUSIBLE_DOMAIN` | Optional cookieless analytics domain |
| `GA_MEASUREMENT_ID` | Optional GA4 id (loads only after cookie consent) |
| `GOOGLE_SITE_VERIFICATION` | Optional Search Console verification token |
| `CONTACT_EMAIL` | Public contact address (footer / privacy / imprint) |
| `OPERATOR_NAME` / `OPERATOR_ADDRESS` / `OPERATOR_COUNTRY` | Imprint operator details — individual is fine, no company needed (address optional) |
| `FLASK_DEBUG` | `1` for local dev only (never in production) |
| `PORT` | Port for the dev server (default 5001) |

## Project structure

```
app.py              Flask routes, i18n URL plumbing, search, sitemap/robots/health
flight_providers.py Affiliate provider abstraction + Travelpayouts integration
geo.py              Balkan cities (EN/SR names + declension), route catalogue
places.py           IATA code -> city name lookup (worldwide)
content.py          Flat-file Markdown blog loader
i18n.py             EN + Serbian translations and the t() helper
templates/          base, index, results, route, city, flights_hub, guides, privacy, terms, imprint, 404/500
content/            *.md guides (front-matter + Markdown)
static/             style.css, app.js, og-image.png, fonts.css, fonts/
data/places.json    Prebuilt code->name map
scripts/            make_og.py · build_places.py · fetch_fonts.py
tests/test_smoke.py pytest smoke suite (30 tests)
```

To add another commission-paying provider, subclass `FlightProvider` in
`flight_providers.py` and add it to `get_active_provider()`. To add a language,
extend `STRINGS` in `i18n.py` and `LANGUAGES`.

## Testing

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Search/route tests run in hermetic **demo mode** (no network).

## Notes

- Fares come from a **cached** API queried by *month*, so results show the
  cheapest days/combos around your date (each fare shows its real dates). For
  fixed-date, real-time fares, Travelpayouts' Flight Search API is request-access.
- `/search` result pages are `noindex` (thin/duplicate); the route pages are the
  indexable SEO surface.
- Never commit `.env`; never run with `debug=True` in production.

## License

**Proprietary — all rights reserved.** This is closed-source software; you may
not use, copy, modify, or distribute it without prior written permission. See
[LICENSE](LICENSE). For permission requests, contact me via [GitHub](https://github.com/NVladan). Third-party
libraries and fonts keep their own licenses.
