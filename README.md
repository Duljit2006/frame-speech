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
- **✍️ Guided Smart Transcription:** Feeds the exact language timeline into OpenAI's Whisper model to enforce the correct alphabet and language during transcription.
- **✨ Beautiful Web Interface:** A completely asynchronous Vanilla JS + HTML/CSS frontend with Server-Sent Events (SSE) for live job tracking.

## 🏗️ Architecture

```mermaid
graph TD
    A[Raw Video / Audio URL] -->|yt-dlp + FFmpeg| B(Audio Extractor)
    B -->|16kHz Mono WAV| C(Voice Activity Detector)
    C -->|Removes Silence| D(Segmentation Engine)
    D -->|3-Second Chunks| E(Language Detector)
    E -->|SpeechBrain + Whisper| F(Timeline Smoother)
    F -->|Clean Language Timeline| G(Smart Transcriber)
    G -->|Subtitles| H[Final Outputs: SRT, TXT & Web UI]
    
    style A fill:#e2e2e2,stroke:#333,stroke-width:2px
    style H fill:#81B29A,stroke:#333,stroke-width:2px
    style B fill:#E07A5F,stroke:#333
    style C fill:#F2CC8F,stroke:#333
    style D fill:#3D2C2E,stroke:#333,color:#fff
    style E fill:#8B7E74,stroke:#333,color:#fff
    style F fill:#E8DDD3,stroke:#333
    style G fill:#B5838D,stroke:#333,color:#fff
```

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

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the Application**
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
