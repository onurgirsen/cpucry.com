#!/usr/bin/env bash
# Rebuild "A History of Tomorrow" from source: frames (headless Chromium) + soundtrack (numpy) → MP4.
# Needs: node + playwright (Chromium), python3 with numpy/scipy/pyloudnorm, ffmpeg with libx264.
set -euo pipefail
cd "$(dirname "$0")"
node render.cjs --cues                 # scene timing → build/cues.json
python3 music.py                        # → build/music.wav
node render.cjs --frames --workers "${WORKERS:-4}"   # → build/frames/*.jpg
ffmpeg -y -framerate 30 -i build/frames/f_%06d.jpg -i build/music.wav \
  -c:v libx264 -preset slow -crf "${CRF:-23}" -pix_fmt yuv420p -profile:v high -level 4.1 \
  -movflags +faststart -c:a aac -b:a 160k -shortest history-of-tomorrow.mp4
