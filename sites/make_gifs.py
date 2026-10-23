#!/usr/bin/env python3
"""Generate the retro GIF set for the Dataset Factory site revamp.

Pure PIL, no network. Every GIF is drawn from scratch: no scraped art,
no licensing questions. Output: /opt/data/cache/scratch/site-assets/*.gif
plus gifs.b64 (base64 map) for embedding into sites/runtime.py.
"""
import base64
import io
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("/opt/data/cache/scratch/site-assets")
OUT.mkdir(parents=True, exist_ok=True)

BLACK = (0, 0, 0)
NEON = [(0, 255, 0), (255, 0, 255), (0, 255, 255), (255, 255, 0), (255, 0, 0)]
FONT = ImageFont.load_default()  # chunky 6x11 bitmap font


def frames_to_gif(frames, duration=120):
    b = io.BytesIO()
    frames[0].save(b, format="GIF", save_all=True, append_images=frames[1:],
                   duration=duration, loop=0, optimize=True)
    return b.getvalue()


def canvas(w, h, bg=BLACK):
    img = Image.new("P", (w, h), bg)
    img.putpalette([0, 0, 0, 255, 255, 255, 0, 255, 0, 255, 0, 255, 0, 255, 255,
                    255, 255, 0, 255, 0, 0, 128, 128, 128, 255, 128, 0, 0, 0, 255,
                    255, 165, 0, 139, 0, 0, 210, 180, 140, 255, 99, 71] + [0] * (256 * 3 - 39 * 3))
    return img


def draw_text(draw, xy, text, fill):
    draw.text(xy, text, font=FONT, fill=fill)


