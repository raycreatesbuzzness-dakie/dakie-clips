"""Project setup, rights check, and the analysis inputs: transcript, chat, loudness."""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import rights
from .common import (PROJECTS, ensure_home, ffmpeg, load_config, read_json, run, slugify,
                     write_json, ytdlp_base)

KEEP_INFO = ["id", "title", "description", "uploader", "uploader_id", "uploader_url", "channel",
             "channel_url", "duration", "upload_date", "timestamp", "webpage_url", "extractor",
             "extractor_key", "license", "availability", "age_limit", "is_live", "was_live",
             "live_status", "tags", "categories", "view_count", "like_count", "comment_count",
             "thumbnail", "language"]


def init(url: str) -> Path:
    ensure_home()
    cfg = load_config()
    res = run(ytdlp_base(cfg) + ["-J", "--skip-download", url], quiet=True, check=False)
    if res.returncode != 0:
        sys.exit("Could not read this link with yt-dlp:\n" + res.stderr[-1500:]
                 + "\nIf YouTube asks you to sign in, set \"cookies_from_browser\" in ~/DakieClips/config.json.")
    full = json.loads(res.stdout)
    info = {k: full.get(k) for k in KEEP_INFO}
    info["has_subtitles"] = sorted((full.get("subtitles") or {}).keys())
    info["has_auto_captions"] = [k for k in (full.get("automatic_captions") or {}) if k.startswith("en")]
    info["source_url"] = url

    day = dt.date.today().isoformat()
    proj = PROJECTS / f"{day}-{slugify(info.get('uploader') or 'stream', 20)}-{slugify(info.get('title') or info['id'], 40)}"
    for sub in ("source", "analysis", "clips", "final"):
        (proj / sub).mkdir(parents=True, exist_ok=True)
    write_json(proj / "info.json", info)

    r = rights.assess(info)
    write_json(proj / "rights.json", r)
    (proj / "rights.md").write_text(rights.to_markdown(r, info))
    print(json.dumps({"project": str(proj), "rights_level": r["level"],
                      "duration_sec": info.get("duration"), "title": info.get("title"),
                      "uploader": info.get("uploader")}, indent=2))
    print(f"\nRights report: {proj / 'rights.md'}")
    return proj


# ---------------------------------------------------------------- transcript
def _json3_to_segments(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    segs = []
    for ev in data.get("events", []):
        if "segs" not in ev:
            continue
        text = "".join(s.get("utf8", "") for s in ev["segs"]).replace("\n", " ").strip()
        if not text:
            continue
        start = ev.get("tStartMs", 0) / 1000
        segs.append({"start": start, "end": start + ev.get("dDurationMs", 2000) / 1000, "text": text})
    return segs


def fetch_platform_captions(proj: Path, info: dict, cfg: dict) -> list[dict] | None:
    if not (info.get("has_subtitles") or info.get("has_auto_captions")):
        return None
    out = proj / "source" / "captions"
    run(ytdlp_base(cfg) + ["--skip-download", "--write-subs", "--write-auto-subs",
                           "--sub-langs", "en,en-orig,en-US,en-GB", "--sub-format", "json3",
                           "-o", str(out), info["source_url"]], check=False)
    files = sorted(proj.glob("source/captions*.json3"), key=lambda p: ("orig" not in p.name, len(p.name)))
    return _json3_to_segments(files[0]) if files else None


def download_scan_audio(proj: Path, info: dict, cfg: dict) -> Path:
    wav = proj / "source" / "scan_audio.wav"
    if wav.exists():
        return wav
    raw = proj / "source" / "scan_audio_raw"
    run(ytdlp_base(cfg) + ["-f", "bestaudio[abr<=96]/worstaudio/Audio_Only/worst",
                           "-o", str(raw) + ".%(ext)s", info["source_url"]])
    src = next(p for p in proj.glob("source/scan_audio_raw.*") if not p.name.endswith((".part", ".ytdl")))
    tmp = wav.with_name("scan_audio.tmp.wav")      # write then rename: a killed scan never leaves a half WAV
    run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", "16000", tmp])
    tmp.replace(wav)
    src.unlink()
    return wav


def loudness_per_second(wav: Path) -> list[float]:
    """RMS level in dBFS for every second of the 16 kHz mono scan audio."""
    proc = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(wav),
                             "-f", "s16le", "-ac", "1", "-ar", "8000", "-"], stdout=subprocess.PIPE)
    out = []
    while True:
        buf = proc.stdout.read(8000 * 2 * 60)
        if not buf:
            break
        a = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768
        n = len(a) // 8000
        if n:
            rms = np.sqrt((a[: n * 8000].reshape(n, 8000) ** 2).mean(axis=1) + 1e-10)
            out += (20 * np.log10(rms)).round(1).tolist()
    proc.wait()
    return out


