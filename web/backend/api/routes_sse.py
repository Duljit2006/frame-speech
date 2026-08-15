import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.core.job_manager import job_manager, JobStatus

router = APIRouter()

async def job_event_generator(job_id: str):
    """Generates SSE events for a specific job."""
    while True:
        job = job_manager.get_job(job_id)
        if not job:
            yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
            break
            
        # Serialize datetime
        job_data = {
            "id": job["id"],
            "status": job["status"],
            "progress": job.get("progress"),
            "result": job["result"],
            "error": job["error"]
        }
        
        yield f"data: {json.dumps(job_data)}\n\n"
        
        if job["status"] in (JobStatus.COMPLETED, JobStatus.FAILED):
            break
            
        # Poll every 2 seconds
        await asyncio.sleep(2.0)

@router.get("/api/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """Server-Sent Events endpoint to stream job updates."""
    return StreamingResponse(job_event_generator(job_id), media_type="text/event-stream")
