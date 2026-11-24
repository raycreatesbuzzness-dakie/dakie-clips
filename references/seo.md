# Metadata and SEO (`clips/clip_NN/meta.json`)

## The house style (from Dakie's best-performing Short)
Dakie's most-viewed Short so far: **"CaseOh's GTA 6 seaplane landing went wrong 😭 #GTA6 #Shorts"**
(2.1K views, 19 likes). What made it work, and what every clip copies:

| Part | Pattern | Why |
|---|---|---|
| Title | `<Streamer>'s GTA 6 <thing> <what went wrong/right> <1 emoji> #GTA6 #Shorts` | Names the streamer first (their fans search them), "GTA 6" early, a tiny story with an outcome, one emoji, and the two hashtags YouTube shows as links above the title |
| Description line 1 | One casual sentence that tells the setup and teases the payoff with "...": *"CaseOh tried to land a seaplane in GTA 6... it did not go to plan"* | Reads like a friend telling you; makes people watch to the end |
| Credit | `Streamer: @handle (channel URL)` then `Clip: <link to the exact moment>` | Clear credit builds trust with the streamer and their fans |
| Hashtags | One line at the bottom, 5 tags: broad + streamer + this moment | Reach plus searchability |

Examples, written for the actual moment (never promise what the clip doesn't show):
- "IShowSpeed's GTA 6 save file got deleted 😭 #GTA6 #Shorts"
- "Kai Cenat's GTA 6 police chase ended in the ocean 💀 #GTA6 #Shorts"
- "CaseOh's GTA 6 seaplane landing went wrong 😭 #GTA6 #Shorts"

Clips are 20–30 seconds: one moment, one payoff. The title must describe that one moment.

```json
{
  "youtube": {
    "title": "IShowSpeed's GTA 6 save file got deleted 😭 #GTA6 #Shorts",
    "description": "Speed played GTA 6 for 52 hours straight... then pressed the wrong button\n\nStreamer: @IShowSpeed (https://www.youtube.com/@IShowSpeed)",
    "hashtags": ["#GTA6", "#GTAVI", "#IShowSpeed", "#SaveFile", "#funny"],
    "tags": ["gta 6", "gta vi", "ishowspeed", "ishowspeed gta 6", "gta 6 save file", "gta 6 clips"]
  },
  "tiktok":    {"caption": "Speed played GTA 6 for 52 hours... then pressed the wrong button 😭 Would you have pressed it?\n\nStreamer: @IShowSpeed (https://www.youtube.com/@IShowSpeed)",
                "hashtags": ["#GTA6", "#GTAVI", "#IShowSpeed", "#SaveFile", "#gaming"]},
  "instagram": {"caption": "...same story line, question, credit...", "hashtags": ["#GTA6", "#IShowSpeed", "#SaveFile", "#gamingreels"]},
  "facebook":  {"caption": "...same story line, question, credit...", "hashtags": ["#GTA6", "#IShowSpeed", "#SaveFile"]},
  "seo": {
    "primary_keyword": "ishowspeed gta 6 delete",
    "secondary_keywords": ["gta 6 save file", "ishowspeed gta 6", "gta 6 funny moments"],
    "target_regions": ["US", "UK", "CA", "AU", "IN", "PH", "DE", "BR", "MX"],
    "posting_times": "Weekdays 12-3 PM and 7-10 PM US Eastern (covers US evenings and EU nights)"
  }
}
```

`dakie package` then adds, under the `Streamer:` line of every text:
- `Clip: <stream URL at the exact second the clip starts>` (YouTube `&t=…s`, Twitch `?t=…h…m…s`), and
- `🎬 Press footage: <credit>` when the press video is CC BY.

On upload, the hashtag list is added as the last line of the YouTube description and of every caption,
so don't repeat it inside the text.

## Rules for every platform
- **Streamer name + "GTA 6" in the first 40 characters** of every title/caption.
- Write in plain, global English (US first, then UK, CA, AU, IN, PH, DE, BR, MX): no local slang that
  doesn't travel; numbers read in any language ("52 hours", "$2,000,000").
- **Credit in every text:** `Streamer: @handle (URL)` (`dakie package` checks it and adds the Clip link).
- Be accurate: the "..." payoff must be in the clip. No bait the clip doesn't pay off.
- 1 emoji in the title (😭 💀 😳 🔥 😂 fit gaming), 1–3 in captions.
- Banned wording (the validator flags it): leak/leaked, full stream, mod menu, free download,
  hacks/cheats, "official", "no copyright intended"/"fair use", giveaway bait, "not clickbait".
- Don't use song titles, artist names or other creators' brands unless they are actually in the clip.
- Put a GTA 6 spoiler warning ("⚠️ GTA 6 story spoilers") on line 2 when the clip shows story twists or the ending.

## Hashtags (5 per clip)
Layers, in this order:
1. **Broad** (shared by all clips): `#GTA6`, `#GTAVI`.
2. **Streamer:** `#IShowSpeed`, `#KaiCenat`, `#CaseOh` (CamelCase, no spaces).
3. **This moment** (1–2 tags no other clip of the stream uses): `#SaveFile`, `#Seaplane`, `#NikoBellic`.
   Take them from what is said or shown (`dakie words`, the frames) and check real searches:
   `dakie keywords "gta 6 <thing>" "<streamer> gta 6"` prints YouTube's live autocomplete.
4. **Vibe** (optional, 1): `#funny`, `#gaming`, `#streamer` (YouTube/TikTok), `#gamingreels` (Instagram).

`dakie package` warns when a set is identical to another clip's, when fewer than 2 tags are unique to the
clip, or when fewer than 2 specific tags match what is said or shown. Per platform: YouTube 3–5 (the
title already carries #GTA6 #Shorts), TikTok 3–6, Instagram 3–5, Facebook 2–5.

## YouTube Shorts
- `title`: the house pattern above, ≤ 100 characters including the hashtags (aim for 45–70).
- `description`: story line (+ spoiler line if needed), blank line, credit. Hashtags come from `hashtags`.
- `tags`: 8–15 search phrases (streamer name, "<streamer> gta 6", the moment, "gta 6 clips").
- Upload `captions.srt` as the English subtitle track.

## TikTok
- `caption`: the story line (written like a comment), then a short question to drive comments
  ("Would you have pressed it?"), then the credit. TikTok search reads the caption, so keep
  "<streamer> GTA 6 <thing>" in the first sentence.

## Instagram Reels
- First 125 characters show before "more": story line with streamer + GTA 6 there, then the question,
  then the credit.

## Facebook Reels
- Story line + question + credit. Plain wording; Facebook's audience skews older and more international.
