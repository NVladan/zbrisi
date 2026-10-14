"""Generate static/og-image.png (1200x630) — the social/messaging share card.

One-off build script. Re-run after rebrands. Requires Pillow.
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
OUT = os.path.join(os.path.dirname(__file__), "..", "static", "og-image.png")

# Dusk gradient stops, matching the site hero.
STOPS = [
    (0.00, (11, 38, 48)), (0.34, (21, 65, 76)), (0.52, (45, 86, 90)),
    (0.84, (181, 81, 47)), (1.00, (232, 154, 72)),
]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def grad_color(y):
    p = y / (H - 1)
    for i in range(len(STOPS) - 1):
        p0, c0 = STOPS[i]
        p1, c1 = STOPS[i + 1]
        if p0 <= p <= p1:
            t = (p - p0) / (p1 - p0) if p1 > p0 else 0
            return lerp(c0, c1, t)
    return STOPS[-1][1]


def font(paths, size):
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)
for y in range(H):
    draw.line([(0, y), (W, y)], fill=grad_color(y))

# Sun glow near the horizon.
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
cx, cy = W // 2, int(H * 0.95)
for r, a in [(380, 35), (320, 45), (260, 65), (200, 100), (140, 150)]:
    gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(247, 193, 108, a))
img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
draw = ImageDraw.Draw(img)

FD = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts") + os.sep
display = font([FD + "georgiab.ttf", FD + "Georgia.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"], 138)
body = font([FD + "segoeui.ttf", FD + "arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"], 40)
mono = font([FD + "consola.ttf", FD + "cour.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"], 26)

CREAM, CORAL, GOLD, MUTED = (251, 238, 222), (225, 84, 43), (242, 196, 102), (232, 222, 205)

draw.text((90, 118), "JEFTINI LETOVI U JEDNOM PRAVCU  ·  BALKAN", font=mono, fill=GOLD)
draw.text((86, 168), "Zbriši", font=display, fill=CREAM)
draw.rectangle([92, 350, 300, 358], fill=CORAL)
draw.text((92, 384), "Beograd · Sarajevo · Skoplje · Zagreb — bilo kuda", font=body, fill=MUTED)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, "PNG")
print("wrote", os.path.abspath(OUT))
