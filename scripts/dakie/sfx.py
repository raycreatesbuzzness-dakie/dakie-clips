"""Sound-effects library: original synthesized starter pack, add your own, suggestions."""
from __future__ import annotations

import re
import shutil
import wave
from pathlib import Path

import numpy as np

from .common import SFX_DIR, ensure_home, read_json, write_json

SR = 48000
LIB = SFX_DIR / "library.json"
ORIGINAL = "Original: synthesized by Dakie Clips (you own it, no attribution needed)"


def _t(d):
    return np.linspace(0, d, int(SR * d), endpoint=False)


def _lowpass(x, alpha):
    """One-pole low-pass; alpha may be an array (time-varying cutoff)."""
    y = np.zeros_like(x)
    a = np.broadcast_to(alpha, x.shape)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _norm(x, peak=0.89):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def _fade(x, ms=8):
    n = int(SR * ms / 1000)
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


def synth_all() -> dict[str, tuple[np.ndarray, list[str], str]]:
    rng = np.random.default_rng(7)
    out = {}

    t = _t(0.7)
    env = np.sin(np.pi * t / t[-1]) ** 2
    out["whoosh"] = (_lowpass(rng.normal(size=len(t)), 0.02 + 0.25 * env) * env,
                     ["transition", "fast", "swipe", "cut"], "transition")

    t = _t(1.4)
    f = 55 * np.exp(-t * 1.2)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3)
    click = rng.normal(size=len(t)) * np.exp(-t * 60) * 0.5
    out["boom_impact"] = (np.tanh(3 * (body + click)), ["impact", "crash", "hit", "explosion", "reveal"], "impact")

    t = _t(1.3)
    f = 140 * np.exp(-t * 1.6) + 28
    out["bass_drop"] = (np.tanh(2.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.5)),
                        ["shock", "reaction", "no way", "reveal", "drop"], "impact")

    t = _t(2.2)
    f = 200 + 1000 * (t / t[-1]) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.5
    noise = _lowpass(rng.normal(size=len(t)), 0.05 + 0.3 * t / t[-1]) * 0.6
    out["riser"] = ((tone + noise) * (t / t[-1]) ** 2, ["build-up", "tension", "suspense", "before"], "tension")

    t = _t(1.2)
    out["ding"] = (sum(np.sin(2 * np.pi * 1320 * k * t) / k for k in (1, 2, 3)) * np.exp(-t * 4),
                   ["correct", "success", "idea", "highlight"], "ui")

    t = _t(0.15)
    f = 700 * np.exp(-t * 18) + 150
    out["pop"] = (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 25), ["pop", "text", "appear", "caption"], "ui")

    t = _t(0.6)
    sq = np.sign(np.sin(2 * np.pi * rng.choice([180, 360, 720, 1440], size=len(t) // 2400 + 1).repeat(2400)[: len(t)] * t))
    gate = rng.random(len(t) // 1200 + 1).repeat(1200)[: len(t)] > 0.35
    out["glitch"] = (sq * gate * 0.6, ["glitch", "bug", "error", "weird", "broken"], "fx")

    t = _t(1.0)
    f = 440 * (1 - t / t[-1]) ** 1.5 + 5
    saw = 2 * ((np.cumsum(f) / SR) % 1) - 1
    out["record_stop"] = (_lowpass(saw, 0.15) * (1 - t / t[-1]), ["stop", "wait", "fail", "awkward", "record scratch"], "fx")

    t = _t(2.5)
    f = 900 + 350 * np.sin(2 * np.pi * 1.6 * t)
    out["police_siren"] = (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t * 4) * np.minimum(1, (t[-1] - t) * 4) * 0.7,
                           ["police", "cops", "wanted", "chase", "busted"], "gta")

    t = _t(0.9)
    blips = np.zeros(len(t))
    for k, st in enumerate((0.0, 0.07, 0.14, 0.2)):
        i = int(st * SR)
        tt = t[: len(t) - i]
        blips[i:] += np.sin(2 * np.pi * (2000 + 400 * k) * tt) * np.exp(-tt * 18)
    out["cash"] = (blips, ["money", "cash", "rich", "bank", "heist", "robbery", "dollars"], "gta")

    t = _t(1.0)
    thump = lambda d: np.sin(2 * np.pi * 50 * (t - d)) * np.exp(-np.clip(t - d, 0, None) * 18) * (t >= d)
    out["heartbeat"] = (thump(0.0) + 0.8 * thump(0.25), ["tension", "nervous", "scary", "suspense", "close call"], "tension")

    t = _t(0.25)
    out["camera_click"] = (rng.normal(size=len(t)) * (np.exp(-t * 80) + 0.6 * np.exp(-np.clip(t - 0.09, 0, None) * 80) * (t > 0.09)),
                           ["photo", "freeze", "snapshot", "screenshot"], "ui")

    t = _t(1.6)
    chord = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (73.4, 87.3, 110))
    out["dun_dun"] = (_lowpass(chord, 0.08) * np.exp(-t * 2.2), ["dramatic", "betrayal", "plot twist", "uh oh"], "tension")
    return out


def _write_wav(path: Path, mono: np.ndarray):
    data = (_fade(_norm(mono.astype(np.float64))) * 32767).astype(np.int16)
    st = np.repeat(data[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


def library() -> list[dict]:
    return read_json(LIB) if LIB.exists() else []


def init_library(force=False):
    ensure_home()
    lib = {e["name"]: e for e in library()}
    for name, (x, tags, cat) in synth_all().items():
        f = SFX_DIR / cat / f"{name}.wav"
        f.parent.mkdir(parents=True, exist_ok=True)
        if force or not f.exists():
            _write_wav(f, x)
        lib.setdefault(name, {"name": name, "file": str(f.relative_to(SFX_DIR)), "category": cat,
                              "tags": tags, "license": ORIGINAL, "source": "dakie sfx synth",
                              "default_gain_db": None})
    write_json(LIB, sorted(lib.values(), key=lambda e: (e["category"], e["name"])))
    print(f"SFX library: {len(lib)} sounds in {SFX_DIR}")


def add(src: str, name: str, tags: list[str], license_: str, source: str, category: str = "custom"):
    if not license_ or license_.lower() in ("unknown", "?"):
        raise SystemExit("A license is required (e.g. 'CC0', 'Pixabay Content License', 'Purchased - Epidemic Sound'). "
                         "Sounds without a known license can get your videos muted or claimed.")
    p = Path(src).expanduser()
    dest = SFX_DIR / category / f"{re.sub(r'[^a-z0-9_]+', '_', name.lower())}{p.suffix.lower()}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dest)
    lib = [e for e in library() if e["name"] != name]
    lib.append({"name": name, "file": str(dest.relative_to(SFX_DIR)), "category": category, "tags": tags,
                "license": license_, "source": source, "default_gain_db": None})
    write_json(LIB, sorted(lib, key=lambda e: (e["category"], e["name"])))
    print(f"Added {name} -> {dest}")


def path_of(name: str) -> Path:
    for e in library():
        if e["name"] == name:
            return SFX_DIR / e["file"]
    raise SystemExit(f"Unknown sound '{name}'. Run: dakie sfx list")


def suggest(words: list[dict], limit: int = 8) -> list[dict]:
    """Keyword-based cue suggestions from word timings. Claude refines these."""
    lib = library()
    out, last = [], -99.0
    for w in words:
        token = w["word"].lower().strip(".,!?\"'")
        for e in lib:
            if any(token and (token == tag or (len(tag) > 3 and tag in token)) for tag in e["tags"]):
                if w["start"] - last > 12:
                    out.append({"t": round(w["start"], 2), "name": e["name"], "because": f"said '{w['word']}'"})
                    last = w["start"]
                break
        if len(out) >= limit:
            break
    return out
