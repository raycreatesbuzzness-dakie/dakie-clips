"""Turn chat, loudness and transcript into ranked candidate moments for Claude to judge."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from .common import load_config, read_json, ts, write_json

CHAT_HYPE = {
    r"\b(lol|lmao+|lmfao|rofl|kekw|lul|omegalul|icant|pepelaugh|xd)\b": 1.0,
    r"(😂|🤣|💀|😭|☠️)": 1.0,
    r"\bclip (it|that)\b|\bclipped\b|\bclip\b": 3.0,
    r"\b(no way|wtf|omg|holy|bro+|yo+|insane|crazy|goated|w+|ww+|lets go+|pog+|poggers|pogchamp)\b": 0.7,
    r"\b(l+|ratio|ff|rip|nooo+|f in chat)\b": 0.5,
    r"[!?]{2,}": 0.4,
}
SPEECH_HYPE = [
    r"oh my god", r"\bno way\b", r"\bwhat the\b", r"\bbro\b", r"let'?s go", r"\bhoy?ly\b",
    r"\bwhat\?!?", r"\brun\b", r"\bcops?\b", r"\bpolice\b", r"\bwanted\b", r"\bcrash", r"\bexplod",
    r"\bhelp\b", r"\bdude\b", r"\binsane\b", r"\bcrazy\b", r"\bha(ha)+\b", r"\bnah\b", r"\bdead\b",
    r"\bchat\b", r"\bclip\b", r"\bfirst time\b", r"\bsecret\b", r"\beaster egg\b", r"\bglitch\b",
]


def _z(a: np.ndarray) -> np.ndarray:
    sd = a.std()
    return (a - a.mean()) / sd if sd > 1e-9 else np.zeros_like(a)


def _smooth(a: np.ndarray, sigma: float) -> np.ndarray:
    r = int(sigma * 3)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    return np.convolve(a, k / k.sum(), mode="same")


def build(proj: Path, top_n: int = 40, chat_delay: float = 8.0) -> list[dict]:
    cfg = load_config()
    info = read_json(proj / "info.json")
    loud = np.array(read_json(proj / "analysis" / "loudness.json"), dtype=float)
    segs = read_json(proj / "analysis" / "transcript.json")["segments"]
    D = int(max(len(loud), info.get("duration") or 0, segs[-1]["end"] if segs else 0)) + 1
    win = int(cfg["target_duration"])

    # chat ------------------------------------------------------------------
    chat_rate = np.zeros(D)
    chat_hype = np.zeros(D)
    chat_path = proj / "analysis" / "chat.jsonl"
    msgs = []
    if chat_path.exists():
        for line in chat_path.open():
            m = json.loads(line)
            t = int(m["t"] - chat_delay)
            if 0 <= t < D:
                msgs.append((t, m["m"]))
                chat_rate[t] += 1
                low = m["m"].lower()
                chat_hype[t] += sum(w for pat, w in CHAT_HYPE.items() if re.search(pat, low))
    has_chat = chat_rate.sum() > 50

    # viewer comments that cite a timestamp ("1:49:47 his first accident 😂")
    cmark = np.zeros(D)
    marks = []
    cm_path = proj / "analysis" / "comment_marks.json"
    if cm_path.exists():
        for m in read_json(cm_path):
            if 0 <= m["t"] < D:
                cmark[int(m["t"])] += 1 + 0.5 * min(m.get("likes", 0), 20)
                marks.append(m)
    has_marks = len(marks) >= 3

    # loudness: spikes above the local (5 min) median ------------------------
    lpad = np.full(D, loud.min() if len(loud) else -60.0)
    lpad[: len(loud)] = loud
    base = np.array([np.median(lpad[max(0, i - 150): i + 150]) for i in range(0, D, 30)])
    base = np.repeat(base, 30)[:D]
    loud_ex = np.clip(lpad - base, 0, None)

    # transcript ------------------------------------------------------------
    speech = np.zeros(D)
    words = np.zeros(D)
    covered = np.zeros(D)
    for s in segs:
        a, b = int(s["start"]), max(int(s["start"]) + 1, int(s["end"]))
        low = s["text"].lower()
        hits = sum(1 for p in SPEECH_HYPE if re.search(p, low)) + low.count("!") * 0.5
        speech[a:b] += hits / (b - a)
        words[a:b] += len(low.split()) / (b - a)
        if s.get("no_speech_prob", 0) < 0.6:
            covered[a:b] = 1

    parts, weights = [_z(_smooth(loud_ex, 6)), _z(_smooth(speech + 0.15 * words, 10))], [0.3, 0.25]
    if has_chat:
        parts.insert(0, _z(_smooth(chat_rate + 2 * chat_hype, 8)))
        weights.insert(0, 0.45)
    if has_marks:
        parts.append(_z(_smooth(cmark, 25)))
        weights.append(0.25 if has_chat else 0.35)
    w = np.array(weights) / sum(weights)
    score = sum(wi * p for wi, p in zip(w, parts))
    score = _smooth(score, 10)

    # peaks with non-max suppression so windows barely overlap ---------------
    order = np.argsort(score)[::-1]
    picked: list[int] = []
    for t in order:
        if t < 20 or t > D - 20:
            continue
        if all(abs(t - p) > win * 0.75 for p in picked):
            picked.append(int(t))
        if len(picked) >= top_n:
            break

    cands = []
    for i, p in enumerate(picked, 1):
        start = int(min(max(0, p - win * 0.3), max(0, D - win)))
        end = min(D, start + win)
        near = [m for t, m in msgs if p - 30 <= t <= p + 30]
        top_msgs = [m for m, _ in Counter(m.strip()[:80] for m in near).most_common(12)]
        tx = " ".join(s["text"] for s in segs if s["end"] > start and s["start"] < end)
        music_like = float(1 - covered[start:end].mean()) if end > start else 0
        loud_ok = float((lpad[start:end] > -35).mean()) if end > start else 0
        cands.append({
            "id": i, "peak": p, "peak_ts": ts(p), "start": start, "end": end,
            "start_ts": ts(start), "end_ts": ts(end), "signal_score": round(float(score[p]), 2),
            "chat_msgs_peak_60s": len(near),
            "chat_rate_vs_avg": round(len(near) / 60 / max(chat_rate.mean(), 1e-6), 1) if has_chat else None,
            "chat_sample": top_msgs,
            "loudness_spike_db": round(float(loud_ex[max(0, p - 10): p + 10].max()), 1),
            "music_risk": "HIGH" if music_like > 0.5 and loud_ok > 0.6 else ("MEDIUM" if music_like > 0.3 and loud_ok > 0.5 else "LOW"),
            "viewer_comments": [f"{ts(m['t'])} ({m.get('likes', 0)} likes): {m['text'][:100]}"
                                for m in marks if start - 30 <= m["t"] <= end + 30],
            "transcript": tx[:2500],
        })
    write_json(proj / "analysis" / "candidates.json", cands)

    md = [f"# Candidate moments: {info.get('title')}",
          f"Signals used: {'chat + ' if has_chat else '(no chat replay) '}{'viewer comment timestamps + ' if has_marks else ''}loudness + transcript. "
          f"Chat is shifted {chat_delay:.0f}s earlier to offset stream delay. Windows are {win}s.", ""]
    for c in cands:
        md += [f"## C{c['id']}  {c['start_ts']} to {c['end_ts']}  (peak {c['peak_ts']}, score {c['signal_score']})",
               f"- chat: {c['chat_msgs_peak_60s']} msgs around peak"
               + (f" ({c['chat_rate_vs_avg']}x average)" if has_chat else "")
               + f" | loudness spike: +{c['loudness_spike_db']} dB | music risk: {c['music_risk']}",
               f"- chat sample: {' | '.join(c['chat_sample'][:8]) or 'n/a'}",
               f"- viewer comments citing this window: {' | '.join(c['viewer_comments']) or 'none'}",
               f"- transcript: {c['transcript']}", ""]
    (proj / "analysis" / "candidates.md").write_text("\n".join(md))
    print(f"{len(cands)} candidates -> {proj / 'analysis' / 'candidates.md'}")
    return cands


def text_range(proj: Path, start: float, end: float, compact: int = 0) -> str:
    segs = read_json(proj / "analysis" / "transcript.json")["segments"]
    sel = [s for s in segs if s["end"] > start and s["start"] < end]
    if not compact:
        return "\n".join(f"[{ts(s['start'])}] {s['text']}" for s in sel)
    buckets: dict[int, list[str]] = {}
    for s in sel:
        buckets.setdefault(int(s["start"] // compact) * compact, []).append(s["text"])
    return "\n".join(f"[{ts(k)}] {' '.join(v)}" for k, v in sorted(buckets.items()))
