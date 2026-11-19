"""Top-panel footage: an original, procedurally generated hydraulic press loop + licensed clip library."""
from __future__ import annotations

import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import PRESS_DIR, ensure_home, ffmpeg, read_json, write_json

LIB = PRESS_DIR / "library.json"
W, H, FPS = 1080, 960, 30
CYCLE = 4.0

OBJECTS = [
    ("crate", (196, 132, 64)), ("ball", (40, 120, 230)), ("can", (220, 40, 50)),
    ("melon", (60, 170, 70)), ("phone", (30, 30, 36)), ("cake", (245, 190, 210)),
    ("gold", (240, 190, 40)), ("tv", (70, 70, 80)),
]


def _ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _draw_object(d: ImageDraw.ImageDraw, kind, color, cx, floor, w, h):
    x0, y0, x1, y1 = cx - w / 2, floor - h, cx + w / 2, floor
    dark = tuple(int(c * 0.6) for c in color)
    light = tuple(min(255, int(c * 1.3) + 20) for c in color)
    if kind == "ball":
        d.ellipse([x0, y0, x1, y1], fill=color, outline=dark, width=6)
        d.ellipse([x0 + w * 0.2, y0 + h * 0.15, x0 + w * 0.45, y0 + h * 0.4], fill=light)
    elif kind == "melon":
        d.ellipse([x0, y0, x1, y1], fill=color, outline=dark, width=6)
        for k in range(1, 5):
            xx = x0 + w * k / 5
            d.arc([xx - w * 0.12, y0, xx + w * 0.12, y1], 270, 90, fill=dark, width=8)
    elif kind == "can":
        d.rectangle([x0, y0 + 14, x1, y1 - 14], fill=color)
        d.ellipse([x0, y0, x1, y0 + 28], fill=(200, 200, 205), outline=dark, width=3)
        d.ellipse([x0, y1 - 28, x1, y1], fill=color)
        d.rectangle([x0, y0 + h * 0.4, x1, y0 + h * 0.55], fill=(255, 255, 255))
    elif kind == "phone":
        d.rounded_rectangle([x0, y0, x1, y1], radius=max(4, min(w, h) * 0.12), fill=color, outline=(120, 120, 130), width=5)
        d.rounded_rectangle([x0 + 10, y0 + 18, x1 - 10, y1 - 18], radius=6, fill=(60, 140, 255))
    elif kind == "cake":
        d.rectangle([x0, y0 + h * 0.3, x1, y1], fill=(170, 110, 60))
        d.rectangle([x0, y0 + h * 0.3, x1, y0 + h * 0.45], fill=color)
        d.ellipse([cx - 14, y0, cx + 14, y0 + h * 0.3], fill=(220, 30, 40))
    elif kind == "gold":
        d.polygon([(x0, y1), (x1, y1), (x1 - w * 0.15, y0), (x0 + w * 0.15, y0)], fill=color, outline=dark)
        d.line([(x0 + w * 0.2, y0 + h * 0.25), (x1 - w * 0.2, y0 + h * 0.25)], fill=light, width=6)
    elif kind == "tv":
        d.rectangle([x0, y0, x1, y1], fill=color, outline=(30, 30, 30), width=6)
        d.rectangle([x0 + w * 0.08, y0 + h * 0.1, x1 - w * 0.08, y1 - h * 0.2], fill=(120, 200, 220))
    else:  # crate
        d.rectangle([x0, y0, x1, y1], fill=color, outline=dark, width=8)
        d.line([(x0, y0), (x1, y1)], fill=dark, width=8)
        d.line([(x1, y0), (x0, y1)], fill=dark, width=8)


def _background() -> Image.Image:
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        v = int(28 + 30 * y / H)
        d.line([(0, y), (W, y)], fill=(v, v + 2, v + 6))
    floor = int(H * 0.82)
    d.rectangle([0, floor, W, H], fill=(55, 55, 60))
    for x in range(-60, W + 60, 60):
        d.polygon([(x, floor), (x + 30, floor), (x + 10, floor + 26), (x - 20, floor + 26)], fill=(240, 190, 0))
    d.rectangle([0, floor + 26, W, H], fill=(48, 48, 52))
    # press frame
    for x in (150, W - 230):
        d.rectangle([x, 70, x + 80, floor], fill=(90, 96, 110), outline=(40, 40, 46), width=4)
    d.rectangle([110, 20, W - 110, 120], fill=(200, 40, 40), outline=(90, 10, 10), width=5)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 58)
    except OSError:
        font = ImageFont.load_default()
    d.text((W / 2, 70), "HYDRAULIC PRESS  100 T", fill=(255, 235, 200), font=font, anchor="mm")
    d.rectangle([260, floor - 12, W - 260, floor + 6], fill=(110, 115, 125))
    return bg


