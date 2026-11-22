"""Word-by-word animated captions (ASS) + hook/CTA titles, and an SRT for platform upload."""
from __future__ import annotations

import re

NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
                "twelve", "thirteen", "twenty", "thirty", "fifty", "hundred", "thousand", "million", "billion",
                "dollars", "bucks", "first", "second", "third"}
PROFANITY = ["fuck", "shit", "bitch", "cunt", "nigga", "nigger", "fag", "retard", "whore", "slut", "dick", "pussy", "cock"]


def _censor(word: str) -> str:
    low = word.lower()
    for p in PROFANITY:
        if p in low:
            i = low.index(p)
            return word[: i + 1] + "*" * (len(p) - 1) + word[i + len(p):]
    return word


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(s: str) -> str:
    return s.replace("{", "(").replace("}", ")").replace("\\", "/")


def clean_words(words: list[dict]) -> list[dict]:
    """Drop empty tokens and rejoin split numbers ("$250" + ",000" -> "$250,000")."""
    out = []
    for w in words:
        word = (w.get("word") or "").strip()
        if not word:
            continue
        if out and re.match(r"^[,.]\d", word) and re.search(r"\d$", out[-1]["word"]):
            out[-1] = {**out[-1], "word": out[-1]["word"] + word, "end": w["end"]}
            continue
        out.append({**w, "word": word})
    return out


def chunk_words(words: list[dict], max_words: int) -> list[list[dict]]:
    words = clean_words(words)
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > 0.45
                    or w["end"] - cur[0]["start"] > 1.8 or re.search(r"[.!?]$", cur[-1]["word"])):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def _wrap_hook(text: str, cfg) -> tuple[list[str], int, int]:
    """Wrap the title to the max width (measured with the real font); return lines and box size."""
    from PIL import ImageFont
    size = cfg["hook_size"]
    try:
        font = ImageFont.truetype(cfg["hook_font_file"], size)
        width = lambda t: font.getlength(t)
    except OSError:
        width = lambda t: len(t) * size * 0.55
    glue = lambda t: re.sub(r"\b(GTA|Part|No\.?|\$)\s+(\d+|VI|V)\b", "\\1\u00a0\\2", t, flags=re.I)
    lines = []
    for para in re.split(r"\\N|\n", glue(text)):
        # split on ordinary spaces only: str.split() would also break the glued "GTA 6"
        words, cur, para_lines = [w for w in re.split(r"[ \t]+", para.strip()) if w], "", []
        for word in words:
            trial = f"{cur} {word}".strip()
            if cur and width(trial) > cfg["hook_max_width"]:
                para_lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            para_lines.append(cur)
        if len(para_lines) == 2 and len(words) > 2:   # balance: no short orphan second line
            best = min(range(1, len(words)),
                       key=lambda k: max(width(" ".join(words[:k])), width(" ".join(words[k:]))))
            a, b = " ".join(words[:best]), " ".join(words[best:])
            if max(width(a), width(b)) <= cfg["hook_max_width"]:
                para_lines = [a, b]
        lines += para_lines
    lines = [l.replace("\u00a0", " ") for l in lines]
    pad_x, pad_y, line_h = int(size * 0.55), int(size * 0.32), size * 1.18
    bw = int(max(width(l) for l in lines) + 2 * pad_x)
    bh = int(len(lines) * line_h + 2 * pad_y)
    return lines, bw, bh


def _rounded_rect(w: float, h: float, r: float) -> str:
    """ASS vector drawing of a rounded rectangle with its top-left at the origin."""
    r = min(r, h / 2, w / 2)
    k = r * 0.5523
    f = lambda *v: " ".join(str(int(round(x))) for x in v)
    return (f"m {f(r, 0)} l {f(w - r, 0)} b {f(w - r + k, 0, w, r - k, w, r)} "
            f"l {f(w, h - r)} b {f(w, h - r + k, w - r + k, h, w - r, h)} "
            f"l {f(r, h)} b {f(r - k, h, 0, h - r + k, 0, h - r)} "
            f"l {f(0, r)} b {f(0, r - k, r - k, 0, r, 0)}")


