"""Top-panel footage: an original, procedurally generated hydraulic press loop + licensed clip library."""
from __future__ import annotations

import math
import random
import re
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


THEMES = [  # one look per generated loop, so every clip's top panel looks different
    dict(name="steel shop", top=(28, 30, 36), bottom=(58, 60, 66), floor=(55, 55, 60), stripe=(240, 190, 0),
         frame=(90, 96, 110), head=(200, 40, 40), label="HYDRAULIC PRESS  100 T", bricks=False),
    dict(name="blue garage", top=(16, 34, 62), bottom=(30, 66, 110), floor=(40, 44, 52), stripe=(255, 255, 255),
         frame=(60, 70, 90), head=(20, 110, 220), label="MEGA PRESS  250 T", bricks=True),
    dict(name="red factory", top=(48, 18, 18), bottom=(92, 34, 30), floor=(60, 44, 40), stripe=(255, 210, 0),
         frame=(120, 70, 60), head=(240, 140, 20), label="CRUSHER  500 T", bricks=True),
    dict(name="green lab", top=(14, 40, 30), bottom=(30, 80, 60), floor=(40, 52, 46), stripe=(0, 230, 120),
         frame=(70, 100, 90), head=(30, 160, 90), label="PRESS LAB  150 T", bricks=False),
    dict(name="night neon", top=(12, 8, 30), bottom=(40, 20, 70), floor=(30, 24, 44), stripe=(255, 40, 200),
         frame=(80, 60, 120), head=(160, 40, 220), label="NEON PRESS  300 T", bricks=False),
    dict(name="desert yard", top=(120, 90, 60), bottom=(190, 150, 100), floor=(150, 120, 80), stripe=(60, 40, 20),
         frame=(110, 90, 70), head=(200, 90, 40), label="YARD PRESS  80 T", bricks=False),
    dict(name="concrete", top=(70, 70, 72), bottom=(120, 120, 122), floor=(90, 90, 92), stripe=(255, 120, 0),
         frame=(60, 60, 64), head=(240, 200, 0), label="HEAVY PRESS  1000 T", bricks=True),
    dict(name="ice", top=(150, 200, 230), bottom=(220, 240, 250), floor=(170, 190, 205), stripe=(0, 90, 200),
         frame=(90, 120, 150), head=(0, 140, 220), label="ARCTIC PRESS  200 T", bricks=False),
]


def _background(theme: dict | None = None) -> Image.Image:
    th = theme or THEMES[0]
    bg = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(th["top"], th["bottom"])))
    floor = int(H * 0.82)
    if th["bricks"]:
        shade = tuple(max(0, c - 14) for c in th["bottom"])
        for row, y in enumerate(range(140, floor, 46)):
            for x in range(-60 * (row % 2), W, 120):
                d.rectangle([x, y, x + 116, y + 42], outline=shade, width=2)
    d.rectangle([0, floor, W, H], fill=th["floor"])
    for x in range(-60, W + 60, 60):
        d.polygon([(x, floor), (x + 30, floor), (x + 10, floor + 26), (x - 20, floor + 26)], fill=th["stripe"])
    d.rectangle([0, floor + 26, W, H], fill=tuple(max(0, c - 8) for c in th["floor"]))
    for x in (150, W - 230):
        d.rectangle([x, 70, x + 80, floor], fill=th["frame"], outline=(40, 40, 46), width=4)
    d.rectangle([110, 20, W - 110, 120], fill=th["head"], outline=(40, 10, 10), width=5)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 58)
    except OSError:
        font = ImageFont.load_default()
    d.text((W / 2, 70), th["label"], fill=(255, 245, 225), font=font, anchor="mm")
    d.rectangle([260, floor - 12, W - 260, floor + 6], fill=(110, 115, 125))
    return bg


def generate(out: Path, seconds: float = 32.0, seed: int = 1):
    rnd = random.Random(seed)
    bg = _background(THEMES[(seed - 1) % len(THEMES)])
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


VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
ORIGINAL = "Original: generated by Dakie Clips (you own it)"


def library() -> list[dict]:
    lib = read_json(LIB) if LIB.exists() else []
    for e in lib:  # older libraries had no priority
        e.setdefault("enabled", True)
        e.setdefault("priority", 5 if e["file"].startswith("generated_") else 8)
    return lib


def save(lib: list[dict]) -> None:
    write_json(LIB, sorted(lib, key=lambda e: (-e.get("priority", 5), e["file"])))


def init_library(n_generated: int = 8):
    """Make sure the starter set exists: one original loop per theme."""
    ensure_home()
    lib = {e["file"]: e for e in library()}
    for seed in range(1, n_generated + 1):
        out = PRESS_DIR / f"generated_press_{seed:02d}.mp4"
        if not out.exists():
            print(f"Rendering original press loop {seed}/{n_generated} ({THEMES[(seed - 1) % len(THEMES)]['name']})...")
            generate(out, seed=seed)
        lib.setdefault(out.name, {"file": out.name, "license": ORIGINAL, "source": "dakie press generator",
                                  "enabled": True, "priority": 5})
    save(list(lib.values()))
    print(f"Press library: {len(lib)} clip(s) in {PRESS_DIR}")


