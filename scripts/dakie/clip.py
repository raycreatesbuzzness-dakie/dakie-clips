"""Per-clip prep (download section, word timings, face tracking) and the final 9:16 render."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import captions, press, sfx
from .common import (PRESS_DIR, ffmpeg, load_config, media_duration, read_json, run, ts,
                     video_size, write_json, ytdlp_base)

SCRIPTS = Path(__file__).resolve().parent.parent


def clip_dir(proj: Path, n: int) -> Path:
    return proj / "clips" / f"clip_{n:02d}"


# ------------------------------------------------------------------ prepare
def prepare(proj: Path, n: int, start: float, end: float) -> dict:
    cfg = load_config()
    info = read_json(proj / "info.json")
    d = clip_dir(proj, n)
    d.mkdir(parents=True, exist_ok=True)
    if end - start < cfg["target_duration"]:
        end = start + cfg["target_duration"]
        print(f"Window extended to {cfg['target_duration']:.0f}s: {ts(start)} to {ts(end)}", file=sys.stderr)
    src = d / "source.mp4"
    if not src.exists():
        run(ytdlp_base(cfg) + ["-f", "bv*[height<=1080][fps<=60]+ba/b[height<=1080]/bv*+ba/b",
                               "--merge-output-format", "mp4", "--download-sections", f"*{start:.2f}-{end:.2f}",
                               "--force-keyframes-at-cuts", "-o", str(src), info["source_url"]])
    dur = media_duration(src)

    wav = d / "audio16k.wav"
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", wav])
    from .fetch import whisper_transcribe
    segs = whisper_transcribe(wav, cfg["whisper_caption_model"], word_timestamps=True)
    words = [w for s in segs for w in s.get("words", []) if w["word"]]
    write_json(d / "words.json", {"segments": segs, "words": words})

    fc = subprocess.run([sys.executable, "-m", "dakie.facecam", str(src), str(d / "facecam.json")],
                        cwd=SCRIPTS, capture_output=True, text=True)
    face = read_json(d / "facecam.json") if (d / "facecam.json").exists() else {"mode": "none", "reason": fc.stderr[-300:]}

    # music risk: loud stretches with no detected speech
    from .fetch import loudness_per_second
    loud = np.array(loudness_per_second(wav))
    speech = np.zeros(len(loud))
    for s in segs:
        if s["no_speech_prob"] < 0.6:
            speech[int(s["start"]): int(s["end"]) + 1] = 1
    risky = []
    for a in range(0, len(loud), 10):
        if loud[a:a + 10].mean() > -32 and speech[a:a + 10].mean() < 0.2:
            risky.append(f"{ts(a)}-{ts(min(len(loud), a + 10))}")

    prep = {"clip": n, "source_start": start, "source_end": end, "source_start_ts": ts(start),
            "source_end_ts": ts(end), "duration": round(dur, 2), "words": len(words),
            "facecam": {k: v for k, v in face.items() if k != "track"},
            "music_risk_windows": risky, "sfx_suggestions": sfx.suggest(words)}
    write_json(d / "prep.json", prep)
    print(json.dumps(prep, indent=2))
    return prep


def dump_words(proj: Path, n: int) -> str:
    words = read_json(clip_dir(proj, n) / "words.json")["segments"]
    return "\n".join(f"[{s['start']:6.1f}-{s['end']:6.1f}] {s['text']}" for s in words)


# ------------------------------------------------------------------ render
def _bump(events, var="t"):
    """Sum of smooth bumps: amount * sin(pi * (t-a)/dur) on [a, a+dur]."""
    terms = [f"{e['amount']}*between({var},{e['t']:.3f},{e['t'] + e['dur']:.3f})*sin(PI*({var}-{e['t']:.3f})/{e['dur']:.3f})"
             for e in events]
    return "+".join(terms) or "0"


def _piecewise(keys):
    """Linear interpolation expression over [(t, v), ...]."""
    if len(keys) == 1:
        return f"{keys[0][1]:.1f}"
    terms = []
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t1 <= t0:
            continue
        terms.append(f"between(t,{t0:.2f},{t1:.2f})*({v0:.1f}+({v1 - v0:.1f})*(t-{t0:.2f})/{t1 - t0:.2f})")
    terms.append(f"gt(t,{keys[-1][0]:.2f})*{keys[-1][1]:.1f}")
    return "+".join(terms)


def render(proj: Path, n: int) -> Path:
    cfg = load_config()
    d = clip_dir(proj, n)
    plan = read_json(d / "plan.json")
    prep = read_json(d / "prep.json")
    words = read_json(d / "words.json")["words"]
    face = read_json(d / "facecam.json") if (d / "facecam.json").exists() else {"mode": "none"}
    src = d / "source.mp4"
    SW, SH = video_size(src)
    W, H, FPS = cfg["width"], cfg["height"], cfg["fps"]
    D = float(cfg["target_duration"])
    Ht = int(H * cfg["top_ratio"]) // 2 * 2
    Hb = H - Ht
    avail = prep["duration"]

    # ---- timeline: optional teaser, then the main moment
    segs = []  # (src_a, src_b, out_a)
    td = 0.0
    if plan.get("teaser"):
        tz = plan["teaser"]
        td = float(tz.get("duration", 2.5))
        segs.append((float(tz["start"]), float(tz["start"]) + td, 0.0))
    ms = float(plan.get("main_start", 0.0))
    me = ms + (D - td)
    if me > avail + 0.05:
        sys.exit(f"Clip {n}: main_start {ms} leaves only {avail - ms:.1f}s of footage, need {D - td:.1f}s. "
                 "Lower main_start or re-run prepare with an earlier start.")
    segs.append((ms, me, td))

    def to_out(t_src):
        a, b, o = segs[-1]
        return t_src - a + o if a <= t_src <= b else None

    out_words = []
    for a, b, o in segs:
        out_words += [{**w, "start": w["start"] - a + o, "end": min(w["end"], b) - a + o}
                      for w in words if a <= w["start"] < b]
    (d / "captions.ass").write_text(captions.build_ass(out_words, cfg, plan.get("hook"), plan.get("cta"),
                                                       plan.get("emphasis", []), D))
    (d / "captions.srt").write_text(captions.build_srt(out_words))

    # ---- sound cues (source time -> output time)
    cues = []
    for c in plan.get("sfx", []):
        t = c["t_out"] if "t_out" in c else to_out(c["t"])
        if t is not None and 0 <= t < D:
            cues.append((t, sfx.path_of(c["name"]), c.get("gain_db", cfg["sfx_default_gain_db"]), c["name"]))
    if td:
        cues.append((max(0, td - 0.35), sfx.path_of("whoosh"), cfg["sfx_default_gain_db"], "whoosh"))
    zooms = []
    for z in plan.get("zooms", []):
        t = to_out(z["t"])
        if t is not None:
            zooms.append({"t": t, "dur": z.get("dur", 0.8), "amount": z.get("amount", 0.15)})

    # ---- gameplay crop anchor (avoid the original webcam when possible)
    s = Hb / SH
    sw = int(round(SW * s / 2) * 2)
    anchor = 0.5
    if face.get("mode") == "overlay" and sw > W:
        bx, _, bw, _ = face["box"]
        if face["side"] == "right" and bx * s >= W:
            anchor = 0.0
        elif face["side"] == "left" and (bx + bw) * s <= sw - W:
            anchor = 1.0

    if plan.get("press_file"):
        pr = next((e for e in press.library() if e["file"] == plan["press_file"]), None)
        if not pr:
            sys.exit(f"press_file {plan['press_file']} is not in the press library (dakie press list)")
    else:
        pr = press.pick(plan.get("press_seed", n))
    inputs = ["-i", str(src), "-stream_loop", "-1", "-i", str(PRESS_DIR / pr["file"])]
    for _, p, _, _ in cues:
        inputs += ["-i", str(p)]

    fc = []
    nseg = len(segs)
    fc.append(f"[0:v]split={nseg}" + "".join(f"[vs{i}]" for i in range(nseg)))
    fc.append(f"[0:a]asplit={nseg}" + "".join(f"[as{i}]" for i in range(nseg)))
    for i, (a, b, _) in enumerate(segs):
        fc.append(f"[vs{i}]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,fps={FPS}[v{i}]")
        fc.append(f"[as{i}]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i in range(nseg)) + f"concat=n={nseg}:v=1:a=1[bv][ba]")

    cam = face.get("mode") == "overlay"
    fc.append("[bv]split=2[gsrc][fsrc]" if cam else "[bv]null[gsrc]")
    game = (f"[gsrc]scale={sw}:{Hb},crop={W}:{Hb}:{int((sw - W) * anchor)}:0,setsar=1")
    if zooms:
        game += (f",zoompan=z='1+({_bump(zooms, 'in/' + str(FPS))})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                 f":d=1:s={W}x{Hb}:fps={FPS}")
    fc.append(game + "[game]")
    fc.append(f"[1:v]scale={W}:{Ht}:force_original_aspect_ratio=increase,crop={W}:{Ht},fps={FPS},"
              f"trim=0:{D},setpts=PTS-STARTPTS,setsar=1[top]")
    fc.append("[top][game]vstack=inputs=2[stack]")
    last = "stack"
    if cam:
        bx, by, bw, bh = face["box"]
        cw, ch = int(bw * 0.86) // 2 * 2, int(bh * 0.86) // 2 * 2
        trk = face.get("track") or []
        if trk:
            def clampx(v):
                return float(np.clip(v - cw / 2, bx, bx + bw - cw))

            def clampy(v):
                return float(np.clip(v - ch * 0.45, by, by + bh - ch))
            kx, ky = [], []
            for a, b, o in segs:
                for t, x, y in trk:
                    if a <= t <= b:
                        kx.append((t - a + o, clampx(x)))
                        ky.append((t - a + o, clampy(y)))
            kx.sort()
            ky.sort()
            xe, ye = (_piecewise(kx), _piecewise(ky)) if kx else (str(bx + (bw - cw) / 2), str(by + (bh - ch) / 2))
        else:
            xe, ye = str(bx + (bw - cw) / 2), str(by + (bh - ch) / 2)
        fw = cfg["facecam_width"]
        fh = int(fw * ch / cw) // 2 * 2
        bd = int(cfg.get("facecam_border", 4))
        fc.append(f"[fsrc]crop={cw}:{ch}:x='{xe}':y='{ye}',scale={fw}:{fh},setsar=1,"
                  f"pad={fw + 2 * bd}:{fh + 2 * bd}:{bd}:{bd}:color={cfg.get('facecam_border_color', 'black')}[cam]")
        fc.append(f"[{last}][cam]overlay=x={W - fw - 2 * bd - cfg['facecam_margin_right']}:"
                  f"y={H - fh - 2 * bd - cfg['facecam_margin_bottom']}[withcam]")
        last = "withcam"
    if cfg.get("progress_bar"):
        fc.append(f"color=c=0xFFD400:s={W}x10:r={FPS}:d={D}[bar]")
        fc.append(f"[{last}][bar]overlay=x='-w+w*t/{D}':y={Ht - 5}:shortest=1[barred]")
        last = "barred"
    fc.append(f"[{last}]ass=captions.ass:fontsdir=/System/Library/Fonts/Supplemental,format=yuv420p[vout]")

    # ---- audio: clean + level the stream audio, then lay SFX under it
    fc.append(f"[ba]highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=2,"
              f"loudnorm=I={cfg['loudness_lufs']}:TP=-1.5:LRA=11,aresample=48000[voice]")
    mix = ["[voice]"]
    for k, (t, _, g, _) in enumerate(cues):
        ms_ = int(t * 1000)
        fc.append(f"[{k + 2}:a]aresample=48000,volume={g}dB,adelay={ms_}|{ms_}[sx{k}]")
        mix.append(f"[sx{k}]")
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.93[aout]")

    script = d / "filter.txt"
    script.write_text(";\n".join(fc))
    out = d / "final.mp4"
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "warning", "-stats", *inputs,
         "-/filter_complex", script.name, "-map", "[vout]", "-map", "[aout]",
         "-t", f"{D}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", str(cfg["crf"]),
         "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", out.name], cwd=d)
    hook_t = min(1.5, float((plan.get("hook") or {}).get("duration") or 1.5))
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{hook_t:.2f}", "-i", out.name,
         "-frames:v", "1", "-q:v", "2", "cover.jpg"], cwd=d)
    write_json(d / "render.json", {"duration": media_duration(out), "press_clip": pr,
                                   "sfx_used": [{"t": round(t, 2), "name": nm, "gain_db": g} for t, _, g, nm in cues],
                                   "facecam_mode": face.get("mode"), "teaser": bool(td)})
    print(f"Rendered {out} ({media_duration(out):.2f}s)")
    return out