def whisper_transcribe(wav: Path, model_name: str, word_timestamps=False, offset=0.0) -> list[dict]:
    """Transcribe a 16 kHz mono WAV in 20-minute chunks (we decode it ourselves, not via PyAV)."""
    import wave
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    out = []
    chunk = 16000 * 60 * 20
    with wave.open(str(wav)) as wf:
        pos = 0
        while True:
            raw = wf.readframes(chunk)
            if not raw:
                break
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
            base = offset + pos / 16000
            pos += len(audio)
            segs, _ = model.transcribe(audio, language="en", vad_filter=True,
                                       word_timestamps=word_timestamps, condition_on_previous_text=False)
            for s in segs:
                item = {"start": round(s.start + base, 2), "end": round(s.end + base, 2),
                        "text": s.text.strip(), "no_speech_prob": round(s.no_speech_prob, 3)}
                if word_timestamps:
                    item["words"] = [{"start": round(w.start + base, 2), "end": round(w.end + base, 2),
                                      "word": w.word.strip(), "p": round(w.probability, 2)} for w in s.words]
                out.append(item)
                print(f"\r  transcribed to {(s.end + base) / 60:.1f} min", end="", file=sys.stderr)
    print(file=sys.stderr)
    return out


# ---------------------------------------------------------------- chat
def _ytdlp_live_chat(proj: Path, info: dict, out: Path) -> int:
    """Fallback: YouTube chat replay via yt-dlp's live_chat subtitle track (JSON lines)."""
    if "live_chat" not in (info.get("has_subtitles") or []):
        return 0
    raw = proj / "source" / "chat.live_chat.json"
    if not raw.exists():
        run(ytdlp_base(load_config()) + ["--skip-download", "--write-subs", "--sub-langs", "live_chat",
                                         "-o", str(proj / "source" / "chat"), info["source_url"]], check=False)
    if not raw.exists():
        return 0
    n = 0
    with raw.open() as src, out.open("w") as f:
        for line in src:
            try:
                d = json.loads(line)["replayChatItemAction"]
            except (ValueError, KeyError):
                continue
            t = int(d.get("videoOffsetTimeMsec", 0)) / 1000
            for a in d.get("actions", []):
                it = a.get("addChatItemAction", {}).get("item", {})
                r = it.get("liveChatTextMessageRenderer") or it.get("liveChatPaidMessageRenderer")
                if not r or t < 0:
                    continue
                text = "".join(x.get("text") or (x.get("emoji", {}).get("shortcuts") or [""])[0]
                               for x in r.get("message", {}).get("runs", []))
                f.write(json.dumps({"t": round(t, 1), "a": r.get("authorName", {}).get("simpleText", ""),
                                    "m": text}, ensure_ascii=False) + "\n")
                n += 1
    return n


