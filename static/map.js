/* ============================================================================
   zbriši — Browse on map ("Departures Atlas")
   A dusk-globe atlas: teal oceans, cream land. Click a country (origin) → it
   burns coral and every reachable country glows gold with a ticket-style price
   tag; click a glowing destination → a boarding-pass panel of city→city routes
   slides in, each linking to a live /search.

   Data (precomputed snapshot, see scripts/build_map_connectivity.py):
     regions.geojson        country polygons {iso, name}
     connectivity.json      {originISO: {destISO: minPriceEUR}}   (loaded once)
     routes/<ISO>.json      {destISO: [{o,on,d,dn,p,date}]}       (per origin)
   ========================================================================== */
(function () {
  "use strict";

  var cfg = JSON.parse(document.getElementById("map-cfg").textContent);
  var T = cfg.i18n;

  // Palette (mirrors style.css tokens).
  var C = {
    coral: "#e1542b",
    gold: "#e8a23a",
    land: "#f1e4cb",
    dim: "#e3d4b6",
    water: "#143f49",
    line: "#0e3b36",
  };

  var $ = function (id) { return document.getElementById(id); };
  var statusText = $("mapStatusText"),
      statusEl = $("mapStatus"),
      resetBtn = $("mapReset"),
      legend = $("mapLegend"),
      loading = $("mapLoading"),
      panel = $("mapPanel"),
      panelRoute = $("mapPanelRoute"),
      panelBody = $("mapPanelBody"),
      departEl = $("mapDepart"),
      returnEl = $("mapReturn"),
      poster = $("mapPoster");

  // --- helpers --------------------------------------------------------------
  function fill(tpl, obj) {
    return (tpl || "").replace(/\{(\w+)\}/g, function (_, k) {
      return obj[k] != null ? obj[k] : "";
    });
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function fallbackDate() {
    var d = new Date(); d.setDate(d.getDate() + 30);
    return d.toISOString().slice(0, 10);
  }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDate(iso) {            // "2026-12-14" -> "14-Dec-2026"
    if (!iso) return "";
    var p = String(iso).split("-");
    if (p.length !== 3) return iso;
    return p[2] + "-" + (MON[parseInt(p[1], 10) - 1] || p[1]) + "-" + p[0];
  }

  // --- state ----------------------------------------------------------------
  var regions = null;          // FeatureCollection (mutated for styling)
  var connectivity = null;     // {originISO: {destISO: price}}
  var names = {};              // iso -> country name
  var origins = null;          // Set of valid origin ISO
  var originISO = null;        // currently selected origin
  var reachable = null;        // {destISO: price} for current origin
  var routesCache = {};        // originISO -> routes json
  var hoveredId = null;
  var openDest = null;         // dest country whose panel is open (for re-render)
  var flexVal = "3";           // date flexibility: 0 (month) | 3 | 7 — defaults to ±3
  var FALLBACK = fallbackDate();

  // Friendly dd-mm-yyyy pickers (display) backed by ISO yyyy-mm-dd values, so
  // the rest of the code keeps reading departEl.value as an ISO date. Native
  // <input type=date> can't be forced to dd-mm-yyyy; flatpickr can.
  if (window.flatpickr) {
    var FP = { dateFormat: "Y-m-d", altInput: true, altFormat: "d-M-Y",
               minDate: "today", disableMobile: true };
    flatpickr(departEl, FP);
    flatpickr(returnEl, FP);
  }

  // --- map (deferred until the visitor opens it) ----------------------------
  // Mapbox bills per map load, so the map is NOT created on page load. Bots and
  // crawlers that merely fetch or render the page never trigger a billable load
  // — only an explicit "open the map" click (the poster) does. Pair this with a
  // URL-restricted token + usage cap in the Mapbox dashboard and a Cloudflare
  // rate-limit / Bot Fight Mode on /map.
  var map, popup, mapStarted = false;

  function startMap() {
    if (mapStarted) return;            // create the (billable) map at most once
    mapStarted = true;
    if (poster) poster.classList.add("is-gone");
    loading.classList.remove("is-hidden");

    mapboxgl.accessToken = cfg.token;
    map = new mapboxgl.Map({
      container: "map",
      style: "mapbox://styles/mapbox/light-v11",
      center: [16, 30],
      zoom: 1.45,
      minZoom: 1,
      maxZoom: 7,
      projection: "globe",
      dragRotate: false,
      pitchWithRotate: false,
      doubleClickZoom: false,  // single click = select; avoid click/dblclick clash
      // Wheel/touch zoom is gated behind ctrl/⌘ (and trackpad pinch) so scrolling
      // the page past this tall map doesn't hijack the wheel. The +/- control
      // (top-right) is the primary zoom for selecting small countries.
      cooperativeGestures: true,
      locale: {
        "CooperativeGesturesHandler.WindowsHelpText": T.zoomWin,
        "CooperativeGesturesHandler.MacHelpText": T.zoomMac,
        "CooperativeGesturesHandler.MobileHelpText": T.zoomTouch,
      },
    });
    // Zoom control top-right (always visible, above the fold).
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");

    popup = new mapboxgl.Popup({
      closeButton: false, closeOnClick: false, offset: 8, className: "map-pop",
    });

    // Dusk atmosphere + recoloured basemap = vintage atlas, not a road map.
    map.on("style.load", function () {
      map.setFog({
        color: "rgb(220, 205, 178)",          // lower haze (warm paper)
        "high-color": "rgb(60, 120, 110)",    // upper sky (teal)
        "horizon-blend": 0.06,
        "space-color": "rgb(13, 20, 24)",     // surrounding space
        "star-intensity": 0.45,
      });
      var recolor = [
        ["water", "fill-color", C.water],
        ["water-shadow", "fill-color", C.water],
        ["background", "background-color", "#e9dcc1"],
        ["land", "background-color", "#ece0c6"],
        ["landcover", "fill-color", "#e3d9bd"],
        ["national-park", "fill-color", "#dfd6ba"],
        ["landuse", "fill-color", "#e6dabd"],
      ];
      recolor.forEach(function (r) {
        if (!map.getLayer(r[0])) return;   // light-v11 lacks some layers; skip quietly
        try { map.setPaintProperty(r[0], r[1], r[2]); } catch (e) {}
      });
      // 'style.load' reliably means we can add sources/layers. We init here
      // because the stricter 'load' event can fail to fire for a deferred globe
      // map (the style loads, but the map never reaches the fully-idle state).
      mapReady = true;
      maybeInit();
    });

    // Init only when BOTH the style and the data are ready. Registering the load
    // handler synchronously (before 'load' can fire) avoids any race.
    var mapReady = false, dataReady = false, inited = false;
    function maybeInit() {
      if (mapReady && dataReady && !inited) { inited = true; addLayers(); }
    }
    map.on("load", function () { mapReady = true; maybeInit(); });  // backup signal

    Promise.all([
      fetch(cfg.regions).then(okJson),
      fetch(cfg.connectivity).then(okJson),
    ]).then(function (res) {
      regions = res[0];
      connectivity = res[1];
      origins = new Set(Object.keys(connectivity));
      regions.features.forEach(function (f) {
        var p = f.properties;
        names[p.iso] = p.name;
        p.role = "";
        p.plabel = "";
      });
      dataReady = true;
      maybeInit();
    }).catch(function (err) {
      console.error("[map] data load failed", err);
      loading.innerHTML = "<span>" + esc(T.error) + "</span>";
      loading.classList.add("is-error");
    });
  }

  if (poster) poster.addEventListener("click", startMap);

  function okJson(r) { if (!r.ok) throw new Error(r.status); return r.json(); }

  // --- layers ---------------------------------------------------------------
  function firstSymbolLayer() {
    var layers = map.getStyle().layers || [];
    for (var i = 0; i < layers.length; i++) {
      if (layers[i].type === "symbol") return layers[i].id;
    }
    return undefined;
  }

  function addLayers() {
    if (map.getSource("countries")) return;
    map.addSource("countries", { type: "geojson", data: regions, promoteId: "iso" });
    var before = firstSymbolLayer();

    map.addLayer({
      id: "rg-fill",
      type: "fill",
      source: "countries",
      paint: {
        "fill-color": ["match", ["get", "role"],
          "origin", C.coral, "dest", C.gold, "dim", C.dim, C.land],
        "fill-opacity": ["match", ["get", "role"],
          "origin", 0.92, "dest", 0.86, "dim", 0.4,
          ["case", ["boolean", ["feature-state", "hover"], false], 0.92, 0.78]],
        "fill-color-transition": { duration: 480 },
        "fill-opacity-transition": { duration: 480 },
      },
    }, before);

    map.addLayer({
      id: "rg-line",
      type: "line",
      source: "countries",
      paint: {
        "line-color": ["match", ["get", "role"], "origin", "#7c2a12", "dest", "#9a6516", C.line],
        "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.4, 4, 1.1],
        "line-opacity": ["match", ["get", "role"], "dim", 0.18, 0.4],
      },
    }, before);

    // Ticket-style price tags sit ABOVE place labels so they always read.
    map.addLayer({
      id: "rg-price",
      type: "symbol",
      source: "countries",
      layout: {
        "text-field": ["get", "plabel"],
        "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 1, 11, 4, 14],
        "text-allow-overlap": false,
        "symbol-sort-key": ["to-number", ["coalesce", ["get", "psort"], 99999]],
        "text-padding": 2,
      },
      paint: {
        "text-color": "#3a1c10",
        "text-halo-color": "#f8ecce",
        "text-halo-width": 1.7,
        "text-halo-blur": 0.4,
      },
    });

    wireEvents();
    map.resize();   // container height is final by now; ensure the canvas fills it
    // Hide the veil once the globe paints. 'idle' can lag on a globe (continuous
    // tile loads), so also fall back to a timer — layers are live by now anyway.
    var hideVeil = function () { loading.classList.add("is-hidden"); };
    map.once("idle", hideVeil);
    setTimeout(hideVeil, 1800);
    statusEl.classList.add("is-ready");
  }

  // --- styling state -> source ---------------------------------------------
  function applyRoles() {
    regions.features.forEach(function (f) {
      var p = f.properties, iso = p.iso;
      if (!originISO) { p.role = ""; p.plabel = ""; p.psort = undefined; return; }
      if (iso === originISO) {
        // The origin doubles as its own DOMESTIC destination: when the snapshot
        // has within-country routes (connectivity[iso][iso]), tag the origin
        // with that price so it reads as clickable. psort -1 keeps the tag on
        // top when it overlaps neighbouring price tags.
        p.role = "origin";
        if (reachable && reachable[iso] != null) {
          p.plabel = cfg.cur + Math.round(reachable[iso]);
          p.psort = -1;
        } else { p.plabel = ""; p.psort = undefined; }
        return;
      }
      if (reachable && reachable[iso] != null) {
        p.role = "dest";
        p.plabel = cfg.cur + Math.round(reachable[iso]);
        p.psort = reachable[iso];
      } else {
        p.role = "dim"; p.plabel = ""; p.psort = undefined;
      }
    });
    map.getSource("countries").setData(regions);
  }

  function selectOrigin(iso, lngLat) {
    originISO = iso;
    reachable = connectivity[iso] || {};
    applyRoles();
    closePanel();
    var hasDomestic = reachable[iso] != null;          // self-key = domestic
    var n = Object.keys(reachable).length - (hasDomestic ? 1 : 0);
    var msg = fill(T.origin, { country: names[iso] || iso }) +
      ' · <b>' + fill(T.count, { n: n }) + "</b>";
    if (hasDomestic) msg += ' · <b class="map-dom-hint">' + esc(T.domesticHint) + "</b>";
    setStatus(msg);
    resetBtn.hidden = false;
    legend.hidden = false;
    document.body.classList.add("map-active");
    if (lngLat) {
      map.easeTo({ center: [lngLat.lng, Math.min(lngLat.lat, 62)], duration: 1100,
        zoom: Math.max(map.getZoom(), 1.5), essential: true });
    }
  }

  function reset() {
    originISO = null; reachable = null;
    applyRoles();
    closePanel();
    setStatus(T.pick);
    resetBtn.hidden = true;
    legend.hidden = true;
    document.body.classList.remove("map-active");
    map.easeTo({ center: [16, 30], zoom: 1.45, duration: 900, essential: true });
  }

  function setStatus(html) { statusText.innerHTML = html; }

  function flashNoConn(iso) {
    setStatus(fill(T.noConn, { country: names[iso] || iso }));
    statusEl.classList.remove("shake"); void statusEl.offsetWidth;
    statusEl.classList.add("shake");
  }

  // --- routes panel ---------------------------------------------------------
  function openPanel(destISO) {
    var o = originISO;
    openDest = destISO;
    if (destISO === o) {                              // domestic (within-country)
      panelRoute.innerHTML =
        '<span class="mpr-plane" aria-hidden="true">✈</span>' +
        '<span class="mpr-a">' + esc(fill(T.domesticTitle, { country: names[o] || o })) + "</span>";
    } else {
      panelRoute.innerHTML =
        '<span class="mpr-a">' + esc(names[o] || o) + "</span>" +
        '<span class="mpr-plane" aria-hidden="true">✈</span>' +
        '<span class="mpr-b">' + esc(names[destISO] || destISO) + "</span>";
    }
    panel.classList.add("is-open");
    panel.setAttribute("aria-hidden", "false");
    panelBody.innerHTML = '<div class="mp-loading"><span class="map-spin"></span></div>';

    var cached = routesCache[o];
    if (cached) { renderRoutes(cached[destISO]); return; }
    fetch(cfg.routesBase + o + ".json?v=" + cfg.v)
      .then(okJson)
      .then(function (data) { routesCache[o] = data; renderRoutes(data[destISO]); })
      .catch(function (err) {
        // Don't cache a transient failure — a re-click should retry. Show an
        // error (not the misleading "no routes here") so it's distinguishable.
        console.error("[map] routes fetch failed for " + o, err);
        panelBody.innerHTML = '<p class="mp-empty">' + esc(T.error) + "</p>";
      });
  }

  function renderRoutes(rows) {
    if (!rows || !rows.length) {
      panelBody.innerHTML = '<p class="mp-empty">' + esc(T.panelEmpty) + "</p>";
      return;
    }
    // User-chosen dates flow into /search. Blank = use the snapshot's cheapest
    // date (and keep showing it); a chosen date overrides both link and label.
    var depart = departEl && departEl.value;
    var ret = returnEl && returnEl.value;
    var html = "";
    rows.forEach(function (r, i) {
      var searchDate = depart || r.date || FALLBACK;
      var showDate = depart || r.date;
      var href = cfg.search + "?departure_location=" + encodeURIComponent(r.o) +
        "&destination_location=" + encodeURIComponent(r.d) +
        "&approx_date=" + encodeURIComponent(searchDate) +
        "&currency=" + encodeURIComponent(cfg.currency);
      if (ret && ret >= searchDate) {
        href += "&return_date=" + encodeURIComponent(ret) + "&trip_type=roundtrip";
      }
      if (flexVal !== "0") href += "&flex=" + flexVal;
      html +=
        '<a class="mp-route" href="' + href + '" style="--i:' + i + '">' +
          '<span class="mp-cities">' +
            '<span class="mp-city">' + esc(r.on) + ' <em class="mp-code">' + esc(r.o) + "</em></span>" +
            '<span class="mp-arrow" aria-hidden="true">→</span>' +
            '<span class="mp-city">' + esc(r.dn) + ' <em class="mp-code">' + esc(r.d) + "</em></span>" +
          "</span>" +
          '<span class="mp-right">' +
            '<span class="mp-price"><span class="mp-from">' + esc(T.from) + "</span>" +
              cfg.cur + Math.round(r.p) + "</span>" +
            (showDate ? '<span class="mp-date">' + esc(fmtDate(showDate)) + "</span>" : "") +
          "</span>" +
        "</a>";
    });
    panelBody.innerHTML = html;
  }

  function closePanel() {
    panel.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
    openDest = null;
  }

  // Re-price the open panel when the traveller changes their dates.
  function onDatesChanged() {
    var rfp = returnEl._flatpickr;
    if (departEl.value) {
      if (rfp) rfp.set("minDate", departEl.value); else returnEl.min = departEl.value;
    }
    if (returnEl.value && departEl.value && returnEl.value < departEl.value) {
      if (rfp) rfp.clear(); else returnEl.value = "";
    }
    if (openDest && originISO) openPanel(openDest);  // re-renders from cache
  }

  // --- events ---------------------------------------------------------------
  function wireEvents() {
    map.on("mousemove", "rg-fill", function (e) {
      if (!e.features.length) return;
      var f = e.features[0], iso = f.properties.iso;
      map.getCanvas().style.cursor = "pointer";
      if (hoveredId !== null && hoveredId !== iso) {
        map.setFeatureState({ source: "countries", id: hoveredId }, { hover: false });
      }
      hoveredId = iso;
      map.setFeatureState({ source: "countries", id: iso }, { hover: true });

      var label = esc(names[iso] || iso);
      if (originISO && iso === originISO && reachable && reachable[iso] != null) {
        label += ' <b class="map-pop-price">' + esc(T.domestic) + " " + esc(T.from) + " " + cfg.cur + Math.round(reachable[iso]) + "</b>";
      } else if (originISO && reachable && reachable[iso] != null) {
        label += ' <b class="map-pop-price">' + esc(T.from) + " " + cfg.cur + Math.round(reachable[iso]) + "</b>";
      } else if (originISO && iso === originISO) {
        label += ' <span class="map-pop-tag">●</span>';
      }
      popup.setLngLat(e.lngLat).setHTML('<span class="map-pop-in">' + label + "</span>").addTo(map);
    });

    map.on("mouseleave", "rg-fill", function () {
      map.getCanvas().style.cursor = "";
      if (hoveredId !== null) {
        map.setFeatureState({ source: "countries", id: hoveredId }, { hover: false });
      }
      hoveredId = null;
      popup.remove();
    });

    map.on("click", "rg-fill", function (e) {
      var iso = e.features[0].properties.iso;
      if (originISO && reachable && reachable[iso] != null) { openPanel(iso); return; }
      if (origins.has(iso)) { selectOrigin(iso, e.lngLat); }
      else { flashNoConn(iso); }
    });
  }

  resetBtn.addEventListener("click", reset);
  $("mapPanelClose").addEventListener("click", closePanel);
  departEl.addEventListener("change", onDatesChanged);
  returnEl.addEventListener("change", onDatesChanged);

  // Date-flexibility segmented control (Whole month / ±3 / ±7).
  var flexSeg = $("mapFlex");
  flexSeg.addEventListener("click", function (e) {
    var btn = e.target.closest(".flex-opt");
    if (!btn) return;
    flexVal = btn.getAttribute("data-flex") || "0";
    Array.prototype.forEach.call(flexSeg.querySelectorAll(".flex-opt"), function (b) {
      b.setAttribute("aria-pressed", b === btn ? "true" : "false");
    });
    if (openDest && originISO) openPanel(openDest);  // re-render links from cache
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (panel.classList.contains("is-open")) closePanel();
      else if (originISO) reset();
    }
  });
})();
