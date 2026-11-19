"""Validate per-platform metadata, run the final copyright checklist, and package deliverables."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import sfx
from .clip import clip_dir
from .common import read_json, slugify, write_json

LIMITS = {
    "youtube": {"title": 100, "description": 5000, "hashtags_max": 15, "hashtags_rec": (3, 5)},
    "tiktok": {"caption": 4000, "hashtags_rec": (3, 6)},
    "instagram": {"caption": 2200, "hashtags_max": 30, "hashtags_rec": (3, 5)},
    "facebook": {"caption": 5000, "hashtags_rec": (2, 5)},
}
RISKY = [
    (r"\bleak(ed|s)?\b", "Leak claims can get videos removed and break Rockstar's video policy."),
    (r"\bfull stream\b|\bfull vod\b", "Implies you are re-uploading the whole stream."),
    (r"\bfree download\b|\bmod menu\b|\bhack(s|ed)?\b|\bcheat(s)?\b", "Cheating/download claims hit spam policies."),
    (r"\bofficial\b", "Implies affiliation with Rockstar or the streamer."),
    (r"\bno copyright\b|\bcopyright free\b|\bfair use\b", "Copyright disclaimers do not protect you and look spammy."),
    (r"\bgiveaway\b|\bfree (vbucks|money|robux|shark cards?)\b", "Giveaway bait is treated as scam/spam."),
    (r"\bnot clickbait\b", "Spam signal."),
]


def _tags_ok(tags):
    return [t for t in tags if not re.fullmatch(r"#[A-Za-z0-9_]+", t)]


def validate(meta: dict, info: dict) -> list[str]:
    w = []
    credit_keys = [k for k in (info.get("uploader"), info.get("channel"), info.get("source_url")) if k]
    for plat, lim in LIMITS.items():
        m = meta.get(plat)
        if not m:
            w.append(f"{plat}: missing")
            continue
        body = m.get("description") or m.get("caption") or ""
        for field in ("title", "description", "caption"):
            if field in lim and len(m.get(field, "")) > lim[field]:
                w.append(f"{plat}: {field} is {len(m[field])} chars (limit {lim[field]})")
        if plat == "youtube" and not m.get("title"):
            w.append("youtube: title missing")
        tags = m.get("hashtags", [])
        bad = _tags_ok(tags)
        if bad:
            w.append(f"{plat}: malformed hashtags {bad}")
        if "hashtags_max" in lim and len(tags) > lim["hashtags_max"]:
            w.append(f"{plat}: {len(tags)} hashtags exceeds {lim['hashtags_max']}")
        lo, hi = lim["hashtags_rec"]
        if not lo <= len(tags) <= hi:
            w.append(f"{plat}: {len(tags)} hashtags; {lo}-{hi} performs best")
        if credit_keys and not any(k.lower() in body.lower() for k in credit_keys):
            w.append(f"{plat}: no credit to the original streamer ({info.get('uploader')}) in the text")
        text = " ".join([m.get("title", ""), body, " ".join(tags)])
        for pat, why in RISKY:
            if re.search(pat, text, re.I):
                w.append(f"{plat}: risky wording /{pat}/: {why}")
    return w


def to_markdown(meta: dict, n: int) -> str:
    y, t, i, f = (meta.get(k, {}) for k in ("youtube", "tiktok", "instagram", "facebook"))
    seo = meta.get("seo", {})
    tag = lambda m: " ".join(m.get("hashtags", []))
    return f"""# Clip {n:02d}: upload kit

## YouTube Shorts
**Title:** {y.get('title', '')}

**Description:**
{y.get('description', '')}

{tag(y)}

**Tags (Studio > Tags):** {', '.join(y.get('tags', []))}

## TikTok
{t.get('caption', '')}

{tag(t)}

## Instagram Reels
{i.get('caption', '')}

{tag(i)}

## Facebook Reels
{f.get('caption', '')}

{tag(f)}

## SEO notes
- **Primary keyword:** {seo.get('primary_keyword', '')}
- **Secondary keywords:** {', '.join(seo.get('secondary_keywords', []))}
- **Target audience/regions:** {', '.join(seo.get('target_regions', []))}
- **Suggested posting times:** {seo.get('posting_times', '')}
- **Upload captions.srt** as closed captions on YouTube and Facebook (helps search + accessibility).
"""


def package(proj: Path, n: int) -> Path:
    info = read_json(proj / "info.json")
    rights = read_json(proj / "rights.json")
    d = clip_dir(proj, n)
    meta = read_json(d / "meta.json")
    rend = read_json(d / "render.json")
    prep = read_json(d / "prep.json")
    warns = validate(meta, info)

    lines = [f"# Clip {n:02d}: copyright checklist", ""]
    lvl = rights["level"]
    lines.append(f"- {'🟢' if lvl == 'GREEN' else '🟡' if lvl == 'YELLOW' else '🔴'} **Source footage** "
                 f"({info.get('uploader')}, {rights['license']}): rights level {lvl}. "
                 + ("Reuse permitted by public signals; keep the credit line." if lvl == "GREEN" else
                    "You do NOT own this footage. Publish only with the streamer's permission."))
    mr = prep.get("music_risk_windows", [])
    lines.append(f"- {'🟡' if mr else '🟢'} **Music:** "
                 + (f"possible music (loud audio, no speech) at {', '.join(mr)} of the clip. "
                    "Listen to these spots; licensed music or GTA radio triggers Content ID/TikTok mutes." if mr
                    else "no music-like stretches detected (still listen for in-game radio)."))
    lines.append(f"- 🟢 **Top panel:** {rend['press_clip']['file']}: {rend['press_clip']['license']}")
    lib = {e["name"]: e for e in sfx.library()}
    used = sorted({c["name"] for c in rend["sfx_used"]})
    lic = [f"{u} ({lib.get(u, {}).get('license', 'UNKNOWN')})" for u in used]
    unknown = [u for u in used if "unknown" in lib.get(u, {}).get("license", "unknown").lower()]
    lines.append(f"- {'🔴' if unknown else '🟢'} **Sound effects:** " + (", ".join(lic) or "none"))
    lines.append("- 🟢 **Captions/hook text:** transcribed from the stream + original hook writing; fonts are macOS system fonts.")
    lines.append(f"- {'🟡' if warns else '🟢'} **Metadata:** " + ("; ".join(warns) if warns else "passes length, hashtag, credit and risky-wording checks."))
    lines += ["", "_Automated checklist, not legal advice._"]

    out = proj / "final" / f"clip_{n:02d}"
    out.mkdir(parents=True, exist_ok=True)
    name = slugify(meta.get("youtube", {}).get("title", f"clip-{n}"), 60)
    shutil.copy2(d / "final.mp4", out / f"{n:02d}-{name}.mp4")
    for f in ("cover.jpg", "captions.srt"):
        if (d / f).exists():
            shutil.copy2(d / f, out / f)
    write_json(out / "metadata.json", meta)
    (out / "metadata.md").write_text(to_markdown(meta, n))
    (out / "copyright_check.md").write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nPackaged -> {out}")
    return out
