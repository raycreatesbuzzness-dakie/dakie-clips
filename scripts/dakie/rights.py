"""Copyright / reuse-rights pre-check for a source stream.

This is a risk screen, not legal advice. It can only see public metadata, so a
GREEN result means "public signals allow reuse", never "you own this footage".
"""
from __future__ import annotations

import re

NO_REUSE = [
    r"do\s*n[o']?t\s+re-?upload", r"no\s+re-?uploads?", r"do\s*n[o']?t\s+clip", r"no\s+clipping",
    r"no\s+clips", r"clipping\s+(is\s+)?not\s+allowed", r"all\s+rights\s+reserved",
    r"unauthori[sz]ed\s+(use|re-?upload|reproduction)", r"will\s+(be\s+)?(dmca|copyright\s+strike)",
    r"do\s*n[o']?t\s+use\s+my\s+content",
]
REUSE_OK = [
    r"clips?\s+(are\s+)?(allowed|welcome)", r"feel\s+free\s+to\s+clip", r"clippers?\s+welcome",
    r"clip\s+channels?\s+(are\s+)?(allowed|welcome)", r"free\s+to\s+(use|clip|reupload)",
    r"clipping\s+(program|campaign)", r"creative\s+commons", r"cc[- ]by",
]
MUSIC = [
    r"music\s+(by|from|used)", r"spotify", r"soundtrack", r"\bsong\b", r"\bplaylist\b", r"\bdj\b",
    r"karaoke", r"epidemic\s+sound", r"streambeats", r"\bncs\b", r"lofi", r"\bbeats?\b",
]
GTA = [r"gta\s*(6|vi)\b", r"grand\s+theft\s+auto\s+(6|vi)\b"]


def _hits(patterns, text):
    return [p for p in patterns if re.search(p, text, re.I)]


def assess(info: dict) -> dict:
    text = " ".join(str(info.get(k) or "") for k in ("title", "description"))
    tags = " ".join(info.get("tags") or [])
    platform = info.get("extractor_key") or info.get("extractor") or "unknown"
    license_ = info.get("license") or ""
    availability = info.get("availability") or "public"
    live_status = info.get("live_status") or ("is_live" if info.get("is_live") else "")
    issues, notes = [], []
    level = "YELLOW"

    if live_status in ("is_live", "is_upcoming", "post_live"):
        issues.append(f"The stream is `{live_status}`. The full replay (VOD) and chat replay are not "
                      "available yet. Wait until the stream has ended and the VOD is processed.")
        level = "RED"
    if availability not in ("public", "unlisted", None):
        issues.append(f"Availability is `{availability}` (members-only/private/paid). That content is "
                      "restricted by the creator and must not be re-published.")
        level = "RED"
    if info.get("age_limit"):
        notes.append(f"Age-restricted ({info['age_limit']}+). Shorts/TikTok/Reels may limit reach or "
                     "reject mature clips; avoid graphic or sexual moments.")

    no = _hits(NO_REUSE, text)
    ok = _hits(REUSE_OK, text + " " + tags)
    if no:
        issues.append("The description contains a no-reuse notice (matched: "
                      + ", ".join(f"`{p}`" for p in no) + "). Treat this stream as off-limits "
                      "unless the streamer gives you written permission.")
        level = "RED"

    cc = "creative commons" in license_.lower()
    if level != "RED":
        if cc:
            level = "GREEN"
            notes.append(f"Licensed `{license_}`. Reuse and editing are allowed with attribution; "
                         "keep the credit line in every description.")
        elif ok:
            level = "GREEN"
            notes.append("The description invites clipping (matched: " + ", ".join(f"`{p}`" for p in ok)
                         + "). Read the exact terms (some programs require their tag/link or "
                         "forbid monetization) and keep proof of them.")
        else:
            notes.append(f"Standard license (`{license_ or 'not stated'}`) and no public clipping "
                         "permission found. The streamer owns this footage. Publishing it needs "
                         "their permission (e.g. a clipping program, Discord rule or DM); "
                         "relying on fair use is risky for a split-screen format with little commentary.")

    music = _hits(MUSIC, text + " " + tags)
    if music:
        notes.append("Music is mentioned in the title/description (" + ", ".join(f"`{p}`" for p in music)
                     + "). Background music is the #1 cause of Content ID / TikTok audio mutes; "
                     "the per-clip report flags segments that sound like music.")
    if _hits(GTA, text + " " + tags):
        notes.append("Game footage: GTA VI belongs to Rockstar Games/Take-Two. Rockstar has "
                     "historically allowed gameplay videos, but check their current video policy, "
                     "avoid unreleased or leaked material, and avoid in-game licensed radio music.")
    else:
        notes.append("The title/description does not mention GTA 6. Confirm this is a GTA 6 stream.")

    return {
        "level": level,
        "platform": platform,
        "license": license_ or "not stated",
        "availability": availability,
        "live_status": live_status or "not live",
        "uploader": info.get("uploader") or info.get("channel"),
        "uploader_url": info.get("uploader_url") or info.get("channel_url"),
        "issues": issues,
        "notes": notes,
        "needs_user_ok": level != "GREEN",
    }


def to_markdown(r: dict, info: dict) -> str:
    icon = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}[r["level"]]
    lines = [
        f"# Rights check: {icon} {r['level']}",
        "",
        f"- **Stream:** {info.get('title')}",
        f"- **Streamer:** {r['uploader']} ({r['uploader_url']})",
        f"- **Platform:** {r['platform']} | **License:** {r['license']} | "
        f"**Availability:** {r['availability']} | **Live status:** {r['live_status']}",
        "",
    ]
    if r["issues"]:
        lines += ["## Blocking issues", *[f"- {i}" for i in r["issues"]], ""]
    lines += ["## Notes", *[f"- {n}" for n in r["notes"]], "",
              "_Automated screen of public metadata only, not legal advice._"]
    return "\n".join(lines)