def _expand(paths) -> list[Path]:
    out = []
    for raw in paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            out += sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT)
        elif p.is_file():
            out.append(p)
        else:
            raise SystemExit(f"Not found: {p}")
    return out


def add(paths, license_: str, source: str = "", priority: int = 8, name: str | None = None,
        credit: str | None = None):
    """Add one or more videos (or folders of videos). Each is converted to 1080p/30fps, no audio."""
    if not license_ or license_.lower() in ("unknown", "?"):
        raise SystemExit("A license is required (e.g. 'Pexels License', 'Pixabay Content License', 'CC0', 'Own footage').")
    if re.search(r"\bCC[ -]?BY\b|attribution", license_, re.I) and not credit:
        raise SystemExit("This license requires attribution: add --credit \"<creator> (CC BY) <url>\".")
    files = _expand(paths)
    if not files:
        raise SystemExit("No video files found.")
    if name and len(files) > 1:
        raise SystemExit("--name only works when adding a single file.")
    from .common import media_duration, slugify
    lib = {e["file"]: e for e in library()}
    for f in files:
        dur = media_duration(f)
        if dur < 4:
            print(f"Skipped {f.name}: not a readable video or shorter than 4 s")
            continue
        dest = PRESS_DIR / f"{slugify(name or f.stem, 60)}.mp4"
        subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(f), "-an",
                        "-vf", "scale='if(gt(a,1),-2,1080)':'if(gt(a,1),1080,-2)',fps=30",
                        "-t", "120", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                        str(dest)], check=True)
        lib[dest.name] = {"file": dest.name, "license": license_, "source": source or str(f),
                          **({"credit": credit} if credit else {}),
                          "enabled": True, "priority": priority}
        print(f"Added {dest.name} ({min(dur, 120):.0f}s)")
    save(list(lib.values()))
    print(f"Press library now has {sum(1 for e in lib.values() if e['enabled'])} enabled clip(s).")


def resolve(name: str) -> str:
    """Accept 'my-clip.mp4', 'my_clip', 'My Clip' ... and return the library file name."""
    files = [e["file"] for e in library()]
    if name in files:
        return name
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower().removesuffix(".mp4"))
    hits = [f for f in files if norm(f) == norm(name)]
    if len(hits) == 1:
        return hits[0]
    raise SystemExit(f"{name} is not in the press library (dakie press list)")


def set_entry(file: str, enabled: bool | None = None, priority: int | None = None):
    file = resolve(file)
    lib = library()
    hit = [e for e in lib if e["file"] == file]
    if not hit:
        raise SystemExit(f"{file} is not in the press library (dakie press list)")
    if enabled is not None:
        hit[0]["enabled"] = enabled
    if priority is not None:
        hit[0]["priority"] = priority
    save(lib)
    print(f"{file}: {'on' if hit[0]['enabled'] else 'off'}, priority {hit[0]['priority']}")


def remove(file: str):
    file = resolve(file)
    lib = library()
    if not any(e["file"] == file for e in lib):
        raise SystemExit(f"{file} is not in the press library (dakie press list)")
    save([e for e in lib if e["file"] != file])
    (PRESS_DIR / file).unlink(missing_ok=True)
    print(f"Removed {file}")


def used_by_other_clips(proj: Path, n: int) -> dict[str, int]:
    """press file -> clip number, for every other clip in this project (plan or last render)."""
    used = {}
    for d in sorted((proj / "clips").glob("clip_*")):
        k = int(d.name.split("_")[1])
        if k == n:
            continue
        for fname, key in (("plan.json", "press_file"), ("render.json", "press_clip")):
            f = d / fname
            if f.exists():
                v = read_json(f).get(key)
                v = v.get("file") if isinstance(v, dict) else v
                if v:
                    used[v] = k
                    break
    return used


def pick_unique(proj: Path, n: int) -> dict:
    """Highest-priority enabled press video that no other clip in this project uses."""
    enabled = [e for e in library() if e.get("enabled", True)]
    if not enabled:
        raise SystemExit("Press library is empty. Run: dakie setup")
    used = used_by_other_clips(proj, n)
    free = sorted((e for e in enabled if e["file"] not in used), key=lambda e: (-e["priority"], e["file"]))
    if not free:
        raise SystemExit(f"All {len(enabled)} press videos are already used by other clips in this project. "
                         "Add more with `dakie press add <files>` or `dakie press generate`.")
    return free[0]


def pick(seed: int) -> dict:
    enabled = [e for e in library() if e.get("enabled", True)]
    if not enabled:
        raise SystemExit("Press library is empty. Run: dakie setup")
    return random.Random(seed).choice(enabled)
