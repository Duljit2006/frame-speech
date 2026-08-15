import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

import threading

class JobManager:
    """
    In-memory job queue for the web API.
    Tracks state, results, and creation time for cleanup.
    """
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
    def get_global_lock(self):
        return self._lock
        
    def create_job(self, job_type: str) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "id": job_id,
            "type": job_type, # 'extract' or 'lid'
            "status": JobStatus.PENDING,
            "progress": None,
            "created_at": datetime.now(),
            "result": None,
            "error": None
        }
        return job_id
        
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)
        
    def update_status(self, job_id: str, status: str, result: Any = None, error: str = None, progress: str = None):
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            if result is not None:
                self._jobs[job_id]["result"] = result
            if error is not None:
                self._jobs[job_id]["error"] = error
            if progress is not None:
                self._jobs[job_id]["progress"] = progress
                
    def cleanup_old_jobs(self, max_age_minutes: int = 120):
        """Removes jobs older than the specified limit, IF they are finished."""
        now = datetime.now()
        expired_ids = []
        for jid, job in self._jobs.items():
            age = now - job["created_at"]
            is_old = age > timedelta(minutes=max_age_minutes)
            is_finished = job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]
            
            if is_old and is_finished:
                expired_ids.append(jid)
                
        for jid in expired_ids:
            del self._jobs[jid]
        return len(expired_ids)

# Global singleton
job_manager = JobManager()