def generate(out: Path, seconds: float = 32.0, seed: int = 1):
    rnd = random.Random(seed)
    bg = _background()
    floor = int(H * 0.82) - 12
    cx = W // 2
    objs = OBJECTS[:]
    rnd.shuffle(objs)
    proc = subprocess.Popen([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                             str(out)], stdin=subprocess.PIPE)
    particles: list[list[float]] = []
    for f in range(int(seconds * FPS)):
        t = f / FPS
        idx = int(t // CYCLE)
        p = (t % CYCLE) / CYCLE
        kind, color = objs[idx % len(objs)]
        ow, oh = 300, 300 if kind not in ("can", "phone") else 360
        if kind == "phone":
            ow = 190
        top_y = floor - oh
        # plate position: descend, crush, hold, rise
        if p < 0.35:
            plate = 130 + (top_y - 130) * _ease(p / 0.35)
            squash = 0.0
        elif p < 0.6:
            q = _ease((p - 0.35) / 0.25)
            squash = q
            plate = top_y + (oh * 0.85) * q
        elif p < 0.8:
            squash, plate = 1.0, top_y + oh * 0.85
        else:
            squash = 1.0
            plate = top_y + oh * 0.85 - (top_y + oh * 0.85 - 130) * _ease((p - 0.8) / 0.2)
        h = oh * (1 - 0.85 * squash)
        w = ow * (1 + 0.75 * squash ** 0.7)
        if 0.35 <= p < 0.6 and f % 2 == 0:
            for _ in range(10):
                particles.append([cx + rnd.uniform(-w / 2, w / 2), floor - h / 2,
                                  rnd.uniform(-14, 14), rnd.uniform(-16, -2), color, rnd.uniform(6, 16)])
        img = bg.copy()
        d = ImageDraw.Draw(img)
        if p < 0.95 or squash < 1:
            _draw_object(d, kind, color, cx, floor, w, max(h, 6))
        for pt in particles:
            pt[0] += pt[2]
            pt[1] += pt[3]
            pt[3] += 1.2
            if pt[1] > floor:
                pt[1], pt[3] = floor, -pt[3] * 0.3
                pt[2] *= 0.7
            d.rectangle([pt[0], pt[1] - pt[5], pt[0] + pt[5], pt[1]], fill=pt[4])
        particles = [pt for pt in particles if abs(pt[2]) > 0.3 and -50 < pt[0] < W + 50][-400:]
        if p > 0.95:
            particles.clear()
        # piston + plate
        d.rectangle([cx - 46, 120, cx + 46, plate], fill=(205, 210, 220), outline=(120, 125, 135), width=4)
        d.rectangle([cx - 46 + 12, 120, cx - 46 + 26, plate], fill=(245, 248, 255))
        d.rectangle([230, plate, W - 230, plate + 46], fill=(150, 155, 168), outline=(70, 72, 80), width=5)
        if 0.35 <= p < 0.62:
            shake = int(6 * math.sin(f * 2.3))
            img = img.transform(img.size, Image.AFFINE, (1, 0, shake, 0, 1, -shake), fillcolor=(30, 30, 30))
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()


def library() -> list[dict]:
    return read_json(LIB) if LIB.exists() else []


def init_library():
    ensure_home()
    lib = {e["file"]: e for e in library()}
    out = PRESS_DIR / "generated_press_01.mp4"
    if not out.exists():
        print("Rendering original hydraulic press loop...")
        generate(out)
    lib.setdefault(out.name, {"file": out.name, "license": "Original: generated by Dakie Clips (you own it)",
                              "source": "dakie press generator", "enabled": True})
    write_json(LIB, list(lib.values()))
    print(f"Press library: {len(lib)} clip(s) in {PRESS_DIR}")


def add(src: str, license_: str, source: str):
    if not license_ or license_.lower() in ("unknown", "?"):
        raise SystemExit("A license is required (e.g. 'Pexels License', 'Pixabay Content License', 'CC0', 'Own footage').")
    p = Path(src).expanduser()
    dest = PRESS_DIR / p.name
    shutil.copy2(p, dest)
    lib = [e for e in library() if e["file"] != p.name]
    lib.append({"file": p.name, "license": license_, "source": source, "enabled": True})
    write_json(LIB, lib)
    print(f"Added {dest}")


def pick(seed: int) -> dict:
    enabled = [e for e in library() if e.get("enabled", True)]
    if not enabled:
        raise SystemExit("Press library is empty. Run: dakie setup")
    return random.Random(seed).choice(enabled)
