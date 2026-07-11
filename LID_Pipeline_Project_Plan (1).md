# Continuous Spoken Language Identification (LID) Pipeline
## Complete 2-Month Engineering Project Plan

---

# TABLE OF CONTENTS

1. [Project Overview & Goals](#1-project-overview--goals)
2. [Complete Tech Stack](#2-complete-tech-stack)
3. [System Architecture Deep-Dive](#3-system-architecture-deep-dive)
4. [Environment Setup & Prerequisites](#4-environment-setup--prerequisites)
5. [Week-by-Week Master Plan](#5-week-by-week-master-plan)
   - Week 1: Foundation & Infrastructure
   - Week 2: Audio Ingestion & VAD
   - Week 3: Sliding Window Segmentation Engine
   - Week 4: LID Model Integration
   - Week 5: Smoothing, Output & JSON Schema
   - Week 6: API Layer & Service Integration
   - Week 7: Testing, Benchmarking & Optimization
   - Week 8: Deployment, Documentation & Launch
6. [Data Strategy & Dataset Preparation](#6-data-strategy--dataset-preparation)
7. [Testing Strategy](#7-testing-strategy)
8. [Monitoring & Observability](#8-monitoring--observability)
9. [Risk Register & Mitigation](#9-risk-register--mitigation)
10. [Team Roles & Responsibilities](#10-team-roles--responsibilities)
11. [Definition of Done](#11-definition-of-done)
12. [Appendix: File & Directory Structure](#12-appendix-file--directory-structure)

---

# 1. PROJECT OVERVIEW & GOALS

## 1.1 Problem Statement

Regional broadcasting — particularly in multilingual nations like India — frequently features live code-switching: a presenter may open in English, shift to Hindi for context, and deliver a punchline in Assamese, all within 30 seconds. Standard Speech-to-Text (STT) and Machine Translation (MT) models are built with a monolingual assumption. When fed multi-lingual audio they either hallucinate (fabricating text in a single language) or completely collapse.

This project builds an **orchestration backbone** — a modular, offline-capable ML pipeline that:

1. Ingests raw broadcast video
2. Extracts and pre-processes audio
3. Detects and timestamps every language switch with high precision
4. Emits a structured JSON payload that downstream systems (STT routers, dubbing engines, archive indexers) can consume directly

## 1.2 Key Performance Indicators (KPIs)

| KPI | Target |
|-----|--------|
| Language switch detection accuracy | ≥ 92% F1 on held-out test set |
| Timestamp precision | ±500 ms of true switch point |
| Latency (per 1-minute audio clip) | < 8 seconds on CPU; < 2s on GPU |
| False switch rate (hallucinated switches) | < 5% |
| Supported languages (Phase 1) | English, Hindi, Assamese |
| Output schema compliance | 100% valid JSON against schema |
| Uptime (API service) | ≥ 99.5% during business hours |

## 1.3 Success Criteria

- Pipeline runs fully offline (no cloud API dependency in the inference path)
- Entire pipeline containerized and reproducible with a single `docker-compose up`
- REST API with documented endpoints (OpenAPI / Swagger)
- Complete test coverage (unit, integration, end-to-end)
- Processing 60-minute archive videos in under 10 minutes on a standard CPU server

---

# 2. COMPLETE TECH STACK

## 2.1 Core Programming Language

### Python 3.11+
**Rationale:** Python is the lingua franca of ML/AI. Virtually every audio processing library, ML framework, and tooling ecosystem has first-class Python support. Python 3.11 brings a significant speed boost (~25% faster than 3.10) and improved error messages, both valuable for a compute-heavy pipeline.

**Key Python features used:**
- `asyncio` for non-blocking I/O in the API layer
- `dataclasses` and `pydantic` for data modeling
- `typing` for strict type hints throughout
- `contextlib` for resource management (audio file handles, model loading)
- `pathlib` for cross-platform file operations

---

## 2.2 Audio Processing Layer

### FFmpeg (v6.x)
**Role:** The industry-standard Swiss-Army knife for multimedia processing.
**How it's used:**
- Strip video payload, extract raw audio track to WAV format
- Normalize audio sample rate to 16kHz (required by VAD and LID models)
- Convert bit depth to 16-bit PCM mono
- Handle virtually any input codec: H.264/H.265 video, AAC/MP3/Opus audio

**CLI usage in pipeline:**
```bash
ffmpeg -i input_video.mp4 \
  -vn \                        # Strip video
  -acodec pcm_s16le \          # 16-bit PCM
  -ar 16000 \                  # 16kHz sample rate
  -ac 1 \                      # Mono channel
  output_audio.wav
```

**Python binding:** `ffmpeg-python` (pip) wraps subprocess calls cleanly.

---

### yt-dlp (v2024.x)
**Role:** Downloads audio/video from social media and streaming platforms (YouTube, Facebook, Instagram, X/Twitter, Dailymotion, Vimeo, and 1000+ others) directly into the pipeline, given only a public URL.
**Why yt-dlp over youtube-dl:** yt-dlp is the actively maintained fork — significantly faster download speeds, better format selection, cookies support for semi-public content, and updated extractors for all major platforms.

**How it's used:**
- Accept a URL string from the API instead of a file upload
- Download the best available audio stream directly (no video download needed, saving bandwidth and storage)
- Pass the downloaded file into the same FFmpeg extraction stage used for file uploads — zero changes to the rest of the pipeline

**Key configuration:**
```python
import yt_dlp

YDL_OPTS = {
    'format': 'bestaudio/best',          # Audio-only where available
    'outtmpl': '/tmp/%(id)s.%(ext)s',   # Temp download path
    'quiet': True,
    'no_warnings': True,
    'postprocessors': [{                  # Re-encode to WAV after download
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
    }],
    'socket_timeout': 30,
    'retries': 3,
}

with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
    info = ydl.extract_info(url, download=True)
    # info['id'], info['title'], info['duration'] available for metadata
```

**Supported platforms (partial list):** YouTube, Facebook, Instagram (public reels/videos), X (Twitter), Dailymotion, Vimeo, Reddit videos, Twitch VODs, and 1000+ others via built-in extractors.

**Limitations documented:**
- Private/login-gated content (private Instagram posts, Facebook friends-only) is not supported without cookies
- Platform rate limiting may apply for high-volume use — implement request queuing per domain
- Downloaded content must comply with the respective platform's Terms of Service; document this clearly in the API

---

### librosa (v0.10.x)
**Role:** Audio analysis and feature extraction library.
**How it's used:**
- Load `.wav` files into NumPy arrays
- Compute mel-spectrograms (visual representation of audio frequency content)
- Compute MFCCs (Mel-Frequency Cepstral Coefficients) as backup features
- Resampling and trimming utilities
- Visualization of waveforms and spectrograms during development

**Critical functions:**
- `librosa.load()` — loads audio as float32 NumPy array
- `librosa.feature.melspectrogram()` — core feature for LID models
- `librosa.effects.trim()` — silence removal
- `librosa.display.waveshow()` — debug visualization

---

### soundfile (v0.12.x)
**Role:** Fast, low-level WAV/FLAC read/write.
**How it's used:** When raw byte-level access is needed (e.g., writing audio chunks to temp buffers for model inference), soundfile is faster than librosa. Used inside the sliding window engine to write chunks to disk or BytesIO streams.

---

### pydub (v0.25.x)
**Role:** High-level audio manipulation built on FFmpeg.
**How it's used:**
- Slicing audio segments by millisecond timestamps (for the windowing engine)
- Exporting audio chunks to BytesIO buffers (in-memory, avoiding disk I/O)
- Audio normalization and gain adjustment
- Merging segments back for downstream routing

---

### numpy (v1.26.x) + scipy (v1.13.x)
**Role:** Numerical computing backbone.
**How they're used:**
- All audio data lives as `np.ndarray` during processing
- `scipy.signal.medfilt()` — the smoothing algorithm (median filter on LID predictions)
- `scipy.signal.find_peaks()` — optional peak detection for sharp language switches
- `np.concatenate()` and array slicing for the sliding window logic

---

## 2.3 Voice Activity Detection (VAD)

### Silero VAD (v4.x, PyTorch-based)
**Role:** Filters human speech from silence, background noise, music, and ambient sounds.
**Why Silero VAD:**
- Extremely lightweight (~1MB model)
- Runs in real-time (faster than audio playback) on CPU
- Highly accurate: 97%+ on standard benchmarks
- No internet required post-download
- Provides timestamps in milliseconds, not just binary speech/no-speech
- Maintained by a dedicated team with regular updates

**How it works internally:** LSTM-based recurrent neural network trained on 6000+ hours of noisy audio across 100+ languages. Processes 30ms or 60ms frames and outputs probability of speech per frame.

**Python integration:**
```python
import torch

model, utils = torch.hub.load(
    repo_or_dir='snakers4/silero-vad',
    model='silero_vad',
    force_reload=False
)
(get_speech_timestamps, _, read_audio, *_) = utils

wav = read_audio('audio.wav', sampling_rate=16000)
speech_timestamps = get_speech_timestamps(wav, model, sampling_rate=16000)
# Returns: [{'start': 0, 'end': 16400}, {'start': 18200, 'end': 34600}, ...]
```

**Alternative considered:** WebRTC VAD — faster but binary (no probabilities), misses more speech in noisy environments.

---

## 2.4 Language Identification (LID) Models

### Primary: SpeechBrain (v1.0.x, PyTorch)
**Role:** The core LID inference engine.
**Why SpeechBrain:**
- Open-source, actively maintained by researchers at Mila (Montreal Institute for Learning Algorithms)
- Pretrained `lang-id-voxlingua107-ecapa` model covers 107 languages including all Indic languages
- ECAPA-TDNN architecture — state-of-the-art for speaker and language recognition
- Produces per-class probability distributions (not just top-1), enabling confidence scoring
- Runs fully offline after initial model download
- GPU acceleration with PyTorch

**Model card for `lang-id-voxlingua107-ecapa`:**
- Trained on VoxLingua107 (6.6K hours, 107 languages)
- Includes Assamese (as), Bengali (bn), Gujarati (gu), Hindi (hi), Kannada (kn), Malayalam (ml), Marathi (mr), Odia (or), Punjabi (pa), Tamil (ta), Telugu (te), Urdu (ur) — all critical for Indian broadcasting

**Python integration:**
```python
from speechbrain.pretrained import EncoderClassifier

language_id = EncoderClassifier.from_hparams(
    source="speechbrain/lang-id-voxlingua107-ecapa",
    savedir="models/lid"
)

# Returns top prediction + probability matrix
out_prob, score, index, text_lab = language_id.classify_file("chunk_001.wav")
# text_lab = ['en: English']
# score = tensor([0.9823])
```

---

### Secondary / Fallback: whisper-langdetect (OpenAI Whisper small)
**Role:** Fallback LID using Whisper's built-in language detection for ambiguous chunks.
**Why:** Whisper's language detector is spectacularly accurate for short clips of mixed-language speech. While full Whisper transcription is expensive, using **only** the language detection head (first 30 seconds of audio → 80 language probabilities) is fast.

**Python integration:**
```python
import whisper

model = whisper.load_model("small")
audio = whisper.load_audio("chunk.wav")
audio = whisper.pad_or_trim(audio)
mel = whisper.log_mel_spectrogram(audio).to(model.device)
_, probs = model.detect_language(mel)
# probs = {'en': 0.91, 'hi': 0.06, 'as': 0.02, ...}
```

**When to use:** If SpeechBrain's top confidence score falls below a configurable threshold (e.g., 0.70), the chunk is re-evaluated by Whisper's detector and the two distributions are ensemble-averaged.

---

### Optional: Wav2Vec2 (Facebook/Meta, via HuggingFace)
**Role:** Feature extractor for custom fine-tuning if off-the-shelf models underperform on the specific broadcast domain.
**When to activate:** If benchmark accuracy on in-domain data (Phase 1 broadcast test set) falls below 88%, fine-tune `facebook/wav2vec2-base` on a labeled subset of the broadcasting archive. Training is done on a GPU (or cloud GPU) over the weekend.

---

## 2.5 ML Framework

### PyTorch (v2.3.x)
**Role:** Backbone for all neural network inference.
**Why:** SpeechBrain, Silero VAD, and Whisper all run on PyTorch. Keeping a single framework eliminates version conflicts and reduces Docker image size.

**Key components used:**
- `torch.hub` — model download and caching
- `torch.no_grad()` context manager — disables gradient computation during inference (critical for memory and speed)
- `torchaudio` — audio loading and transformation tightly integrated with PyTorch tensors
- CUDA support for GPU acceleration (automatic device detection)

### torchaudio (v2.3.x)
**Role:** PyTorch-native audio I/O and transformations.
**How it's used:**
- `torchaudio.load()` — loads WAV directly into a PyTorch tensor
- `torchaudio.transforms.Resample()` — on-the-fly resampling (GPU-accelerated)
- `torchaudio.transforms.MelSpectrogram()` — feature extraction on GPU

---

## 2.6 Data Validation & Schema

### Pydantic (v2.x)
**Role:** Data validation, serialization, and the JSON schema definition.
**How it's used:**
- Define the output JSON schema as Pydantic models (provides automatic validation, serialization, and OpenAPI schema generation)
- Validate incoming API request payloads
- Runtime type enforcement on internal pipeline data structures

**Example schema definition:**
```python
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class LanguageSegment(BaseModel):
    start_time: float = Field(..., ge=0.0)
    end_time: float = Field(..., gt=0.0)
    language_code: str = Field(..., min_length=2, max_length=5)
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class BroadcastMetadata(BaseModel):
    primary_languages_detected: List[str]
    total_speech_duration_seconds: float

class LIDResult(BaseModel):
    broadcast_id: str
    processing_timestamp: datetime
    metadata: BroadcastMetadata
    timeline: List[LanguageSegment]
```

---

## 2.7 API Layer

### FastAPI (v0.111.x)
**Role:** The REST API framework exposing pipeline endpoints.
**Why FastAPI:**
- Native async support (critical for handling multiple concurrent video processing jobs)
- Automatic OpenAPI/Swagger UI generation from Pydantic models (zero extra work for documentation)
- Dependency injection system for managing model lifecycles
- Background task support for long-running audio processing jobs
- One of the fastest Python web frameworks (benchmarked at Nginx-level throughput)

**Key endpoints designed:**
```
POST   /api/v1/analyze          # Submit video/audio file for LID analysis
POST   /api/v1/analyze/url      # Submit a YouTube/Facebook/Instagram/etc. URL
GET    /api/v1/jobs/{job_id}    # Poll job status
GET    /api/v1/jobs/{job_id}/result  # Fetch completed result JSON
DELETE /api/v1/jobs/{job_id}    # Cancel or clean up job
GET    /api/v1/health           # Health check
GET    /api/v1/models           # List loaded models and their status
```

### Uvicorn (v0.30.x)
**Role:** ASGI server running FastAPI in production.
**Configuration:** Run with multiple workers (`--workers 4`) for parallelism; `--loop uvloop` for maximum async performance.

### aiofiles (v23.x)
**Role:** Async file I/O for the API layer — non-blocking reads/writes when saving uploaded video files to disk.

---

## 2.8 Task Queue & Job Management

### Celery (v5.3.x) + Redis (v7.x)
**Role:** Asynchronous task queue for long-running processing jobs.
**Why:** Audio processing of a 60-minute broadcast takes several minutes. The API must respond immediately (202 Accepted) while the job runs in the background. Celery workers pick up jobs from a Redis message broker.

**Architecture:**
```
FastAPI → Redis (broker) → Celery Worker → LID Pipeline → Redis (result backend) → FastAPI
```

**Celery configuration highlights:**
- Task time limit: 30 minutes per job
- Soft time limit: 25 minutes (raises exception, allows graceful cleanup)
- Result expiry: 24 hours
- Concurrency: 2 workers per CPU core (pipeline is I/O bound between stages)
- Task routing: `high_priority` queue for short clips (< 5 min), `standard` for longer

### Redis (v7.x)
**Role (dual):**
1. Celery message broker
2. Result backend for completed LID JSON payloads
3. Rate-limiting cache for the API layer

---

## 2.9 Storage

### MinIO (S3-compatible Object Storage)
**Role:** Stores raw uploaded videos, intermediate audio extracts, and final JSON results.
**Why MinIO:**
- Fully open-source, self-hosted (no cloud vendor lock-in)
- S3-compatible API (can swap to AWS S3 in production with zero code changes)
- High-performance object storage for binary files (video, audio)

**Bucket layout:**
```
lid-pipeline/
├── uploads/          # Raw video files
├── audio/            # Extracted WAV files
├── chunks/           # Temporary windowed chunks (TTL: 1 hour)
└── results/          # Final JSON payloads (permanent)
```

### PostgreSQL (v16.x)
**Role:** Relational metadata store.
**Stores:**
- Job records (job_id, status, submitted_at, completed_at, file_path)
- Processing metrics (per-stage latency, model confidence distributions)
- User/API key management
- Historical analytics (language distribution by broadcast ID)

### SQLAlchemy (v2.x) + asyncpg
**Role:** Async ORM for PostgreSQL interaction within FastAPI.

---

## 2.10 Containerization & Orchestration

### Docker (v26.x) + Docker Compose (v2.x)
**Role:** Package every service (API, Celery workers, Redis, PostgreSQL, MinIO) into isolated containers, enabling one-command deployment.

**Services in `docker-compose.yml`:**
- `api` — FastAPI + Uvicorn
- `worker` — Celery worker (can scale: `docker-compose up --scale worker=4`)
- `redis` — Message broker + cache
- `postgres` — Metadata database
- `minio` — Object storage
- `flower` — Celery monitoring dashboard
- `prometheus` — Metrics collection
- `grafana` — Metrics dashboards

### NVIDIA Container Toolkit (Optional GPU)
**Role:** Exposes GPU to Docker containers for accelerated PyTorch inference. If the deployment server has an NVIDIA GPU, inference speed improves 5–10x.

---

## 2.11 Testing Framework

### pytest (v8.x)
**Role:** Primary test runner.
**Plugins used:**
- `pytest-asyncio` — test async FastAPI endpoints
- `pytest-cov` — code coverage reporting
- `pytest-mock` — mock ML models in unit tests (avoids loading 500MB models during CI)
- `pytest-benchmark` — benchmark processing speed per pipeline stage

### httpx (v0.27.x)
**Role:** Async HTTP client for integration-testing FastAPI endpoints.

### factory_boy (v3.3.x)
**Role:** Generate realistic test data (fake job records, audio metadata) for database layer tests.

---

## 2.12 Code Quality & CI/CD

### Ruff (v0.4.x)
**Role:** Extremely fast Python linter + formatter (replaces flake8, isort, and black).

### mypy (v1.10.x)
**Role:** Static type checker. Enforces type hints across the entire codebase.

### pre-commit (v3.7.x)
**Role:** Git hooks that run ruff, mypy, and security checks before every commit.

### GitHub Actions
**Role:** CI/CD pipeline.
**Workflow:**
```
push → lint (ruff + mypy) → unit tests → integration tests → build Docker image → push to registry
```

---

## 2.13 Monitoring & Observability

### Prometheus (v2.52.x)
**Role:** Metrics collection from the API and Celery workers.
**Metrics tracked:**
- `lid_jobs_total` — counter by status (submitted, completed, failed)
- `lid_processing_duration_seconds` — histogram per pipeline stage
- `lid_model_confidence` — histogram of confidence scores
- `lid_language_switches_per_broadcast` — gauge
- API request latency, error rates

### Grafana (v11.x)
**Role:** Dashboards visualizing Prometheus metrics in real-time.

### structlog (v24.x)
**Role:** Structured (JSON) logging throughout the pipeline. Every log line carries context: `job_id`, `stage`, `duration_ms`, `language_detected`.

### Sentry (optional)
**Role:** Real-time error tracking and stack trace aggregation for production exceptions.

### Flower (v2.x)
**Role:** Web UI for monitoring Celery workers, task queues, and job statuses in real-time.

---

## 2.14 Documentation

### MkDocs + Material Theme
**Role:** Auto-generates a beautiful documentation website from Markdown files.
**Sections:**
- Architecture overview
- API reference (auto-imported from FastAPI OpenAPI schema)
- Developer guide (how to add a new language)
- Operations guide (deployment, scaling, monitoring)

---

## 2.15 Development Environment

| Tool | Version | Purpose |
|------|---------|---------|
| Git | 2.45+ | Version control |
| GitHub | — | Remote repository, PR reviews, CI/CD |
| VS Code | Latest | IDE with Python, Docker, and REST Client extensions |
| Jupyter Lab | 4.x | Exploratory audio analysis and model debugging |
| Postman | Latest | Manual API endpoint testing |
| DBeaver | Latest | PostgreSQL GUI client |
| Docker Desktop | 4.x | Local container management |
| pyenv | 2.x | Python version management |
| Poetry | 1.8.x | Dependency management and virtual environments |

---

## 2.16 Tech Stack Summary Table

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11 |
| Audio Extraction | FFmpeg + ffmpeg-python | 6.x |
| Social Media Ingestion | yt-dlp | 2024.x |
| Audio Analysis | librosa | 0.10.x |
| Audio I/O | soundfile, pydub, torchaudio | Latest |
| Numerics | numpy, scipy | Latest |
| VAD | Silero VAD | 4.x |
| LID (Primary) | SpeechBrain ECAPA | 1.0.x |
| LID (Secondary) | OpenAI Whisper small | Latest |
| ML Framework | PyTorch | 2.3.x |
| Data Validation | Pydantic | 2.x |
| API Framework | FastAPI | 0.111.x |
| ASGI Server | Uvicorn | 0.30.x |
| Task Queue | Celery | 5.3.x |
| Message Broker | Redis | 7.x |
| Object Storage | MinIO | Latest |
| Database | PostgreSQL | 16.x |
| ORM | SQLAlchemy + asyncpg | 2.x |
| Containers | Docker + Compose | 26.x |
| Testing | pytest + plugins | 8.x |
| Linting | Ruff + mypy | Latest |
| CI/CD | GitHub Actions | — |
| Monitoring | Prometheus + Grafana | Latest |
| Logging | structlog | 24.x |
| Documentation | MkDocs Material | Latest |
| Dep. Management | Poetry | 1.8.x |

---

# 3. SYSTEM ARCHITECTURE DEEP-DIVE

## 3.1 Pipeline Data Flow

```
[Video File Upload]   [Social Media URL]
         │             │ (YouTube / Facebook /
         │             │  Instagram / etc.)
         │             ▼
         │    ┌─────────────────────┐
         │    │  Stage 0: URL       │  yt-dlp downloads best
         │    │  Ingestion          │  audio stream → local file
         │    └─────────┬───────────┘
         │              │
         └──────────────┘
                  │
                  ▼
┌─────────────────────┐
│  Stage 1: Modality  │  FFmpeg strips video payload
│     Isolation       │  Output: 16kHz mono WAV
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Stage 2: Voice     │  Silero VAD analyzes full WAV
│  Activity Detection │  Output: [(start_ms, end_ms), ...]
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Stage 3: Sliding   │  Active speech segments are
│  Window             │  chopped into 2-3s overlapping
│  Segmentation       │  micro-chunks
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Stage 4: LID       │  SpeechBrain classifies each
│  Inference          │  chunk → probability matrix
│                     │  Whisper fallback for low-conf
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Stage 5: Smoothing │  Median filter on frame-level
│  Algorithm          │  predictions → merged timeline
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Stage 6: JSON      │  Pydantic serialization
│  Output             │  Validated against schema
└─────────────────────┘
```

## 3.2 Sliding Window Logic (Detailed)

The most algorithmically nuanced stage. Given a speech segment from VAD [15.2s → 72.8s]:

**Step A: Chunk generation**
```
Window size (W) = 3.0 seconds
Step size (S)   = 1.0 second (overlap = W - S = 2.0s)

Chunks generated:
  chunk_01: [15.2s → 18.2s]
  chunk_02: [16.2s → 19.2s]
  chunk_03: [17.2s → 20.2s]
  ...
  chunk_N:  [69.8s → 72.8s]
```

**Step B: LID inference per chunk**
Each chunk returns a probability vector over all 107 languages.

**Step C: Frame-level prediction sequence**
```
t=15.2: {en: 0.95, hi: 0.03, as: 0.02}  → "en"
t=16.2: {en: 0.93, hi: 0.05, as: 0.02}  → "en"
t=17.2: {en: 0.61, hi: 0.34, as: 0.05}  → "en"  (borderline — smoothing handles)
t=18.2: {en: 0.21, hi: 0.73, as: 0.06}  → "hi"
t=19.2: {en: 0.08, hi: 0.89, as: 0.03}  → "hi"
...
```

**Step D: Median filter smoothing**
Apply `scipy.signal.medfilt(predictions, kernel_size=5)` to the integer-encoded prediction sequence. This means a language switch is only confirmed if 3 of 5 consecutive chunks agree — a single misclassified chunk cannot trigger a false switch.

**Step E: Boundary collapse**
Runs of identical labels are collapsed into segments:
```
en: [15.2s → 17.7s]
hi: [17.7s → 45.1s]
```
The boundary is placed at the midpoint of the transition zone.

## 3.3 Confidence Score Calculation

For each output segment, the confidence score is computed as the **mean of the top-1 probability scores** across all chunks within that segment:

```python
segment_confidence = np.mean([
    chunk_probs[predicted_lang]
    for chunk_probs in segment_chunks
])
```

Low-confidence segments (< 0.70) are flagged with `"flag": "low_confidence"` in the output JSON, allowing human review.

## 3.4 API Request Lifecycle

```
1. Client sends POST /api/v1/analyze with video file (multipart) or S3 URI
2. FastAPI validates request, stores file to MinIO, creates job record in PostgreSQL
3. Returns HTTP 202 Accepted with {"job_id": "abc123", "status_url": "/api/v1/jobs/abc123"}
4. Celery worker picks up job from Redis queue
5. Worker runs 6-stage pipeline, stores result JSON in MinIO + PostgreSQL
6. Client polls GET /api/v1/jobs/abc123 → {"status": "completed", "result_url": "..."}
7. Client fetches GET /api/v1/jobs/abc123/result → Full LID JSON payload
```

---

# 4. ENVIRONMENT SETUP & PREREQUISITES

## 4.1 Hardware Requirements

**Minimum (Development):**
- CPU: 4-core x86_64, 2.5 GHz+
- RAM: 16 GB (models consume ~4 GB at peak)
- Storage: 50 GB SSD (models + test data + Docker images)
- OS: Ubuntu 22.04 LTS or macOS 13+

**Recommended (Production):**
- CPU: 8-core x86_64, 3.0 GHz+
- RAM: 32 GB
- GPU: NVIDIA RTX 3090 or A10 with 24 GB VRAM (optional but recommended)
- Storage: 500 GB NVMe SSD
- OS: Ubuntu 22.04 LTS

## 4.2 Initial Machine Setup (Ubuntu 22.04)

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Build essentials
sudo apt install -y build-essential git curl wget unzip \
    python3.11 python3.11-dev python3.11-venv \
    ffmpeg libsndfile1-dev portaudio19-dev \
    libpq-dev postgresql-client

# Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose V2
sudo apt install -y docker-compose-plugin

# pyenv (Python version manager)
curl https://pyenv.run | bash
pyenv install 3.11.9
pyenv global 3.11.9

# Poetry (dependency management)
curl -sSL https://install.python-poetry.org | python3 -

# CUDA (if GPU available)
# Follow https://developer.nvidia.com/cuda-downloads for CUDA 12.x
```

## 4.3 Repository Initialization

```bash
# Create project
mkdir lid-pipeline && cd lid-pipeline
git init
git remote add origin https://github.com/your-org/lid-pipeline.git

# Poetry project
poetry init --name "lid-pipeline" --python "^3.11"

# Install core deps
poetry add \
    torch==2.3.0 torchaudio==2.3.0 \
    speechbrain==1.0.0 \
    silero-vad \
    openai-whisper \
    librosa soundfile pydub ffmpeg-python \
    yt-dlp \
    numpy scipy \
    fastapi uvicorn[standard] aiofiles \
    celery[redis] \
    redis \
    sqlalchemy[asyncio] asyncpg \
    pydantic pydantic-settings \
    structlog \
    boto3  # For MinIO S3-compatible client

poetry add --group dev \
    pytest pytest-asyncio pytest-cov pytest-mock pytest-benchmark \
    httpx factory-boy \
    ruff mypy \
    pre-commit \
    jupyter jupyterlab \
    ipython

# Activate virtual environment
poetry shell
```

---

# 5. WEEK-BY-WEEK MASTER PLAN

---

## WEEK 1: Foundation & Infrastructure
**Theme:** "Get everyone on the same ground."
**Goal:** Repository structure, CI/CD, Docker environment, database schemas all operational before a single line of pipeline code is written.

### Day 1 (Monday): Repository Architecture & Standards

**Morning (4 hours):**
- Initialize Git repository with branch protection rules (require PR reviews, CI passing before merge)
- Agree on branching strategy: `main` (protected), `develop`, `feature/[name]` branches
- Set up GitHub repository, add team members, configure issue templates
- Create the complete directory structure (see Appendix 12) as empty folders with `.gitkeep`

**Afternoon (4 hours):**
- Write `pyproject.toml` with all dependencies (see §4.3)
- Configure `ruff.toml`: line length 100, enable pyflakes + isort rules
- Configure `mypy.ini`: strict mode, Python 3.11 target
- Write `.pre-commit-config.yaml` with ruff, mypy, trailing-whitespace, end-of-file-fixer hooks
- Run `pre-commit install` on all dev machines
- Create `CONTRIBUTING.md` documenting coding standards, PR template, and commit message format (Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`)

**Deliverable:** Clean repo that auto-lints on every commit.

---

### Day 2 (Tuesday): Docker & Infrastructure

**Morning (4 hours):**
- Write `Dockerfile` for the main application:
  - Base: `python:3.11-slim`
  - Install system deps: ffmpeg, libsndfile1
  - Copy Poetry lockfile and install Python deps
  - Multi-stage build: builder stage installs deps, runtime stage copies only what's needed (reduces image from ~8GB to ~3GB)
- Write `Dockerfile.worker` for Celery workers (inherits from main but runs `celery worker` entrypoint)

**Afternoon (4 hours):**
- Write `docker-compose.yml` with all services: `api`, `worker`, `redis`, `postgres`, `minio`, `flower`, `prometheus`, `grafana`
- Write `.env.example` with all required environment variables
- Write `docker-compose.override.yml` for local development (volume mounts for hot-reload)
- Test: `docker-compose up` — all services start healthy

**Deliverable:** `docker-compose up` brings up entire stack from scratch.

---

### Day 3 (Wednesday): Database Schema & Migrations

**Morning (4 hours):**
- Design PostgreSQL schema:
  - `jobs` table: job_id (UUID PK), status, file_path, submitted_at, started_at, completed_at, error_message, result_path
  - `job_metrics` table: job_id (FK), stage_name, duration_ms, recorded_at
  - `language_events` table: job_id (FK), start_time, end_time, language_code, confidence_score
- Install Alembic (`poetry add alembic`)
- Run `alembic init migrations`
- Write the initial migration file

**Afternoon (4 hours):**
- Write SQLAlchemy models for all tables (using async declarative base)
- Write repository layer classes: `JobRepository`, `MetricsRepository`, `EventRepository`
- Write unit tests for repository layer (using a test PostgreSQL instance via pytest fixtures)
- Run migrations: `alembic upgrade head`

**Deliverable:** Database schema in place with a tested repository layer.

---

### Day 4 (Thursday): GitHub Actions CI/CD Pipeline

**Morning (4 hours):**
Write `.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff mypy
      - run: ruff check .
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    services:
      postgres: { image: postgres:16, env: { POSTGRES_PASSWORD: test } }
      redis: { image: redis:7 }
    steps:
      - uses: actions/checkout@v4
      - run: pip install poetry && poetry install
      - run: poetry run pytest tests/unit tests/integration --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: docker/build-push-action@v5
        with: { push: true, tags: ghcr.io/your-org/lid-pipeline:${{ github.sha }} }
```

**Afternoon (4 hours):**
- Write `.github/workflows/deploy.yml` for deployment to staging on `develop` branch push
- Set up GitHub Environments: `staging` and `production`
- Configure repository secrets: `DOCKER_REGISTRY_TOKEN`, `STAGING_SSH_KEY`
- First CI run — fix any issues

**Deliverable:** Every push is automatically linted, tested, and (on `develop`) deployed.

---

### Day 5 (Friday): Configuration System & Logging

**Morning (4 hours):**
- Write `src/config.py` using Pydantic Settings:
  - `DATABASE_URL`, `REDIS_URL`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`
  - `VAD_THRESHOLD` (float, default 0.5)
  - `WINDOW_SIZE_SECONDS` (float, default 3.0)
  - `WINDOW_STEP_SECONDS` (float, default 1.0)
  - `SMOOTHING_KERNEL_SIZE` (int, default 5)
  - `LID_CONFIDENCE_THRESHOLD` (float, default 0.70)
  - `FALLBACK_TO_WHISPER` (bool, default True)
  - All values read from environment variables with defaults
- Write `src/logging_config.py` — configure structlog with JSON renderer for production, colorized console renderer for development
- Write a `get_logger()` factory function used by every module

**Afternoon (4 hours):**
- Week 1 retrospective: document any blockers
- Write `ARCHITECTURE.md` explaining the high-level design decisions
- Create and close all Week 1 GitHub issues
- Team knowledge-sharing session: make sure every team member can run the stack locally

**Week 1 Deliverables Checklist:**
- [ ] Git repo with branch protection and pre-commit hooks
- [ ] Docker Compose stack (all services healthy)
- [ ] PostgreSQL schema + Alembic migrations
- [ ] SQLAlchemy models + repository layer + tests
- [ ] GitHub Actions CI passing (lint + test + build)
- [ ] Pydantic config system
- [ ] Structlog structured logging
- [ ] `ARCHITECTURE.md` and `CONTRIBUTING.md`

---

## WEEK 2: Audio Ingestion & Voice Activity Detection
**Theme:** "From video file to clean speech timestamps."
**Goal:** A working pipeline from raw video input through VAD, producing a list of speech intervals ready for windowing.

### Day 6 (Monday): FFmpeg Audio Extraction Module

**Morning (4 hours):**
Create `src/pipeline/stages/audio_extraction.py`:

```python
import asyncio
import ffmpeg
from pathlib import Path
from dataclasses import dataclass
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class AudioExtractionResult:
    output_path: Path
    duration_seconds: float
    sample_rate: int
    channels: int

async def extract_audio(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 16000
) -> AudioExtractionResult:
    """Extract and normalize audio from any video/audio input."""
    logger.info("audio_extraction.start", input=str(input_path))

    stream = (
        ffmpeg
        .input(str(input_path))
        .audio
        .output(
            str(output_path),
            acodec='pcm_s16le',
            ar=sample_rate,
            ac=1,          # Mono
            f='wav'
        )
        .overwrite_output()
    )

    # Run in thread pool to avoid blocking the event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, stream.run, None, True)

    # Probe output to get actual duration
    probe = ffmpeg.probe(str(output_path))
    duration = float(probe['streams'][0]['duration'])

    logger.info("audio_extraction.complete", duration=duration)
    return AudioExtractionResult(output_path, duration, sample_rate, 1)
```

- Write corresponding unit tests in `tests/unit/test_audio_extraction.py`
  - Mock ffmpeg subprocess calls
  - Test various input formats (MP4, MKV, AVI, MP3, M4A)
  - Test error handling (corrupt file, no audio stream, permission denied)
  - Test async execution

**Afternoon (4 hours):**
- Write integration tests using a real small test video file (create a 10-second synthetic test video with `ffmpeg` during test setup)
- Handle edge cases: video with no audio track (raise `AudioExtractionError`), video with multiple audio tracks (extract track 0 by default, configurable), HDR video (audio extraction is codec-agnostic)
- Add Prometheus metric: `audio_extraction_duration_seconds`

**Deliverable:** `extract_audio()` function fully tested.

---

### Day 7 (Tuesday): File Upload & Storage Integration

**Morning (4 hours):**
Create `src/storage/minio_client.py`:
- Wrap boto3 S3 client for MinIO
- `upload_file(local_path, bucket, key)` — async upload
- `download_file(bucket, key, local_path)` — async download
- `generate_presigned_url(bucket, key, expiry_seconds)` — for result delivery
- `delete_file(bucket, key)` — for cleanup

**Afternoon (4 hours):**
- Write the first FastAPI endpoint: `POST /api/v1/analyze`
  - Accept multipart file upload OR JSON body with `{"s3_uri": "s3://bucket/key"}`
  - Validate file size (max 2 GB), file type (video/audio MIME types)
  - Save to MinIO `uploads/` bucket
  - Create job record in PostgreSQL
  - Enqueue Celery task
  - Return 202 Accepted with job ID
- Write the second input endpoint: `POST /api/v1/analyze/url`
  - Accept JSON body: `{"url": "https://www.youtube.com/watch?v=..."}`
  - Validate URL format (must be `https://`, must resolve to a supported platform via `yt_dlp.extractor.gen_extractors()`)
  - Create job record in PostgreSQL with `source_type = "url"` and `source_url` stored
  - Enqueue a Celery task that calls `src/pipeline/stages/url_downloader.py` before the standard audio extraction stage
  - Return 202 Accepted with job ID — same response schema as file upload
- Write tests for both endpoints using `httpx.AsyncClient`

**Deliverable:** Files can be uploaded via API and stored in MinIO; social media URLs can be submitted and queued for download.

---

### Day 8 (Wednesday): Silero VAD Integration

**Morning (4 hours):**
Create `src/pipeline/stages/voice_activity_detection.py`:

```python
import torch
import numpy as np
from dataclasses import dataclass
from typing import List
from src.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class SpeechInterval:
    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

class SileroVAD:
    """Singleton wrapper for Silero VAD model."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        logger.info("vad.model_loading")
        self.model, self.utils = torch.hub.load(
            'snakers4/silero-vad',
            'silero_vad',
            force_reload=False,
            verbose=False
        )
        self.model.eval()
        (self.get_speech_timestamps,
         self.save_audio,
         self.read_audio,
         self.VADIterator,
         self.collect_chunks) = self.utils
        logger.info("vad.model_loaded")

    def detect_speech(
        self,
        audio_path: str,
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        window_size_samples: int = 512,
        speech_pad_ms: int = 30
    ) -> List[SpeechInterval]:

        wav = self.read_audio(audio_path, sampling_rate=16000)

        raw_timestamps = self.get_speech_timestamps(
            wav,
            self.model,
            sampling_rate=16000,
            threshold=threshold,
            min_speech_duration_ms=min_speech_duration_ms,
            min_silence_duration_ms=min_silence_duration_ms,
            window_size_samples=window_size_samples,
            speech_pad_ms=speech_pad_ms,
            return_seconds=True
        )

        intervals = [
            SpeechInterval(t['start'], t['end'])
            for t in raw_timestamps
        ]

        total_speech = sum(i.duration_seconds for i in intervals)
        logger.info(
            "vad.complete",
            segments=len(intervals),
            total_speech_seconds=round(total_speech, 2)
        )
        return intervals
```

**Afternoon (4 hours):**
- Write comprehensive unit tests for VAD:
  - Pure silence audio → no speech intervals returned
  - Pure speech audio → single interval covering full duration
  - Speech-silence-speech pattern → two separate intervals
  - Noisy audio → intervals don't include noise bursts
  - Very short clips (< 250ms) → filtered out
- Create test audio fixtures:
  - `tests/fixtures/audio/silence_5s.wav` — 5 seconds of silence
  - `tests/fixtures/audio/speech_5s.wav` — synthetic speech (text-to-speech)
  - `tests/fixtures/audio/noisy_speech.wav` — speech with background noise overlay
- Mock `torch.hub.load` in unit tests to avoid downloading the model in CI

**Deliverable:** `SileroVAD` class producing accurate speech intervals.

---

### Day 9 (Thursday): VAD Tuning & Benchmarking

**Morning (4 hours):**
- Collect 20 short real broadcasting audio samples (10-30 seconds each) covering:
  - Clean studio speech (English, Hindi, Assamese)
  - Outdoor reporting with crowd noise
  - Music intros/outros
  - Split-screen phone calls
- Manually annotate these as ground truth VAD labels (use Audacity for annotation)
- Run `SileroVAD` with default parameters and compute F1 score

**Afternoon (4 hours):**
- Parameter sweep: test `threshold` from 0.3 to 0.7, `min_silence_duration_ms` from 50 to 500
- Document optimal parameters in `config.py` defaults
- Write a Jupyter notebook `notebooks/01_vad_analysis.ipynb` visualizing:
  - Waveform with VAD-detected speech regions highlighted
  - False positive/negative rates per parameter set
  - Processing speed benchmark (ms per second of audio)
- Commit notebook and results

**Deliverable:** VAD tuned to ≥ 95% F1 on in-domain test set.

---

### Day 10 (Friday): VAD Pipeline Integration & Stage Orchestrator

**Morning (4 hours):**
Create `src/pipeline/orchestrator.py` — the master class that chains all stages:

```python
from src.pipeline.stages.audio_extraction import extract_audio
from src.pipeline.stages.voice_activity_detection import SileroVAD
from src.models.job import Job

class LIDPipelineOrchestrator:

    def __init__(self):
        self.vad = SileroVAD()

    async def run(self, job: Job) -> dict:
        # Stage 1: Audio extraction
        audio_result = await extract_audio(job.input_path, job.audio_path)

        # Stage 2: VAD
        speech_intervals = self.vad.detect_speech(str(job.audio_path))

        # Stages 3-6 will be added in subsequent weeks
        return {"status": "partial", "speech_intervals": speech_intervals}
```

**Afternoon (4 hours):**
- Integrate the orchestrator with the Celery task
- Write the job status polling endpoint: `GET /api/v1/jobs/{job_id}`
- Test full flow: upload video → Celery runs stages 1-2 → poll for status
- Week 2 retrospective and documentation update

**Week 2 Deliverables Checklist:**
- [ ] `extract_audio()` module + tests
- [ ] File upload API endpoint + MinIO integration
- [ ] `SileroVAD` class + tests + benchmark notebook
- [ ] VAD parameter tuning documented
- [ ] `LIDPipelineOrchestrator` skeleton with stages 1-2 wired
- [ ] Celery task running stages 1-2 end-to-end

---

## WEEK 3: Sliding Window Segmentation Engine
**Theme:** "Chop the audio into precisely overlapping micro-chunks."
**Goal:** A mathematically correct, memory-efficient windowing engine that generates audio chunks ready for LID inference.

### Day 11 (Monday): Window Generation Algorithm

**Morning (4 hours):**
Create `src/pipeline/stages/windowing.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Iterator
import soundfile as sf
import numpy as np
from src.pipeline.stages.voice_activity_detection import SpeechInterval
from src.config import settings

@dataclass
class AudioChunk:
    chunk_id: str
    start_seconds: float
    end_seconds: float
    sample_rate: int
    audio_data: np.ndarray = field(repr=False)

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


def generate_chunks(
    audio_path: Path,
    speech_intervals: List[SpeechInterval],
    window_size: float = 3.0,
    step_size: float = 1.0,
    sample_rate: int = 16000
) -> Iterator[AudioChunk]:
    """
    Generator that yields AudioChunk objects for each
    overlapping window within each speech interval.
    Uses generator pattern to avoid loading all chunks into memory.
    """
    audio, sr = sf.read(str(audio_path), dtype='float32')
    assert sr == sample_rate, f"Expected {sample_rate}Hz, got {sr}Hz"

    window_samples = int(window_size * sample_rate)
    step_samples = int(step_size * sample_rate)

    chunk_counter = 0

    for interval in speech_intervals:
        interval_start_sample = int(interval.start_seconds * sample_rate)
        interval_end_sample = int(interval.end_seconds * sample_rate)
        interval_audio = audio[interval_start_sample:interval_end_sample]

        pos = 0
        while pos + window_samples <= len(interval_audio):
            chunk_audio = interval_audio[pos:pos + window_samples]
            chunk_start = interval.start_seconds + (pos / sample_rate)
            chunk_end = chunk_start + window_size

            yield AudioChunk(
                chunk_id=f"chunk_{chunk_counter:06d}",
                start_seconds=chunk_start,
                end_seconds=chunk_end,
                sample_rate=sample_rate,
                audio_data=chunk_audio
            )
            chunk_counter += 1
            pos += step_samples

        # Handle the tail (last chunk of each interval)
        remaining = len(interval_audio) - pos
        if remaining >= int(0.5 * sample_rate):  # Min 0.5s for meaningful LID
            chunk_audio = interval_audio[pos:]
            # Zero-pad to window_size
            padded = np.zeros(window_samples, dtype=np.float32)
            padded[:len(chunk_audio)] = chunk_audio

            chunk_start = interval.start_seconds + (pos / sample_rate)
            yield AudioChunk(
                chunk_id=f"chunk_{chunk_counter:06d}",
                start_seconds=chunk_start,
                end_seconds=interval.end_seconds,
                sample_rate=sample_rate,
                audio_data=padded
            )
            chunk_counter += 1
```

**Afternoon (4 hours):**
- Write exhaustive unit tests:
  - Known input with 3 chunks expected → exactly 3 chunks produced
  - Boundary conditions: interval shorter than window → single padded chunk
  - Overlap correctness: chunk N and chunk N+1 share expected samples
  - Memory safety: generator pattern tested with `next()` — no full list materialization
  - Zero-padding integrity: tail chunk pads with zeros, not noise

---

### Day 12 (Tuesday): Chunk Serialization & Temp Storage

**Morning (4 hours):**
- Write `src/pipeline/stages/chunk_store.py`:
  - Temporary chunk storage using Python's `tempfile.TemporaryDirectory` (automatic cleanup)
  - Option to write to BytesIO (in-memory) for small payloads or disk for large archives
  - MinIO upload for chunks that need to survive across worker restarts
  - `ChunkStore.save(chunk)` → returns a path or stream reference
  - `ChunkStore.load(chunk_id)` → returns `AudioChunk`
  - `ChunkStore.cleanup(job_id)` → deletes all temp files for a job

**Afternoon (4 hours):**
- Write `src/pipeline/stages/chunk_writer.py`:
  - Converts `AudioChunk.audio_data` (NumPy array) to a WAV file on disk or BytesIO
  - Uses `soundfile.write()` for efficiency
  - Writes to `/tmp/{job_id}/chunks/chunk_XXXXXX.wav`
- Write integration test: given a real 30-second WAV with 2 speech intervals, verify:
  - Exact number of expected chunks are generated
  - Each written WAV file is exactly `window_size` seconds long (or padded correctly)
  - No sample data corruption (compare first 100 samples of expected vs actual)

---

### Day 13 (Wednesday): Windowing Performance Optimization

**Morning (4 hours):**
Using `pytest-benchmark`, profile the windowing engine against:
- 5-minute audio (one speech interval)
- 30-minute audio (many speech intervals with gaps)
- 60-minute audio (stress test)

Profile with `cProfile` and `snakeviz` to identify hotspots. Expected bottleneck: disk I/O for chunk writing.

**Optimization strategies to implement:**
1. **Batch writing:** Accumulate 50 chunks in memory before writing to disk (amortizes syscall overhead)
2. **Memory mapping:** Use `np.memmap` for the source audio array (avoids loading 60-min WAV entirely into RAM)
3. **Parallel chunk generation:** Use `concurrent.futures.ThreadPoolExecutor` to process multiple speech intervals simultaneously

**Afternoon (4 hours):**
- Implement the memory-mapping optimization:
  ```python
  audio = np.memmap(str(audio_path), dtype='float32', mode='r',
                    offset=44)  # Skip WAV header
  ```
- Re-benchmark and document improvement
- Target: process 60-minute audio into chunks in < 20 seconds on CPU

---

### Day 14 (Thursday): Windowing Integration with Orchestrator

**Morning (4 hours):**
- Add Stage 3 to `LIDPipelineOrchestrator`:
  ```python
  # Stage 3: Sliding Window Segmentation
  chunk_store = ChunkStore(job_id=job.job_id)
  chunks = list(generate_chunks(
      audio_path=job.audio_path,
      speech_intervals=speech_intervals,
      window_size=settings.WINDOW_SIZE_SECONDS,
      step_size=settings.WINDOW_STEP_SECONDS
  ))
  for chunk in chunks:
      chunk_store.save(chunk)
  ```
- Update job status in PostgreSQL after each stage (enables progress tracking in the API)

**Afternoon (4 hours):**
- End-to-end test: upload a real video → stages 1-3 complete → verify chunk files exist
- Write a notebook `notebooks/02_windowing_visualization.ipynb`:
  - Visual overlay of VAD intervals and chunk boundaries on a waveform plot
  - Verify overlaps are correct visually

---

### Day 15 (Friday): Error Handling & Resilience

**Morning (4 hours):**
Write `src/pipeline/exceptions.py` — all custom exceptions:
```python
class PipelineError(Exception): ...
class AudioExtractionError(PipelineError): ...
class VADError(PipelineError): ...
class WindowingError(PipelineError): ...
class LIDInferenceError(PipelineError): ...
class SchemaValidationError(PipelineError): ...
```

Wrap every stage in the orchestrator with:
- Specific exception catching
- Structured error logging (stage, job_id, error_message, traceback)
- Update job status to `"failed"` in PostgreSQL with error details
- Automatic temp file cleanup on failure

**Afternoon (4 hours):**
- Implement Celery task retry logic:
  - Retry up to 3 times on transient errors (network, disk full)
  - Exponential backoff: 10s, 60s, 300s
  - Permanent failure (corrupt file, unsupported format) — no retry, mark as `"failed"`
- Write tests for all error paths

**Week 3 Deliverables Checklist:**
- [ ] `generate_chunks()` generator function + tests
- [ ] `ChunkStore` class + temp file management
- [ ] Memory-mapped audio loading for large files
- [ ] Performance benchmarks documented
- [ ] Error handling + custom exceptions
- [ ] Celery retry logic
- [ ] Stages 1-3 wired in orchestrator

---

## WEEK 4: LID Model Integration
**Theme:** "Give the pipeline its brain."
**Goal:** SpeechBrain and Whisper integrated, producing language predictions for every chunk.

### Day 16 (Monday): SpeechBrain Model Management

**Morning (4 hours):**
Create `src/pipeline/models/speechbrain_lid.py`:

```python
import torch
import numpy as np
from speechbrain.pretrained import EncoderClassifier
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

class SpeechBrainLID:
    """
    Thread-safe singleton wrapper for SpeechBrain LID model.
    Loaded once at worker startup and reused across all jobs.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return
        logger.info("speechbrain.loading")
        self.classifier = EncoderClassifier.from_hparams(
            source="speechbrain/lang-id-voxlingua107-ecapa",
            savedir=settings.MODEL_CACHE_DIR / "speechbrain_lid",
            run_opts={"device": "cuda" if torch.cuda.is_available() else "cpu"}
        )
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._loaded = True
        logger.info("speechbrain.loaded", device=self._device)

    def classify_chunk(self, audio_data: np.ndarray, sample_rate: int = 16000) -> dict:
        """
        Returns: {'language_code': str, 'confidence': float, 'all_probs': dict}
        """
        with torch.no_grad():
            waveform = torch.tensor(audio_data).unsqueeze(0).to(self._device)
            out_prob, score, index, text_lab = self.classifier.classify_batch(waveform)

        # Parse language code from SpeechBrain label (e.g., "en: English" → "en")
        lang_code = text_lab[0].split(':')[0].strip()
        confidence = float(score[0])

        # Build full probability dictionary for all 107 languages
        all_probs = {
            label.split(':')[0].strip(): float(prob)
            for label, prob in zip(
                self.classifier.hparams.label_encoder.decode_ndim(
                    list(range(len(out_prob[0])))
                ),
                out_prob[0].tolist()
            )
        }

        return {
            'language_code': lang_code,
            'confidence': confidence,
            'all_probs': all_probs
        }
```

**Afternoon (4 hours):**
- Write unit tests (mocking `EncoderClassifier` to avoid downloading model in CI)
- Write integration test using a real audio clip (requires model downloaded manually and marked as `@pytest.mark.integration`)
- Test GPU vs CPU code path (mock `torch.cuda.is_available()`)
- Test edge cases: silent chunk (VAD should have filtered these, but defensive coding), very short chunk after padding

---

### Day 17 (Tuesday): Whisper Fallback Integration

**Morning (4 hours):**
Create `src/pipeline/models/whisper_lid.py`:

```python
import whisper
import torch
import numpy as np
from src.logging_config import get_logger

logger = get_logger(__name__)

class WhisperLanguageDetector:
    """Fallback language detector using Whisper's language detection head."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return
        logger.info("whisper.loading")
        self.model = whisper.load_model(
            "small",
            download_root=settings.MODEL_CACHE_DIR / "whisper"
        )
        self._loaded = True
        logger.info("whisper.loaded")

    def detect_language(self, audio_data: np.ndarray) -> dict:
        with torch.no_grad():
            audio = whisper.pad_or_trim(audio_data.astype(np.float32))
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            _, probs = self.model.detect_language(mel)

        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        top_lang = sorted_probs[0]

        return {
            'language_code': top_lang[0],
            'confidence': top_lang[1],
            'all_probs': dict(sorted_probs[:20])  # Top 20 languages
        }
```

**Afternoon (4 hours):**
Create `src/pipeline/stages/lid_inference.py` — the combined inference engine:

```python
from src.pipeline.models.speechbrain_lid import SpeechBrainLID
from src.pipeline.models.whisper_lid import WhisperLanguageDetector
from src.pipeline.stages.windowing import AudioChunk
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

def classify_chunk(chunk: AudioChunk) -> dict:
    """
    Primary: SpeechBrain.
    Fallback: Whisper if confidence < threshold.
    Ensemble: average both distributions if using fallback.
    """
    speechbrain = SpeechBrainLID()
    primary_result = speechbrain.classify_chunk(chunk.audio_data, chunk.sample_rate)

    if primary_result['confidence'] >= settings.LID_CONFIDENCE_THRESHOLD:
        return {**primary_result, 'model_used': 'speechbrain'}

    # Fallback to Whisper
    if settings.FALLBACK_TO_WHISPER:
        logger.debug("lid.whisper_fallback", chunk_id=chunk.chunk_id,
                     primary_confidence=primary_result['confidence'])
        whisper_detector = WhisperLanguageDetector()
        fallback_result = whisper_detector.detect_language(chunk.audio_data)

        # Ensemble: average the shared languages
        shared_langs = set(primary_result['all_probs']) & set(fallback_result['all_probs'])
        ensemble_probs = {
            lang: (primary_result['all_probs'].get(lang, 0) +
                   fallback_result['all_probs'].get(lang, 0)) / 2
            for lang in shared_langs
        }

        top_lang = max(ensemble_probs, key=ensemble_probs.get)
        return {
            'language_code': top_lang,
            'confidence': ensemble_probs[top_lang],
            'all_probs': ensemble_probs,
            'model_used': 'ensemble'
        }

    return {**primary_result, 'model_used': 'speechbrain_low_conf'}
```

---

### Day 18 (Wednesday): Batch Inference Optimization

**Morning (4 hours):**
SpeechBrain supports batched inference — classify multiple chunks in a single forward pass, which is 5–8x faster than one-at-a-time on GPU and 2–3x on CPU.

Implement `classify_batch()`:
```python
def classify_batch(self, chunks: List[AudioChunk], batch_size: int = 16) -> List[dict]:
    results = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        waveforms = torch.stack([
            torch.tensor(c.audio_data).unsqueeze(0)
            for c in batch
        ]).squeeze(1).to(self._device)

        with torch.no_grad():
            out_probs, scores, indices, text_labs = self.classifier.classify_batch(waveforms)

        for j, (chunk, prob, score, label) in enumerate(
            zip(batch, out_probs, scores, text_labs)
        ):
            lang_code = label.split(':')[0].strip()
            results.append({
                'chunk_id': chunk.chunk_id,
                'language_code': lang_code,
                'confidence': float(score),
                'all_probs': {...}
            })

    return results
```

**Afternoon (4 hours):**
- Benchmark: sequential vs. batch inference at batch sizes 8, 16, 32, 64
- Document optimal batch size per hardware configuration
- Write `tests/benchmark/test_lid_inference.py` using `pytest-benchmark`
- Add model warm-up: on worker startup, run one dummy inference to load model weights into cache

---

### Day 19 (Thursday): LID Integration Testing with Real Audio

**Morning (4 hours):**
Collect a 3-minute real broadcasting sample with:
- 0:00–0:45 → English (news intro)
- 0:45–1:30 → Hindi (reporter on ground)
- 1:30–2:00 → Assamese (interview subject)
- 2:00–2:30 → English (anchor wrap-up)
- 2:30–3:00 → Hindi + English code-switching within sentences

Manually annotate true language segments as ground truth.

Run the full stages 1-4 and compare predicted segments to ground truth. Compute:
- Per-language precision and recall
- Switch detection accuracy (how many true switches were detected within ±500ms)

**Afternoon (4 hours):**
- Identify failure modes: which language transitions are hardest?
- Hypothesis: Assamese often confused with Bengali (both Assam region languages with shared phonemes)
- Write test cases covering each failure mode as regression tests

---

### Day 20 (Friday): Model Pre-loading at Worker Startup

**Morning (4 hours):**
All models must be pre-loaded when the Celery worker starts, not on the first job (which would cause the first job to be slow and could timeout):

```python
# src/worker/celery_app.py
from celery.signals import worker_ready

@worker_ready.connect
def load_models(**kwargs):
    logger.info("worker.loading_models")
    SpeechBrainLID().load()
    WhisperLanguageDetector().load()
    SileroVAD()  # Singleton initialization loads model
    logger.info("worker.models_loaded")
```

Write a health check that verifies all models are loaded:
`GET /api/v1/health` returns `{"status": "healthy", "models": {"speechbrain": "loaded", "whisper": "loaded", "silero_vad": "loaded"}}`

**Afternoon (4 hours):**
- Wire Stage 4 (LID inference) into the orchestrator
- End-to-end test: upload 3-minute bilingual clip → stages 1-4 complete → inspect per-chunk predictions
- Week 4 retrospective

**Week 4 Deliverables Checklist:**
- [ ] `SpeechBrainLID` singleton with batch inference
- [ ] `WhisperLanguageDetector` singleton with ensemble logic
- [ ] `classify_chunk()` and `classify_batch()` with fallback logic
- [ ] Model pre-loading at worker startup
- [ ] Health check endpoint verifying model states
- [ ] Integration test with real bilingual audio
- [ ] Stages 1-4 wired in orchestrator

---

## WEEK 5: Smoothing Algorithm, Timeline Construction & JSON Output
**Theme:** "Turn raw predictions into a polished, validated timeline."
**Goal:** The complete pipeline output in validated JSON format.

### Day 21 (Monday): Smoothing Algorithm Implementation

**Morning (4 hours):**
Create `src/pipeline/stages/smoothing.py`:

```python
import numpy as np
from scipy.signal import medfilt
from typing import List
from src.pipeline.stages.windowing import AudioChunk
from src.logging_config import get_logger

logger = get_logger(__name__)

LANGUAGE_TO_INT = {}  # Built dynamically from observed languages
INT_TO_LANGUAGE = {}

def encode_languages(predictions: List[str]) -> np.ndarray:
    """Map language strings to integers for numerical smoothing."""
    for lang in predictions:
        if lang not in LANGUAGE_TO_INT:
            idx = len(LANGUAGE_TO_INT)
            LANGUAGE_TO_INT[lang] = idx
            INT_TO_LANGUAGE[idx] = lang
    return np.array([LANGUAGE_TO_INT[p] for p in predictions], dtype=np.int32)

def apply_median_filter(
    encoded: np.ndarray,
    kernel_size: int = 5
) -> np.ndarray:
    """Apply median filter. kernel_size must be odd."""
    if kernel_size % 2 == 0:
        kernel_size += 1
    return medfilt(encoded, kernel_size=kernel_size).astype(np.int32)

def build_timeline(
    chunks: List[AudioChunk],
    predictions: List[dict],
    kernel_size: int = 5
) -> List[dict]:
    """
    Full smoothing pipeline:
    1. Extract top-1 language from each chunk prediction
    2. Encode as integers
    3. Apply median filter
    4. Decode back to language strings
    5. Collapse runs → timeline segments
    6. Compute per-segment confidence as mean of chunk confidences
    """
    raw_langs = [p['language_code'] for p in predictions]
    raw_confs = [p['confidence'] for p in predictions]

    encoded = encode_languages(raw_langs)
    smoothed = apply_median_filter(encoded, kernel_size)
    smoothed_langs = [INT_TO_LANGUAGE[i] for i in smoothed]

    # Collapse consecutive same-language chunks into segments
    segments = []
    if not chunks:
        return segments

    current_lang = smoothed_langs[0]
    seg_start = chunks[0].start_seconds
    seg_confidences = [raw_confs[0]]

    for i in range(1, len(chunks)):
        if smoothed_langs[i] != current_lang:
            # Language switch detected — close current segment
            segments.append({
                'start_time': round(seg_start, 3),
                'end_time': round(chunks[i-1].end_seconds, 3),
                'language_code': current_lang,
                'confidence_score': round(float(np.mean(seg_confidences)), 4)
            })
            # Start new segment
            current_lang = smoothed_langs[i]
            seg_start = chunks[i].start_seconds
            seg_confidences = [raw_confs[i]]
        else:
            seg_confidences.append(raw_confs[i])

    # Close final segment
    segments.append({
        'start_time': round(seg_start, 3),
        'end_time': round(chunks[-1].end_seconds, 3),
        'language_code': current_lang,
        'confidence_score': round(float(np.mean(seg_confidences)), 4)
    })

    logger.info("smoothing.complete",
                raw_switches=sum(1 for i in range(1, len(raw_langs)) if raw_langs[i] != raw_langs[i-1]),
                smoothed_switches=len(segments) - 1)

    return segments
```

**Afternoon (4 hours):**
- Write unit tests for every function in `smoothing.py`:
  - Known input sequence with 1 language → 1 segment output
  - Sequence with isolated single-chunk mismatch → smoothed out by median filter
  - True switch at index 10 → switch preserved after smoothing
  - Edge case: only 1 chunk total
  - Edge case: `kernel_size` larger than `len(predictions)` (clip kernel to len)

---

### Day 22 (Tuesday): JSON Schema & Output Serialization

**Morning (4 hours):**
Create `src/models/output.py` — the Pydantic schema:

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class LanguageSegment(BaseModel):
    start_time: float = Field(..., ge=0.0, description="Segment start in seconds")
    end_time: float = Field(..., gt=0.0, description="Segment end in seconds")
    language_code: str = Field(..., min_length=2, max_length=5)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    flag: Optional[str] = Field(None, description="'low_confidence' or 'review_required'")

    @field_validator('end_time')
    @classmethod
    def end_must_be_after_start(cls, v: float, info) -> float:
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be greater than start_time')
        return v

class BroadcastMetadata(BaseModel):
    primary_languages_detected: List[str]
    total_speech_duration_seconds: float
    total_language_switches: int
    processing_duration_seconds: float

class LIDResult(BaseModel):
    broadcast_id: str
    processing_timestamp: datetime
    pipeline_version: str = Field(default="1.0.0")
    metadata: BroadcastMetadata
    timeline: List[LanguageSegment]

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)
```

**Afternoon (4 hours):**
- Write `src/pipeline/stages/output_builder.py`:
  - Takes segments list, job metadata, processing times
  - Constructs `LIDResult` Pydantic object
  - Validates schema (Pydantic raises on invalid data)
  - Flags segments with `confidence_score < 0.70` as `"low_confidence"`
  - Serializes to JSON string
  - Saves to MinIO `results/` bucket and PostgreSQL `language_events` table
- Write tests validating the full output against the expected JSON schema

---

### Day 23 (Wednesday): Edge Case Handling & Robustness

**Morning (4 hours):**
Handle the following edge cases gracefully:

- **All silence:** Audio has no speech → `timeline: []`, `total_speech_duration_seconds: 0.0`
- **Single language:** No switches → single segment spanning full duration
- **Very short broadcast (< 5s):** Handle gracefully, may produce 0-1 chunks
- **Extremely noisy audio:** VAD produces fragmented 100ms intervals → merge short intervals closer than 500ms
- **Back-to-back same language:** After smoothing, consecutive segments with the same language must be merged (defensive post-processing step)
- **High proportion of low-confidence segments (> 40%):** Flag at the `metadata` level as `"high_uncertainty_broadcast"`

**Afternoon (4 hours):**
- Implement the interval merger for very fragmented VAD output
- Write tests for all 6 edge cases above with synthetic audio fixtures

---

### Day 24 (Thursday): Full Pipeline End-to-End Test

**Morning (4 hours):**
Wire the complete 6-stage pipeline:

```python
# src/pipeline/orchestrator.py (complete)
async def run(self, job: Job) -> LIDResult:
    # Stage 1: Audio Extraction
    audio_result = await extract_audio(job.input_path, job.audio_path)

    # Stage 2: VAD
    speech_intervals = self.vad.detect_speech(str(job.audio_path))

    # Stage 3: Windowing
    chunks = list(generate_chunks(job.audio_path, speech_intervals))

    # Stage 4: LID Inference
    predictions = self.lid.classify_batch(chunks)

    # Stage 5: Smoothing
    timeline = build_timeline(chunks, predictions)

    # Stage 6: Output
    result = build_output(job, audio_result, timeline)
    await save_result(result)

    return result
```

**Afternoon (4 hours):**
- End-to-end integration test with the manually annotated 3-minute bilingual clip from Day 19
- Compare output JSON against ground truth
- Compute official metrics: F1 for language detection, timestamp precision
- Create the notebook `notebooks/03_full_pipeline_validation.ipynb`

---

### Day 25 (Friday): Result Delivery Endpoints

**Morning (4 hours):**
Complete the API result endpoints:
- `GET /api/v1/jobs/{job_id}` → job status, progress percentage, estimated completion
- `GET /api/v1/jobs/{job_id}/result` → full LID JSON (or 404 if incomplete)
- Add webhook support: clients can optionally register a callback URL, the API POSTs the result JSON to it on completion
- Add response compression (gzip) for large JSON payloads

**Afternoon (4 hours):**
- Week 5 retrospective
- Update `notebooks/03_full_pipeline_validation.ipynb` with final metrics
- Update `ARCHITECTURE.md` with the complete flow diagram

**Week 5 Deliverables Checklist:**
- [ ] `apply_median_filter()` + `build_timeline()` + tests
- [ ] `LIDResult` Pydantic schema + validation
- [ ] `output_builder.py` + MinIO/PostgreSQL persistence
- [ ] All 6 edge cases handled + tested
- [ ] Complete 6-stage orchestrator
- [ ] Result delivery API endpoints
- [ ] Webhook callback support
- [ ] Official metrics on test set documented

---

## WEEK 6: API Layer, Authentication & Service Integration
**Theme:** "Make the pipeline accessible as a production-grade service."
**Goal:** Secure, rate-limited, documented REST API ready for downstream integration.

### Day 26 (Monday): Authentication & Authorization

**Morning (4 hours):**
Implement API key authentication:
- `api_keys` table in PostgreSQL: `key_hash`, `client_name`, `created_at`, `last_used_at`, `rate_limit_rps`
- FastAPI dependency: `async def get_api_key(x_api_key: str = Header(...)) -> APIKey`
- Never store raw keys — only SHA-256 hashes
- On first run, generate an admin key via CLI: `poetry run python -m src.cli generate-api-key --name "admin"`

**Afternoon (4 hours):**
- Implement rate limiting using Redis sliding window algorithm:
  - Store request count per API key per minute in Redis with TTL
  - `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` response headers
  - 429 Too Many Requests response when limit exceeded
- Write tests for authentication and rate limiting

---

### Day 27 (Tuesday): File Upload & URL Input Hardening

**Morning (4 hours):**
Harden the file upload endpoint:
- **File size limit:** Reject files > 2 GB with 413 Payload Too Large
- **MIME type validation:** Accept only `video/*` and `audio/*` content types (and wav, mp4, mkv, mp3, m4a, ogg explicitly)
- **Magic bytes check:** Don't trust client-provided MIME type — validate file magic bytes using `python-magic`
- **Filename sanitization:** Strip all non-alphanumeric characters from uploaded filenames, limit to 200 chars
- **Checksum:** Compute SHA-256 of uploaded file, store in job record, return in API response for client verification
- **Deduplication:** If SHA-256 matches an existing job in the past 24 hours, return the existing result

Harden the URL submission endpoint (`POST /api/v1/analyze/url`):
- **Schema validation:** Reject anything that is not a well-formed `https://` URL (use `pydantic.AnyHttpsUrl`)
- **Platform allowlist:** Use `yt_dlp.extractor.gen_extractors()` to check the URL against known extractors; reject URLs from unsupported or disallowed platforms with 422 Unprocessable Entity and a descriptive error message
- **SSRF protection:** Resolve the URL's domain to an IP and reject any that resolve to private/loopback ranges (10.x, 172.16.x, 192.168.x, 127.x) to prevent Server-Side Request Forgery attacks
- **Duration cap:** After `yt_dlp.extract_info(url, download=False)` (metadata-only probe), reject videos longer than a configurable `MAX_URL_DURATION_SECONDS` (default: 7200 seconds / 2 hours) before any download begins
- **Deduplication:** Store the canonical URL (from `info['webpage_url']`) in PostgreSQL; if the same URL was successfully processed in the past 24 hours, return the cached result immediately

**Afternoon (4 hours):**
- Implement chunked upload support for very large files (> 500 MB):
  - `POST /api/v1/upload/init` → returns `upload_id`
  - `PUT /api/v1/upload/{upload_id}/chunk/{part_number}` → uploads a part
  - `POST /api/v1/upload/{upload_id}/complete` → finalizes and triggers analysis
- Write `src/pipeline/stages/url_downloader.py`:
  - `async def download_from_url(url: str, output_dir: Path) -> Path` — wraps yt-dlp in a thread pool executor (non-blocking)
  - Logs platform name, video title, duration, and download speed via structlog
  - Raises `URLDownloadError` (added to `exceptions.py`) for private videos, geo-blocked content, deleted videos, and yt-dlp extraction failures
  - Adds `URLDownloadError` to the Celery task retry logic — retries up to 2 times for transient network failures; no retry for permanent errors (private video, unsupported URL)

---

### Day 28 (Wednesday): OpenAPI Documentation & SDK

**Morning (4 hours):**
Enrich FastAPI endpoint definitions with full OpenAPI metadata:
```python
@router.post(
    "/analyze",
    response_model=JobCreatedResponse,
    status_code=202,
    summary="Submit a broadcast for language identification",
    description="""
    Accepts a video or audio file and initiates asynchronous LID analysis.
    Returns a job ID for status polling.

    **Supported formats:** MP4, MKV, AVI, MOV, MP3, WAV, AAC, OGG, FLAC

    **Max file size:** 2 GB

    **Processing time:** ~1 minute per 10 minutes of audio (on CPU)

    To submit a social media URL instead of a file, use `POST /api/v1/analyze/url`
    with body `{"url": "https://..."}`. Supported platforms include YouTube,
    Facebook, Instagram (public), X/Twitter, Dailymotion, Vimeo, and 1000+ others.
    """,
    responses={
        202: {"description": "Job accepted and queued"},
        400: {"description": "Invalid file format or unsupported URL"},
        413: {"description": "File too large or video duration exceeds limit"},
        422: {"description": "URL platform not supported or failed SSRF check"},
        429: {"description": "Rate limit exceeded"},
    }
)
```

**Afternoon (4 hours):**
- Set up MkDocs with Material theme
- Write documentation pages:
  - `docs/quickstart.md` — "Your first LID analysis in 5 minutes"
  - `docs/api-reference.md` — auto-generated from OpenAPI schema
  - `docs/architecture.md` — pipeline stages with diagrams
  - `docs/configuration.md` — all config variables with descriptions
  - `docs/adding-a-language.md` — how to extend to a new language

---

### Day 29 (Thursday): CLI Tool

**Morning (4 hours):**
Create a CLI wrapper for the pipeline using `typer` (FastAPI's sibling for CLIs):

```python
# src/cli.py
import typer
app = typer.Typer()

@app.command()
def analyze(
    input_file: Path = typer.Argument(..., help="Path to video/audio file"),
    output_file: Path = typer.Option(None, help="Output JSON path (default: stdout)"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """Run LID analysis on a local file without the API."""
    ...

@app.command()
def analyze_url(
    url: str = typer.Argument(..., help="Public URL of a YouTube/Facebook/Instagram/etc. video"),
    output_file: Path = typer.Option(None, help="Output JSON path (default: stdout)"),
    verbose: bool = typer.Option(False, "--verbose", "-v")
):
    """Download audio from a social media URL and run LID analysis on it."""
    ...

@app.command()
def generate_api_key(name: str = typer.Option(...)):
    """Generate a new API key for a client."""
    ...
```

**Afternoon (4 hours):**
- Docker-friendly entrypoints:
  - `docker run lid-pipeline analyze /data/input.mp4`
  - `docker run lid-pipeline analyze-url "https://www.youtube.com/watch?v=..."`
- Write man-page-style help text for both commands
- Integration tests:
  - `cli analyze tests/fixtures/bilingual_3min.mp4 | python -m json.tool`
  - `cli analyze-url "https://www.youtube.com/watch?v=<public_test_video>" | python -m json.tool` (use a known short public video in CI with a mocked yt-dlp call)

---

### Day 30 (Friday): Integration Test Suite

**Morning (4 hours):**
Write a comprehensive integration test suite in `tests/integration/`:
- Full upload → process → retrieve flow
- Full URL submission → process → retrieve flow (yt-dlp mocked with a pre-downloaded fixture file to avoid real network calls in CI)
- URL rejection cases: private URL, SSRF attempt (private IP range), unsupported platform, video exceeding duration cap
- Authentication rejection (invalid key, missing key, expired key)
- Rate limit trigger (burst 100 requests)
- Large file upload (use a generated 1 GB WAV of silence)
- Concurrent jobs (submit 5 jobs simultaneously, verify all complete correctly)
- Webhook delivery test (set up a mock webhook receiver with `httpx`)

**Afternoon (4 hours):**
- Week 6 retrospective
- Document integration test results
- All tests must pass in CI before Week 7

**Week 6 Deliverables Checklist:**
- [ ] API key authentication + SHA-256 hashing
- [ ] Redis-based rate limiting
- [ ] File upload hardening (MIME, magic bytes, size, checksum, dedup)
- [ ] Chunked upload support
- [ ] `POST /api/v1/analyze/url` endpoint with yt-dlp integration
- [ ] `url_downloader.py` stage (yt-dlp wrapper with SSRF protection, duration cap, dedup)
- [ ] URL input hardening (platform allowlist, SSRF check, duration probe before download)
- [ ] `analyze-url` CLI command
- [ ] Full OpenAPI documentation (both endpoints documented)
- [ ] MkDocs documentation site
- [ ] CLI tool with `typer`
- [ ] Comprehensive integration test suite (including URL rejection cases)

---

## WEEK 7: Testing, Benchmarking & Optimization
**Theme:** "Prove it works, prove it's fast."
**Goal:** ≥ 80% test coverage, all KPIs met, no P0/P1 bugs.

### Day 31 (Monday): Test Coverage Audit

**Morning:**
Run `pytest --cov=src --cov-report=html` and inspect the HTML coverage report.
Identify all uncovered lines and write tests for each one.
Target: 80% coverage overall, 95% for pipeline stages.

**Afternoon:**
Focus on integration gaps:
- Every error path must be covered
- Every Pydantic validation error must be tested
- Mock all external services (MinIO, PostgreSQL, Redis) in unit tests using `pytest-mock`

---

### Day 32 (Tuesday): Performance Benchmarking

Run a comprehensive benchmark suite:

**Audio lengths tested:** 1 min, 5 min, 15 min, 30 min, 60 min

**Metrics per stage:**

| Stage | Target (CPU) | Target (GPU) |
|-------|-------------|-------------|
| Audio extraction (FFmpeg) | < 0.1× realtime | < 0.1× realtime |
| VAD (Silero) | < 0.05× realtime | < 0.02× realtime |
| Windowing | < 0.02× realtime | < 0.02× realtime |
| LID batch inference | < 1× realtime | < 0.2× realtime |
| Smoothing + output | < 0.01× realtime | < 0.01× realtime |

If any stage misses its target:
- **LID inference:** increase batch size, enable torch.compile(), half-precision (fp16) inference
- **FFmpeg extraction:** check disk I/O, ensure SSD; use `/dev/shm` (RAM disk) for temp files
- **VAD:** already very fast; check if model is on CPU when GPU is available

---

### Day 33 (Wednesday): Accuracy Deep-Dive

**Morning:**
Build a formal evaluation set:
- Collect 50 broadcast clips (1-5 minutes each) from publicly available regional news archives
- Mix of clean and noisy conditions, all possible language pairs
- Manually annotate with precise timestamps (use Audacity with label tracks)
- Establish inter-annotator agreement (if 2 annotators available)

**Afternoon:**
Run the full pipeline on all 50 clips. Compute:
- Overall F1 per language
- Switch detection accuracy (precision/recall for detecting a switch within ±500ms)
- Confusion matrix (which language pairs are confused most)
- False switch rate (switches in segments that should be monolingual)

---

### Day 34 (Thursday): Optimization Sprint

Based on benchmarks and accuracy analysis, identify and fix the top 3 issues.

**Common optimizations:**
1. **Torch compilation:** `model = torch.compile(model)` — ~30% inference speed boost on PyTorch 2.x
2. **Half-precision inference:** `model.half()` on GPU — 2x memory reduction, ~1.5x speed boost
3. **Dynamic batching:** Queue chunks and process in batches of 32 rather than processing per-chunk
4. **Audio preprocessing caching:** Cache mel-spectrograms between VAD and LID stages (avoid computing twice)
5. **Async orchestration:** Run VAD and model warm-up concurrently using `asyncio.gather()`

---

### Day 35 (Friday): Load Testing & Soak Test

**Morning (4 hours):**
Load test with Locust:
```python
from locust import HttpUser, task

class LIDUser(HttpUser):
    @task
    def submit_job(self):
        with open("tests/fixtures/bilingual_30s.mp4", "rb") as f:
            self.client.post("/api/v1/analyze", files={"file": f},
                             headers={"X-API-Key": "test_key"})
```

Test scenarios:
- 10 concurrent users for 5 minutes
- 50 concurrent users for 5 minutes (verify rate limiting activates)
- 5 concurrent users for 30 minutes (soak test — check for memory leaks)

**Afternoon (4 hours):**
- Fix any memory leaks found (common culprit: chunks not being cleaned up after job completion)
- Ensure `ChunkStore.cleanup()` is always called in a `finally` block
- Week 7 retrospective

**Week 7 Deliverables Checklist:**
- [ ] ≥ 80% test coverage
- [ ] All pipeline stage benchmarks meet targets
- [ ] Formal evaluation set (50 clips) with metrics documented
- [ ] Top 3 optimizations implemented
- [ ] Load test at 10 and 50 concurrent users passes
- [ ] No memory leaks in 30-minute soak test

---

## WEEK 8: Deployment, Documentation & Launch
**Theme:** "Ship it."
**Goal:** Production deployment on a real server, complete documentation, monitoring live.

### Day 36 (Monday): Production Infrastructure Setup

- Provision a production server (minimum specs from §4.1)
- Set up DNS, TLS certificate (Let's Encrypt via Certbot), NGINX reverse proxy
- Configure NGINX as reverse proxy to FastAPI/Uvicorn, with:
  - SSL termination
  - Request size limit: 2 GB
  - Gzip compression
  - Rate limiting headers passthrough
- Set up firewall rules: only ports 80, 443, and SSH from known IPs
- Configure daily PostgreSQL backups to MinIO

---

### Day 37 (Tuesday): Monitoring Stack Deployment

- Deploy Prometheus with a `prometheus.yml` scraping the API and Celery worker
- Deploy Grafana with pre-built dashboards:
  - **Pipeline Overview:** Jobs per hour, success rate, average processing time
  - **Model Performance:** Confidence distributions, fallback rate (SpeechBrain → Whisper), language distribution
  - **Infrastructure:** CPU, memory, disk I/O per container
  - **API:** Request rate, latency P50/P95/P99, error rate
- Set up Grafana alerting: PagerDuty/email/Slack notifications when:
  - Error rate > 5% over 5 minutes
  - P99 latency > 60 seconds
  - Any Docker container restarts
  - Disk usage > 80%

---

### Day 38 (Wednesday): Staged Rollout & Smoke Testing

**Morning (4 hours):**
Deploy to a staging environment (identical to production). Run the full integration test suite against staging. All tests must pass before production deploy.

**Afternoon (4 hours):**
Production deploy with zero-downtime rolling update:
```bash
docker-compose pull                    # Pull new images
docker-compose up -d --no-deps api     # Update API (graceful)
docker-compose up -d --no-deps worker  # Update worker
```

Run smoke tests on production:
- Upload a known 3-minute bilingual clip
- Verify result matches expected output within acceptable tolerance
- Verify Prometheus metrics are updating
- Verify Grafana dashboards show live data

---

### Day 39 (Thursday): Documentation Finalization

- Complete all MkDocs pages
- Record a 5-minute demo video showing:
  - API call via Postman (or curl)
  - Uploaded video being processed
  - JSON result with timestamps
  - Grafana dashboard showing live metrics
- Write runbook for common operational tasks:
  - How to add a new Celery worker
  - How to clear the job queue
  - How to regenerate an API key
  - How to restore from backup
  - How to add a new language to the pipeline

---

### Day 40 (Friday): Project Handoff & Launch

**Morning (4 hours):**
- Final KPI verification: run the evaluation pipeline on the 50-clip test set one more time on production
- All KPIs must be green before launch announcement
- Final code review and merge of all PRs to `main`
- Tag release: `git tag v1.0.0`

**Afternoon (4 hours):**
- Launch announcement to stakeholders
- Share API documentation link
- Schedule a 2-week post-launch check-in to review Grafana metrics and user feedback
- Create backlog for v1.1 features: real-time streaming support, speaker diarization, additional languages

**Week 8 Deliverables Checklist:**
- [ ] Production server provisioned and secured
- [ ] NGINX + TLS configured
- [ ] Prometheus + Grafana monitoring live
- [ ] Staging deploy with all integration tests passing
- [ ] Production deploy (zero-downtime)
- [ ] Smoke tests on production passing
- [ ] Complete MkDocs documentation site live
- [ ] Demo video recorded
- [ ] Operational runbook written
- [ ] `v1.0.0` release tagged
- [ ] All KPIs verified on production

---

# 6. DATA STRATEGY & DATASET PREPARATION

## 6.1 Training / Fine-tuning Data (if needed)

The project uses pretrained models (SpeechBrain VoxLingua107, Whisper small), so no training is needed for the base case. However, if fine-tuning is needed for the specific Assamese broadcasting domain:

**Sources for Assamese and Hindi speech:**
- OpenSLR (open-source speech/language resources) — SLR70 (Assamese), SLR103 (Hindi)
- IIIT-H's MILE Lab corpora — Indian language broadcast speech
- AIR (All India Radio) open archives
- Common Voice (Mozilla) — has Hindi, may have Assamese contributions

**Annotation format for fine-tuning:**
A TSV file with columns: `audio_path`, `language_code`, `start_seconds`, `end_seconds`

## 6.2 Evaluation Data

50 clips (minimum) with:
- At least 10 clips per language pair (EN-HI, EN-AS, HI-AS, EN-HI-AS)
- At least 5 clips per noise condition (clean studio, outdoor, phone call)
- Manual annotation by 2 independent annotators, resolving disagreements
- Gold-standard timestamps stored as `tests/evaluation/annotations/*.json`

## 6.3 Data Versioning

Use DVC (Data Version Control) to version large datasets:
```bash
dvc init
dvc add tests/evaluation/audio/
git add tests/evaluation/audio.dvc .gitignore
git commit -m "feat: add evaluation dataset v1"
dvc push  # Pushes to MinIO remote
```

---

# 7. TESTING STRATEGY

## 7.1 Test Pyramid

```
         ┌──────────────────────┐
         │    E2E Tests (5%)    │  Full API + real files
         ├──────────────────────┤
         │ Integration Tests    │  Multi-component, mocked externals
         │       (25%)          │
         ├──────────────────────┤
         │   Unit Tests (70%)   │  Single function/class, all mocked
         └──────────────────────┘
```

## 7.2 Test Categories & Marks

```python
# pytest marks
@pytest.mark.unit           # Fast, no I/O, no models
@pytest.mark.integration    # Real DB, Redis; mocked models
@pytest.mark.e2e            # Full stack, real models
@pytest.mark.slow           # > 30 seconds (excluded from fast CI)
@pytest.mark.gpu            # Requires CUDA GPU
@pytest.mark.benchmark      # Performance benchmarks
```

CI runs `unit` and `integration` tests on every push. `e2e` and `slow` tests run nightly on `develop`.

## 7.3 Audio Test Fixtures

Synthetic test audio generated during `conftest.py` session setup using `scipy.io.wavfile`:
- `silence_5s.wav` — pure silence
- `noise_5s.wav` — Gaussian white noise
- `tone_440hz_5s.wav` — pure tone (not speech)
- `synthetic_speech_en_5s.wav` — generated by `espeak-ng` in English
- `synthetic_speech_hi_5s.wav` — generated by `espeak-ng` in Hindi
- `synthetic_bilingual_10s.wav` — concatenated EN (5s) + HI (5s)

---

# 8. MONITORING & OBSERVABILITY

## 8.1 Key Metrics

```python
# src/metrics.py (Prometheus client)
from prometheus_client import Counter, Histogram, Gauge

JOBS_TOTAL = Counter('lid_jobs_total', 'Total jobs', ['status'])
PROCESSING_DURATION = Histogram(
    'lid_processing_duration_seconds',
    'Processing duration per stage',
    ['stage'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
)
CONFIDENCE_SCORE = Histogram(
    'lid_confidence_score',
    'LID confidence scores',
    ['language_code'],
    buckets=[0.1, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99]
)
ACTIVE_JOBS = Gauge('lid_active_jobs', 'Currently processing jobs')
FALLBACK_RATE = Counter('lid_whisper_fallbacks_total', 'Times Whisper fallback was used')
```

## 8.2 Structured Log Format

Every log line is a JSON object:
```json
{
  "timestamp": "2026-06-20T14:30:01.234Z",
  "level": "info",
  "logger": "src.pipeline.stages.lid_inference",
  "event": "lid.chunk_classified",
  "job_id": "abc123",
  "chunk_id": "chunk_000042",
  "language_code": "hi",
  "confidence": 0.923,
  "duration_ms": 87,
  "model_used": "speechbrain"
}
```

## 8.3 Alerting Rules (Prometheus AlertManager)

```yaml
groups:
  - name: lid_pipeline
    rules:
      - alert: HighErrorRate
        expr: rate(lid_jobs_total{status="failed"}[5m]) / rate(lid_jobs_total[5m]) > 0.05
        for: 2m
        annotations:
          summary: "LID pipeline error rate above 5%"

      - alert: SlowProcessing
        expr: histogram_quantile(0.99, rate(lid_processing_duration_seconds_bucket[5m])) > 60
        for: 5m
        annotations:
          summary: "P99 processing latency above 60 seconds"
```

---

# 9. RISK REGISTER & MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Assamese LID accuracy < 85% | Medium | High | Fine-tune SpeechBrain on Assamese broadcasting data; collect 10h labeled data |
| GPU not available in production | Low | Medium | Ensure all targets are met on CPU; GPU is a performance bonus, not a requirement |
| Silero VAD misses non-standard speech styles (fast speech, whispers) | Medium | Medium | Tune `threshold` lower (0.3); add energy-based fallback VAD |
| Large video files (> 1GB) cause memory issues | Low | High | Memory-mapped audio; streaming chunk generation; temp file cleanup |
| Code-switching within a single sentence | High | Low | Sub-sentence-level LID is out of scope for v1.0; document as known limitation |
| SpeechBrain model download fails in air-gapped environment | Low | High | Bundle model weights in Docker image; provide offline model cache instructions |
| Redis failure causes job loss | Low | High | Redis persistence (AOF mode); Celery task acknowledgment only after successful DB write |
| Week slippage on any deliverable | Medium | Medium | Weekly buffer: all weeks planned for 4 days; 1 day per week is buffer for reviews, unexpected issues |
| SpeechBrain API changes between v1.0 and future versions | Low | Medium | Pin exact version in `pyproject.toml`; pin Docker base images by digest |
| False switch detection in music segments | Medium | Low | VAD should filter music; add a post-processing check: segments < 1.0s are merged with neighbors |
| Social media platform blocks yt-dlp (anti-bot measures, extractor breakage) | Medium | Medium | Pin yt-dlp to a known good version; monitor yt-dlp GitHub for extractor fixes; implement graceful 503 response with `"retry_after"` hint when download fails |
| SSRF attack via crafted URL submission | Low | Critical | Resolve domain to IP before download; block all RFC-1918 ranges; apply allowlist of known platform domains as an additional layer |
| Platform Terms of Service violation from high-volume downloading | Medium | High | Document TOS compliance responsibility to API consumers; implement per-domain rate limiting (e.g., max 60 YouTube downloads/hour); log all URL downloads for audit |

---

# 10. TEAM ROLES & RESPONSIBILITIES

| Role | Responsibilities | Weeks Active |
|------|-----------------|-------------|
| ML Engineer (Lead) | LID model selection, SpeechBrain + Whisper integration, smoothing algorithm, accuracy evaluation | 1–7 |
| Backend Engineer | FastAPI, Celery, PostgreSQL, MinIO, authentication, API hardening | 1–6 |
| Audio/DSP Engineer | FFmpeg pipeline, Silero VAD tuning, windowing engine, audio fixtures | 1–5 |
| DevOps / Infrastructure Engineer | Docker Compose, GitHub Actions, Prometheus, Grafana, production deployment | 1–2, 7–8 |
| QA Engineer | Test strategy, integration tests, load tests, evaluation dataset annotation | 3–8 |

**For a solo developer:** assign 2 days per week to each role. The backend and audio stages are the most parallel-friendly; infrastructure can be done on evenings.

---

# 11. DEFINITION OF DONE

A feature is considered "Done" only when ALL of the following are true:

1. **Code written** — Feature branch created, code implemented
2. **Tests written** — Unit tests coverage ≥ 80% for new code
3. **Tests passing** — All existing tests still pass (no regressions)
4. **CI passing** — GitHub Actions (lint + test + build) is green
5. **PR reviewed** — At least 1 peer review and approval
6. **Documentation updated** — Docstrings added, MkDocs page updated if needed
7. **Metrics instrumented** — Relevant Prometheus metrics added
8. **Structured logging added** — All new code paths emit structured log lines
9. **Merged to develop** — PR squash-merged to `develop`
10. **Deployed to staging** — CI auto-deployed to staging environment

A sprint is "Done" only when all items on the week's deliverables checklist above are done.

---

# 12. APPENDIX: FILE & DIRECTORY STRUCTURE

```
lid-pipeline/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── deploy.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/
│   ├── quickstart.md
│   ├── architecture.md
│   ├── api-reference.md
│   ├── configuration.md
│   └── adding-a-language.md
│
├── notebooks/
│   ├── 01_vad_analysis.ipynb
│   ├── 02_windowing_visualization.ipynb
│   └── 03_full_pipeline_validation.ipynb
│
├── src/
│   ├── __init__.py
│   ├── config.py                    # Pydantic Settings
│   ├── logging_config.py            # structlog setup
│   ├── metrics.py                   # Prometheus metrics
│   ├── cli.py                       # Typer CLI
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app factory
│   │   ├── dependencies.py          # auth, rate limiting
│   │   └── routers/
│   │       ├── analyze.py           # POST /analyze
│   │       ├── jobs.py              # GET /jobs/{id}
│   │       └── health.py            # GET /health
│   │
│   ├── worker/
│   │   ├── celery_app.py            # Celery instance + signals
│   │   └── tasks.py                 # @celery.task definitions
│   │
│   ├── pipeline/
│   │   ├── orchestrator.py          # LIDPipelineOrchestrator
│   │   ├── exceptions.py            # Custom exceptions
│   │   ├── stages/
│   │   │   ├── url_downloader.py        # yt-dlp wrapper for social media URLs
│   │   │   ├── audio_extraction.py
│   │   │   ├── voice_activity_detection.py
│   │   │   ├── windowing.py
│   │   │   ├── lid_inference.py
│   │   │   ├── smoothing.py
│   │   │   └── output_builder.py
│   │   └── models/
│   │       ├── speechbrain_lid.py
│   │       └── whisper_lid.py
│   │
│   ├── storage/
│   │   ├── minio_client.py
│   │   └── chunk_store.py
│   │
│   └── db/
│       ├── base.py                  # SQLAlchemy base
│       ├── models.py                # ORM models
│       └── repositories/
│           ├── job_repository.py
│           ├── metrics_repository.py
│           └── event_repository.py
│
├── tests/
│   ├── conftest.py                  # Shared fixtures, test DB setup
│   ├── fixtures/
│   │   └── audio/                   # Synthetic test WAV files
│   ├── unit/
│   │   ├── test_audio_extraction.py
│   │   ├── test_vad.py
│   │   ├── test_windowing.py
│   │   ├── test_lid_inference.py
│   │   ├── test_smoothing.py
│   │   └── test_output_builder.py
│   ├── integration/
│   │   ├── test_api_analyze.py
│   │   ├── test_api_jobs.py
│   │   └── test_storage.py
│   ├── e2e/
│   │   └── test_full_pipeline.py
│   ├── evaluation/
│   │   ├── annotations/             # Ground truth JSON files
│   │   └── run_evaluation.py        # Compute F1, switch accuracy
│   └── benchmark/
│       └── test_performance.py
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile
│   │   ├── Dockerfile.worker
│   │   └── .dockerignore
│   ├── nginx/
│   │   └── nginx.conf
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alert_rules.yml
│   └── grafana/
│       └── dashboards/
│           ├── pipeline_overview.json
│           └── infrastructure.json
│
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
│
├── models/                          # Model weight cache (gitignored)
│
├── docker-compose.yml
├── docker-compose.override.yml      # Local dev overrides
├── pyproject.toml
├── poetry.lock
├── ruff.toml
├── mypy.ini
├── .pre-commit-config.yaml
├── .env.example
├── mkdocs.yml
├── ARCHITECTURE.md
├── CONTRIBUTING.md
└── README.md
```

---

*Document version: 1.1.0 | Created: June 20, 2026 | Updated: July 1, 2026 (added social media URL ingestion via yt-dlp) | Project duration: 8 weeks (40 working days)*
