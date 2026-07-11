import torch
from typing import List, Dict
from pathlib import Path

from ...config import settings
from ..exceptions import VADError

class VADProcessor:
    """
    Uses Silero VAD to detect speech intervals in a 16kHz audio file.
    Filters out silence and non-speech to save compute in later ML stages.
    """
    def __init__(self):
        try:
            # Load Silero VAD from torch hub
            # It is lightweight enough to run perfectly on CPU locally.
            self.model, self.utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            # Unpack utilities
            (self.get_speech_timestamps, _, self.read_audio, _, _) = self.utils
        except Exception as e:
            raise VADError(f"Failed to load Silero VAD model: {e}")
            
    def process(self, audio_path: str) -> List[Dict[str, float]]:
        """
        Takes a standardized 16kHz audio file path and returns speech intervals.
        
        Args:
            audio_path: Path to the 16kHz Mono WAV file.
            
        Returns:
            List of dictionaries containing start and end times in seconds.
            Example: [{'start': 1.250, 'end': 3.400}, ...]
        """
        if not Path(audio_path).exists():
            raise VADError(f"Audio file not found: {audio_path}")
            
        try:
            # Use soundfile instead of torchaudio to bypass Windows DLL issues
            import soundfile as sf
            audio_data, sr = sf.read(audio_path)
            
            if sr != settings.SAMPLE_RATE:
                raise VADError(f"Expected {settings.SAMPLE_RATE}Hz but got {sr}Hz in {audio_path}")
                
            # Convert to float32 tensor
            wav = torch.from_numpy(audio_data).float()
            
            # Get speech timestamps using the threshold from config
            speech_timestamps = self.get_speech_timestamps(
                wav, 
                self.model, 
                sampling_rate=settings.SAMPLE_RATE,
                threshold=settings.VAD_THRESHOLD
            )
            
            # Silero returns indices (samples). We convert them to seconds.
            intervals = []
            for segment in speech_timestamps:
                start_sec = segment['start'] / settings.SAMPLE_RATE
                end_sec = segment['end'] / settings.SAMPLE_RATE
                intervals.append({
                    'start': round(start_sec, 3),
                    'end': round(end_sec, 3)
                })
                
            return intervals
            
        except Exception as e:
            raise VADError(f"Failed to process VAD on {audio_path}: {str(e)}")
