import os
import tempfile
import threading
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from backend.core.job_manager import job_manager
from backend.services.extractor_service import run_extractor_job
from backend.services.lid_service import run_lid_job
from backend.services.transcription_service import run_transcription_job

router = APIRouter()

class URLInput(BaseModel):
    url: str

class TranscribeInput(BaseModel):
    url: str
    model_size: str = "small"
    task: str = "transcribe"
    use_lid_hints: bool = True

async def save_upload_file(upload_file: UploadFile) -> str:
    # Save the uploaded file to a temporary location
    try:
        suffix = os.path.splitext(upload_file.filename)[1]
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'wb') as f:
            content = await upload_file.read()
            f.write(content)
        return path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

@router.post("/api/extract")
async def extract_audio_url(data: URLInput):
    """Start an extraction job from a URL."""
    job_id = job_manager.create_job("extract")
    # Run in a background thread so the HTTP request completes immediately
    thread = threading.Thread(target=run_extractor_job, args=(job_id, data.url, False))
    thread.start()
    return {"job_id": job_id}

@router.post("/api/extract/upload")
async def extract_audio_file(file: UploadFile = File(...)):
    """Start an extraction job from an uploaded file."""
    temp_path = await save_upload_file(file)
    job_id = job_manager.create_job("extract")
    thread = threading.Thread(target=run_extractor_job, args=(job_id, temp_path, True))
    thread.start()
    return {"job_id": job_id}

@router.post("/api/detect-language")
async def detect_language_url(data: URLInput):
    """Start a LID job from a URL."""
    job_id = job_manager.create_job("lid")
    thread = threading.Thread(target=run_lid_job, args=(job_id, data.url, False))
    thread.start()
    return {"job_id": job_id}

@router.post("/api/detect-language/upload")
async def detect_language_file(file: UploadFile = File(...)):
    """Start a LID job from an uploaded file."""
    temp_path = await save_upload_file(file)
    job_id = job_manager.create_job("lid")
    thread = threading.Thread(target=run_lid_job, args=(job_id, temp_path, True))
    thread.start()
    return {"job_id": job_id}

@router.post("/api/transcribe")
async def transcribe_url(data: TranscribeInput):
    """Start a transcription job from a URL."""
    job_id = job_manager.create_job("transcribe")
    thread = threading.Thread(
        target=run_transcription_job,
        args=(job_id, data.url, data.model_size, data.task, data.use_lid_hints, False),
    )
    thread.start()
    return {"job_id": job_id}

@router.post("/api/transcribe/upload")
async def transcribe_file(
    file: UploadFile = File(...),
    model_size: str = Form("small"),
    task: str = Form("transcribe"),
    use_lid_hints: bool = Form(True),
):
    """Start a transcription job from an uploaded file."""
    temp_path = await save_upload_file(file)
    job_id = job_manager.create_job("transcribe")
    thread = threading.Thread(
        target=run_transcription_job,
        args=(job_id, temp_path, model_size, task, use_lid_hints, True),
    )
    thread.start()
    return {"job_id": job_id}

@router.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Poll for job status."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

