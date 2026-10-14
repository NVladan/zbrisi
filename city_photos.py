"""City background photos for the destination cards (landing grid + /anywhere).

Two jobs in one place:

  * `IMAGES` / `image_for(code)` — the local index of static/img/cities/<CODE>.jpg
    photos the app serves.
  * `ensure(codes)` — on-demand fetch: when a destination shows up that we don't
    have a photo for yet, a single background worker downloads one from Pexels,
    crops it and saves it, so it's there on the next view. The "anywhere" data
    surfaces a different long tail of airports on every call, so we can't
    pre-bake them all; this fills the gaps automatically, locally and on the
    host (set PEXELS_API_KEY there too). Falls back to the brand gradient until
    a photo lands, and no-ops entirely when no API key is configured.

The batch tool scripts/fetch_city_images.py reuses `query_for` + `download_one`.
"""
import io
import os
import re
import threading
import time
from queue import Queue, Empty

import requests
from dotenv import load_dotenv

import geo
import places

# Load .env now so PEXELS_API_KEY is available even though app.py imports this
# module before it calls load_dotenv() itself (import order would otherwise leave
# the key empty and silently disable on-demand fetching). Idempotent.
load_dotenv()

try:
    from PIL import Image, ImageOps
    RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS
except ImportError:  # Pillow missing -> on-demand disabled, gradients still work
    Image = None

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "static", "img", "cities")
SIZE = (840, 600)          # card-friendly 1.4:1; Pillow cover-crops to this
API = "https://api.pexels.com/v1/search"
_HTTP_TIMEOUT = 30
# A browser-like UA: the default python-requests UA trips Pexels' Cloudflare
# bot-protection (429s after a few hundred calls regardless of the real rate
# limit), which kneecaps bulk fetching.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Landmark-focused search terms read far better on the cards than generic
# skylines. Any other code falls back to its real city name (places.json).
QUERIES = {
    # --- Balkan origins ---
    "BEG": "Belgrade Serbia Kalemegdan fortress",
    "INI": "Nis Serbia fortress",
    "TGD": "Podgorica Montenegro Millennium Bridge",
    "TIV": "Tivat Montenegro Porto Montenegro marina",
    "SJJ": "Sarajevo Bosnia Bascarsija old town",
    "SKP": "Skopje North Macedonia stone bridge",
    "ZAG": "Zagreb Croatia cathedral old town",
    "LJU": "Ljubljana Slovenia dragon bridge castle",
    "SOF": "Sofia Bulgaria Alexander Nevsky cathedral",
    "TIA": "Tirana Albania Skanderbeg square",
    "PRN": "Pristina Kosovo city",
    "TZL": "Tuzla Bosnia old town",
    "BNX": "Banja Luka Bosnia Kastel fortress",
    "OHD": "Ohrid North Macedonia lake church",
    # --- Popular destinations ---
    "VIE": "Vienna Austria Schonbrunn palace",
    "BER": "Berlin Brandenburg Gate",
    "BCN": "Barcelona Sagrada Familia",
    "ROM": "Rome Colosseum",
    "MIL": "Milan Italy Duomo cathedral",
    "PAR": "Paris Eiffel Tower",
    "LON": "London England Big Ben",
    "AMS": "Amsterdam canal houses",
    "IST": "Istanbul Hagia Sophia",
    "ATH": "Athens Acropolis Parthenon",
    "ZRH": "Zurich Switzerland old town river",
    "FRA": "Frankfurt Germany skyline river",
    "MLA": "Valletta Malta harbour",
    "DXB": "Dubai Burj Khalifa skyline",
    "BRU": "Brussels Belgium Grand Place",
    "DTM": "Dortmund Germany city",
    "NUE": "Nuremberg Germany old town castle",
    "HAM": "Hamburg Germany Elbphilharmonie harbour",
    "CPH": "Copenhagen Denmark Nyhavn",
    "OSL": "Oslo Norway opera house",
    "STO": "Stockholm Sweden Gamla Stan old town",
    "BUD": "Budapest Hungary parliament Danube",
    "PRG": "Prague Czech Charles Bridge castle",
    "WAW": "Warsaw Poland old town square",
    "MAD": "Madrid Spain Gran Via",
    "LIS": "Lisbon Portugal tram Alfama",
    "FMM": "Memmingen Germany old town marketplace",
    "STR": "Stuttgart Germany Schlossplatz",
    "MUC": "Munich Germany Marienplatz",
    "CGN": "Cologne Germany cathedral",
    "HAJ": "Hannover Germany new town hall",
    "BSL": "Basel Switzerland Rhine old town",
    "EIN": "Eindhoven Netherlands city",
    "GOT": "Gothenburg Sweden harbour",
    "CTA": "Catania Sicily Etna cathedral",
    "VCE": "Venice Italy Grand Canal",
}

