# zbriši — TODO / backlog

Running list of ideas not yet built. Done items are checked.

## Search experience
- [x] Flight times + duration on result cards
- [x] Price calendar — cheapest fare per day (route pages + destination searches)
- [x] Flexible round-trip dates — optional/blank return suggests the cheapest
      returns; ±3/±7-day date-flexibility control on the search card
- [x] **"Anywhere under €X" budget explorer** — `/anywhere` page (+ `/sr`): From +
      budget form, a deals grid of destination posters sorted cheapest-first, and a
      sticky "fare throttle" slider that live-filters by budget client-side. Reuses
      the cheapest-per-destination data via a shared cache (`_anywhere_deals`, which
      now also powers city pages). Budget input on the home page too; in nav +
      footer + sitemap. (API: origin-only "anywhere" search.)
- [x] **Recent searches** — last few home-form searches saved in `localStorage`
      (no DB), shown as boarding-pass "stub" chips under the search card. Click a
      chip to re-run (GET to `/search`), × to remove, "Clear" to wipe. Dedups,
      keeps the newest 5; hidden until there's history.
- [x] **Passengers selector** — picker for adults/children/infants; encoded into
      the Aviasales booking deeplink (`…{DEST}{adults}{children}{infants}`).
- [x] **Auto-detect "From"** — prefills the departure city from the visitor's IP
      via Travelpayouts `whereami` (CORS, no permission prompt, no cookies). Fills
      only an empty From (home search + budget-explorer promo), never submits;
      shows an editable "📍 from your location" note, cached per session.
      Privacy page updated (EN+SR).
- [ ] **More result filters** — departure time-of-day (morning/evening), max
      duration, baggage-included fares.
- [x] **Price-context badges** — each fare gets a "Great price" / "Below average"
      chip vs. the route's own fares (`_annotate_price_context`: ≤85% of avg →
      great, < avg → below, needs ≥3 fares). Shown on results (single-route only)
      + route pages; cheapest is skipped (already "Best price"). EN + SR.
- [x] **Baggage / total-price note** — "base fare · cabin bag only" micro-line
      under each fare (adds "· per person" when >1 passenger).
- [ ] **Calendar month navigation** — prev/next month on the price calendar
      (use a query param + canonical to the no-param URL to avoid SEO bloat).
- [x] **Map view** — `/map` (+ `/en/map`) "Pretraži na mapi / Browse on map": a
      Mapbox GL dusk-globe ("Departures Atlas") of ~226 country polygons. Click a
      country → it turns coral and every reachable country glows gold with a
      "from €X" tag; click a destination → a boarding-pass side panel of cheapest
      city→city routes, each linking to live `/search`. Data is a precomputed
      static snapshot (`scripts/build_map_regions.py` dissolves MAPA admin-1 →
      countries; `scripts/build_map_connectivity.py` crawls the Aviasales
      "anywhere" API → `static/map/connectivity.json` + `routes/<ISO>.json`).
      Re-run the connectivity script periodically to refresh fares. In nav +
      footer + sitemap. EN + SR. (Country names in labels are English only.)
      Mapbox zoom control (top-right) + ctrl/⌘-scroll/pinch zoom for tiny
      countries. Optional Depart/Return date filter in the hero flows into the
      route `/search` links (blank = the snapshot's cheapest day; a return date
      makes it a round-trip search).

## Growth / retention (these need a small DB — e.g. SQLite)
- [ ] **Price alerts / email capture** — "tell us your route, we email you when
      it drops." First real reason to add a database. The retention loop.
- [ ] Saved searches / watchlist.

## SEO / content (DB-free)
- [x] Programmatic route pages + city hubs + sitemap + hreflang
- [x] Enriched route pages ("Korisno da znaš")
- [x] Markdown blog (`/guides`)
- [x] Structured data (WebSite/Organization/Breadcrumb/FAQ/Article)
- [x] Self-hosted fonts (GDPR + perf)
- [x] More guides — added origin guides (Sarajevo, Zagreb, Tuzla) + a "cheapest
      time to fly" evergreen, in SR + EN (9 guides total, up from 3).
- [x] Expand the route catalog — +3 Balkan origins (Tuzla, Banja Luka, Ohrid) and
      +10 destinations; 504 route pairs (was 286), 527 sitemap URLs (was 306).

## Legal / compliance
> Not legal advice — confirm specifics once the operating entity + country are
> decided (rules differ across the EU / Balkans).
- [x] Privacy policy page exists (`/privacy`, EN + SR) + cookie-consent banner
- [x] Contact email wired into footer + privacy + imprint (`CONTACT_EMAIL`)
- [x] **Terms of Use page** (`/terms`, EN + SR) — covers indicative prices, "we
      don't sell tickets / booking on third-party sites", the affiliate
      relationship, and a liability disclaimer. In footer + sitemap.
- [x] **Imprint / legal notice** (`/imprint`, EN + SR) — operator + contact. In
      footer + sitemap.
- [x] **Operator identity** — set via `OPERATOR_*` env vars (individual,
      no company), address left blank, contact email wired in. Not legal advice —
      confirm the specifics for your own country if you ever scale up.
- [x] Cookie-consent gating verified — GA4 loads only after explicit "Accept"
      (anonymize_ip on), Plausible is cookieless, banner only shows when GA is
      configured. Wording can still be tweaked to taste, but gating is correct.

## Monetisation (beyond flights)
- [x] Cross-sell on results ("complete your trip"): Hotels works out of the box
      (contextual Hotellook + marker); Insurance / eSIM / Transfers cards appear
      once you set `XSELL_INSURANCE` / `XSELL_ESIM` / `XSELL_TRANSFERS` to your
      Travelpayouts "Create link" URLs. Same marker, higher commission.

## Infrastructure / deploy
- [x] Production WSGI (gunicorn/waitress), ProxyFix, /health, 404/500
- [x] **Deployed live** at https://zbrisi.com — Contabo VPS, gunicorn + nginx +
      systemd, HTTPS via Let's Encrypt (auto-renewing), ufw firewall, runs as
      user `vladan`. DNS at Namecheap.
- [x] **Travelpayouts**: project `Zbrisi.com`, ownership verified, Drive installed
      (`TP_DRIVE_SRC`). Marker earning. (Payout method still optional.)
- [x] **Google Search Console** verified (DNS TXT) + sitemap submitted — 306 URLs
      discovered.
- [x] Analytics: Google Analytics 4 live + consent-gated (`GA_MEASUREMENT_ID`).
      (Plausible was the cookieless alternative; chose free GA.)
- [x] Landing-page city photos (Pexels) + static asset cache-busting (`?v=mtime`)
      so deploys auto-refresh browser caches.
- [ ] Round-trip: optional fixed-date / **real-time** fares (Flight Search API,
      request-access — distinct from the cached flexible-dates feature above).
- [ ] Shared fare cache across workers (Redis) — current cache is per-process.
