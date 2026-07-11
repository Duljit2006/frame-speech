from pathlib import Path
from typing import Optional
import ffmpeg
import yt_dlp

from ...config import settings
from ..exceptions import AudioExtractionError, URLDownloadError

class AudioExtractor:
    """
    Handles fetching and converting audio from local files or web URLs.
    Normalizes all inputs to 16kHz, mono, 16-bit PCM WAV for the pipeline.
    """
    def __init__(self, output_dir: Optional[str] = None):
        """
        Args:
            output_dir: directory to store the processed audio files.
                        If None, uses a temporary directory.
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            # Default to a folder inside the project directory (e.g., lid-pipeline/data/processed_audio)
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            self.output_dir = project_root / "data" / "processed_audio"

            
        self.output_dir.mkdir(parents=True, exist_ok=True)
            
    def process_input(self, input_path: str) -> Path:
        """
        Takes a local file path or a URL and returns a path to a 
        standardized WAV file (16kHz, mono).
        """
        if input_path.startswith(("http://", "https://")):
            return self._download_and_extract_url(input_path)
        else:
            if not Path(input_path).exists():
                raise AudioExtractionError(f"Local file not found: {input_path}")
            return self._extract_local_file(input_path)

    def _duration_filter(self, info: dict, *, incomplete: bool) -> Optional[str]:
        """Filter out videos longer than the maximum configured duration."""
        duration = info.get('duration')
        if duration and duration > settings.MAX_URL_DURATION_SECONDS:
            return f"Video exceeds max duration of {settings.MAX_URL_DURATION_SECONDS} seconds"
        return None

    def _download_and_extract_url(self, url: str) -> Path:
        """
        Downloads audio from a URL using yt-dlp and converts to WAV.
        """
        out_filename = "downloaded_audio_%(id)s.%(ext)s"
        out_template = str(self.output_dir / out_filename)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
            }],
            'postprocessor_args': [
                '-ar', str(settings.SAMPLE_RATE),
                '-ac', '1',
            ],
            'quiet': True,
            'no_warnings': True,
            'match_filter': self._duration_filter,
            'extractor_args': {'youtube': ['player_client=android']},
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Check if it was filtered out
                if not info:
                     raise URLDownloadError("Video was filtered out (possibly too long).")
                     
                # Get expected final WAV file path
                video_id = info.get('id', 'unknown')
                expected_path = self.output_dir / f"downloaded_audio_{video_id}.wav"
                
                if expected_path.exists():
                    return expected_path
                else:
                    raise URLDownloadError(f"Expected output file not found: {expected_path}")
                    
        except yt_dlp.utils.DownloadError as e:
            raise URLDownloadError(f"yt-dlp download failed for URL {url}: {str(e)}")
        except Exception as e:
            raise URLDownloadError(f"Unexpected error processing URL {url}: {str(e)}")

    def _extract_local_file(self, file_path: str) -> Path:
        """
        Converts a local media file to the target audio format using ffmpeg-python.
        """
        input_path = Path(file_path)
        output_filename = f"processed_{input_path.stem}.wav"
        output_path = self.output_dir / output_filename
        
        try:
            # acodec='pcm_s16le' ensures 16-bit WAV
            # ac=1 ensures mono
            # ar=settings.SAMPLE_RATE ensures standard sample rate (16kHz)
            (
                ffmpeg
                .input(str(input_path))
                .output(str(output_path),
                        acodec='pcm_s16le',
                        ac=1,
                        ar=settings.SAMPLE_RATE)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return output_path
        except ffmpeg.Error as e:
            stderr_output = e.stderr.decode('utf-8') if e.stderr else str(e)
            raise AudioExtractionError(f"FFmpeg extraction failed for {file_path}:\n{stderr_output}")

