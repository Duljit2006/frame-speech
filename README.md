<div align="center">
  
# 🎙️ FrameSpeech
**AI Audio Intelligence Pipeline for Code-Switched Transcription**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-Hub-ee4c2c.svg?style=flat&logo=PyTorch&logoColor=white)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*An advanced AI-powered pipeline capable of analyzing videos and audio files to automatically detect and transcribe multiple languages seamlessly.*

</div>

---

## 📌 The Problem

When speakers mix multiple languages (e.g., speaking English and Hindi in the same sentence), standard AI models get confused. They try to force everything into one language, resulting in severe "hallucinations" or completely broken transcriptions. 

**FrameSpeech** solves this by actively monitoring the language *second-by-second*, ensuring accurate, code-switched subtitles.

## 🚀 Features

- **📺 Direct YouTube Extraction:** Paste any YouTube URL and the system automatically rips, downmixes, and standardizes the audio track.
- **🔇 Smart Silence Filtering:** Uses Silero VAD to detect exact timestamps of human speech, throwing away background music and silence to save GPU memory.
- **🧠 Granular Language Detection:** Chops speech into 3-second overlapping windows and analyzes them using SpeechBrain (ECAPA-TDNN).
- **⏱️ Timeline Smoothing:** Applies a non-linear median filter to fix AI hallucinations and create a cohesive language timeline.
- **✍️ Guided Smart Transcription:** Feeds the exact language timeline into OpenAI's `faster-whisper` model to enforce the correct alphabet and language during transcription.
- **🤖 Gemini AI Text Correction:** A powerful post-processing layer using a full-context batching algorithm to merge fragmented sentences, enforce proper native orthography (like Assamese), and preserve English loanwords.
- **✨ Beautiful Web Interface:** A completely asynchronous Vanilla JS + HTML/CSS frontend featuring Server-Sent Events (SSE) for live tracking, Dual Language Analytics charts, and dynamic code-switch highlighting.

## 🏗️ Architecture

```mermaid
graph TD
    A["🎬 Raw Video / Audio URL"] -->|"Downloads & Rips"| B("1. Audio Extractor")
    B -->|"16kHz Mono WAV"| C("2. Voice Activity Detector")
    C -->|"Removes Silence"| D("3. Segmentation Engine")
    D -->|"3-Second Chunks"| E("4. Language Detector")
    E -->|"Raw AI Predictions"| F("5. Timeline Smoother")

    F -->|"Clean Language Timeline"| G("6. Whisper Transcriber")
    G -->|"Raw Transcript Segments"| H("7. Gemini Text Corrector")
    H -->|"Corrected Sentences"| I["📄 Final Outputs: SRT, TXT & Web UI"]

    style A fill:#e2e2e2,stroke:#333,stroke-width:2px,color:#000
    style B fill:#E07A5F,stroke:#333,stroke-width:2px,color:#fff
    style C fill:#F2CC8F,stroke:#333,stroke-width:2px,color:#000
    style D fill:#3D2C2E,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#8B7E74,stroke:#333,stroke-width:2px,color:#fff
    style F fill:#E8DDD3,stroke:#333,stroke-width:2px,color:#000
    style G fill:#457B9D,stroke:#333,stroke-width:2px,color:#fff
    style H fill:#B5838D,stroke:#333,stroke-width:2px,color:#fff
    style I fill:#81B29A,stroke:#333,stroke-width:2px,color:#000
```

### 📂 Codebase Mapping
Each block in the pipeline maps directly to a specific Python module located in `lid-pipeline/src/pipeline/stages/`:

| Pipeline Block | Description | Source File |
|---|---|---|
| **1. Audio Extractor** | Downloads and standardizes audio | [`audio_extractor.py`](lid-pipeline/src/pipeline/stages/audio_extractor.py) |
| **2. Voice Activity Detector** | Removes silence using Silero VAD | [`vad.py`](lid-pipeline/src/pipeline/stages/vad.py) |
| **3. Segmentation Engine** | Chops audio into 3-second overlapping chunks | [`segmentation.py`](lid-pipeline/src/pipeline/stages/segmentation.py) |
| **4. Language Detector** | Runs SpeechBrain ECAPA-TDNN predictions | [`lid_processor.py`](lid-pipeline/src/pipeline/stages/lid_processor.py) |
| **5. Timeline Smoother** | Fixes predictions using median filters | [`smoothing.py`](lid-pipeline/src/pipeline/stages/smoothing.py) |
| **6. Whisper Transcriber** | Runs `faster-whisper` with language hints | [`transcriber.py`](lid-pipeline/src/pipeline/stages/transcriber.py) |
| **7. Gemini Text Corrector** | Fixes orthography and sentence fragmentation | [`text_corrector.py`](lid-pipeline/src/pipeline/stages/text_corrector.py) |
| **Orchestrator** | Glues all the stages together into a single pipeline | [`../orchestrator.py`](lid-pipeline/src/pipeline/orchestrator.py) |

## 🛠️ Setup & Installation

**Prerequisites:**
- Windows/Linux with Python 3.11+
- FFmpeg installed and in your system PATH
- An NVIDIA GPU (4GB+ VRAM recommended) for CUDA acceleration

**1. Clone the repository**
```bash
git clone https://github.com/Duljit2006/frame-speech.git
cd frame-speech
```

**2. Set up the virtual environment**
```bash
cd lid-pipeline
python -m venv venv
venv\Scripts\activate
```

**3. Environment Variables**
Create a `.env` file in the project root directory and add your Google Gemini API key (required for Model 3 Text Correction):
```ini
GEMINI_API_KEY="your_api_key_here"
```

**4. Install dependencies**
```bash
pip install -r requirements.txt
```

**5. Run the Application**
If you are on Windows, simply double-click the `start_server.bat` file in the root directory!
Alternatively, run:
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 📸 Interface

The frontend provides an intuitive Workspace environment. You can paste URLs, upload local files, choose your Whisper model size (Tiny through Large-v3), and track processing progress live.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Duljit2006/frame-speech/issues).

## 📝 License
This project is [MIT](https://opensource.org/licenses/MIT) licensed.
