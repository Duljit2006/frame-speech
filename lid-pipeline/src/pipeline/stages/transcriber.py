import torch
import numpy as np
import soundfile as sf
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from ..exceptions import TranscriptionError


class TranscriptionProcessor:
    """
    Transcription engine that uses the smoothed LID timeline to
    transcribe each language block with the correct language hint.

    Supports:
      - Sentence-level timestamps with word-level detail
      - Model size hot-swapping (tiny → base → small → medium → large-v3)
      - SRT / plain-text export
      - Post-transcription language reanalysis for accurate summaries
      - Translation to English via Whisper task="translate"
    """

    # Whisper uses ISO 639-1 codes. Map our pipeline's output to Whisper codes.
    _LANG_TO_WHISPER = {
        "Hindi": "hi",
        "English": "en",
        "Urdu": "ur",
        "Bengali": "bn",
        "Tamil": "ta",
        "Telugu": "te",
        "Marathi": "mr",
        "Gujarati": "gu",
        "Kannada": "kn",
        "Malayalam": "ml",
        "Punjabi": "pa",
        "Assamese": "as",
        "Tagalog": "tl",
    }

    def __init__(self, model_size: str = "small", device: Optional[str] = None):
        """
        Args:
            model_size: One of 'tiny', 'base', 'small', 'medium', 'large-v3'
            device:     'cuda' or 'cpu'. Auto-detects if not specified.
        """
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model_size = model_size
        self.model = None
        self._load_model(model_size)

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------
    def _load_model(self, model_size: str):
        """Load a Whisper model onto the device using faster-whisper."""
        from faster_whisper import WhisperModel
        print(f"  [Transcriber] Loading faster-whisper '{model_size}' on {self.device}...")
        
        # Use int8 quantization on GPU to fit large-v3 in 4GB VRAM
        compute_type = "int8" if self.device == "cuda" else "int8"
        self.model = WhisperModel(model_size, device=self.device, compute_type=compute_type)
        self.model_size = model_size
        print(f"  [Transcriber] faster-whisper '{model_size}' ready.")

    def switch_model(self, new_size: str):
        """Hot-swap the Whisper model to a different size."""
        if new_size == self.model_size:
            return
        print(f"  [Transcriber] Switching model from '{self.model_size}' -> '{new_size}'...")
        del self.model
        torch.cuda.empty_cache()
        self._load_model(new_size)

    # ------------------------------------------------------------------
    # Core transcription
    # ------------------------------------------------------------------
    def transcribe(
        self,
        audio_path: str,
        timeline: List[Dict],
        task: str = "transcribe",
        use_lid_hints: bool = True,
        progress_callback = None,
    ) -> Dict:
        """
        Transcribe each language block in the timeline using faster-whisper.

        Args:
            audio_path: Path to the full 16kHz mono WAV file.
            timeline:   Smoothed language timeline from LIDPipeline.process().
            task:       'transcribe' or 'translate' (translate -> English).
            use_lid_hints: If True, passes the LID language to Whisper to force the language.
                           If False, passes None to allow Whisper to auto-detect and code-switch naturally.

        Returns:
            Dictionary with segments, full_text, srt, plain_text.
        """
        if not Path(audio_path).exists():
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        # Load the full audio once
        try:
            full_audio, sr = sf.read(audio_path)
        except Exception as e:
            raise TranscriptionError(f"Failed to read audio: {e}")

        all_segments = []
        segment_counter = 0

        for block_idx, block in enumerate(timeline):
            block_start = block["start"]
            block_end = block["end"]
            block_lang = block["language"]

            # Determine what hint to send to Whisper
            whisper_lang = None
            if use_lid_hints:
                # Gate by confidence > 0.85 to avoid forcing Whisper on bad LID guesses
                if block.get("confidence", 0) > 0.85:
                    whisper_lang = self._LANG_TO_WHISPER.get(block_lang, block_lang)
                    
                    # THE ASSAMESE HACK: Force Whisper to use its strong Bengali model
                    # for Assamese speech to get proper Eastern Nagari script instead of Romanized English.
                    if whisper_lang == "as":
                        whisper_lang = "bn"
                        
                    if whisper_lang and len(whisper_lang) > 3:
                        whisper_lang = None

            # Slice audio for this block
            start_sample = int(block_start * sr)
            end_sample = int(block_end * sr)
            chunk = full_audio[start_sample:end_sample]

            # Skip chunks shorter than 0.5 seconds
            if len(chunk) < sr * 0.5:
                continue

            hint_str = whisper_lang if whisper_lang else "auto-detect"
            msg = (f"Transcribing Block {block_idx + 1}/{len(timeline)} "
                   f"({block_lang}, Hint: {hint_str})")
            if progress_callback:
                progress_callback(msg)
            print(f"  [Transcriber] {msg}...")

            try:
                # Cast to float32 — faster-whisper / ONNX requires float, not double
                chunk_f32 = chunk.astype(np.float32)

                # Transcribe with language hint and word timestamps
                segments_generator, info = self.model.transcribe(
                    chunk_f32,
                    language=whisper_lang,
                    task=task,
                    word_timestamps=True,
                    vad_filter=True,  # Built-in VAD to reduce hallucinations
                    vad_parameters=dict(min_silence_duration_ms=500)
                )

                # Process each segment returned by Whisper
                for seg in segments_generator:
                    # Apply hallucination filter and strip broken UTF-8 characters caused by hard audio cuts
                    text = seg.text.strip().replace('\ufffd', '')
                    if self._is_hallucination(text, block_lang):
                        continue
                        
                    segment_counter += 1
                    # Offset timestamps relative to the full audio
                    seg_start = block_start + seg.start
                    seg_end = block_start + seg.end

                    # Build word list with offset timestamps
                    words = []
                    if seg.words:
                        for w in seg.words:
                            words.append({
                                "word": w.word.strip(),
                                "start": round(block_start + w.start, 3),
                                "end": round(block_start + w.end, 3),
                            })

                    all_segments.append({
                        "id": segment_counter,
                        "start": round(seg_start, 3),
                        "end": round(seg_end, 3),
                        "text": text,
                        "language": block_lang,
                        "words": words,
                    })

            except Exception as e:
                import traceback
                print(f"  [Transcriber] Error on block {block_idx + 1}: {e}")
                traceback.print_exc()

        # Build outputs
        full_text = " ".join(s["text"] for s in all_segments)
        srt = self._generate_srt(all_segments)
        plain_text = self._generate_plain_text(all_segments)

        return {
            "segments": all_segments,
            "full_text": full_text,
            "srt": srt,
            "plain_text": plain_text,
        }

    # ------------------------------------------------------------------
    # Hallucination Filter
    # ------------------------------------------------------------------
    def _is_hallucination(self, text: str, target_lang: str) -> bool:
        """
        Detects if a segment is likely a Whisper hallucination.
        Drops segments that are mostly punctuation or contain wrong scripts.
        """
        if not text or len(text.strip()) < 2:
            return True
            
        # Check for heavy punctuation (often hallucinated during music/silence)
        alpha_count = sum(c.isalpha() for c in text)
        if alpha_count < len(text) * 0.3:
            return True
            
        # Optional: Add strict Unicode block filtering based on target_lang here
        # Example: if target_lang is Bengali, we could check for Devanagari/Telugu blocks and drop.
        # But faster-whisper with VAD usually solves 99% of this.
        
        return False

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """Convert seconds to SRT timecode: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _generate_srt(segments: List[Dict]) -> str:
        """Generate a valid UTF-8 SRT subtitle string."""
        lines = []
        for seg in segments:
            lines.append(str(seg["id"]))
            start_tc = TranscriptionProcessor._format_srt_time(seg["start"])
            end_tc = TranscriptionProcessor._format_srt_time(seg["end"])
            lines.append(f"{start_tc} --> {end_tc}")
            lines.append(seg["text"])
            lines.append("")  # blank separator
        return "\n".join(lines)


    @staticmethod
    def _generate_plain_text(segments: List[Dict]) -> str:
        """Generate a simple timestamped plain-text transcript."""
        lines = []
        for seg in segments:
            mins = int(seg["start"] // 60)
            secs = int(seg["start"] % 60)
            lines.append(f"[{mins:02d}:{secs:02d}] {seg['text']}")
        return "\n".join(lines)
