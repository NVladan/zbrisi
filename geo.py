"""
Geography for Zbriši's Balkan wedge.

Defines the cities we feature (with English + Serbian names), which ones are
treated as departure origins (the Balkan focus) vs. popular destinations, and a
generator for the origin->destination route catalogue that powers the
programmatic-SEO landing pages and the sitemap.
"""

# code -> names + country, in both languages. `g` is a poster-style gradient.
CITIES = {
    # --- Balkan origins -------------------------------------------------
    "BEG": {"en": "Belgrade",   "sr": "Beograd",   "country_en": "Serbia",                 "country_sr": "Srbija",               "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "INI": {"en": "Niš",        "sr": "Niš",       "country_en": "Serbia",                 "country_sr": "Srbija",               "g": "linear-gradient(150deg,#a8472f,#3f2a44)"},
    "TGD": {"en": "Podgorica",  "sr": "Podgorica", "country_en": "Montenegro",             "country_sr": "Crna Gora",            "g": "linear-gradient(150deg,#356f75,#23303f)"},
    "TIV": {"en": "Tivat",      "sr": "Tivat",     "country_en": "Montenegro",             "country_sr": "Crna Gora",            "g": "linear-gradient(150deg,#1f8f86,#2a4a52)"},
    "SJJ": {"en": "Sarajevo",   "sr": "Sarajevo",  "country_en": "Bosnia & Herzegovina",   "country_sr": "Bosna i Hercegovina",  "g": "linear-gradient(150deg,#4a6b3a,#283a2a)"},
    "SKP": {"en": "Skopje",     "sr": "Skoplje",   "country_en": "North Macedonia",        "country_sr": "Severna Makedonija",   "g": "linear-gradient(150deg,#c06a2a,#5e3320)"},
    "ZAG": {"en": "Zagreb",     "sr": "Zagreb",    "country_en": "Croatia",                "country_sr": "Hrvatska",             "g": "linear-gradient(150deg,#356f95,#2a3650)"},
    "LJU": {"en": "Ljubljana",  "sr": "Ljubljana", "country_en": "Slovenia",               "country_sr": "Slovenija",            "g": "linear-gradient(150deg,#3a7c8f,#28414f)"},
    "SOF": {"en": "Sofia",      "sr": "Sofija",    "country_en": "Bulgaria",               "country_sr": "Bugarska",             "g": "linear-gradient(150deg,#8a4a2c,#3a2a3f)"},
    "TIA": {"en": "Tirana",     "sr": "Tirana",    "country_en": "Albania",                "country_sr": "Albanija",             "g": "linear-gradient(150deg,#b5424f,#4a2330)"},
    "PRN": {"en": "Pristina",   "sr": "Priština",  "country_en": "Kosovo",                 "country_sr": "Kosovo",               "g": "linear-gradient(150deg,#5a3578,#2c2340)"},
    "TZL": {"en": "Tuzla",      "sr": "Tuzla",     "country_en": "Bosnia & Herzegovina",   "country_sr": "Bosna i Hercegovina",  "g": "linear-gradient(150deg,#4a6b3a,#283a2a)"},
    "BNX": {"en": "Banja Luka", "sr": "Banja Luka","country_en": "Bosnia & Herzegovina",   "country_sr": "Bosna i Hercegovina",  "g": "linear-gradient(150deg,#46704a,#283a2e)"},
    "OHD": {"en": "Ohrid",      "sr": "Ohrid",     "country_en": "North Macedonia",        "country_sr": "Severna Makedonija",   "g": "linear-gradient(150deg,#c06a2a,#5e3320)"},

    # --- Popular destinations ------------------------------------------
    "VIE": {"en": "Vienna",     "sr": "Beč",       "country_en": "Austria",     "country_sr": "Austrija",            "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "BER": {"en": "Berlin",     "sr": "Berlin",    "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#293a5e,#7180a0)"},
    "BCN": {"en": "Barcelona",  "sr": "Barselona", "country_en": "Spain",       "country_sr": "Španija",             "g": "linear-gradient(150deg,#e2603a,#b5325f)"},
    "ROM": {"en": "Rome",       "sr": "Rim",       "country_en": "Italy",       "country_sr": "Italija",             "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "MIL": {"en": "Milan",      "sr": "Milano",    "country_en": "Italy",       "country_sr": "Italija",             "g": "linear-gradient(150deg,#7a4b8f,#3a2a4f)"},
    "PAR": {"en": "Paris",      "sr": "Pariz",     "country_en": "France",      "country_sr": "Francuska",           "g": "linear-gradient(150deg,#34507a,#26304a)"},
    "LON": {"en": "London",     "sr": "London",    "country_en": "United Kingdom","country_sr": "Velika Britanija",   "g": "linear-gradient(150deg,#3a5a6f,#262f3f)"},
    "AMS": {"en": "Amsterdam",  "sr": "Amsterdam", "country_en": "Netherlands", "country_sr": "Holandija",           "g": "linear-gradient(150deg,#356f95,#2a3650)"},
    "IST": {"en": "Istanbul",   "sr": "Istanbul",  "country_en": "Türkiye",     "country_sr": "Turska",              "g": "linear-gradient(150deg,#523578,#bb4259)"},
    "ATH": {"en": "Athens",     "sr": "Atina",     "country_en": "Greece",      "country_sr": "Grčka",               "g": "linear-gradient(150deg,#2a6f8f,#23414f)"},
    "ZRH": {"en": "Zurich",     "sr": "Cirih",     "country_en": "Switzerland", "country_sr": "Švajcarska",          "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "FRA": {"en": "Frankfurt",  "sr": "Frankfurt", "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#3a4a6f,#262f3f)"},
    "MLA": {"en": "Malta",      "sr": "Malta",     "country_en": "Malta",       "country_sr": "Malta",               "g": "linear-gradient(150deg,#d9842c,#6f3686)"},
    "DXB": {"en": "Dubai",      "sr": "Dubai",     "country_en": "UAE",         "country_sr": "UAE",                 "g": "linear-gradient(150deg,#c06a2a,#5e3320)"},
    "BRU": {"en": "Brussels",   "sr": "Brisel",    "country_en": "Belgium",     "country_sr": "Belgija",             "g": "linear-gradient(150deg,#3a5a6f,#262f3f)"},
    "DTM": {"en": "Dortmund",   "sr": "Dortmund",  "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#3a4a6f,#262f3f)"},
    "NUE": {"en": "Nuremberg",  "sr": "Nirnberg",  "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#293a5e,#7180a0)"},
    "HAM": {"en": "Hamburg",    "sr": "Hamburg",   "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#356f95,#2a3650)"},
    "CPH": {"en": "Copenhagen", "sr": "Kopenhagen","country_en": "Denmark",     "country_sr": "Danska",              "g": "linear-gradient(150deg,#2a6f8f,#23414f)"},
    "OSL": {"en": "Oslo",       "sr": "Oslo",      "country_en": "Norway",      "country_sr": "Norveška",            "g": "linear-gradient(150deg,#3a7c8f,#28414f)"},
    "STO": {"en": "Stockholm",  "sr": "Stokholm",  "country_en": "Sweden",      "country_sr": "Švedska",             "g": "linear-gradient(150deg,#34507a,#26304a)"},
    "BUD": {"en": "Budapest",   "sr": "Budimpešta","country_en": "Hungary",     "country_sr": "Mađarska",            "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "PRG": {"en": "Prague",     "sr": "Prag",      "country_en": "Czechia",     "country_sr": "Češka",               "g": "linear-gradient(150deg,#7a4b8f,#3a2a4f)"},
    "WAW": {"en": "Warsaw",     "sr": "Varšava",   "country_en": "Poland",      "country_sr": "Poljska",             "g": "linear-gradient(150deg,#a8472f,#3f2a44)"},
    "MAD": {"en": "Madrid",     "sr": "Madrid",    "country_en": "Spain",       "country_sr": "Španija",             "g": "linear-gradient(150deg,#e2603a,#b5325f)"},
    "LIS": {"en": "Lisbon",     "sr": "Lisabon",   "country_en": "Portugal",    "country_sr": "Portugal",            "g": "linear-gradient(150deg,#1f8f86,#e0b24a)"},
    "FMM": {"en": "Memmingen",  "sr": "Memingen",  "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#3a4a6f,#262f3f)"},
    "STR": {"en": "Stuttgart",  "sr": "Štutgart",  "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#293a5e,#7180a0)"},
    "MUC": {"en": "Munich",     "sr": "Minhen",    "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#3a4a6f,#262f3f)"},
    "CGN": {"en": "Cologne",    "sr": "Keln",      "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#356f95,#2a3650)"},
    "HAJ": {"en": "Hannover",   "sr": "Hanover",   "country_en": "Germany",     "country_sr": "Nemačka",             "g": "linear-gradient(150deg,#293a5e,#7180a0)"},
    "BSL": {"en": "Basel",      "sr": "Bazel",     "country_en": "Switzerland", "country_sr": "Švajcarska",          "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "EIN": {"en": "Eindhoven",  "sr": "Ajndhoven", "country_en": "Netherlands", "country_sr": "Holandija",           "g": "linear-gradient(150deg,#356f95,#2a3650)"},
    "GOT": {"en": "Gothenburg", "sr": "Geteborg",  "country_en": "Sweden",      "country_sr": "Švedska",             "g": "linear-gradient(150deg,#34507a,#26304a)"},
    "CTA": {"en": "Catania",    "sr": "Katanija",  "country_en": "Italy",       "country_sr": "Italija",             "g": "linear-gradient(150deg,#b5503a,#5e3328)"},
    "VCE": {"en": "Venice",     "sr": "Venecija",  "country_en": "Italy",       "country_sr": "Italija",             "g": "linear-gradient(150deg,#7a4b8f,#3a2a4f)"},
}

# Balkan departure cities (the wedge) and the destinations we build pages for.
ORIGINS = ["BEG", "INI", "TGD", "TIV", "SJJ", "SKP", "ZAG", "LJU", "SOF", "TIA", "PRN",
           "TZL", "BNX", "OHD"]
DESTINATIONS = ["VIE", "BER", "BCN", "ROM", "MIL", "PAR", "LON", "AMS", "IST", "ATH",
                "ZRH", "FRA", "MLA", "DXB", "BRU", "DTM", "NUE", "HAM", "CPH", "OSL",
                "STO", "BUD", "PRG", "WAW", "MAD", "LIS",
                "FMM", "STR", "MUC", "CGN", "HAJ", "BSL", "EIN", "GOT", "CTA", "VCE"]


# Serbian genitive ("iz X" = from X) and accusative ("za X" = to X) forms, so
# headings read as natural Serbian instead of "iz Beograd".
_SR_CASES = {
    "BEG": ("Beograda", "Beograd"),   "INI": ("Niša", "Niš"),
    "TGD": ("Podgorice", "Podgoricu"),"TIV": ("Tivta", "Tivat"),
    "SJJ": ("Sarajeva", "Sarajevo"),  "SKP": ("Skoplja", "Skoplje"),
    "ZAG": ("Zagreba", "Zagreb"),     "LJU": ("Ljubljane", "Ljubljanu"),
    "SOF": ("Sofije", "Sofiju"),      "TIA": ("Tirane", "Tiranu"),
    "PRN": ("Prištine", "Prištinu"),
    "VIE": ("Beča", "Beč"),           "BER": ("Berlina", "Berlin"),
    "BCN": ("Barselone", "Barselonu"),"ROM": ("Rima", "Rim"),
    "MIL": ("Milana", "Milano"),      "PAR": ("Pariza", "Pariz"),
    "LON": ("Londona", "London"),     "AMS": ("Amsterdama", "Amsterdam"),
    "IST": ("Istanbula", "Istanbul"), "ATH": ("Atine", "Atinu"),
    "ZRH": ("Ciriha", "Cirih"),       "FRA": ("Frankfurta", "Frankfurt"),
    "MLA": ("Malte", "Maltu"),        "DXB": ("Dubaija", "Dubai"),
    "BRU": ("Brisela", "Brisel"),     "DTM": ("Dortmunda", "Dortmund"),
    "NUE": ("Nirnberga", "Nirnberg"), "HAM": ("Hamburga", "Hamburg"),
    "CPH": ("Kopenhagena", "Kopenhagen"), "OSL": ("Osla", "Oslo"),
    "STO": ("Stokholma", "Stokholm"), "BUD": ("Budimpešte", "Budimpeštu"),
    "PRG": ("Praga", "Prag"),         "WAW": ("Varšave", "Varšavu"),
    "MAD": ("Madrida", "Madrid"),     "LIS": ("Lisabona", "Lisabon"),
    "TZL": ("Tuzle", "Tuzlu"),        "BNX": ("Banje Luke", "Banju Luku"),
    "OHD": ("Ohrida", "Ohrid"),
    "FMM": ("Memingena", "Memingen"), "STR": ("Štutgarta", "Štutgart"),
    "MUC": ("Minhena", "Minhen"),     "CGN": ("Kelna", "Keln"),
    "HAJ": ("Hanovera", "Hanover"),   "BSL": ("Bazela", "Bazel"),
    "EIN": ("Ajndhovena", "Ajndhoven"), "GOT": ("Geteborga", "Geteborg"),
    "CTA": ("Katanije", "Kataniju"),  "VCE": ("Venecije", "Veneciju"),
}


def city_name(code, lang="en"):
    """Localised city name, falling back to the raw code."""
    c = CITIES.get(code)
    if not c:
        return code
    return c.get(lang) or c.get("en") or code


def city_decl(code, lang="en", case="nom"):
    """City name in the requested grammatical case (Serbian only; else nominative)."""
    if lang != "sr":
        return city_name(code, lang)
    forms = _SR_CASES.get(code)
    if forms:
        if case == "gen":
            return forms[0]
        if case == "acc":
            return forms[1]
    return city_name(code, "sr")


def local_matches(query, lang="en", limit=6):
    """Match the query against our known cities (EN + SR names + code)."""
    q = query.strip().lower()
    if not q:
        return []
    out = []
    for code, c in CITIES.items():
        names = [c.get("en", ""), c.get("sr", "")]
        if (code.lower().startswith(q)
                or any(n.lower().startswith(q) for n in names)
                or any(q in n.lower() for n in names)):
            disp = c.get(lang) or c["en"]
            out.append({
                "value": code,
                "label": f"{disp} ({code})",
                "name": disp,
                "country": c.get(f"country_{lang}") or c.get("country_en", ""),
                "code": code,
                "type": "city",
            })
        if len(out) >= limit:
            break
    return out


def resolve_name(text):
    """Reverse-lookup a city name (EN or SR) to its IATA code, else None."""
    q = (text or "").strip().lower()
    if not q:
        return None
    for code, c in CITIES.items():
        if q in (c.get("en", "").lower(), c.get("sr", "").lower()):
            return code
    return None


def country_name(code, lang="en"):
    c = CITIES.get(code)
    if not c:
        return ""
    return c.get(f"country_{lang}") or c.get("country_en") or ""


def gradient(code):
    c = CITIES.get(code)
    return c.get("g") if c else "linear-gradient(150deg,#356f95,#2a3650)"


def route_catalog():
    """All (origin, destination) pairs we build SEO pages for."""
    return [(o, d) for o in ORIGINS for d in DESTINATIONS if o != d]


def destinations_for(origin):
    """Destinations offered from a given origin (for related-links / hub)."""
    return [d for d in DESTINATIONS if d != origin]


def origins_for(destination):
    """Balkan origins that fly to a given destination (for related links)."""
    return [o for o in ORIGINS if o != destination]


def is_known(code):
    return code in CITIES
