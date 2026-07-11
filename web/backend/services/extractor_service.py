import os
import shutil
from pathlib import Path
from backend.core.config import state
from backend.core.job_manager import job_manager, JobStatus

def run_extractor_job(job_id: str, input_source: str, is_temp_file: bool = False):
    """Runs the extraction in a background thread."""
    try:
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        
        # Run extraction
        audio_path = state.extractor.process_input(input_source)
        
        # Cleanup uploaded temp file if necessary
        if is_temp_file and os.path.exists(input_source):
            try:
                os.remove(input_source)
            except:
                pass
                
        # Build success result
        # Extract video ID for embed if it's a URL
        embed_url = None
        if "youtube.com" in input_source or "youtu.be" in input_source:
            # Basic youtube ID extraction
            import re
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", input_source)
            if match:
                embed_url = f"https://www.youtube.com/embed/{match.group(1)}"

        # The audio_path is absolute. We need to serve it, so we'll pass the relative path
        # from the lid-pipeline/data directory
        filename = audio_path.name
        serve_url = f"/audio/{filename}"
        
        result = {
            "success": True,
            "filename": filename,
            "audio_url": serve_url,
            "video_embed_url": embed_url
        }
        
        job_manager.update_status(job_id, JobStatus.COMPLETED, result=result)
        
    except Exception as e:
        job_manager.update_status(job_id, JobStatus.FAILED, error=str(e))
        if is_temp_file and os.path.exists(input_source):
            try:
                os.remove(input_source)
            except:
                pass