def globe(size=36):
    """Spinning wireframe-ish globe: rotating meridian ellipses."""
    frames = []
    cx = cy = size // 2
    r = size // 2 - 2
    for i in range(12):
        img = canvas(size, size)
        d = ImageDraw.Draw(img)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 255, 255))
        phase = i * math.pi / 6
        for k in (-0.66, -0.33, 0, 0.33, 0.66):
            w = abs(math.cos(phase)) * r
            if w > 0.5:
                x0 = cx - w
                d.arc([x0, cy - r, cx + w, cy + r], 0 if k >= 0 else 180,
                      360 if k >= 0 else 360, fill=(0, 255, 255))
        d.line([cx - r, cy, cx + r, cy], fill=(0, 255, 255))
        d.ellipse([cx - r // 3, cy - r // 3, cx + r // 3, cy + r // 3], fill=(0, 0, 255))
        frames.append(img)
    return frames_to_gif(frames, 100)


def construction(w=150, h=40):
    """Blazing UNDER CONSTRUCTION barrier: diagonal stripes + flashing text."""
    frames = []
    for i in range(8):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        for x in range(-h, w, 12):
            d.polygon([(x, h), (x + h, 0), (x + h + 6, 0), (x + 6, h)],
                      fill=(255, 165, 0) if (x // 12) % 2 == 0 else (0, 0, 0))
        if i % 2 == 0:
            text = "UNDER CONSTRUCTION"
            tw = d.textlength(text, font=FONT)
            tx = (w - tw) / 2
            d.rectangle([tx - 3, 12, tx + tw + 3, 26], fill=(0, 0, 0))
            draw_text(d, (tx, 14), text, (255, 255, 0))
        frames.append(img)
    return frames_to_gif(frames, 150)


def flame(w=16, h=24):
    """Flickering pixel flame."""
    import random
    random.seed(7)
    frames = []
    for i in range(10):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        for x in range(w):
            for y in range(h):
                dy = (h - 1 - y) / h
                flick = random.random() * 0.25
                if random.random() < (dy * 0.95 + flick - 0.15):
                    if dy > 0.75:
                        color = (255, 0, 0)
                    elif dy > 0.45:
                        color = (255, 165, 0)
                    else:
                        color = (255, 255, 0)
                    d.point((x, y), fill=color)
        frames.append(img)
    return frames_to_gif(frames, 90)


def newbadge(w=52, h=26):
    """Color-cycling NEW! starburst."""
    frames = []
    for i in range(6):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        color = NEON[i % len(NEON)]
        d.polygon([(w // 2, 0), (w - 8, h // 2), (w // 2, h), (8, h // 2)],
                  outline=color)
        d.polygon([(w // 2, 3), (w - 12, h // 2), (w // 2, h - 3), (12, h // 2)],
                  fill=(255, 0, 0) if i % 2 else (255, 255, 0))
        text = "NEW!"
        tw = d.textlength(text, font=FONT)
        draw_text(d, ((w - tw) / 2, 8), text, (0, 0, 0) if i % 2 else (255, 255, 255))
        frames.append(img)
    return frames_to_gif(frames, 120)


def starfield(w=64, h=64):
    """Tilable animated starfield tile for the page background."""
    import random
    stars = [(random.randrange(w), random.randrange(h),
              random.choice([(255, 255, 255), (0, 255, 255), (255, 255, 0), (255, 0, 255)]))
             for _ in range(14)]
    frames = []
    for i in range(8):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        for x, y, c in stars:
            show = (x + y + i * 3) % 8 < 5
            if show:
                d.point((x, y), fill=c)
                if (x + y) % 3 == 0:
                    d.point(((x + 1) % w, y), fill=c)
        frames.append(img)
    return frames_to_gif(frames, 200)


def counter(n="0042137", w=7 * 11, h=15):
    """Odometer hit counter (static)."""
    img = canvas(w, h)
    d = ImageDraw.Draw(img)
    for idx, ch in enumerate(n):
        x = 1 + idx * 11
        d.rectangle([x, 1, x + 10, h - 1], fill=(30, 30, 30), outline=(128, 128, 128))
        draw_text(d, (x + 2, 2), ch, (255, 0, 255))
    return frames_to_gif([img], 0)


def emailgif(w=28, h=16):
    """Rotating @ envelope."""
    frames = []
    for i in range(8):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        wob = int(math.sin(i * math.pi / 4) * 6)
        d.rectangle([2 + wob // 2, 2, w - 4 + wob // 2, h - 3],
                    outline=(255, 255, 0), fill=(0, 0, 0))
        d.line([2 + wob // 2, 2, w // 2 + wob // 2, h // 2], fill=(255, 255, 0))
        d.line([w // 2 + wob // 2, h // 2, w - 4 + wob // 2, 2], fill=(255, 255, 0))
        draw_text(d, (w // 2 + wob // 2 + 2, 1), "@", (0, 255, 0))
        frames.append(img)
    return frames_to_gif(frames, 120)


def donebadge(w=96, h=22):
    """100% COMPLETE badge for finished datasets (static, with a slow shine pulse)."""
    frames = []
    for i in range(4):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, w - 1, h - 1], fill=(0, 128, 0), outline=(255, 255, 0))
        # check mark
        d.line([(6, 11), (10, 16), (18, 5)], fill=(255, 255, 255), width=2)
        text = "100% COMPLETE"
        tw = d.textlength(text, font=FONT)
        draw_text(d, ((w - 26 - tw) / 2 + 22, 5), text, (255, 255, 255))
        if i == 2:
            d.line([(26, 2), (30, 18)], fill=(0, 255, 0))
        frames.append(img)
    return frames_to_gif(frames, 350)


def rainbow(w=300, h=6):
    """Rainbow horizontal rule (static)."""
    img = canvas(w, h)
    d = ImageDraw.Draw(img)
    bands = [(255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0), (0, 255, 255), (0, 0, 255), (255, 0, 255)]
    bw = w // len(bands)
    for i, c in enumerate(bands):
        d.rectangle([i * bw, 0, (i + 1) * bw, h], fill=c)
    return frames_to_gif([img], 0)


def bullet(w=10, h=10):
    """Pulsing neon ball."""
    frames = []
    for i in range(4):
        img = canvas(w, h)
        d = ImageDraw.Draw(img)
        r = 2 + (i % 4) * 1
        d.ellipse([w // 2 - r - 1, h // 2 - r - 1, w // 2 + r, h // 2 + r],
                  fill=NEON[i % len(NEON)])
        frames.append(img)
    return frames_to_gif(frames, 150)


ASSETS = {
    "globe": globe(),
    "construction": construction(),
    "flame": flame(),
    "newbadge": newbadge(),
    "donebadge": donebadge(),
    "starfield": starfield(),
    "counter": counter(),
    "email": emailgif(),
    "rainbow": rainbow(),
    "bullet": bullet(),
}

b64 = {}
total = 0
for name, data in ASSETS.items():
    (OUT / f"{name}.gif").write_bytes(data)
    b64[name] = base64.b64encode(data).decode()
    total += len(data)
    print(f"{name}.gif: {len(data):,} bytes")

(OUT / "gifs.b64.json").write_text(json.dumps(b64))
print(f"total: {total:,} bytes; base64 total: {sum(len(v) for v in b64.values()):,} chars")
