import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

from app.config import (
    ORIGINALS_DIR,
    FFMPEG_PATH,
    NODE_PATH,
    YOUTUBE_PROXY,
    get_cookies_file_path,
)

logger = logging.getLogger(__name__)

def _get_ydl_base_opts(use_cookies: bool = False) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_PATH,
    }

    # Proxy support
    if YOUTUBE_PROXY:
        opts["proxy"] = YOUTUBE_PROXY
        logger.info("Using configured proxy for YouTube extraction")

    # JavaScript runtime for signature challenges
    if NODE_PATH and os.path.exists(NODE_PATH):
        opts["js_runtimes"] = {"node": {"path": NODE_PATH}}

    # Cookie and Player Client Configuration
    cookies_path = get_cookies_file_path() if use_cookies else None
    if cookies_path and cookies_path.exists():
        opts["cookiefile"] = str(cookies_path)
        logger.info(f"Using cookies file: {cookies_path}")
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["web", "mweb", "android"],
            }
        }
    else:
        # visionos client bypasses YouTube bot detection and PO-token challenges without cookies
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["visionos", "web"],
            }
        }

    return opts

def _handle_yt_error(e: Exception, action: str) -> None:
    err_msg = str(e)
    logger.error(f"Error {action}: {err_msg}")
    
    if "confirm you’re not a bot" in err_msg or "confirm you're not a bot" in err_msg or "Sign in to confirm" in err_msg:
        raise ValueError(
            "YouTube bot verification triggered on this server. "
            "Fix: The visionos client is automatically used, but if this video requires authentication, "
            "provide cookies via /etc/secrets/cookies.txt or YOUTUBE_COOKIES_BASE64."
        )
    raise ValueError(f"Failed to {action}: {err_msg}")

def extract_video_id(url: str) -> Optional[str]:
    """
    Extracts 11-character video ID from common YouTube URL patterns.
    """
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def _extract_metadata_with_opts(url: str, use_cookies: bool = False) -> Dict[str, Any]:
    opts = _get_ydl_base_opts(use_cookies=use_cookies)
    opts["extract_flat"] = False

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("No video information could be found.")

    video_id = info.get("id") or extract_video_id(url)
    duration = info.get("duration", 0)
    
    # Format duration to mm:ss or hh:mm:ss
    if duration:
        m, s = divmod(int(duration), 60)
        h, m = divmod(m, 60)
        duration_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
    else:
        duration_str = "Unknown"

    meta = {
        "id": video_id,
        "title": info.get("title", "Unknown Title"),
        "uploader": info.get("uploader") or info.get("channel", "Unknown Artist"),
        "duration": duration,
        "duration_str": duration_str,
        "thumbnail": info.get("thumbnail"),
        "original_url": info.get("webpage_url", url),
    }

    # Cache metadata JSON
    meta_path = ORIGINALS_DIR / f"{video_id}.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Could not cache metadata JSON: {e}")

    return meta

def get_video_metadata(url: str) -> Dict[str, Any]:
    """
    Fetches video metadata without downloading the full audio stream.
    Tries visionos client first (cookie-free bot bypass), falls back to cookies if configured.
    """
    try:
        return _extract_metadata_with_opts(url, use_cookies=False)
    except Exception as e:
        if get_cookies_file_path():
            logger.info("Attempting metadata extraction with cookies fallback...")
            try:
                return _extract_metadata_with_opts(url, use_cookies=True)
            except Exception as e2:
                _handle_yt_error(e2, "fetching video information")
        _handle_yt_error(e, "fetching video information")

def get_cached_metadata(video_id: str) -> Optional[Dict[str, Any]]:
    meta_path = ORIGINALS_DIR / f"{video_id}.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def _download_with_opts(download_url: str, video_id: str, use_cookies: bool = False) -> Dict[str, Any]:
    expected_mp3 = ORIGINALS_DIR / f"{video_id}.mp3"

    opts = _get_ydl_base_opts(use_cookies=use_cookies)
    opts.update({
        "format": "bestaudio/best",
        "outtmpl": str(ORIGINALS_DIR / f"{video_id}.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    })

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(download_url, download=True)

    video_id = info.get("id", video_id)
    duration = info.get("duration", 0)
    if duration:
        m, s = divmod(int(duration), 60)
        h, m = divmod(m, 60)
        duration_str = f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
    else:
        duration_str = "Unknown"

    meta = {
        "id": video_id,
        "title": info.get("title", "Unknown Title"),
        "uploader": info.get("uploader") or info.get("channel", "Unknown Artist"),
        "duration": duration,
        "duration_str": duration_str,
        "thumbnail": info.get("thumbnail"),
        "original_url": info.get("webpage_url", download_url),
        "file_path": str(expected_mp3),
    }

    # Cache metadata JSON
    meta_path = ORIGINALS_DIR / f"{video_id}.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return meta

def download_audio_track(url_or_id: str) -> Dict[str, Any]:
    """
    Downloads and extracts original audio as MP3 if not already in cache.
    Returns metadata dict including the path to the MP3 file.
    Tries visionos client first (bypasses cloud IP bot check without cookies),
    then falls back to cookies if needed.
    """
    video_id = extract_video_id(url_or_id) or url_or_id
    expected_mp3 = ORIGINALS_DIR / f"{video_id}.mp3"

    # If already downloaded and cached, return immediately
    cached_meta = get_cached_metadata(video_id)
    if expected_mp3.exists() and expected_mp3.stat().st_size > 0:
        if cached_meta:
            cached_meta["file_path"] = str(expected_mp3)
            return cached_meta

    download_url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else url_or_id

    # 1. Try with visionos client (bypasses bot challenges on cloud IPs)
    try:
        return _download_with_opts(download_url, video_id, use_cookies=False)
    except Exception as e:
        # 2. If failed and cookies are present, retry with cookies
        if get_cookies_file_path():
            logger.info("Attempting audio download with cookies fallback...")
            try:
                return _download_with_opts(download_url, video_id, use_cookies=True)
            except Exception as e2:
                _handle_yt_error(e2, "downloading audio from YouTube")
        _handle_yt_error(e, "downloading audio from YouTube")
