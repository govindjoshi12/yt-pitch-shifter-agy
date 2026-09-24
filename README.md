# 🎵 YouTube to MP3 Pitch Shifter

> [!NOTE]  
> ### ⚡ Vibe Coded Notice
> **This entire application was 100% vibe coded.**  
> Conceived, architected, implemented, and debugged through conversational AI pair programming. From zero lines of code to an implementation plan, Python FastAPI backend, Spotify Pedalboard / Rubber Band DSP pipeline, Web Audio API frontend, and real-time interval shifting—all driven purely by human intent and iterative AI generation.

---

A fast, responsive web application that lets you paste any YouTube link, load the audio, preview and shift its pitch in real-time inside your browser (**-12 to +12 semitones** without altering tempo), and export the resulting studio-grade MP3.

---

## ✨ Features

- **In-Browser Real-Time Preview**: Powered by Tone.js and the Web Audio API. Adjust the pitch and hear the transposition change instantaneously with zero buffering latency.
- **Pitch Stepper (-12 to +12 Semitones)**: Clean `[-]` and `[+]` stepper with dynamic musical interval badges (*e.g., Octave Down, Minor 3rd Up, Tritone, Original Key*).
- **Studio-Quality MP3 Export**: Backend renders using Spotify's `pedalboard` (C++ Rubber Band DSP) with FFmpeg fallback, preserving transients and tempo without robotic phasing.
- **Smart Audio Caching**: Downloaded originals and transposed tracks are cached locally under `backend/cache/` to avoid redundant YouTube requests.
- **Custom Player Controls**: Custom timeline scrubber, dynamic play/pause toggle, volume slider with mute button, and elapsed/total duration indicators.
- **Robust YouTube Extraction**: Configured with `yt-dlp` and local Node.js JavaScript challenge execution to maintain reliability against YouTube's anti-bot updates.

---

## 🏗️ Architecture

This app uses a **Hybrid Processing Model**:

```
                       ┌───────────────────────┐
                       │   YouTube Video URL   │
                       └───────────┬───────────┘
                                   │
                                   ▼
                       ┌───────────────────────┐
                       │    FastAPI Backend    │
                       │   (yt-dlp + Node JS)  │
                       └───────────┬───────────┘
                                   │
                                   ▼
                        Original MP3 Cached
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
         ▼                                                   ▼
┌───────────────────────────────┐           ┌────────────────────────────────┐
│       Frontend (Browser)      │           │         Backend Export         │
│  - Web Audio / Tone.js        │           │  - Spotify Pedalboard DSP      │
│  - Instant -12 to +12 preview │           │  - Studio MP3 rendering        │
│  - Zero round-trip delay      │           │  - Streams file to downloader  │
└───────────────────────────────┘           └────────────────────────────────┘
```

1. **Client-Side Real-Time Preview**: Audio is decoded into the browser's audio buffer and routed through a `Tone.PitchShift` node. Users hear instant transposition as they tap `+` or `-`.
2. **Server-Side High-Fidelity Rendering**: When the user clicks **Download MP3**, the server performs Rubber Band pitch processing and LAME MP3 encoding, ensuring maximum audio quality and eliminating browser memory limits on long tracks.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (Python 3.13 tested)
- **Node.js** (required by `yt-dlp` for YouTube's JavaScript challenge solver)

### 1. Launch the Server
Clone or enter the directory, then run the startup script:

```bash
./run.sh
```

*(This automatically creates the Python virtual environment in `.venv`, installs dependencies from `backend/requirements.txt`, and boots the server).*

Or start manually:
```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Run backend with static frontend mounted
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Open the App
Navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📖 How to Use

1. Paste any YouTube video, music, or shorts link into the input field.
2. Click **Load Audio**.
3. Use the **Play / Pause** button to start previewing.
4. Click **`+`** or **`-`** to shift the pitch up or down by semitones (or click **Reset (0)** to return to original).
5. Click **Download MP3** to export your transposed track.

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check endpoint (`{"status": "ok"}`) |
| `GET` | `/api/info?url={url}` | Extracts video title, duration, author, thumbnail |
| `POST` | `/api/prepare` | Downloads & caches original audio track from YouTube |
| `GET` | `/api/stream/{video_id}` | Streams audio with HTTP Range support for scrubbing |
| `GET` | `/api/download?video_id={id}&pitch={n}` | Renders pitch-shifted audio (-12 to +12 st) & downloads MP3 |

Interactive Swagger documentation is available at: **`http://localhost:8000/docs`**.

---

## 🧪 Testing

Run the automated integration and unit test suite:

```bash
source .venv/bin/activate
cd backend
pytest tests/test_backend.py -v
```

Tests verify:
- Health check route
- Static frontend asset delivery
- Pedalboard pitch shifting and MP3 generation on synthetic audio
- Semitone bounds validation (`-12 <= pitch <= 12`)

---

## 🗂️ Project Structure

```
yt-pitch-shifter/
├── backend/
│   ├── app/
│   │   ├── config.py           # Paths, cache directories, tool detection
│   │   ├── main.py             # FastAPI endpoints & static file serving
│   │   ├── services/
│   │   │   ├── audio.py        # Pedalboard / FFmpeg pitch transposition
│   │   │   └── youtube.py      # yt-dlp metadata & audio extractor
│   ├── cache/                  # Cached original & transposed audio tracks
│   ├── requirements.txt        # Backend Python dependencies
│   └── tests/
│       └── test_backend.py     # Backend test suite
├── frontend/
│   ├── index.html              # Modern semantic UI layout
│   ├── style.css               # Responsive dark-mode styling & spinner
│   ├── app.js                  # Audio playback & pitch shifting logic
│   └── tone.js                 # Local offline copy of Tone.js
├── run.sh                      # One-click startup script
└── README.md                   # Project documentation
```
