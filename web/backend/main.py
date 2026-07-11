import asyncio
import os
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.config import state, PIPELINE_ROOT
from backend.core.job_manager import job_manager
from backend.api import routes_jobs, routes_sse
from src.pipeline.stages.audio_extractor import AudioExtractor
from src.pipeline import LIDPipeline

app = FastAPI(title="FrameSpeech API")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task for cleanup
async def cleanup_task():
    while True:
        # Clean jobs older than 120 minutes
        num_cleaned = job_manager.cleanup_old_jobs(max_age_minutes=120)
        if num_cleaned > 0:
            print(f"[Cleanup] Removed {num_cleaned} old jobs from memory.")
            
        # Clean old audio files
        audio_dir = PIPELINE_ROOT / "data" / "processed_audio"
        if audio_dir.exists():
            now = time.time()
            max_age_seconds = 120 * 60
            for f in audio_dir.glob("*.wav"):
                if f.is_file():
                    age = now - f.stat().st_mtime
                    if age > max_age_seconds:
                        try:
                            os.remove(f)
                            print(f"[Cleanup] Deleted old file: {f.name}")
                        except Exception as e:
                            print(f"[Cleanup] Failed to delete {f.name}: {e}")

        # Clean old download files (SRT, TXT)
        downloads_dir = PIPELINE_ROOT / "data" / "downloads"
        if downloads_dir.exists():
            now = time.time()
            max_age_seconds = 120 * 60
            for f in downloads_dir.iterdir():
                if f.is_file() and f.suffix in (".srt", ".txt"):
                    age = now - f.stat().st_mtime
                    if age > max_age_seconds:
                        try:
                            os.remove(f)
                            print(f"[Cleanup] Deleted old download: {f.name}")
                        except Exception as e:
                            print(f"[Cleanup] Failed to delete {f.name}: {e}")
                            
        await asyncio.sleep(60 * 5) # Run every 5 minutes

@app.on_event("startup")
async def startup_event():
    print("=============================================")
    print("Starting FrameSpeech Server...")
    print("Loading heavy AI models into GPU memory...")
    # Initialize the pipelines (this takes a few seconds)
    state.extractor = AudioExtractor()
    state.lid_pipeline = LIDPipeline()
    print("Models loaded successfully!")
    print("=============================================")
    
    # Start cleanup task
    asyncio.create_task(cleanup_task())

from fastapi.responses import RedirectResponse

# Include API routers
app.include_router(routes_jobs.router)
app.include_router(routes_sse.router)

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/app")


# Mount the static folders
frontend_dir = Path(__file__).parent.parent / "frontend"
app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

audio_dir = PIPELINE_ROOT / "data" / "processed_audio"
if not audio_dir.exists():
    os.makedirs(audio_dir, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

downloads_dir = PIPELINE_ROOT / "data" / "downloads"
if not downloads_dir.exists():
    os.makedirs(downloads_dir, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=str(downloads_dir)), name="downloads")
