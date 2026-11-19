#!/bin/sh
# Dakie Clips installer: private Python 3.12 env + tools, no Homebrew or admin password needed.
set -e
ROOT="$HOME/.dakie_clips"
SKILL="$(cd "$(dirname "$0")" && pwd -P)"
mkdir -p "$ROOT" "$HOME/.local/bin"

if [ ! -x "$ROOT/bootstrap/bin/uv" ]; then
  /usr/bin/python3 -m venv "$ROOT/bootstrap"
  "$ROOT/bootstrap/bin/pip" -q install --upgrade pip uv
fi
UV="$ROOT/bootstrap/bin/uv"
"$UV" python install 3.12
[ -x "$ROOT/venv/bin/python" ] || "$UV" venv --python 3.12 "$ROOT/venv"
VIRTUAL_ENV="$ROOT/venv" "$UV" pip install --upgrade \
  "yt-dlp[default,curl-cffi]" deno imageio-ffmpeg faster-whisper "opencv-python-headless<5" numpy pillow chat-downloader

chmod +x "$SKILL/scripts/dakie_cli"
ln -sf "$SKILL/scripts/dakie_cli" "$HOME/.local/bin/dakie"
"$HOME/.local/bin/dakie" setup
"$HOME/.local/bin/dakie" doctor
echo
echo "Done. Update yt-dlp regularly (sites change): $0"
