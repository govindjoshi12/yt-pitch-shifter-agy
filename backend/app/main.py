import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

from app.config import (
    ORIGINALS_DIR,
    TRANSPOSED_DIR,
    MIN_PITCH_SEMITONES,
    MAX_PITCH_SEMITONES,
)
from app.services.youtube import (
    get_video_metadata,
    download_audio_track,
    get_cached_metadata,
    extract_video_id,
)
from app.services.audio import process_pitch_shift, sanitize_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("yt-pitch-shifter")

app = FastAPI(
    title="YouTube to MP3 with Pitch Shifter",
    description="Backend API for downloading YouTube audio and transposing pitch without tempo changes",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PrepareRequest(BaseModel):
    url: str

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/info")
async def get_info(url: str = Query(..., description="YouTube video URL")):
    """
    Retrieves video metadata (title, duration, thumbnail, author)
    without downloading the entire audio stream.
    """
    try:
        meta = get_video_metadata(url)
        video_id = meta["id"]
        # Check if already cached on disk
        mp3_path = ORIGINALS_DIR / f"{video_id}.mp3"
        meta["is_cached"] = mp3_path.exists() and mp3_path.stat().st_size > 0
        return meta
    except Exception as e:
        logger.error(f"Error fetching info: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/prepare")
async def prepare_audio(req: PrepareRequest):
    """
    Downloads and extracts original audio into cache if not already present.
    Returns metadata and audio stream availability.
    """
    try:
        meta = download_audio_track(req.url)
        return {
            "status": "ready",
            "metadata": meta,
            "stream_url": f"/api/stream/{meta['id']}"
        }
    except Exception as e:
        logger.error(f"Error preparing audio: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream/{video_id}")
async def stream_audio(video_id: str):
    """
    Streams the raw original audio file with HTTP Range support for audio seeking.
    """
    audio_path = ORIGINALS_DIR / f"{video_id}.mp3"
    if not audio_path.exists() or audio_path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail="Audio track not found. Please prepare the audio first.")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"}
    )

@app.get("/api/download")
async def download_mp3(
    video_id: str = Query(..., description="YouTube video ID"),
    pitch: int = Query(0, ge=MIN_PITCH_SEMITONES, le=MAX_PITCH_SEMITONES, description="Transposition in semitones (-12 to +12)")
):
    """
    Transposes audio pitch by specified semitones (without changing tempo)
    and streams the resulting MP3 file with proper attachment headers.
    """
    try:
        processed_path = process_pitch_shift(video_id, pitch)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing pitch shift for {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process pitch shift: {str(e)}")

    # Retrieve video title for filename
    meta = get_cached_metadata(video_id)
    title = meta.get("title", video_id) if meta else video_id
    
    pitch_label = f"{pitch:+d}st" if pitch != 0 else "original"
    download_filename = f"{sanitize_filename(title)} [{pitch_label}].mp3"

    return FileResponse(
        path=str(processed_path),
        media_type="audio/mpeg",
        filename=download_filename,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'}
    )

# Mount frontend directory for static serving
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
