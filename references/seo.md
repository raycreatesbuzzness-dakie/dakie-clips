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
- Hashtags: `#Word` only (letters/numbers/underscore). See **Hashtag research** below; every clip
  gets its own set.
- Banned wording (the validator flags it): leak/leaked, full stream, mod menu, free download,
  hacks/cheats, "official", "no copyright intended"/"fair use", giveaway bait, "not clickbait".
- Don't use song titles, artist names or other creators' brands unless they are actually in the clip.
- Emojis: 0–2 in titles, fine in captions.

## Hashtag research (do this for every clip)
Hashtags must describe **this clip's moment**, not the stream in general. Ten clips from one stream
must have ten different hashtag sets. `dakie package` warns when a set is identical to another
clip's, when fewer than 2 tags are unique to the clip, or when fewer than 2 specific tags match words
actually said or shown in it.

1. **List what's in the clip** from its transcript (`dakie words`) and frames: the streamer, game
   characters (Jason, Lucia), places (Vice City, Leonida, the beach, the jewelry store), actions
   (robbery, police chase, boat fight, first drive), objects (baby, gold chain, helicopter), and the
   emotion (funny, fail, scared, shocked).
2. **Check real searches:** `dakie keywords "gta 6 <action>" "<streamer> gta 6" "gta 6 <place>"`
   prints YouTube's live autocomplete, which is what people actually type. Prefer phrases that
   appear there.
3. **Build the set, three layers:**
   - 1–2 **broad** tags for reach: `#GTA6`, `#GTAVI` (the only tags all clips may share);
   - 1 **streamer** tag: `#KaiCenat`;
   - 2–4 **moment** tags from steps 1–2 that no other clip uses: `#GTA6Robbery #GoldChain`,
     `#GTA6Boat #BoatFight`, `#GTA6Baby #FirstDrive`. CamelCase them so they read well.
4. **Per platform:**
   - YouTube Shorts: 3–5 in the description (the first 3 show above the title); `#Shorts` optional.
     Put the moment keywords in the `tags` list too (8–15 search phrases from step 2).
   - TikTok: 3–6; TikTok search reads the caption, so also write the main keyword phrase into the
     caption sentence.
   - Instagram Reels: 3–5 (more doesn't help); keyword phrase in the first 125 characters.
   - Facebook Reels: 2–5, plain and readable.
5. Never use unrelated trending tags (#fyp spam, other games, other streamers) or anything in the
   banned-wording list. Misleading tags hurt reach and break platform spam rules.

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
Each video is 50–60 seconds, which every platform treats as a Short/Reel, and short clips get the
highest completion rates. Hook in the first second, payoff before the end, and a loopable ending
(cut right after the punchline) helps replays.
