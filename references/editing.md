# Editing plan (`clips/clip_NN/plan.json`)

All times are **seconds from the start of the downloaded clip** (the times `dakie words` prints),
unless the key is `t_out` (seconds in the finished video).

```json
{
  "teaser":     {"start": 131.2, "duration": 2.5},
  "main_start": 0.0,
  "hook":       {"text": "Speed thought the cops were gone in GTA 6!!"},
  "emphasis":   ["cops", "helicopter", "no", "way"],
  "sfx": [
    {"t": 12.4, "name": "police_siren", "gain_db": -16},
    {"t": 131.6, "name": "boom_impact", "gain_db": -9},
    {"t_out": 0.05, "name": "bass_drop", "gain_db": -10}
  ],
  "zooms": [{"t": 131.4, "dur": 0.9, "amount": 0.18}],
  "cta": "FOLLOW FOR MORE GTA 6",
  "press_seed": 1
}
```

| key | rule |
|---|---|
| `teaser` | Optional cold open: 2–3 s of the climax shown first, then a whoosh, then the clip from `main_start`. Use it when the payoff happens after ~30 s. It must sit inside the downloaded footage. |
| `main_start` | Where the story starts. Total length is fixed at `target_duration`, so `main_start + (target_duration − teaser)` must be ≤ the clip length (`prep.json → duration`). |
| `hook.text` | The title in the white rounded box, on screen the **whole video** (Dakie's reference layout). Sentence case exactly as written (not all caps), 30–45 characters so it fits on 2 lines, wraps automatically. Optional `duration` (seconds) to show it only at the start. |
| `emphasis` | 4–12 single words that carry the story (names, "cops", numbers, "NO WAY"). Shown in yellow in the captions. |
| `sfx` | 3–8 cues per 3-minute clip, spaced ≥ 10 s apart. Use `dakie sfx list` names only. |
| `zooms` | 2–5 punch-ins on the gameplay at peak reactions. `amount` 0.12–0.25, `dur` 0.6–1.2 s. |
| `cta` | Optional text for the last 3 s (keep it short; no "link in bio" for Shorts). |
| `cam_off` | Optional `[[start, end], ...]` (clip seconds) where the cam box is hidden, e.g. while the stream shows the camera full-screen and has no webcam overlay. Check a frame timeline of `source.mp4` during QA. |
| `press_file` | Which top-panel clip to use (`dakie press list`). Prefer real footage (`pexels_press_*`) and use a different clip for each of the 5 videos where possible. If omitted, `press_seed` picks one at random. |

## Writing the hook (first 3 seconds decide retention)
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
between the panels, the active word in yellow (slightly larger), emphasis words also yellow (set `emphasis_color` for another color), profanity
masked (`f***`) because it limits TikTok/YouTube reach. Change fonts, colors and size in
`~/DakieClips/config.json`. If Whisper misheard a key word, fix it in `words.json` (the `word`
field in both `segments[].words` and `words`) and re-render.
