import os
import shutil
from pathlib import Path
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
ORIGINALS_DIR = CACHE_DIR / "originals"
TRANSPOSED_DIR = CACHE_DIR / "transposed"

ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
TRANSPOSED_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
NODE_PATH = shutil.which("node") or "/opt/homebrew/bin/node"

MIN_PITCH_SEMITONES = -12
MAX_PITCH_SEMITONES = 12
