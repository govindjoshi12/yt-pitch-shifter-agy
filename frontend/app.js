/**
 * YouTube to MP3 Pitch Shifter - Client Application
 */

const INTERVAL_NAMES = {
  "-12": "Octave Down (-12 st)",
  "-11": "Major 7th Down (-11 st)",
  "-10": "Minor 7th Down (-10 st)",
  "-9": "Major 6th Down (-9 st)",
  "-8": "Minor 6th Down (-8 st)",
  "-7": "Perfect 5th Down (-7 st)",
  "-6": "Tritone Down (-6 st)",
  "-5": "Perfect 4th Down (-5 st)",
  "-4": "Major 3rd Down (-4 st)",
  "-3": "Minor 3rd Down (-3 st)",
  "-2": "Major 2nd Down (-2 st)",
  "-1": "Minor 2nd Down (-1 st)",
  "0": "Original Key (0 st)",
  "1": "Minor 2nd Up (+1 st)",
  "2": "Major 2nd Up (+2 st)",
  "3": "Minor 3rd Up (+3 st)",
  "4": "Major 3rd Up (+4 st)",
  "5": "Perfect 4th Up (+5 st)",
  "6": "Tritone Up (+6 st)",
  "7": "Perfect 5th Up (+7 st)",
  "8": "Minor 6th Up (+8 st)",
  "9": "Major 6th Up (+9 st)",
  "10": "Minor 7th Up (+10 st)",
  "11": "Major 7th Up (+11 st)",
  "12": "Octave Up (+12 st)",
};

// State
let currentPitch = 0;
let currentVideoId = null;
let currentMetadata = null;
let isPlaying = false;
let isAudioLoaded = false;
let playbackOffset = 0;
let playbackStartTime = 0;
let animationFrameId = null;

// Tone.js nodes
let playerNode = null;
let pitchShiftNode = null;
let volumeNode = null;

// DOM Elements
const urlForm = document.getElementById("urlForm");
const youtubeUrlInput = document.getElementById("youtubeUrl");
const clearBtn = document.getElementById("clearBtn");
const loadBtn = document.getElementById("loadBtn");
const loadingState = document.getElementById("loadingState");
const loadingText = document.getElementById("loadingText");
const errorState = document.getElementById("errorState");
const errorMessage = document.getElementById("errorMessage");

const playerCard = document.getElementById("playerCard");
const videoThumb = document.getElementById("videoThumb");
const videoTitle = document.getElementById("videoTitle");
const videoUploader = document.getElementById("videoUploader");
const videoDuration = document.getElementById("videoDuration");

const pitchDownBtn = document.getElementById("pitchDownBtn");
const pitchUpBtn = document.getElementById("pitchUpBtn");
const pitchResetBtn = document.getElementById("pitchResetBtn");
const pitchValueEl = document.getElementById("pitchValue");
const pitchIntervalEl = document.getElementById("pitchInterval");

const playPauseBtn = document.getElementById("playPauseBtn");
const playIcon = document.getElementById("playIcon");
const pauseIcon = document.getElementById("pauseIcon");
const playerStateText = document.getElementById("playerStateText");
const seekSlider = document.getElementById("seekSlider");
const currentTimeEl = document.getElementById("currentTime");
const totalTimeEl = document.getElementById("totalTime");
const volumeSlider = document.getElementById("volumeSlider");
const muteBtn = document.getElementById("muteBtn");

const downloadBtn = document.getElementById("downloadBtn");
const downloadBtnText = document.getElementById("downloadBtnText");

