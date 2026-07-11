import os
from pathlib import Path
from typing import List, Dict, Optional

from .stages.audio_extractor import AudioExtractor
from .stages.vad import VADProcessor
from .stages.segmentation import SegmentationEngine
from .stages.lid_processor import LIDProcessor
from .stages.smoothing import LanguageSmoother
from .stages.transcriber import TranscriptionProcessor

class LIDPipeline:
    """
    End-to-end Orchestrator for the Language Identification Pipeline.
    Takes a YouTube URL or local audio file and returns a smoothed language timeline.
    """
    def __init__(self):
        # Initialize all stages once so models stay in memory
        self.extractor = AudioExtractor()
        self.vad = VADProcessor()
        self.engine = SegmentationEngine()
        self.lid = LIDProcessor()
        self.smoother = LanguageSmoother()
        
    def process(self, input_source: str) -> List[Dict]:
        """
        Run the full LID pipeline on an audio source.
        
        Args:
            input_source: YouTube URL or local file path
            
        Returns:
            List of smoothed language blocks:
            [{'start': 0.0, 'end': 10.5, 'language': 'Hindi', ...}, ...]
        """
        # Step 1: Extract Audio
        audio_path = self.extractor.process_input(input_source)
        
        # Step 2: Voice Activity Detection
        vad_intervals = self.vad.process(str(audio_path))
        if not vad_intervals:
            return []
            
        # Step 3: Sliding Window Segmentation
        windows = self.engine.process(vad_intervals)
        if not windows:
            return []
            
        # Step 4 & 5: LID Inference (SpeechBrain & Whisper)
        raw_results = self.lid.process(str(audio_path), windows)
        if not raw_results:
            return []
            
        # Step 6: Time-Bin Voting & Smoothing
        smoothed_timeline = self.smoother.process(raw_results)
        
        return smoothed_timeline

    def transcribe(
        self,
        input_source: str,
        model_size: str = "small",
        task: str = "transcribe",
        use_lid_hints: bool = True,
    ) -> Dict:
        """
        Run the full LID pipeline and then transcribe the audio.

        Runs process() first to get the smoothed language timeline,
        then creates a TranscriptionProcessor and transcribes each
        language block with the correct language hint.

        Args:
            input_source: YouTube URL or local file path
            model_size:   Whisper model size ('tiny','base','small','medium','large-v3')
            task:         'transcribe' or 'translate' (translate -> English)
            use_lid_hints: Whether to pass the LID language as a hint to Whisper.

        Returns:
            Dict with keys:
              - timeline:   Smoothed language blocks from the LID stage
              - audio_path: Path to the extracted WAV file
              - segments:   Sentence-level transcription segments
              - full_text:  Complete transcription as a single string
              - srt:        SRT subtitle string
              - plain_text: Timestamped plain-text string
        """
        # Step 1-6: Run the full LID pipeline
        audio_path = self.extractor.process_input(input_source)

        vad_intervals = self.vad.process(str(audio_path))
        if not vad_intervals:
            return {"timeline": [], "segments": [], "full_text": "",
                    "srt": "", "plain_text": "",
                    "audio_path": str(audio_path)}

        windows = self.engine.process(vad_intervals)
        if not windows:
            return {"timeline": [], "segments": [], "full_text": "",
                    "srt": "", "plain_text": "",
                    "audio_path": str(audio_path)}

        raw_results = self.lid.process(str(audio_path), windows)
        if not raw_results:
            return {"timeline": [], "segments": [], "full_text": "",
                    "srt": "", "plain_text": "",
                    "audio_path": str(audio_path)}

        smoothed_timeline = self.smoother.process(raw_results)

        # Step 7: Transcription
        print("  --- Starting Transcription ---")
        transcriber = TranscriptionProcessor(
            model_size=model_size, device=self.lid.device
        )
        transcription = transcriber.transcribe(
            str(audio_path), smoothed_timeline, task=task, use_lid_hints=use_lid_hints
        )

        # Free the transcriber's GPU memory when done
        del transcriber
        import torch
        torch.cuda.empty_cache()

        return {
            "timeline": smoothed_timeline,
            "audio_path": str(audio_path),
            **transcription,
        }
