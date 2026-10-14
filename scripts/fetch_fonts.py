"""Self-host the web fonts (privacy/GDPR + performance).

Downloads the woff2 files Google Fonts would serve and writes static/fonts.css
pointing at the local copies, so no request ever goes to Google at runtime.
Re-run if the font selection changes. Keeps ALL subsets (incl. latin-ext for
Serbian diacritics š č ć ž đ).
"""
import os
import re
import urllib.request

CSS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Fraunces:ital,opsz,wght@0,9..144,400..900;1,9..144,400..900"
    "&family=Hanken+Grotesk:wght@400..800"
    "&family=DM+Mono:ital,wght@0,400;0,500;1,400"
    "&display=swap"
)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

ROOT = os.path.join(os.path.dirname(__file__), "..", "static")
FONTS_DIR = os.path.join(ROOT, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


css = fetch(CSS_URL).decode("utf-8")
urls = sorted(set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", css)))
print(f"{len(urls)} font files to download")

total = 0
for u in urls:
    name = u.split("/")[-1]
    data = fetch(u)
    total += len(data)
    with open(os.path.join(FONTS_DIR, name), "wb") as f:
        f.write(data)
    css = css.replace(u, f"fonts/{name}")

with open(os.path.join(ROOT, "fonts.css"), "w", encoding="utf-8") as f:
    f.write(css)
print(f"wrote static/fonts.css + {len(urls)} woff2 ({total // 1024} KB total)")
