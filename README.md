# Dakie Clips

A [Claude Code](https://claude.com/claude-code) skill that turns a GTA 6 livestream (YouTube,
Twitch, Kick and other sites [yt-dlp](https://github.com/yt-dlp/yt-dlp) supports) into five
3-minute vertical clips for YouTube Shorts, TikTok, Instagram Reels and Facebook Reels.

```
dakie_clips https://www.youtube.com/watch?v=...
```

Claude checks the stream's reuse rights, finds and ranks the 10 best moments, **waits for you to
approve 5**, then edits them and writes the titles, descriptions and hashtags for each platform.

## What the videos look like
- **Top 45%:** hydraulic press footage (an original generated loop, or licensed clips you add)
- **Bottom 55%:** the gameplay, with the streamer's webcam tracked and placed bottom-right
- **Title** in a white rounded box for the whole video, e.g. "Speed meets his workmates at GTA 6!! Damn!"
- **Word-by-word captions** on the seam between the panels, with the spoken word in yellow
- A 2–3 s cold-open teaser of the payoff, zoom punch-ins, sound effects, audio leveled to −14 LUFS
- Exactly 3:00, 1080×1920, 30 fps

## How it works
1. **Rights check** (`dakie init`): license, members-only/live status, "no clipping" or
   "clips welcome" notices. It stops and asks you unless reuse is clearly allowed.
2. **Scan** (`dakie scan`): chat replay, viewer comments that cite timestamps, a loudness curve, and
   a transcript (platform captions, or local Whisper).
3. **Rank** (`dakie candidates`): scores every moment from chat spikes ("CLIP IT", KEKW, LMAO),
   comment timestamps, volume spikes and excited speech. Claude reads the transcript and picks the
   top 10, then **stops for your approval of 5**.
4. **Edit** (`dakie prepare` / `dakie render`): downloads only the approved sections, transcribes
   word-by-word, finds and tracks the webcam, and renders with ffmpeg.
5. **Package** (`dakie package`): validates the metadata for each platform (lengths, hashtags,
   streamer credit, risky wording) and writes a copyright checklist per clip.

## Install (macOS)
**You need:** a Mac (tested on Apple Silicon; Windows and Linux are not supported),
[Claude Code](https://claude.com/claude-code) (the Claude desktop app's Code tab or the `claude`
terminal app), and about 3 GB of free disk space. No Homebrew or admin password is needed:
everything goes into a private Python environment in `~/.dakie_clips`.

### Option A: with git (easiest to update)
Open **Terminal** and run:

```bash
git clone https://github.com/raycreatesbuzzness-dakie/dakie-clips ~/.claude/skills/dakie-clips
sh ~/.claude/skills/dakie-clips/install.sh
```

> **First time using developer tools on this Mac?** `git clone` opens a popup asking to install
> the **Command Line Tools**. Click **Install**, wait for it to finish, then run the commands again.

### Option B: from the ZIP
1. On this page click **Code → Download ZIP** (or use a zip someone shared with you) and unzip it.
2. **Rename the folder to exactly `dakie-clips`.** GitHub's ZIP unpacks as `dakie-clips-main`,
   and the skill won't load under that name.
3. Move the folder into `~/.claude/skills/`. In Finder press **⌘⇧G** and type `~/.claude/skills`.
   If the folder doesn't exist yet, create it first in Terminal: `mkdir -p ~/.claude/skills`
4. Run the installer in Terminal:
   ```bash
   sh ~/.claude/skills/dakie-clips/install.sh
   ```

The installer takes about 5–10 minutes and ends with a checklist where every line should say `ok`.

### Start clipping
Open a **new** Claude Code session and type:

```
dakie_clips https://www.youtube.com/watch?v=...
```

Finished videos land in `~/DakieClips/projects/<stream>/final/`, one folder per clip with the video,
cover image, `captions.srt` and `metadata.md` (copy-paste titles, descriptions and hashtags).
The first clip takes longer because the speech-recognition models download on first use.

### Troubleshooting
- **`dakie_clips` does nothing:** check that `~/.claude/skills/dakie-clips/SKILL.md` exists (folder
  named exactly `dakie-clips`), then start a new session.
- **YouTube says "sign in to confirm you're not a bot":** set `"cookies_from_browser": "chrome"`
  (or `"safari"`) in `~/DakieClips/config.json`.
- **Updating:** `cd ~/.claude/skills/dakie-clips && git pull`, then run `install.sh` again.
  ZIP installs: replace the folder with the new download.

The installer sets up Python 3.12 (via [uv](https://github.com/astral-sh/uv)), yt-dlp, ffmpeg
(via imageio-ffmpeg), faster-whisper, OpenCV and chat-downloader, then builds the sound-effect and
press-footage libraries in `~/DakieClips/`. It links the `dakie` command to `~/.local/bin/dakie`.

## Commands
| command | what it does |
|---|---|
| `dakie doctor` | check the installed tools |
| `dakie init <url>` | create a project and run the rights check |
| `dakie scan <project>` | chat replay, comment timestamps, loudness, transcript |
| `dakie candidates <project>` | rank candidate moments → `analysis/candidates.md` |
| `dakie text <project> <from> <to> [--compact 60]` | print the transcript for a range |
| `dakie prepare <project> <n> <start> <end>` | download a clip section, captions, face tracking |
| `dakie render <project> <n>` | render `clips/clip_NN/plan.json` → `final.mp4` |
| `dakie package <project> <n>` | validate metadata, copyright checklist, copy to `final/` |
| `dakie sfx list \| add \| suggest` | manage the sound-effects library |
| `dakie press list \| add \| generate` | manage the hydraulic press footage |

Layout, fonts, colors, clip length and Whisper models are set in `~/DakieClips/config.json`.

## Adding your own media
Sound effects and press clips **require a license** when you add them, so every video's copyright
checklist can list where each element came from:

```bash
dakie sfx add boom.wav --name big_boom --tags "impact,crash" --license "CC0" --source https://...
dakie press add press.mp4 --license "Pexels License" --source https://www.pexels.com/video/...
```

Good free sources: [Pexels](https://www.pexels.com/search/videos/hydraulic%20press/) and
[Pixabay](https://pixabay.com) for footage, [freesound.org](https://freesound.org) (CC0 filter) and
Pixabay for sounds. The 13 starter sound effects and the press animation are generated by the tool
itself, so you own them.

## Copyright: read this
The tool screens for risks but **cannot make another streamer's footage yours**. The gameplay,
voice and webcam belong to the streamer, so publish clips only with their permission (a clipping
program, Discord rules, or a direct OK). The checks are automated screens of public information,
not legal advice. Background music is the most common reason clips get claimed or muted; the tool
flags music-like audio so you can check it. See `references/copyright.md`.

## Credits
Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), [OpenCV](https://opencv.org),
[chat-downloader](https://github.com/xenova/chat-downloader) and [uv](https://github.com/astral-sh/uv).
Not affiliated with Rockstar Games, Take-Two, YouTube, Twitch, TikTok or Meta.

## License
MIT. See [LICENSE](LICENSE).
