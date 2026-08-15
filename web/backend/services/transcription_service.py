import os
from pathlib import Path
from backend.core.config import state, PIPELINE_ROOT
from backend.core.job_manager import job_manager, JobStatus


def run_transcription_job(
    job_id: str,
    input_source: str,
    model_size: str = "small",
    task: str = "transcribe",
    use_lid_hints: bool = True,
    region: str = "global",
    is_temp_file: bool = False,
):
    """
    Runs the full LID + Transcription pipeline in a background thread.
    Saves SRT and TXT files alongside the processed audio.
    """
    try:
        job_manager.update_status(job_id, JobStatus.PROCESSING)

        def progress_callback(msg: str):
            job_manager.update_status(job_id, JobStatus.PROCESSING, progress=msg)

        # Run the combined pipeline
        with job_manager.get_global_lock():
            result = state.lid_pipeline.transcribe(
                input_source,
                model_size=model_size,
                task=task,
                use_lid_hints=use_lid_hints,
                region=region,
                progress_callback=progress_callback
            )

        # Cleanup uploaded temp file if necessary
        if is_temp_file and os.path.exists(input_source):
            try:
                os.remove(input_source)
            except Exception:
                pass

        # Save SRT and TXT to the downloads directory
        downloads_dir = PIPELINE_ROOT / "data" / "downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        srt_filename = f"{job_id}.srt"
        txt_filename = f"{job_id}.txt"

        srt_path = downloads_dir / srt_filename
        txt_path = downloads_dir / txt_filename

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(result.get("srt", ""))

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result.get("plain_text", ""))

        # Build YouTube embed URL
        embed_url = None
        if "youtube.com" in input_source or "youtu.be" in input_source:
            import re
            match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", input_source)
            if match:
                embed_url = f"https://www.youtube.com/embed/{match.group(1)}"

        # Compute LID-level summary (from the timeline, same as Model 2)
        timeline = result.get("timeline", [])
        total_duration = sum(b["end"] - b["start"] for b in timeline) if timeline else 0
        lang_durations = {}
        for b in timeline:
            lang = b["language"]
            lang_durations[lang] = lang_durations.get(lang, 0) + (b["end"] - b["start"])

        lid_summary = []
        for lang, dur in sorted(lang_durations.items(), key=lambda x: x[1], reverse=True):
            pct = (dur / total_duration) * 100 if total_duration > 0 else 0
            lid_summary.append({
                "language": lang,
                "duration_seconds": round(dur, 1),
                "percentage": round(pct, 1),
            })

        segments = result.get("segments", [])
        corrected_durations = {}
        corrected_total = 0
        for s in segments:
            dur = s["end"] - s["start"]
            if dur < 0:
                dur = 0
            lang = s["language"]
            corrected_durations[lang] = corrected_durations.get(lang, 0) + dur
            corrected_total += dur
            
        corrected_summary = []
        for lang, dur in sorted(corrected_durations.items(), key=lambda x: x[1], reverse=True):
            pct = (dur / corrected_total) * 100 if corrected_total > 0 else 0
            corrected_summary.append({
                "language": lang,
                "duration_seconds": round(dur, 1),
                "percentage": round(pct, 1),
            })

        final_result = {
            "success": True,
            "timeline": timeline,
            "segments": segments,
            "full_text": result.get("full_text", ""),
            "lid_summary": lid_summary,
            "corrected_summary": corrected_summary,
            "total_duration": round(total_duration, 1),
            "video_embed_url": embed_url,
            "srt_download": f"/downloads/{srt_filename}",
            "txt_download": f"/downloads/{txt_filename}",
        }

        job_manager.update_status(job_id, JobStatus.COMPLETED, result=final_result)

    except Exception as e:
        job_manager.update_status(job_id, JobStatus.FAILED, error=str(e))
        if is_temp_file and os.path.exists(input_source):
            try:
                os.remove(input_source)
            except Exception:
                pass