// Format seconds into mm:ss
function formatTime(secs) {
  if (isNaN(secs) || secs < 0) return "0:00";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

// Show/Hide Errors
function showError(msg) {
  errorMessage.textContent = msg;
  errorState.hidden = false;
}

function clearError() {
  errorState.hidden = true;
  errorMessage.textContent = "";
}

// Input clear button toggle
youtubeUrlInput.addEventListener("input", () => {
  clearBtn.hidden = !youtubeUrlInput.value;
  clearError();
});

clearBtn.addEventListener("click", () => {
  youtubeUrlInput.value = "";
  clearBtn.hidden = true;
  youtubeUrlInput.focus();
});

// Update Pitch UI & Tone.js Node
function updatePitch(newPitch) {
  currentPitch = Math.max(-12, Math.min(12, newPitch));
  
  // UI Display
  const sign = currentPitch > 0 ? "+" : "";
  pitchValueEl.textContent = `${sign}${currentPitch}`;
  pitchIntervalEl.textContent = INTERVAL_NAMES[currentPitch.toString()] || `${currentPitch} semitones`;
  
  // Buttons disable state
  pitchDownBtn.disabled = currentPitch <= -12;
  pitchUpBtn.disabled = currentPitch >= 12;

  // Download button text
  if (currentPitch === 0) {
    downloadBtnText.textContent = "Download MP3 (Original)";
  } else {
    downloadBtnText.textContent = `Download MP3 (${sign}${currentPitch} st)`;
  }

  // Real-time audio pitch node update
  if (pitchShiftNode) {
    pitchShiftNode.pitch = currentPitch;
  }
}

pitchDownBtn.addEventListener("click", () => updatePitch(currentPitch - 1));
pitchUpBtn.addEventListener("click", () => updatePitch(currentPitch + 1));
pitchResetBtn.addEventListener("click", () => updatePitch(0));

// Audio Engine Setup
function setupAudioEngine(streamUrl) {
  return new Promise((resolve, reject) => {
    try {
      playerStateText.textContent = "Loading audio stream into memory...";

      // Clean up previous nodes
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      if (playerNode) {
        try { playerNode.stop(); playerNode.dispose(); } catch (e) {}
      }
      if (pitchShiftNode) {
        try { pitchShiftNode.dispose(); } catch (e) {}
      }

      // Initialize Tone.js PitchShift & Volume
      pitchShiftNode = new Tone.PitchShift({
        pitch: currentPitch,
        windowSize: 0.1, // Optimal for preserving tempo & rhythm
      });

      volumeNode = new Tone.Volume(Tone.gainToDb(parseFloat(volumeSlider.value)));
      pitchShiftNode.chain(volumeNode, Tone.Destination);

      playerNode = new Tone.Player({
        url: streamUrl,
        autostart: false,
        onload: () => {
          isAudioLoaded = true;
          const dur = playerNode.buffer.duration;
          seekSlider.max = dur;
          totalTimeEl.textContent = formatTime(dur);
          playerStateText.textContent = "Ready to preview";
          updatePlayState(false);
          resolve();
        },
        onerror: (err) => {
          console.error("Tone.Player load error:", err);
          reject(new Error("Failed to load and decode audio stream."));
        },
        onstop: () => {
          if (isPlaying) {
            const currentPos = getCurrentPlaybackPosition();
            if (currentPos >= playerNode.buffer.duration - 0.2) {
              playbackOffset = 0;
              updatePlayState(false);
              seekSlider.value = 0;
              currentTimeEl.textContent = "0:00";
            }
          }
        }
      }).connect(pitchShiftNode);

    } catch (err) {
      console.error("Audio engine setup error:", err);
      reject(err);
    }
  });
}

function getCurrentPlaybackPosition() {
  if (!playerNode || !playerNode.buffer) return 0;
  if (!isPlaying) return playbackOffset;
  const elapsed = Tone.now() - playbackStartTime;
  return Math.min(playbackOffset + elapsed, playerNode.buffer.duration);
}

function updatePlayState(playing) {
  isPlaying = playing;
  if (playing) {
    playIcon.hidden = true;
    pauseIcon.hidden = false;
    playerStateText.textContent = `Playing (${currentPitch >= 0 ? "+" : ""}${currentPitch} st)`;
    startProgressLoop();
  } else {
    playIcon.hidden = false;
    pauseIcon.hidden = true;
    playerStateText.textContent = "Paused";
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
  }
}

function startProgressLoop() {
  const updateProgress = () => {
    if (isPlaying && playerNode && playerNode.buffer) {
      const pos = getCurrentPlaybackPosition();
      seekSlider.value = pos;
      currentTimeEl.textContent = formatTime(pos);
      animationFrameId = requestAnimationFrame(updateProgress);
    }
  };
  animationFrameId = requestAnimationFrame(updateProgress);
}

async function togglePlay() {
  if (!isAudioLoaded || !playerNode) return;
  await Tone.start();

  if (isPlaying) {
    playbackOffset = getCurrentPlaybackPosition();
    playerNode.stop();
    updatePlayState(false);
  } else {
    const dur = playerNode.buffer.duration;
    if (playbackOffset >= dur - 0.1) {
      playbackOffset = 0;
    }
    playbackStartTime = Tone.now();
    playerNode.start(undefined, playbackOffset);
    updatePlayState(true);
  }
}

playPauseBtn.addEventListener("click", togglePlay);

// Seeking
seekSlider.addEventListener("input", (e) => {
  const targetTime = parseFloat(e.target.value);
  currentTimeEl.textContent = formatTime(targetTime);
  if (isPlaying) {
    playerNode.stop();
    playbackOffset = targetTime;
    playbackStartTime = Tone.now();
    playerNode.start(undefined, playbackOffset);
  } else {
    playbackOffset = targetTime;
  }
});

// Volume control
volumeSlider.addEventListener("input", (e) => {
  const vol = parseFloat(e.target.value);
  if (volumeNode) {
    if (vol === 0) {
      volumeNode.mute = true;
    } else {
      volumeNode.mute = false;
      volumeNode.volume.value = Tone.gainToDb(vol);
    }
  }
});

let isMuted = false;
let prevVolume = 1;
muteBtn.addEventListener("click", () => {
  if (!volumeNode) return;
  isMuted = !isMuted;
  if (isMuted) {
    prevVolume = parseFloat(volumeSlider.value);
    volumeSlider.value = 0;
    volumeNode.mute = true;
  } else {
    volumeSlider.value = prevVolume > 0 ? prevVolume : 1;
    volumeNode.mute = false;
    volumeNode.volume.value = Tone.gainToDb(parseFloat(volumeSlider.value));
  }
});

// Handle Form Submission
urlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = youtubeUrlInput.value.trim();
  if (!url) return;

  clearError();
  loadingState.hidden = false;
  playerCard.hidden = true;
  loadingText.textContent = "Connecting to YouTube...";
  loadBtn.disabled = true;

  try {
    // 1. Fetch info and prepare audio track on backend
    loadingText.textContent = "Downloading & preparing audio from YouTube...";
    const response = await fetch("/api/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Server responded with status ${response.status}`);
    }

    const data = await response.json();
    currentMetadata = data.metadata;
    currentVideoId = currentMetadata.id;

    // 2. Display metadata
    videoThumb.src = currentMetadata.thumbnail || "";
    videoTitle.textContent = currentMetadata.title;
    videoUploader.textContent = currentMetadata.uploader;
    videoDuration.textContent = currentMetadata.duration_str;

    // Reset pitch to 0 for new video
    updatePitch(0);
    playbackOffset = 0;
    seekSlider.value = 0;
    currentTimeEl.textContent = "0:00";

    // 3. Load audio stream into Tone.js
    loadingText.textContent = "Initializing real-time pitch processor...";
    await setupAudioEngine(`/api/stream/${currentVideoId}`);

    // Finished loading: show player, hide spinner, re-enable button
    loadingState.hidden = true;
    playerCard.hidden = false;
    loadBtn.disabled = false;

  } catch (err) {
    console.error("Preparation error:", err);
    showError(err.message || "Failed to load audio from the provided YouTube link.");
    loadingState.hidden = true;
    playerCard.hidden = true;
    loadBtn.disabled = false;
  }
});

// Download high-quality MP3 from Backend
downloadBtn.addEventListener("click", async () => {
  if (!currentVideoId) return;

  const originalBtnText = downloadBtnText.textContent;
  downloadBtn.disabled = true;
  downloadBtnText.textContent = "Rendering studio-grade MP3...";

  try {
    const downloadUrl = `/api/download?video_id=${encodeURIComponent(currentVideoId)}&pitch=${currentPitch}`;
    
    // Trigger download
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", "");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => {
      downloadBtn.disabled = false;
      downloadBtnText.textContent = originalBtnText;
    }, 2500);

  } catch (err) {
    console.error("Download error:", err);
    showError("Download failed: " + err.message);
    downloadBtn.disabled = false;
    downloadBtnText.textContent = originalBtnText;
  }
});
