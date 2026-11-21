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


GENERIC_TAGS = {"gta6", "gtavi", "gta", "gta5", "gaming", "gamer", "games", "videogames", "shorts", "youtubeshorts",
                "fyp", "foryou", "foryoupage", "viral", "trending", "reels", "reel", "gamingreels", "gamingclips",
                "clips", "funny", "explore", "streamer", "twitch", "kick", "youtube"}


def keyword_suggestions(phrase: str, limit: int = 12) -> list[str]:
    """What people actually type into YouTube search for this phrase (public autocomplete)."""
    import json as _json
    import urllib.parse
    import urllib.request
    url = ("https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl=en&q="
           + urllib.parse.quote(phrase))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (dakie-clips keyword research)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return _json.loads(r.read().decode("utf-8", "replace"))[1][:limit]
    except Exception as e:  # research is best-effort
        return [f"(no suggestions: {type(e).__name__})"]


def _tag_tokens(tag: str) -> list[str]:
    body = tag.lstrip("#")
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", body)
    return [p.lower() for p in parts if len(p) > 1 or p.isdigit()]


def hashtag_checks(proj: Path, n: int, meta: dict) -> list[str]:
    """Hashtags must be about THIS clip: unique vs. other clips, and grounded in what is said/shown."""
    w = []
    words_f = clip_dir(proj, n) / "words.json"
    said = " ".join(x["word"] for x in read_json(words_f)["words"]).lower() if words_f.exists() else ""
    said += " " + " ".join(str(v) for v in (meta.get("youtube", {}).get("title", ""),
                                             " ".join(meta.get("seo", {}).get("secondary_keywords", []))))
    info_f = proj / "info.json"
    if info_f.exists():
        inf = read_json(info_f)
        said += " " + " ".join(str(inf.get(k) or "") for k in ("uploader", "channel"))
    said = said.lower()
    others = {}
    for d in sorted((proj / "clips").glob("clip_*")):
        k = int(d.name.split("_")[1])
        if k != n and (d / "meta.json").exists():
            others[k] = read_json(d / "meta.json")
    for plat in ("youtube", "tiktok", "instagram", "facebook"):
        tags = [t.lower() for t in meta.get(plat, {}).get("hashtags", [])]
        if not tags:
            continue
        other_tags = {t.lower() for o in others.values() for t in o.get(plat, {}).get("hashtags", [])}
        for k, o in others.items():
            if sorted(t.lower() for t in o.get(plat, {}).get("hashtags", [])) == sorted(tags):
                w.append(f"{plat}: hashtags are identical to clip {k}; make them about this clip's moment")
        unique = [t for t in tags if t not in other_tags and t.lstrip("#") not in GENERIC_TAGS]
        if others and len(unique) < 2:
            w.append(f"{plat}: only {len(unique)} hashtag(s) unique to this clip (need 2+ about this moment)")
        raw = meta.get(plat, {}).get("hashtags", [])
        specific = [t for t in raw if t.lstrip("#").lower() not in GENERIC_TAGS]
        squashed = re.sub(r"[^a-z0-9]", "", said)
        grounded = [t for t in specific
                    if t.lstrip("#").lower().replace("gta6", "") and (
                        t.lstrip("#").lower().replace("gta6", "") in squashed
                        or any(tok in said for tok in _tag_tokens(t) if tok not in ("gta", "6", "vi")))]
        if len(grounded) < 2:
            w.append(f"{plat}: only {len(grounded)} hashtag(s) match what happens in the clip "
                     f"({', '.join(specific) or 'none'}); use characters, places, actions or quotes from it")
    return w


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
    # CC BY press footage: its credit line must appear in every platform's text
    from . import press as _press
    pc = rend.get("press_clip", {})
    credit = pc.get("credit") or next((e.get("credit") for e in _press.library() if e["file"] == pc.get("file")), None)
    if credit:
        line = f"🎬 Press footage: {credit}"
        for plat, key in (("youtube", "description"), ("tiktok", "caption"), ("instagram", "caption"), ("facebook", "caption")):
            m = meta.get(plat)
            if m and credit not in m.get(key, ""):
                m[key] = (m.get(key, "").rstrip() + "\n" + line).strip()
        write_json(d / "meta.json", meta)
    prep = read_json(d / "prep.json")
    warns = validate(meta, info) + hashtag_checks(proj, n, meta)

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
    lines.append(f"- 🟢 **Top panel:** {rend['press_clip']['file']}: {rend['press_clip']['license']}"
                 + (f" (credit added to every description: {credit})" if credit else ""))
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
