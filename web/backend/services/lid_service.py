import os
from backend.core.config import state
from backend.core.job_manager import job_manager, JobStatus

def run_lid_job(job_id: str, input_source: str, region: str = "global", is_temp_file: bool = False):
    """Runs the full LID Pipeline in a background thread."""
    try:
        job_manager.update_status(job_id, JobStatus.PROCESSING)
        
        def progress_callback(msg: str):
            job_manager.update_status(job_id, JobStatus.PROCESSING, progress=msg)

        # Run full pipeline
        timeline = state.lid_pipeline.process(input_source, region=region, progress_callback=progress_callback)
        
        # Cleanup uploaded temp file if necessary
        if is_temp_file and os.path.exists(input_source):
            try:
                os.remove(input_source)
            except:
                pass
                
        embed_url = None
        if "youtube.com" in input_source or "youtu.be" in input_source:
            import re
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", input_source)
            if match:
                embed_url = f"https://www.youtube.com/embed/{match.group(1)}"

        # Compute summary statistics
        total_duration = sum(b['end'] - b['start'] for b in timeline) if timeline else 0
        lang_durations = {}
        for b in timeline:
            lang = b['language']
            lang_durations[lang] = lang_durations.get(lang, 0) + (b['end'] - b['start'])
            
        summary = []
        for lang, dur in sorted(lang_durations.items(), key=lambda x: x[1], reverse=True):
            pct = (dur / total_duration) * 100 if total_duration > 0 else 0
            summary.append({"language": lang, "duration_seconds": dur, "percentage": pct})
            
        result = {
            "success": True,
            "timeline": timeline,
            "summary": summary,
            "total_duration": total_duration,
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
