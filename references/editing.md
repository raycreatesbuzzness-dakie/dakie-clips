# Editing plan (`clips/clip_NN/plan.json`)

## Layout (config `"layout": "cam_top"`, Dakie's v2 sample)
- **Top 32%:** the streamer's webcam, cropped from the stream's webcam overlay (`facecam.json` box) and
  filling the width: this panel is for their reactions, so the box must cover the whole webcam.
- **Bottom 68%:** the gameplay.
- **Bottom-right corner:** the hydraulic press video in a small window (`press_inset_*` in config).
- **Title box** straddles the seam (mostly over the webcam); **captions** sit just below it on the gameplay.
- No webcam in the stream (or `cam_off` stretches): the top panel shows a crop of the stream instead.
- The v1 layout (press on top, webcam box bottom-right) is `"layout": "press_top"` in config.

All times are **seconds from the start of the downloaded clip** (the times `dakie words` prints),
unless the key is `t_out` (seconds in the finished video).

```json
{
  "duration":   28,
  "teaser":     {"start": 24.2, "duration": 1.2},
  "main_start": 3.0,
  "hook":       {"text": "Speed thought the cops were gone in GTA 6!!"},
  "emphasis":   ["cops", "helicopter", "no", "way"],
  "sfx": [
    {"t_out": 0.05, "name": "bass_drop", "gain_db": -10},
    {"t": 12.4, "name": "police_siren", "gain_db": -16},
    {"t": 24.6, "name": "boom_impact", "gain_db": -9}
  ],
  "zooms": [{"t": 24.4, "dur": 0.9, "amount": 0.18}],
  "cta": "FOLLOW FOR MORE GTA 6"
}
```

| key | rule |
|---|---|
| `duration` | Optional finished length in seconds, **20–30** (`min_duration`–`max_duration` in config). Default `target_duration` (28). One moment per clip: start on the setup, end right after the payoff (cut the aftermath). |
| `teaser` | Optional cold open: 1–1.5 s of the climax shown first, then a whoosh, then the clip from `main_start`. Use it only when the payoff lands after ~12 s. It must sit inside the downloaded footage. |
| `main_start` | Where the story starts. `main_start + (duration − teaser)` must be ≤ the clip length (`prep.json → duration`). Cut any slow intro: the first spoken line should land within 1 s. |
| `hook.text` | The title in the white rounded box, on screen the **whole video** (Dakie's reference layout). Sentence case exactly as written (not all caps), 30–45 characters so it fits on 2 lines, wraps automatically. Optional `duration` (seconds) to show it only at the start. |
| `emphasis` | 3–8 single words that carry the story (names, "cops", "baby", "NO WAY"). Shown in coral red and slightly larger in the captions. |
| `caption_palette` | Optional list of ASS colours for the spoken-word highlight in this clip (default: yellow, cyan, pink, orange from config). |
| `sfx` | 2–4 cues per clip, spaced ≥ 5 s apart. Use names from `dakie sfx list`, including sounds Dakie added. Vary the sounds across the 10 clips. |
| `zooms` | 1–2 punch-ins on the gameplay at peak reactions. `amount` 0.12–0.25, `dur` 0.6–1.2 s. |
| `cta` | Optional text for the last 3 s (keep it short; no "link in bio" for Shorts). |
| `cam_off` | Optional `[[start, end], ...]` (clip seconds) where the stream has no webcam overlay (e.g. the camera is shown full-screen). There the top panel shows a crop of the stream instead of the webcam. Check a frame timeline of `source.mp4` during QA. |
| `cam_off_anchor` | Where the crops point during `cam_off` stretches (and the top panel when no webcam exists): 0 = left, 0.5 = centre (default), 1 = right. Use it when the person who matters stands off-centre in the full-screen camera. |
| `press_file` | Normally **leave it out**: the renderer gives each clip in the project its own press video, highest priority first (real footage before generated loops). Set it only to choose a specific free video; one already used by another clip is refused unless `"press_reuse": true`. |

## Writing the title (first 3 seconds decide retention)
Dakie's house style (from the reference): **streamer name + what happens + "at/in GTA 6" + short
reaction**, like a friend telling you about it, e.g. "Speed meets his workmates at GTA 6!! Damn!".
Patterns, written for this exact moment and true to what happens:
- **Story:** "Speed meets his workmates at GTA 6!! Damn!"
- **Curiosity gap:** "Kai didn't see the train coming in GTA 6..."
- **Stakes:** "$1,000,000 heist with 1 HP left in GTA 6!!"
- **Reaction:** "Chat couldn't believe what he did in GTA 6"
- **Discovery:** "He found a GTA 6 secret nobody knew about"

Rules: no lies or bait the clip doesn't pay off (hurts retention and violates misleading-metadata
policies), no slurs, no quoting song lyrics, no other creators' catchphrases as the headline, no emojis
(the caption renderer can't draw color emoji). Start the clip on motion or speech, not on silence.
`t_out: 0.05` + `bass_drop` or `boom_impact` under the hook is a strong opener.

## Sound effects
Match sound to on-screen events: `police_siren` for wanted levels/chases, `boom_impact` for crashes and
explosions, `bass_drop` for shock reveals, `record_stop` for fails/awkward pauses, `cash` for money,
`heartbeat`/`riser` before a close call (place the riser to *end* on the payoff), `dun_dun` for
betrayals/plot twists, `glitch` for game bugs, `ding` for clever plays, `pop` sparingly for text.
Gain: −8 to −10 dB for impacts at a payoff, −14 to −18 dB for beds (siren, heartbeat, riser).
Never put a cue on top of an important line of dialogue; land it in the gap right after.
`dakie sfx suggest <project> <n>` lists keyword-based ideas to start from.

## Captions
Captions are generated automatically from Whisper word timings: 3 words per line on the seam
between the panels, white text with a heavy black outline, and colour that moves with the speech:

- the **spoken word** pops slightly larger in a colour that changes every caption line
  (yellow → cyan → pink → orange, `highlight_palette` in config);
- **emphasis** words stay coral red (`emphasis_color`) and pop larger;
- **numbers and money** ("13", "$527", "first", "hundred") stay lime green (`number_color`).

Profanity is masked (`f***`) because it limits TikTok/YouTube reach. Change fonts, colours and size
in `~/DakieClips/config.json`. If Whisper misheard or missed a key line (the full-stream transcript
often has it), fix `words.json`: edit the `word` field, or insert new words with `start`/`end`
times into both `words` and a `segments` entry, then re-render.
