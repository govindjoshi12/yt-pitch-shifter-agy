import os
import shutil
import base64
import logging
from pathlib import Path
from typing import Optional
import imageio_ffmpeg

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
ORIGINALS_DIR = CACHE_DIR / "originals"
TRANSPOSED_DIR = CACHE_DIR / "transposed"

ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
TRANSPOSED_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
NODE_PATH = shutil.which("node") or ("/opt/homebrew/bin/node" if os.path.exists("/opt/homebrew/bin/node") else None)

MIN_PITCH_SEMITONES = -12
MAX_PITCH_SEMITONES = 12

# Optional proxy for datacenter deployments
YOUTUBE_PROXY = os.getenv("YOUTUBE_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")

def get_cookies_file_path() -> Optional[Path]:
    """
    Resolves the cookies.txt path for yt-dlp.
    Supports:
    1. YOUTUBE_COOKIES_FILE env var
    2. Render Secret File at /etc/secrets/cookies.txt
    3. cookies.txt in backend/ or root/
    4. YOUTUBE_COOKIES_BASE64 env var
    5. YOUTUBE_COOKIES env var (raw text)
    """
    # 1. Explicit environment path
    env_path = os.getenv("YOUTUBE_COOKIES_FILE")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # 2. Render Secret Files standard path
    render_secret = Path("/etc/secrets/cookies.txt")
    if render_secret.exists():
        return render_secret

    # 3. Base64 environment variable (prevents newline corruption in Render dashboard)
    b64_cookies = os.getenv("YOUTUBE_COOKIES_BASE64")
    if b64_cookies:
        try:
            decoded = base64.b64decode(b64_cookies.strip()).decode("utf-8")
            cookie_file = CACHE_DIR / "cookies.txt"
            cookie_file.write_text(decoded, encoding="utf-8")
            return cookie_file
        except Exception as e:
            logger.warning(f"Failed to decode YOUTUBE_COOKIES_BASE64: {e}")

    # 4. Raw string environment variable
    raw_cookies = os.getenv("YOUTUBE_COOKIES")
    if raw_cookies:
        try:
            cookie_file = CACHE_DIR / "cookies.txt"
            cookie_file.write_text(raw_cookies, encoding="utf-8")
            return cookie_file
        except Exception as e:
            logger.warning(f"Failed to write YOUTUBE_COOKIES: {e}")

    # 5. Local file in project
    local_backend = BASE_DIR / "cookies.txt"
    if local_backend.exists():
        return local_backend
    local_root = BASE_DIR.parent / "cookies.txt"
    if local_root.exists():
        return local_root

    return None
