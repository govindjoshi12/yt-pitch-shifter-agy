import pytest
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
from pedalboard.io import AudioFile

from app.main import app
from app.config import ORIGINALS_DIR, TRANSPOSED_DIR

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_static_frontend_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "PitchShift" in response.text
    assert "pitchDownBtn" in response.text

def test_pitch_shift_and_download_synthetic():
    # Create a synthetic 1-second test audio file in ORIGINALS_DIR
    test_video_id = "test_synth_123"
    test_mp3 = ORIGINALS_DIR / f"{test_video_id}.mp3"
    
    sr = 44100
    t = np.linspace(0, 1, sr, False)
    audio = np.vstack([np.sin(2 * np.pi * 440 * t), np.sin(2 * np.pi * 440 * t)]).astype(np.float32)
    
    with AudioFile(str(test_mp3), "w", sr, 2) as f:
        f.write(audio)

    # Test download with pitch +3
    response = client.get(f"/api/download?video_id={test_video_id}&pitch=3")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 0
    
    # Check that transposed file was created
    expected_transposed = TRANSPOSED_DIR / f"{test_video_id}_pitch_+3.mp3"
    assert expected_transposed.exists()

    # Clean up test files
    test_mp3.unlink(missing_ok=True)
    expected_transposed.unlink(missing_ok=True)

def test_pitch_bounds_validation():
    response = client.get("/api/download?video_id=fake&pitch=13")
    assert response.status_code == 422 # Validation error for > 12

    response = client.get("/api/download?video_id=fake&pitch=-13")
    assert response.status_code == 422 # Validation error for < -12

def test_cookies_resolution_from_env(monkeypatch):
    import base64
    from app.config import get_cookies_file_path, CACHE_DIR

    fake_cookie_content = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t2147483647\tTEST\t123"
    b64_content = base64.b64encode(fake_cookie_content.encode("utf-8")).decode("utf-8")
    
    monkeypatch.setenv("YOUTUBE_COOKIES_BASE64", b64_content)
    cookie_path = get_cookies_file_path()
    assert cookie_path is not None
    assert cookie_path.exists()
    assert cookie_path.read_text(encoding="utf-8") == fake_cookie_content

