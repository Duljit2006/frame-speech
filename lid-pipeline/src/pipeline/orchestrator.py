import os
from pathlib import Path
from typing import List, Dict, Optional

from .stages.audio_extractor import AudioExtractor
from .stages.vad import VADProcessor
from .stages.segmentation import SegmentationEngine
from .stages.lid_processor import LIDProcessor
from .stages.smoothing import LanguageSmoother
from .stages.transcriber import TranscriptionProcessor
from .stages.text_corrector import TextCorrectionProcessor


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
        self.text_corrector = TextCorrectionProcessor()
        
    def process(self, input_source: str, region: str = "global", progress_callback = None) -> List[Dict]:
        """
        Run the full LID pipeline on an audio source.
        
        Args:
            input_source: YouTube URL or local file path
            region: Language region whitelist (e.g. "indian" or "global")
            progress_callback: Callback function for progress updates
            
        Returns:
            List of smoothed language blocks:
            [{'start': 0.0, 'end': 10.5, 'language': 'Hindi', ...}, ...]
        """
        # Step 1: Extract Audio
        if progress_callback: progress_callback("Extracting Audio...")
        audio_path = self.extractor.process_input(input_source)
        
        # Step 2: Voice Activity Detection
        if progress_callback: progress_callback("Running Voice Activity Detection...")
        vad_intervals = self.vad.process(str(audio_path))
        if not vad_intervals:
            return []
            
        # Step 3: Sliding Window Segmentation
        windows = self.engine.process(vad_intervals)
        if not windows:
            return []
            
        # Step 4 & 5: LID Inference (SpeechBrain & Whisper)
        if progress_callback: progress_callback("Initializing LID Inference...")
        raw_results = self.lid.process(str(audio_path), windows, region=region, progress_callback=progress_callback)
        if not raw_results:
            return []
            
        # Step 6: Time-Bin Voting & Smoothing
        if progress_callback: progress_callback("Applying Temporal Smoothing...")
        smoothed_timeline = self.smoother.process(raw_results, region=region)
        
        return smoothed_timeline

    def transcribe(
        self,
        input_source: str,
        model_size: str = "small",
        task: str = "transcribe",
        use_lid_hints: bool = True,
        region: str = "global",
        progress_callback = None,
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

        raw_results = self.lid.process(
            str(audio_path), windows, region=region, progress_callback=progress_callback
        )
        if not raw_results:
            return {"timeline": [], "segments": [], "full_text": "",
                    "srt": "", "plain_text": "",
                    "audio_path": str(audio_path)}

        smoothed_timeline = self.smoother.process(raw_results, region=region)

        # Step 7: Transcription
        # First, offload LID models from GPU to free VRAM for faster-whisper
        print("  --- Offloading LID models from GPU ---")
        try:
            self.lid.sb_model.to("cpu")
            if getattr(self.lid, 'whisper_model', None) is not None:
                # faster-whisper cannot be offloaded with .to("cpu"). 
                # We must delete it; it will be lazy-loaded again if needed for the next job.
                del self.lid.whisper_model
                self.lid.whisper_model = None
        except Exception as e:
            print(f"  Warning: Failed to offload LID models: {e}")
        import torch
        torch.cuda.empty_cache()

        print("  --- Starting Transcription ---")
        transcriber = TranscriptionProcessor(
            model_size=model_size, device=self.lid.device
        )
        transcription = transcriber.transcribe(
            str(audio_path), smoothed_timeline, task=task, use_lid_hints=use_lid_hints,
            progress_callback=progress_callback
        )

        # Free the transcriber's GPU memory when done
        del transcriber
        torch.cuda.empty_cache()

        # Reload LID models back to GPU for future jobs
        print("  --- Reloading LID models to GPU ---")
        try:
            self.lid.sb_model.to(self.lid.device)
            # The fallback Whisper model doesn't need reloading since we deleted it during offloading.
            # It will be lazy-loaded on the next job if needed.
        except Exception as e:
            print(f"  Warning: Failed to reload LID models: {e}")

        # Step 8: Post-Transcription AI Text Correction (always runs when API key is available)
        segments = transcription.get("segments", [])
        if segments:
            print("  --- Starting Post-Transcription AI Text Correction ---")
            segments = self.text_corrector.correct(segments, progress_callback=progress_callback)
            # Recompute full_text, srt, plain_text with corrected segments
            transcription["segments"] = segments
            transcription["full_text"] = " ".join(s["text"] for s in segments)
            transcription["srt"] = TranscriptionProcessor._generate_srt(segments)
            transcription["plain_text"] = TranscriptionProcessor._generate_plain_text(segments)

        return {
            "timeline": smoothed_timeline,
            "audio_path": str(audio_path),
            **transcription,
        }

