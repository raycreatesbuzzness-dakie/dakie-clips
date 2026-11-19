# Copyright rules Dakie Clips applies

This is a risk screen, not legal advice. Be direct with the user about what the tool can and
cannot guarantee.

## What Dakie owns vs. doesn't
| element | owner | status |
|---|---|---|
| Hydraulic press footage (`generated_press_*.mp4`) | Dakie: generated from scratch by the pipeline | ✅ safe |
| Starter sound effects (synthesized) | Dakie: generated from scratch | ✅ safe |
| Added SFX/press clips | whoever the recorded license says | ✅ only if the license is recorded and allows commercial reuse |
| Captions, hooks, titles, descriptions | Dakie (original writing + transcription of speech) | ✅ |
| Fonts | macOS system fonts (Impact/Arial Black) rendered into video | ✅ |
| **Streamer's gameplay, voice and webcam** | **the streamer** | ⚠️ needs permission |
| **GTA 6 game footage/music** | Rockstar Games/Take-Two | ⚠️ gameplay videos generally tolerated; in-game licensed radio is not |
| Background music on stream | the music rights holders | ❌ main cause of claims and mutes |

**The final video can never be 100% Dakie's own** because the core footage belongs to the
streamer. Combining it with original elements doesn't transfer ownership. Say this plainly
whenever the user asks whether a clip is "safe" or "owned".

## Rights levels (from `dakie init`)
- **GREEN:** Creative Commons license, or the description explicitly invites clipping. Still keep a
  screenshot/link of the permission and follow its terms (credit format, monetization rules).
- **YELLOW:** standard license, no permission found. Proceeding is the user's decision; tell them
  to get permission first (many big streamers run clipping programs or allow clips via Discord rules).
- **RED:** live right now, members-only/private, or the creator forbids clipping/reuploads. Do not
  continue unless the user says they have written permission.

## Platform-specific risks to report
- **YouTube Shorts > 1 minute with an active Content ID claim get blocked worldwide.** Our clips are
  3 minutes, so any copyrighted music in a clip means a blocked Short. Treat music risk as serious.
- TikTok/Instagram/Facebook mute or remove videos with detected copyrighted audio; repeat
  matches can restrict the account.
- Streamers can file takedowns (DMCA) for unauthorized reuploads; three YouTube copyright
  strikes terminate a channel.
- Reused-content policies: YouTube's monetization and TikTok's Creator Rewards penalize clips with
  little original contribution. The hook, captions, edit, sound design and commentary-style
  captions are the transformation; don't skip them.

## Checks Claude must do
1. Phase 1: report the rights level and every issue before downloading video.
2. Phase 2: avoid music-risk HIGH windows; mention MEDIUM ones.
3. Phase 3: read `prep.json → music_risk_windows`; if a window falls in the clip, tell the user the
   timestamps to listen to, or move `main_start` to avoid it.
4. Phase 4: `copyright_check.md` per clip must have no 🔴. Report every 🟡 to the user.
5. Never put song lyrics, song titles, other creators' trademarks or "no copyright intended"
   disclaimers into captions, hooks or metadata.
6. Never add SFX or press footage without a known license.
