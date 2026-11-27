"""Shared paths, config and helpers for Dakie Clips."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path(os.environ.get("DAKIE_HOME", Path.home() / "DakieClips"))
VENV = Path.home() / ".dakie_clips" / "venv"
PROJECTS = HOME / "projects"
SFX_DIR = HOME / "sfx_library"
PRESS_DIR = HOME / "press_library"
CONFIG_PATH = HOME / "config.json"

CONFIG_VERSION = 2
DEFAULT_CONFIG = {
    "config_version": CONFIG_VERSION,
    "target_duration": 28.0,           # seconds; default length of each finished clip
    "min_duration": 20.0,              # a plan may set "duration" anywhere in this range
    "max_duration": 30.0,              # short, punchy clips: one moment, payoff, done
    "width": 1080,
    "height": 1920,
    "fps": 30,
    # Layout. "cam_top" (v2, Dakie's current sample): streamer's webcam fills the top panel, gameplay
    # below, hydraulic press in a small window bottom-right. "press_top" (v1): press on top, gameplay
    # below, webcam box bottom-right.
    "layout": "cam_top",
    "top_ratio": 0.32,                 # share of height used by the top panel (webcam in cam_top)
    "press_inset_width": 470,          # cam_top: px size of the press window, bottom-right
    "press_inset_height": 290,
    "press_inset_margin_right": 40,
    "press_inset_margin_bottom": 40,
    "press_inset_border": 0,
    "facecam_width": 420,              # press_top: px width of the streamer cam box
    "facecam_margin_right": 24,
    "facecam_margin_bottom": 52,
    "facecam_border": 4,
    "facecam_border_color": "black",
    "progress_bar": False,
    # Title box (white rounded box, black sentence-case text, on screen the whole video)
    "hook_font": "Arial",
    "hook_font_file": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "hook_size": 64,
    "hook_gap": 22,                    # px between the title box and the captions below it
    "hook_max_width": 880,             # px of text per line before wrapping
    # Captions (heavy white uppercase, active word yellow, on the seam)
    "caption_font": "Arial Black",
    "caption_size": 104,
    "caption_y": None,                 # None = on the seam between press and gameplay
    "caption_color": "&H00FFFFFF",
    # Colors are ASS &H00BBGGRR. The spoken word rotates through the palette (one colour per caption
    # line), story keywords get the emphasis colour, numbers/money get the number colour.
    "highlight_palette": ["&H0000E5FF", "&H00FFE123", "&H00D84FFF", "&H001F9AFF"],  # yellow, cyan, pink, orange
    "emphasis_color": "&H003B3BFF",    # coral red, slightly larger
    "number_color": "&H003BFF4B",      # lime green for 13, $527, 100%
    "highlight_color": "&H0000E5FF",   # fallback when highlight_palette is empty
    "max_words_per_line": 3,
    "censor_profanity_in_captions": True,
    "whisper_scan_model": "base",
    "whisper_caption_model": "small",
    "loudness_lufs": -14.0,
    "sfx_default_gain_db": -10.0,
    "crf": 19,
    "cookies_from_browser": None,      # e.g. "chrome" if YouTube asks to sign in
}


# keys whose defaults changed in config v2 (20-30 s clips, webcam-on-top layout); an older config.json
# gets these reset once, everything else the user set is kept
_V2_KEYS = ("target_duration", "min_duration", "max_duration", "layout", "top_ratio", "press_inset_width",
            "press_inset_height", "press_inset_margin_right", "press_inset_margin_bottom", "press_inset_border")


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        user = json.loads(CONFIG_PATH.read_text())
        if user.get("config_version", 1) < CONFIG_VERSION:
            for k in _V2_KEYS:
                user[k] = DEFAULT_CONFIG[k]
            user["config_version"] = CONFIG_VERSION
            CONFIG_PATH.write_text(json.dumps(user, indent=2))
            print("config.json updated to v2: 20-30 s clips, webcam-on-top layout "
                  "(set \"layout\": \"press_top\" for the old one)", file=sys.stderr)
        cfg.update(user)
    return cfg


def ensure_home() -> None:
    for d in (HOME, PROJECTS, SFX_DIR, PRESS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))


_FFMPEG = None


def _has_libass(exe: str) -> bool:
    try:
        out = subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return False
    return any(line.split()[1:2] == ["ass"] for line in out.splitlines() if line.strip())


def ffmpeg() -> str:
    """An ffmpeg that can burn in captions (libass). A system ffmpeg (e.g. Homebrew's) is used only
    if it has the `ass` filter; otherwise the bundled imageio-ffmpeg build, which always does."""
    global _FFMPEG
    if _FFMPEG:
        return _FFMPEG
    found = shutil.which("ffmpeg")
    if found and _has_libass(found):
        _FFMPEG = found
    else:
        import imageio_ffmpeg
        _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    return _FFMPEG


def venv_bin(name: str) -> str:
    p = VENV / "bin" / name
    return str(p) if p.exists() else (shutil.which(name) or name)


def run(cmd: list[str], quiet: bool = False, check: bool = True, **kw) -> subprocess.CompletedProcess:
    if not quiet:
        print("$ " + " ".join(str(c) for c in cmd)[:400], file=sys.stderr)
    return subprocess.run([str(c) for c in cmd], check=check, text=True,
                          capture_output=quiet, **kw)


def ytdlp_base(cfg: dict) -> list[str]:
    deno = VENV / "bin" / "deno"
    base = [venv_bin("yt-dlp"), "--ffmpeg-location", ffmpeg(), "--no-playlist"]
    if deno.exists():
        base += ["--js-runtimes", f"deno:{deno}"]
    if cfg.get("cookies_from_browser"):
        base += ["--cookies-from-browser", cfg["cookies_from_browser"]]
    return base


def slugify(text: str, n: int = 50) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s[:n] or "stream"


def project_dir(name: str) -> Path:
    p = Path(name)
    if p.is_dir():
        return p
    p = PROJECTS / name
    if not p.is_dir():
        sys.exit(f"Project not found: {name}")
    return p


def read_json(p: Path):
    return json.loads(Path(p).read_text())


def write_json(p: Path, data) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def ts(sec: float) -> str:
    sec = max(0, float(sec))
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def parse_ts(text) -> float:
    if isinstance(text, (int, float)):
        return float(text)
    parts = [float(x) for x in str(text).strip().split(":")]
    sec = 0.0
    for p in parts:
        sec = sec * 60 + p
    return sec


def media_duration(path: Path) -> float:
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def has_audio(path: Path) -> bool:
    """True when the file has an audio stream that actually decodes (an empty track counts as none)."""
    out = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:a:0",
                          "-t", "3", "-f", "null", "-"], capture_output=True, text=True)
    if out.returncode != 0:
        return False
    times = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", out.stderr)
    return bool(times) and any(float(s) + 60 * int(m) + 3600 * int(h) > 0.5 for h, m, s in times)


def video_size(path: Path) -> tuple[int, int]:
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Video: .*?, (\d{3,5})x(\d{3,5})", out)
    return (int(m[1]), int(m[2])) if m else (1920, 1080)