def build_ass(words, cfg, hook=None, cta=None, emphasis=(), duration=58.0) -> str:
    W, H = cfg["width"], cfg["height"]
    seam = int(H * cfg["top_ratio"])
    cy = cfg["caption_y"] or seam
    font, size = cfg["caption_font"], cfg["caption_size"]
    emph = {e.lower().strip(".,!?") for e in emphasis}
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{cfg['caption_color']},&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,8,3,5,40,40,0,1
Style: Box,Arial,20,&H00FFFFFF,&H000000FF,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Hook,{cfg['hook_font']},{cfg['hook_size']},&H00000000,&H000000FF,&H00FFFFFF,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1
Style: Cta,{font},{int(size*0.7)},&H00FFFFFF,&H000000FF,&H00000000,&H96000000,-1,0,0,0,100,100,1,0,1,6,3,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    palette = list(cfg.get("highlight_palette") or [cfg.get("highlight_color", "&H0000E5FF")])
    num_col = cfg.get("number_color", palette[0])
    is_num = lambda w: bool(re.search(r"\d|\$|%", w)) or w.lower().strip(".,!?") in NUMBER_WORDS
    caps = []   # [start, end, text]; trimmed below so two caption lines never overlap
    for ci, ch in enumerate(chunk_words(words, cfg["max_words_per_line"])):
        active = palette[ci % len(palette)]          # new colour every line keeps the eye moving
        end_chunk = ch[-1]["end"] + 0.12
        for i, w in enumerate(ch):
            st = w["start"]
            en = ch[i + 1]["start"] if i + 1 < len(ch) else end_chunk
            parts = []
            for j, x in enumerate(ch):
                txt = _esc(_censor(x["word"]) if cfg["censor_profanity_in_captions"] else x["word"]).upper()
                key = x["word"].lower().strip(".,!?\"'")
                still = cfg["emphasis_color"] if key in emph else (num_col if is_num(x["word"]) else None)
                if j == i:
                    col = still or active
                    size = 116 if key in emph else 110
                    parts.append(f"{{\\c{col}\\fscx{size}\\fscy{size}}}{txt}{{\\r}}")
                elif still:
                    parts.append(f"{{\\c{still}}}{txt}{{\\r}}")
                else:
                    parts.append(txt)
            pop = "{\\fscx70\\fscy70\\t(0,90,\\fscx100\\fscy100)}" if i == 0 else ""
            caps.append([st, en, f"{{\\pos({W//2},{cy})}}{pop}{' '.join(parts)}"])
    caps.sort(key=lambda c: c[0])
    for i, c in enumerate(caps):
        if i + 1 < len(caps):
            c[1] = min(c[1], caps[i + 1][0])
        if c[1] - c[0] >= 0.04:
            ev.append(f"Dialogue: 1,{_ass_time(c[0])},{_ass_time(c[1])},Cap,,0,0,0,,{c[2]}")
    if hook and hook.get("text"):
        hd = float(hook.get("duration") or duration)
        lines, bw, bh = _wrap_hook(hook["text"], cfg)
        # bottom edge sits just above the seam captions, like the reference layout
        by = int(cy - cfg["caption_size"] * 0.6 - cfg.get("hook_gap", 22) - bh)
        bx = (W - bw) // 2
        ev.append(f"Dialogue: 3,{_ass_time(0)},{_ass_time(hd)},Box,,0,0,0,,"
                  f"{{\\an7\\pos({bx},{by})\\fad(150,0)\\p1}}{_rounded_rect(bw, bh, cfg['hook_size'] * 0.7)}{{\\p0}}")
        txt = "\\N".join(_esc(x) for x in lines)
        ev.append(f"Dialogue: 4,{_ass_time(0)},{_ass_time(hd)},Hook,,0,0,0,,"
                  f"{{\\pos({W // 2},{by + bh // 2})\\fad(150,0)}}{txt}")
    if cta:
        ev.append(f"Dialogue: 3,{_ass_time(duration-3)},{_ass_time(duration)},Cta,,0,0,0,,"
                  f"{{\\pos({W//2},{int(seam*0.3)})\\fad(200,0)}}{_esc(cta).upper()}")
    return head + "\n".join(ev) + "\n"


def build_srt(words, max_words=7) -> str:
    def t(s):
        ms = int(round(s * 1000))
        return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
    out = []
    for i, ch in enumerate(chunk_words(words, max_words), 1):
        out.append(f"{i}\n{t(ch[0]['start'])} --> {t(ch[-1]['end'])}\n{' '.join(_censor(w['word']) for w in ch)}\n")
    return "\n".join(out)
