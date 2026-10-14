/* zbriši — custom autocomplete, search UX, and results sort/filter.
   Vanilla JS, feature-detected so the same file runs on every page.        */
(function () {
    "use strict";

    /* ------------------------------------------------------------------ *
     * Custom city/airport autocomplete (replaces jQuery UI)
     * ------------------------------------------------------------------ */
    function setupAutocomplete(field) {
        const input = field.querySelector("[data-ac-input]");
        if (!input) return;

        const menu = document.createElement("div");
        menu.className = "ac-menu";
        menu.setAttribute("role", "listbox");
        field.appendChild(menu);

        let items = [];
        let active = -1;
        let timer = null;
        let lastQuery = "";

        const close = () => { menu.classList.remove("open"); menu.innerHTML = ""; active = -1; };

        const planeIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>';
        const cityIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>';

        function render() {
            if (!items.length) { close(); return; }
            menu.innerHTML = items.map((it, i) => {
                const isAir = it.type === "airport";
                const name = it.name || it.label || it.code;
                const meta = [it.country].filter(Boolean).join(" · ");
                return `<div class="ac-item ${isAir ? "is-airport" : ""} ${i === active ? "active" : ""}" role="option" data-i="${i}">
                    <span class="ic">${isAir ? planeIcon : cityIcon}</span>
                    <span><span class="name">${name}</span>${meta ? `<div class="meta">${meta}</div>` : ""}</span>
                    <span class="code">${it.code}</span>
                </div>`;
            }).join("");
            menu.classList.add("open");
        }

        function choose(i) {
            const it = items[i];
            if (!it) return;
            const name = it.name || it.label || it.code;
            input.value = `${name} (${it.code})`;
            close();
            input.dispatchEvent(new Event("change"));
        }

        const acUrl = document.body.dataset.acUrl || "/autocomplete";
        async function fetchSuggest(q) {
            try {
                const r = await fetch(acUrl + "?query=" + encodeURIComponent(q));
                if (!r.ok) return;
                const data = await r.json();
                if (input.value.trim() !== q) return; // stale
                items = data;
                active = -1;
                render();
            } catch (e) { /* network: silently ignore */ }
        }

        input.addEventListener("input", () => {
            const q = input.value.trim();
            if (q === lastQuery) return;
            lastQuery = q;
            clearTimeout(timer);
            if (q.length < 2) { close(); return; }
            timer = setTimeout(() => fetchSuggest(q), 170);
        });

        input.addEventListener("keydown", (e) => {
            if (!menu.classList.contains("open")) return;
            if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(active + 1, items.length - 1); render(); }
            else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(active - 1, 0); render(); }
            else if (e.key === "Enter") { if (active >= 0) { e.preventDefault(); choose(active); } }
            else if (e.key === "Escape") { close(); }
        });

        menu.addEventListener("mousedown", (e) => {
            const el = e.target.closest(".ac-item");
            if (el) { e.preventDefault(); choose(parseInt(el.dataset.i, 10)); }
        });

        input.addEventListener("focus", () => field.classList.add("focused"));
        input.addEventListener("blur", () => { field.classList.remove("focused"); setTimeout(close, 120); });
    }

    document.querySelectorAll("[data-ac]").forEach(setupAutocomplete);

    /* ------------------------------------------------------------------ *
     * "Surprise me — anywhere" + destination inspiration chips
     * ------------------------------------------------------------------ */
    const destInput = document.getElementById("destination_location");
    const depInput = document.getElementById("departure_location");

    const anywhereBtn = document.getElementById("anywhereBtn");
    if (anywhereBtn && destInput) {
        anywhereBtn.addEventListener("click", () => {
            destInput.value = "";
            destInput.placeholder = "✦ Anywhere — surprise me";
            (depInput && !depInput.value ? depInput : document.getElementById("approx_date")).focus();
        });
    }

    document.querySelectorAll(".dest-card").forEach((card) => {
        card.addEventListener("click", () => {
            if (destInput) destInput.value = card.dataset.label || card.dataset.code;
            const form = document.getElementById("searchForm");
            if (form) form.scrollIntoView({ behavior: "smooth", block: "center" });
            if (depInput && !depInput.value) setTimeout(() => depInput.focus(), 400);
        });
    });

    /* ------------------------------------------------------------------ *
     * Trip type: one-way / round-trip toggle (reveals the return field)
     * ------------------------------------------------------------------ */
    (function tripType() {
        const pills = document.getElementById("tripPills");
        const form = document.getElementById("flightForm");
        const tripInput = document.getElementById("tripType");
        const returnInput = document.getElementById("return_date");
        const departInput = document.getElementById("approx_date");
        const hint = document.getElementById("returnHint");
        if (!pills || !form) return;

        // dd-Mon-yyyy pickers — consistent for every visitor (native <input
        // type=date> renders per browser locale). The original inputs keep their
        // ISO value + name, so form submission and the rest of the JS are
        // unchanged. Return allows manual edit so it can be cleared back to
        // blank ("suggest the cheapest returns"); depart can't be emptied.
        if (window.flatpickr) {
            const FP = { dateFormat: "Y-m-d", altInput: true, altFormat: "d-M-Y",
                         minDate: "today", disableMobile: true };
            if (departInput) flatpickr(departInput, FP);
            if (returnInput) flatpickr(returnInput, Object.assign({}, FP, { allowInput: true }));
        }
        const setMin = (inp, d) => {
            if (inp._flatpickr) inp._flatpickr.set("minDate", d || "today");
            else inp.min = d;
        };
        const setDateVal = (inp, d) => {
            if (inp._flatpickr) inp._flatpickr.setDate(d, false);
            else inp.value = d;
        };

        // The return date is OPTIONAL: blank = "suggest the cheapest returns".
        function updateHint() {
            if (!hint) return;
            const empty = !returnInput || !returnInput.value;
            hint.textContent = empty ? hint.dataset.suggest : hint.dataset.near;
            hint.classList.toggle("is-suggest", empty);
        }

        function setMode(mode) {
            const round = mode === "roundtrip";
            form.classList.toggle("roundtrip", round);
            if (tripInput) tripInput.value = mode;
            pills.querySelectorAll("button").forEach((b) =>
                b.setAttribute("aria-pressed", String(b.dataset.trip === mode)));
            if (returnInput) {
                returnInput.required = false;          // never required — blank is valid
                if (round && departInput && departInput.value) {
                    setMin(returnInput, departInput.value);
                }
            }
            updateHint();
        }

        pills.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-trip]");
            if (btn) setMode(btn.dataset.trip);
        });
        if (returnInput) {
            returnInput.addEventListener("input", updateHint);
            returnInput.addEventListener("change", updateHint);  // flatpickr fires change
        }
        if (departInput && returnInput) {
            departInput.addEventListener("change", () => {
                setMin(returnInput, departInput.value);
                if (returnInput.value && returnInput.value < departInput.value) {
                    setDateVal(returnInput, departInput.value);
                }
                updateHint();
            });
        }
        updateHint();

        // Date flexibility: whole month (0) vs +/- N days, as a segmented control.
        const flexSeg = document.querySelector(".flex-seg");
        const flexInput = document.getElementById("flexInput");
        if (flexSeg && flexInput) {
            flexSeg.addEventListener("click", (e) => {
                const b = e.target.closest("button[data-flex]");
                if (!b) return;
                flexInput.value = b.dataset.flex;
                flexSeg.querySelectorAll("button").forEach((x) =>
                    x.setAttribute("aria-pressed", String(x === b)));
            });
        }
    })();

    /* ------------------------------------------------------------------ *
     * Passengers picker — steppers for adults / children / infants
     * ------------------------------------------------------------------ */
    (function paxPicker() {
        const picker = document.getElementById("paxPicker");
        if (!picker) return;
        const btn = document.getElementById("paxBtn");
        const panel = document.getElementById("paxPanel");
        const label = document.getElementById("paxLabel");
        const inputs = {
            adults: document.getElementById("adultsInput"),
            children: document.getElementById("childrenInput"),
            infants: document.getElementById("infantsInput"),
        };
        const counts = { adults: 1, children: 0, infants: 0 };
        const MIN = { adults: 1, children: 0, infants: 0 };
        const MAX_TOTAL = 9;

        function render() {
            let total = 0;
            for (const k in counts) {
                total += counts[k];
                inputs[k].value = counts[k];
                const c = picker.querySelector('[data-count="' + k + '"]');
                if (c) c.textContent = counts[k];
                const minus = picker.querySelector('.pax-step-btn[data-pax="' + k + '"][data-dir="-1"]');
                if (minus) minus.disabled = counts[k] <= MIN[k];
            }
            picker.querySelectorAll('.pax-step-btn[data-dir="1"]').forEach((b) => {
                b.disabled = total >= MAX_TOTAL;
            });
            label.textContent = total + " " + (total === 1 ? label.dataset.one : label.dataset.many);
        }

        picker.addEventListener("click", (e) => {
            const step = e.target.closest(".pax-step-btn");
            if (!step || step.disabled) return;
            const k = step.dataset.pax, dir = +step.dataset.dir;
            counts[k] = Math.max(MIN[k], counts[k] + dir);
            render();
        });

        function setOpen(open) {
            panel.hidden = !open;
            btn.setAttribute("aria-expanded", String(open));
        }
        btn.addEventListener("click", (e) => { e.stopPropagation(); setOpen(panel.hidden); });
        document.getElementById("paxDone").addEventListener("click", () => setOpen(false));
        document.addEventListener("click", (e) => { if (!picker.contains(e.target)) setOpen(false); });
        document.addEventListener("keydown", (e) => { if (e.key === "Escape") setOpen(false); });

        render();
    })();

    /* ------------------------------------------------------------------ *
     * Loading overlay on search submit
     * ------------------------------------------------------------------ */
    const form = document.getElementById("searchForm");
    const loader = document.getElementById("loader");
    if (form && loader) {
        form.addEventListener("submit", () => { loader.classList.add("show"); });
    }
    // Hide the overlay whenever the page is shown — crucially on back/forward
    // cache restores, where the "Scanning the skies…" loader would otherwise
    // stay stuck after pressing the browser Back button.
    if (loader) {
        window.addEventListener("pageshow", () => { loader.classList.remove("show"); });
    }

    /* ------------------------------------------------------------------ *
     * Cookie consent + consent-gated analytics (GA4). Plausible, if used,
     * is cookieless and loaded server-side without consent.
     * ------------------------------------------------------------------ */
    (function consent() {
        const banner = document.getElementById("cookieBanner");
        const gaId = document.body.dataset.ga;
        const KEY = "zbrisi_consent";

        function loadGA(id) {
            if (!id || window.gtag) return;
            const s = document.createElement("script");
            s.async = true;
            s.src = "https://www.googletagmanager.com/gtag/js?id=" + id;
            document.head.appendChild(s);
            window.dataLayer = window.dataLayer || [];
            window.gtag = function () { window.dataLayer.push(arguments); };
            window.gtag("js", new Date());
            window.gtag("config", id, { anonymize_ip: true });
        }

        const stored = localStorage.getItem(KEY);
        if (stored === "accepted") loadGA(gaId);
        if (!banner) return;
        if (stored) { banner.style.display = "none"; return; }

        banner.classList.add("show");
        const accept = document.getElementById("cookieAccept");
        const decline = document.getElementById("cookieDecline");
        if (accept) accept.addEventListener("click", () => {
            localStorage.setItem(KEY, "accepted"); loadGA(gaId); banner.classList.remove("show");
        });
        if (decline) decline.addEventListener("click", () => {
            localStorage.setItem(KEY, "declined"); banner.classList.remove("show");
        });
    })();

    /* Track outbound "View deal" clicks (works with Plausible or GA). */
    document.querySelectorAll(".deal-link").forEach((a) => {
        a.addEventListener("click", () => {
            try {
                if (window.plausible) window.plausible("View Deal");
                if (window.gtag) window.gtag("event", "view_deal", { transport_type: "beacon" });
            } catch (e) { /* ignore */ }
        });
    });

    /* ------------------------------------------------------------------ *
     * Budget explorer: "fare throttle" slider live-filters the deal grid
     * (only runs on /anywhere).
     * ------------------------------------------------------------------ */
    (function budgetExplorer() {
        const throttle = document.getElementById("bxThrottle");
        const grid = document.getElementById("dealGrid");
        const range = document.getElementById("bxRange");
        if (!throttle || !grid || !range) return;

        const capVal = document.getElementById("bxCapVal");
        const countEl = document.getElementById("bxCount");
        const noMatch = document.getElementById("bxNoMatch");
        const cards = Array.from(grid.querySelectorAll(".deal-card"));
        const symbol = throttle.dataset.symbol || "";
        const min = parseInt(throttle.dataset.min, 10) || 0;
        const max = parseInt(throttle.dataset.max, 10) || 0;
        const tpl = throttle.dataset.tpl || "{n} · {amount}";
        const tplAll = throttle.dataset.tplAll || "{n}";

        const fillPct = (v) => (max <= min ? 100 : ((v - min) / (max - min)) * 100);

        function apply() {
            const cap = parseInt(range.value, 10);
            let n = 0;
            cards.forEach((c) => {
                const ok = (parseFloat(c.dataset.price) || 0) <= cap;
                c.classList.toggle("out", !ok);
                if (ok) n++;
            });
            if (capVal) capVal.textContent = symbol + cap;
            range.style.setProperty("--fill", fillPct(cap) + "%");
            if (countEl) {
                countEl.innerHTML = (cap >= max ? tplAll : tpl)
                    .replace("{n}", "<b>" + n + "</b>")
                    .replace("{amount}", symbol + cap);
            }
            if (noMatch) noMatch.hidden = n > 0;
            grid.style.display = n > 0 ? "" : "none";
        }
        range.addEventListener("input", apply);
        apply();
    })();

    /* ------------------------------------------------------------------ *
     * Recent searches — remember the last few on the home form (localStorage)
     * and show them as quick chips. No DB.
     * ------------------------------------------------------------------ */
    (function recentSearches() {
        const KEY = "zbrisi_recent";
        const MAX = 5;
        const read = () => {
            try { return JSON.parse(localStorage.getItem(KEY)) || []; }
            catch (e) { return []; }
        };
        const write = (arr) => {
            try { localStorage.setItem(KEY, JSON.stringify(arr.slice(0, MAX))); }
            catch (e) { /* quota / private mode — ignore */ }
        };
        const strip = (s) => (s || "").replace(/\s*\([A-Z]{3}\)\s*$/, "").trim();
        const esc = (s) => (s || "").replace(/[&<>"']/g, (c) =>
            ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

        // Capture the current search when the home form is submitted.
        const form = document.getElementById("searchForm");
        if (form) form.addEventListener("submit", () => {
            const v = (id) => { const el = document.getElementById(id); return el ? el.value.trim() : ""; };
            const from = v("departure_location");
            if (!from) return;
            const item = {
                from, to: v("destination_location"), date: v("approx_date"),
                ret: v("return_date"), trip: v("tripType"), cur: v("currencyInput"),
                flex: v("flexInput"), ad: v("adultsInput"), ch: v("childrenInput"), inf: v("infantsInput"),
            };
            const sig = (x) => [x.from, x.to, x.date, x.ret, x.trip].join("|").toLowerCase();
            const arr = read().filter((x) => sig(x) !== sig(item));
            arr.unshift(item);
            write(arr);
        });

        // Render the chips (home page only).
        const box = document.getElementById("recentSearches");
        if (!box) return;
        const chips = document.getElementById("recentChips");
        const searchUrl = box.dataset.searchUrl || "/search";
        const anywhere = box.dataset.anywhere || "Anywhere";
        const histIcon = '<svg class="rc-ic" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 5.3L3 8"/><path d="M12 7v5l4 2"/></svg>';
        const fmtDate = (d) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(d || ""); return m ? `${m[3]}.${m[2]}.` : ""; };

        function buildUrl(it) {
            const p = new URLSearchParams();
            p.set("departure_location", it.from);
            if (it.to) p.set("destination_location", it.to);
            p.set("approx_date", it.date);
            if (it.ret) p.set("return_date", it.ret);
            p.set("trip_type", it.trip || "oneway");
            if (it.cur) p.set("currency", it.cur);
            if (it.flex) p.set("flex", it.flex);
            if (it.ad) p.set("adults", it.ad);
            if (it.ch) p.set("children", it.ch);
            if (it.inf) p.set("infants", it.inf);
            return searchUrl + "?" + p.toString();
        }

        function render() {
            const arr = read();
            box.hidden = !arr.length;
            if (!arr.length) return;
            chips.innerHTML = arr.map((it, i) => {
                const to = strip(it.to) || anywhere;
                const date = fmtDate(it.date);
                return `<div class="recent-chip">
                    <button type="button" class="rc-go" data-i="${i}">
                        ${histIcon}
                        <span class="rc-route">${esc(strip(it.from))}<span class="rc-arrow">→</span>${esc(to)}</span>
                        ${date ? `<span class="rc-date">${date}</span>` : ""}
                    </button>
                    <button type="button" class="rc-del" data-del="${i}" aria-label="×">×</button>
                </div>`;
            }).join("");
        }

        chips.addEventListener("click", (e) => {
            const go = e.target.closest(".rc-go");
            const del = e.target.closest(".rc-del");
            if (go) {
                const it = read()[parseInt(go.dataset.i, 10)];
                if (it) window.location.href = buildUrl(it);
            } else if (del) {
                const arr = read();
                arr.splice(parseInt(del.dataset.del, 10), 1);
                write(arr);
                render();
            }
        });
        const clearBtn = document.getElementById("recentClear");
        if (clearBtn) clearBtn.addEventListener("click", () => { write([]); render(); });
        render();
    })();

    /* ------------------------------------------------------------------ *
     * Auto-detect "From": prefill the departure city from the visitor's IP
     * (Travelpayouts whereami — no permission prompt, no cookies). Only fills
     * an empty field, never submits; the user can type over it.
     * ------------------------------------------------------------------ */
    (function autoDetectFrom() {
        const inputs = ["departure_location", "promoFrom"]
            .map((id) => document.getElementById(id)).filter(Boolean);
        const empties = inputs.filter((i) => !i.value.trim());
        if (!empties.length) return;

        const KEY = "zbrisi_geo";
        const noteText = document.body.dataset.geoNote || "";

        function addNote(inp) {
            const wrap = inp.closest("[data-ac]");
            if (!wrap || !noteText || wrap.querySelector(".geo-note")) return;
            const el = document.createElement("small");
            el.className = "geo-note";
            el.textContent = noteText;
            wrap.appendChild(el);
            inp.addEventListener("input", () => el.remove(), { once: true });
        }
        function apply(d) {
            if (!d || !d.iata || !d.name) return;
            const val = `${d.name} (${d.iata})`;
            empties.forEach((inp) => {
                if (inp.value.trim()) return;        // user already typed
                inp.value = val;
                inp.dispatchEvent(new Event("change"));
                addNote(inp);
            });
        }

        const cached = sessionStorage.getItem(KEY);
        if (cached) { try { apply(JSON.parse(cached)); } catch (e) { /* ignore */ } return; }

        const ctrl = ("AbortController" in window) ? new AbortController() : null;
        const timer = ctrl ? setTimeout(() => ctrl.abort(), 4000) : null;
        fetch("https://www.travelpayouts.com/whereami?locale=en", ctrl ? { signal: ctrl.signal } : {})
            .then((r) => (r.ok ? r.json() : null))
            .then((d) => {
                if (timer) clearTimeout(timer);
                if (d && d.iata && d.name) {
                    try { sessionStorage.setItem(KEY, JSON.stringify({ iata: d.iata, name: d.name })); } catch (e) { /* ignore */ }
                    apply(d);
                }
            })
            .catch(() => { if (timer) clearTimeout(timer); });
    })();

    /* ------------------------------------------------------------------ *
     * Results: sort + filter (only runs on the results page)
     * ------------------------------------------------------------------ */
    const list = document.getElementById("resultsList");
    if (!list) return;

    const tickets = Array.from(list.querySelectorAll(".ticket"));
    const visCount = document.getElementById("visCount");
    const noMatch = document.getElementById("noMatch");
    const state = { sort: "price", stops: "any", maxPrice: Infinity, airlines: null };

    const num = (el, attr) => parseFloat(el.dataset[attr]) || 0;

    function apply() {
        let visible = 0;
        tickets.forEach((t) => {
            const okStops = state.stops === "any" || num(t, "stops") <= parseInt(state.stops, 10);
            const okPrice = num(t, "price") <= state.maxPrice;
            const okAir = !state.airlines || state.airlines.has(t.dataset.airline);
            const show = okStops && okPrice && okAir;
            t.style.display = show ? "" : "none";
            if (show) visible++;
        });

        const shown = tickets.filter((t) => t.style.display !== "none");
        shown.sort((a, b) => {
            if (state.sort === "price") return num(a, "price") - num(b, "price");
            if (state.sort === "stops") return num(a, "stops") - num(b, "stops") || num(a, "price") - num(b, "price");
            if (state.sort === "date") return (a.dataset.date || "").localeCompare(b.dataset.date || "") || num(a, "price") - num(b, "price");
            return 0;
        });
        shown.forEach((t) => list.appendChild(t));

        if (visCount) visCount.textContent = visible;
        if (noMatch) noMatch.style.display = visible ? "none" : "block";
        list.style.display = visible ? "" : "none";
        updateFilterDot();
    }

    function bindSeg(id, key, cast) {
        const seg = document.getElementById(id);
        if (!seg) return;
        seg.addEventListener("click", (e) => {
            const btn = e.target.closest("button");
            if (!btn) return;
            seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
            state[key] = cast ? cast(btn.dataset[key]) : btn.dataset[key];
            apply();
        });
    }
    bindSeg("sortSeg", "sort");
    bindSeg("stopsSeg", "stops");

    const priceRange = document.getElementById("priceRange");
    const priceVal = document.getElementById("priceVal");
    if (priceRange) {
        const curLabel = (priceVal ? priceVal.textContent.split(" ").pop() : "");
        priceRange.addEventListener("input", () => {
            state.maxPrice = parseFloat(priceRange.value);
            if (priceVal) priceVal.textContent = Math.round(state.maxPrice) + " " + curLabel;
            apply();
        });
    }

    const airlineList = document.getElementById("airlineList");
    if (airlineList) {
        airlineList.addEventListener("change", () => {
            const checked = Array.from(airlineList.querySelectorAll("input:checked")).map((c) => c.value);
            const all = airlineList.querySelectorAll("input").length;
            state.airlines = checked.length === all ? null : new Set(checked);
            apply();
        });
    }

    const panel = document.getElementById("filterPanel");
    const toggle = document.getElementById("filtersToggle");
    if (toggle && panel) {
        toggle.addEventListener("click", () => {
            const open = panel.classList.toggle("open");
            toggle.setAttribute("aria-expanded", String(open));
        });
    }

    function updateFilterDot() {
        if (!toggle) return;
        const active = state.stops !== "any" || (priceRange && state.maxPrice < parseFloat(priceRange.max)) || state.airlines !== null;
        toggle.classList.toggle("active", !!active);
    }

    function resetFilters() {
        state.stops = "any"; state.maxPrice = Infinity; state.airlines = null;
        const stopsSeg = document.getElementById("stopsSeg");
        if (stopsSeg) stopsSeg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.stops === "any")));
        if (priceRange) { priceRange.value = priceRange.max; priceRange.dispatchEvent(new Event("input")); }
        if (airlineList) airlineList.querySelectorAll("input").forEach((c) => (c.checked = true));
        apply();
    }
    const clearBtn = document.getElementById("filterClear");
    const emptyReset = document.getElementById("emptyReset");
    if (clearBtn) clearBtn.addEventListener("click", resetFilters);
    if (emptyReset) emptyReset.addEventListener("click", resetFilters);
})();
