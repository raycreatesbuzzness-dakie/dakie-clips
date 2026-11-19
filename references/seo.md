# Metadata and SEO (`clips/clip_NN/meta.json`)

Audience: English-speaking, international, with the US first, then the UK, Canada, Australia,
India, the Philippines, Germany, Brazil and Mexico (big GTA short-form audiences). Write in plain,
global English: no local slang that doesn't travel, no US-only references, and use numbers
("$1,000,000", "5 STARS") because they read in any language.

```json
{
  "youtube": {
    "title": "GTA 6 Cops Didn't Expect This Escape 😳",
    "description": "First line repeats the hook + main keyword...\n\n🎮 Streamer: <name> - <stream URL>\n#GTA6 #GTAVI #Shorts",
    "hashtags": ["#GTA6", "#GTAVI", "#Shorts"],
    "tags": ["gta 6", "gta vi", "gta 6 gameplay", "gta 6 funny moments", "<streamer name>"]
  },
  "tiktok":    {"caption": "...", "hashtags": ["#GTA6", "#GTAVI", "#gaming", "#gta6clips"]},
  "instagram": {"caption": "...", "hashtags": ["#GTA6", "#GTAVI", "#gamingreels"]},
  "facebook":  {"caption": "...", "hashtags": ["#GTA6", "#Gaming"]},
  "seo": {
    "primary_keyword": "gta 6 police chase",
    "secondary_keywords": ["gta 6 funny moments", "gta 6 gameplay", "<streamer> gta 6"],
    "target_regions": ["US", "UK", "CA", "AU", "IN", "PH", "DE", "BR", "MX"],
    "posting_times": "Weekdays 12-3 PM and 7-10 PM US Eastern (covers US evenings and EU nights)"
  }
}
```

## Rules for every platform
- Lead with the **search keyword + the hook**: "GTA 6" (or "GTA VI") must be in the first 40
  characters of every title/caption. People search "gta 6 + funny/glitch/police/heist/secret/easter egg".
- **Credit line in every text:** `Streamer: <name> (<stream URL>)`. `dakie package` checks it.
- Be accurate to the clip; never promise something the clip doesn't show.
- Hashtags: `#Word` only (letters/numbers/underscore). Use broad + niche + streamer:
  `#GTA6 #GTAVI` + one topic tag (`#GTA6Funny`, `#GTA6Glitch`, `#GTA6Police`) + `#<StreamerName>`.
- Banned wording (the validator flags it): leak/leaked, full stream, mod menu, free download,
  hacks/cheats, "official", "no copyright intended"/"fair use", giveaway bait, "not clickbait".
- Don't use song titles, artist names or other creators' brands unless they are actually in the clip.
- Emojis: 0–2 in titles, fine in captions.

## YouTube Shorts
- Title ≤ 100 characters, aim for 40–60 so it isn't cut off. Pattern: `GTA 6 <what happens> <emotion/result>`.
- Description: line 1 = hook sentence with the primary keyword; line 2 = 1–2 sentences of context
  with secondary keywords; then the credit line; then 3–5 hashtags (the first 3 show above the title;
  more than 15 hashtags makes YouTube ignore all of them). `#Shorts` is optional.
- `tags`: 8–15 search phrases (also the streamer's name and "gta 6 clips").
- Upload `captions.srt` as the English subtitle track. Set the video language to English.
  Turn on auto-translated titles/descriptions if available: that is the main international lever.

## TikTok
- Caption: a hook line written like a comment ("bro really thought he escaped 💀"), then a question
  to drive comments ("Would you have bailed?"), then the credit line, then 3–6 hashtags.
- TikTok search reads the caption and on-screen text, so put the keyword phrase in the caption naturally.

## Instagram Reels
- First 125 characters show before "more": hook + keyword there. Then credit, then 3–5 hashtags
  (Instagram is limiting hashtag counts; more doesn't help).
- Suggest a cover frame: `cover.jpg` shows the hook.

## Facebook Reels
- Shorter, conversational: 1–2 sentences + a question + credit + 2–5 hashtags.
- Facebook's audience skews older and more international; plain wording works best.

## Length note
Each video is exactly 3:00. YouTube Shorts and Instagram Reels allow up to 3 minutes, and TikTok
allows longer. If Facebook doesn't offer the upload as a Reel, post it as a regular video.
