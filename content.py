"""Flat-file markdown blog — the content engine, no database required.

Articles live as .md files in content/ with a simple front-matter block:

    ---
    title: ...
    description: ...
    lang: sr            # sr | en
    slug: my-article
    date: 2026-06-19
    ---
    # Markdown body...

Loaded once at import. Re-deploy to publish new posts.
"""
import glob
import os

import markdown as _md

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")


def _parse(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    meta, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            _, fm, body = parts
            for line in fm.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
    slug = meta.get("slug") or os.path.splitext(os.path.basename(path))[0]
    return {
        "slug": slug,
        "lang": meta.get("lang", "sr"),
        "title": meta.get("title", slug),
        "description": meta.get("description", ""),
        "date": meta.get("date", ""),
        "_body": body.strip(),
    }


_GUIDES = []
if os.path.isdir(_DIR):
    for _p in sorted(glob.glob(os.path.join(_DIR, "*.md"))):
        try:
            _GUIDES.append(_parse(_p))
        except OSError:
            pass
# Newest first.
_GUIDES.sort(key=lambda g: g.get("date", ""), reverse=True)


def all_guides():
    """Every guide (all languages) — used for the sitemap."""
    return _GUIDES


def guides_for(lang):
    """Guides in the given language, falling back to all if none exist yet."""
    items = [g for g in _GUIDES if g["lang"] == lang]
    return items or _GUIDES


def get(slug, lang=None):
    """Render one guide (prefers the requested language) -> dict with rendered html."""
    matches = [g for g in _GUIDES if g["slug"] == slug]
    if not matches:
        return None
    chosen = next((g for g in matches if g["lang"] == lang), matches[0])
    out = dict(chosen)
    out["html"] = _md.markdown(chosen["_body"], extensions=["extra", "sane_lists"])
    return out