_IMG_EXTS = (".jpg", ".jpeg", ".webp", ".png")


def _load_index():
    out = {}
    if os.path.isdir(OUT_DIR):
        for f in os.listdir(OUT_DIR):
            name, ext = os.path.splitext(f)
            if ext.lower() in _IMG_EXTS:
                out[name.upper()] = f
    return out


# CODE -> filename for every photo we already have on disk.
IMAGES = _load_index()


def image_for(code):
    """Filename of the local photo for a code, or None. Also picks up files a
    sibling process created after this one started (cheap disk stat)."""
    if not code:
        return None
    c = code.upper()
    f = IMAGES.get(c)
    if f:
        return f
    p = os.path.join(OUT_DIR, f"{c}.jpg")
    if os.path.exists(p):
        IMAGES[c] = f"{c}.jpg"
        return IMAGES[c]
    return None


def query_for(code):
    """Pexels search query for a code: a curated landmark term where we have one,
    else the real city name (cleaned of any airport qualifier)."""
    c = code.upper()
    if c in QUERIES:
        return QUERIES[c]
    if geo.is_known(c):
        name = geo.city_name(c, "en")
        country = geo.country_name(c, "en")
        return f"{name} {country} cityscape".strip()
    name = places.city_name(c)
    if name == c:
        return ""
    return re.split(r"[,/]", name)[0].strip()


def download_one(code, key, query=None):
    """Search Pexels, crop and save static/img/cities/<CODE>.jpg. Returns True on
    success, False if there's nothing usable. Raises on HTTP/network errors."""
    if Image is None:
        return False
    c = code.upper()
    query = query if query is not None else query_for(c)
    if not query:
        return False
    r = requests.get(
        API,
        params={"query": query, "orientation": "landscape",
                "per_page": 5, "size": "large"},
        headers={"Authorization": key, "User-Agent": _UA,
                 "Accept": "application/json"},
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    photos = r.json().get("photos") or []
    if not photos:
        return False
    src = photos[0]["src"].get("landscape") or photos[0]["src"]["large"]
    img_bytes = requests.get(src, headers={"User-Agent": _UA},
                             timeout=_HTTP_TIMEOUT).content
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = ImageOps.fit(img, SIZE, method=RESAMPLE, centering=(0.5, 0.4))
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{c}.jpg")
    tmp = out + ".tmp"
    img.save(tmp, "JPEG", quality=82, optimize=True)
    os.replace(tmp, out)        # atomic, so a half-written file is never served
    IMAGES[c] = f"{c}.jpg"
    return True


# ----------------------------------------------------------------------------
# On-demand background fetching (one paced worker, to dodge Cloudflare bursts).
# ----------------------------------------------------------------------------
_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
_PACE = float(os.environ.get("CITY_PHOTO_PACE", "1.5"))   # seconds between fetches
_queue = Queue()
_seen = set()           # codes queued/in-flight/done — don't re-enqueue
_lock = threading.Lock()
_worker_started = False


def _worker():
    while True:
        try:
            code = _queue.get(timeout=60)
        except Empty:
            continue
        transient = False
        try:
            download_one(code, _KEY)
        except requests.HTTPError as exc:
            transient = getattr(exc.response, "status_code", None) in (429, 500, 502, 503)
        except Exception:  # noqa: BLE001  (network etc. — try again later)
            transient = True
        if transient:
            with _lock:
                _seen.discard(code)     # allow a later retry
            time.sleep(15)              # back off when throttled
        _queue.task_done()
        time.sleep(_PACE)


def ensure(codes):
    """Queue background photo fetches for any of `codes` we don't have yet.
    No-op without an API key (the cards just keep their gradient)."""
    if not _KEY or Image is None:
        return
    global _worker_started
    with _lock:
        if not _worker_started:
            threading.Thread(target=_worker, daemon=True, name="city-photos").start()
            _worker_started = True
        for code in codes:
            if not code:
                continue
            c = code.upper()
            if c in _seen or image_for(c):
                continue
            _seen.add(c)
            _queue.put(c)
