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

DEFAULT_CONFIG = {
    "target_duration": 180.0,          # seconds; YouTube Shorts/IG Reels max is 3:00
    "width": 1080,
    "height": 1920,
    "fps": 30,
    # Layout (matches Dakie's sample: press 45% on top, gameplay 55% below)
    "top_ratio": 0.45,                 # share of height used by the hydraulic press panel
    "facecam_width": 420,              # px width of the streamer cam box (~39% of the frame)
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
    "highlight_color": "&H0000FFFF",   # ASS BGR: yellow
    "emphasis_color": "&H0000FFFF",    # ASS BGR: yellow (set e.g. &H003C3CFF for red)
    "max_words_per_line": 3,
    "censor_profanity_in_captions": True,
    "whisper_scan_model": "base",
    "whisper_caption_model": "small",
    "loudness_lufs": -14.0,
    "sfx_default_gain_db": -10.0,
    "crf": 19,
    "cookies_from_browser": None,      # e.g. "chrome" if YouTube asks to sign in
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text()))
    return cfg


def ensure_home() -> None:
    for d in (HOME, PROJECTS, SFX_DIR, PRESS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))


def ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


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


def video_size(path: Path) -> tuple[int, int]:
    out = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Video: .*?, (\d{3,5})x(\d{3,5})", out)
    return (int(m[1]), int(m[2])) if m else (1920, 1080)
