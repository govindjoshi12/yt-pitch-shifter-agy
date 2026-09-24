import os
import subprocess
import logging
from pathlib import Path
from typing import Optional
import numpy as np
from pedalboard import Pedalboard, PitchShift
from pedalboard.io import AudioFile

from app.config import (
    ORIGINALS_DIR,
    TRANSPOSED_DIR,
    FFMPEG_PATH,
    MIN_PITCH_SEMITONES,
    MAX_PITCH_SEMITONES,
)

logger = logging.getLogger(__name__)

def sanitize_filename(name: str) -> str:
    """
    Sanitizes string for use in HTTP Content-Disposition filename.
    """
    clean = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", ".", "(", ")", "[", "]"))
    return clean.strip() or "audio"

def get_transposed_path(video_id: str, semitones: int) -> Path:
    sign = "+" if semitones > 0 else ""
    return TRANSPOSED_DIR / f"{video_id}_pitch_{sign}{semitones}.mp3"

def shift_audio_with_pedalboard(input_path: Path, output_path: Path, semitones: int) -> None:
    """
    Shifts audio pitch using Spotify's Pedalboard (Rubber Band DSP).
    Preserves original tempo with studio mastering quality.
    """
    logger.info(f"Pitch shifting with Pedalboard: {input_path} by {semitones} semitones")
    with AudioFile(str(input_path)) as f:
        audio = f.read(f.frames)
        sr = f.samplerate

    board = Pedalboard([PitchShift(semitones=float(semitones))])
    shifted = board(audio, sr)

    # Write output mp3
    temp_output = output_path.with_suffix(".tmp.mp3")
    with AudioFile(str(temp_output), "w", sr, shifted.shape[0]) as f:
        f.write(shifted)

    temp_output.replace(output_path)

def shift_audio_with_ffmpeg(input_path: Path, output_path: Path, semitones: int) -> None:
    """
    Fallback pitch shifter using FFmpeg's asetrate + atempo filters.
    """
    logger.info(f"Pitch shifting with FFmpeg fallback: {input_path} by {semitones} semitones")
    ratio = 2.0 ** (semitones / 12.0)
    tempo_corr = 1.0 / ratio

    # Sample rate assumed at 44100
    filter_chain = f"asetrate=44100*{ratio:.6f},aresample=44100,atempo={tempo_corr:.6f}"

    temp_output = output_path.with_suffix(".tmp.mp3")
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(input_path),
        "-filter:a", filter_chain,
        "-b:a", "192k",
        str(temp_output)
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error(f"FFmpeg pitch shifting failed: {result.stderr}")
        raise RuntimeError(f"FFmpeg error: {result.stderr}")

    temp_output.replace(output_path)

def process_pitch_shift(video_id: str, semitones: int) -> Path:
    """
    Takes an existing video_id from cache, verifies pitch is in [-12, 12],
    and produces/returns the transposed MP3 file path.
    """
    if not (MIN_PITCH_SEMITONES <= semitones <= MAX_PITCH_SEMITONES):
        raise ValueError(f"Pitch transposition must be between {MIN_PITCH_SEMITONES} and {MAX_PITCH_SEMITONES} semitones.")

    original_file = ORIGINALS_DIR / f"{video_id}.mp3"
    if not original_file.exists() or original_file.stat().st_size == 0:
        raise FileNotFoundError(f"Audio file for video '{video_id}' not found in cache.")

    # 0 semitones requires no pitch shift
    if semitones == 0:
        return original_file

    transposed_file = get_transposed_path(video_id, semitones)
    if transposed_file.exists() and transposed_file.stat().st_size > 0:
        logger.info(f"Returning cached transposed file: {transposed_file}")
        return transposed_file

    # Attempt with pedalboard first; fallback to ffmpeg if needed
    try:
        shift_audio_with_pedalboard(original_file, transposed_file, semitones)
    except Exception as e:
        logger.warning(f"Pedalboard processing error: {e}. Falling back to FFmpeg.")
        shift_audio_with_ffmpeg(original_file, transposed_file, semitones)

    return transposed_file