def fetch_chat(proj: Path, info: dict) -> int:
    out = proj / "analysis" / "chat.jsonl"
    if out.exists() and out.stat().st_size > 0:
        return sum(1 for _ in out.open())
    try:
        from chat_downloader import ChatDownloader
        chat = ChatDownloader().get_chat(info["source_url"], message_types=["text_message"])
        n = 0
        with out.open("w") as f:
            for m in chat:
                t = m.get("time_in_seconds")
                if t is None or t < 0:
                    continue
                f.write(json.dumps({"t": round(t, 1), "a": (m.get("author") or {}).get("name", ""),
                                    "m": m.get("message", "")}, ensure_ascii=False) + "\n")
                n += 1
                if n % 2000 == 0:
                    print(f"\r  chat messages: {n}", end="", file=sys.stderr)
        print(file=sys.stderr)
        if n:
            return n
    except Exception as e:  # chat replay is optional (Kick, disabled chat, etc.)
        print(f"chat-downloader: {type(e).__name__}: {e}", file=sys.stderr)
    out.unlink(missing_ok=True)
    n = _ytdlp_live_chat(proj, info, out)
    if not n:
        out.unlink(missing_ok=True)
        print("Chat replay unavailable for this video.", file=sys.stderr)
    return n


def fetch_comment_marks(proj: Path, info: dict, cfg: dict) -> int:
    """Timestamps viewers cite in YouTube comments: an engagement signal when chat is missing."""
    import re
    out = proj / "analysis" / "comment_marks.json"
    if out.exists():
        return len(read_json(out))
    if "youtube" not in (info.get("extractor_key") or "").lower():
        return 0
    res = run(ytdlp_base(cfg) + ["-J", "--skip-download", "--write-comments", "--extractor-args",
                                 "youtube:max_comments=2000;comment_sort=top", info["source_url"]],
              quiet=True, check=False)
    if res.returncode != 0:
        return 0
    marks = []
    for c in json.loads(res.stdout).get("comments") or []:
        for m in re.finditer(r"\b(\d{1,2}):(\d{2}):(\d{2})\b|\b(\d{1,3}):(\d{2})\b", c.get("text", "")):
            sec = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]) if m[1] else int(m[4]) * 60 + int(m[5])
            marks.append({"t": sec, "likes": c.get("like_count") or 0, "text": c["text"][:160]})
    write_json(out, marks)
    return len(marks)


def scan(proj: Path) -> None:
    cfg = load_config()
    info = read_json(proj / "info.json")
    status = {}

    print("1/3 chat replay", file=sys.stderr)
    status["chat_messages"] = fetch_chat(proj, info)
    status["comment_timestamps"] = fetch_comment_marks(proj, info, cfg)

    print("2/3 audio for loudness + transcript", file=sys.stderr)
    wav = download_scan_audio(proj, info, cfg)
    lpath = proj / "analysis" / "loudness.json"
    loud = None
    if lpath.exists():                             # resume: reuse a finished loudness pass
        try:
            loud = read_json(lpath)
        except ValueError:
            loud = None
        if not isinstance(loud, list) or len(loud) < 0.98 * float(info.get("duration") or 0):
            loud = None
    if loud is None:
        loud = loudness_per_second(wav)
        tmp = lpath.with_name("loudness.tmp.json")
        write_json(tmp, loud)
        tmp.replace(lpath)

    print("3/3 transcript", file=sys.stderr)
    tpath = proj / "analysis" / "transcript.json"
    if not tpath.exists():
        segs = fetch_platform_captions(proj, info, cfg)
        source = "platform captions"
        if not segs:
            source = f"whisper-{cfg['whisper_scan_model']}"
            segs = whisper_transcribe(wav, cfg["whisper_scan_model"])
        write_json(tpath, {"source": source, "segments": segs})
    t = read_json(tpath)
    status["transcript_source"] = t["source"]
    status["transcript_segments"] = len(t["segments"])
    status["audio_seconds"] = len(loud)
    write_json(proj / "analysis" / "scan_status.json", status)
    print(json.dumps(status, indent=2))
