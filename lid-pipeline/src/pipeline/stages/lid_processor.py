import torch
import numpy as np
import soundfile as sf
from typing import List, Dict, Optional
from pathlib import Path

from ...config import settings
from ..exceptions import LIDInferenceError

class LIDProcessor:
    """
    Performs Language Identification on audio windows using:
      - Primary: SpeechBrain ECAPA-TDNN (speechbrain/lang-id-voxlingua107-ecapa)
        Trained on VoxLingua107 (real YouTube data across 107 languages).
      - Fallback: OpenAI Whisper (when SpeechBrain confidence is below threshold)
    """
    def __init__(self, device: Optional[str] = None):
        """
        Args:
            device: 'cuda' or 'cpu'. Auto-detects if not specified.
        """
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"  LID Device: {self.device}")

        # Monkey-patch torchaudio for SpeechBrain 0.5.16 compatibility with PyTorch 2.3+
        import torchaudio
        if not hasattr(torchaudio, 'set_audio_backend'):
            torchaudio.set_audio_backend = lambda x: None

        import huggingface_hub
        if hasattr(huggingface_hub, 'hf_hub_download'):
            _orig_download = huggingface_hub.hf_hub_download
            def _patched_download(*args, **kwargs):
                if 'use_auth_token' in kwargs:
                    kwargs['token'] = kwargs.pop('use_auth_token')
                try:
                    return _orig_download(*args, **kwargs)
                except Exception as e:
                    # SpeechBrain 0.5.16 expects a ValueError if custom.py is missing
                    filename = kwargs.get('filename') or (args[1] if len(args) > 1 else None)
                    if filename == 'custom.py' and ('404' in str(e) or 'not found' in str(e).lower()):
                        raise ValueError("Mocked ValueError for missing custom.py")
                    raise
            huggingface_hub.hf_hub_download = _patched_download

        # Load SpeechBrain VoxLingua107 model (trained on real YouTube data)
        try:
            from speechbrain.pretrained import EncoderClassifier
            self.sb_model = EncoderClassifier.from_hparams(
                source="speechbrain/lang-id-voxlingua107-ecapa",
                savedir=str(Path(__file__).resolve().parent.parent.parent.parent / "models_cache" / "speechbrain_lid_vox107"),
                run_opts={"device": self.device}
            )
            print("  SpeechBrain VoxLingua107 LID model loaded.")
        except Exception as e:
            raise LIDInferenceError(f"Failed to load SpeechBrain model: {e}")

        # Load Whisper model (lazy: only if fallback is enabled)
        self.whisper_model = None
        if settings.FALLBACK_TO_WHISPER:
            try:
                import whisper
                self.whisper_model = whisper.load_model("base", device=self.device)
                print("  Whisper fallback model loaded.")
            except Exception as e:
                print(f"  Warning: Could not load Whisper fallback model: {e}")

    def process(self, audio_path: str, windows: List[Dict[str, float]]) -> List[Dict]:
        """
        Runs LID inference on each sliding window.

        Args:
            audio_path: Path to the full 16kHz Mono WAV file.
            windows: List of window dicts from SegmentationEngine,
                     e.g., [{'start': 1.2, 'end': 4.2}, ...]

        Returns:
            List of result dicts, e.g.:
            [
                {
                    'start': 1.2,
                    'end': 4.2,
                    'language': 'en',
                    'confidence': 0.92,
                    'source': 'speechbrain'
                },
                ...
            ]
        """
        if not Path(audio_path).exists():
            raise LIDInferenceError(f"Audio file not found: {audio_path}")

        # Load full audio once
        try:
            full_audio, sr = sf.read(audio_path)
        except Exception as e:
            raise LIDInferenceError(f"Failed to read audio file: {e}")

        results = []
        total = len(windows)
        for i, window in enumerate(windows):
            start_sample = int(window['start'] * sr)
            end_sample = int(window['end'] * sr)
            chunk = full_audio[start_sample:end_sample]

            # Skip very short chunks (< 0.3 seconds)
            if len(chunk) < sr * 0.3:
                results.append({
                    'start': window['start'],
                    'end': window['end'],
                    'language': 'unknown',
                    'confidence': 0.0,
                    'source': 'skipped'
                })
                continue

            # Progress indicator
            if (i + 1) % 25 == 0 or i == 0 or i == total - 1:
                print(f"  Processing window {i+1}/{total}...")

            result = self._classify_chunk(chunk, sr, window)
            results.append(result)

        return results

    def _classify_chunk(self, chunk: np.ndarray, sr: int, window: Dict[str, float]) -> Dict:
        """
        Classifies a single audio chunk. Uses SpeechBrain first,
        falls back to Whisper if confidence is below threshold.
        """
        # --- SpeechBrain Primary ---
        try:
            # Convert numpy to torch tensor
            waveform = torch.from_numpy(chunk).float().unsqueeze(0).to(self.device)

            # Run SpeechBrain inference
            prediction = self.sb_model.classify_batch(waveform)

            # prediction returns: (out_prob, score, index, text_label)
            # out_prob is log-softmax posteriors. We need actual probabilities.
            log_posteriors = prediction[0].squeeze(0)  # Shape: [num_languages]
            probabilities = torch.exp(log_posteriors)   # Convert to real probabilities (0-1)

            # Get the top prediction
            top_prob, top_idx = probabilities.max(dim=-1)
            confidence = top_prob.item()
            language = prediction[3][0]  # Text label of the best class

            if confidence >= settings.LID_CONFIDENCE_THRESHOLD:
                return {
                    'start': window['start'],
                    'end': window['end'],
                    'language': language,
                    'confidence': round(confidence, 4),
                    'source': 'speechbrain'
                }
        except Exception as e:
            print(f"  SpeechBrain error on window {window['start']}-{window['end']}: {e}")

        # --- Whisper Fallback ---
        if self.whisper_model and settings.FALLBACK_TO_WHISPER:
            try:
                return self._whisper_fallback(chunk, sr, window)
            except Exception as e:
                print(f"  Whisper fallback error on window {window['start']}-{window['end']}: {e}")

        # If both fail, return unknown
        return {
            'start': window['start'],
            'end': window['end'],
            'language': 'unknown',
            'confidence': 0.0,
            'source': 'failed'
        }

    def _whisper_fallback(self, chunk: np.ndarray, sr: int, window: Dict[str, float]) -> Dict:
        """
        Uses Whisper's built-in language detection as a fallback.
        Whisper expects 30-second padded audio at 16kHz.
        """
        import whisper

        # Pad or trim to 30 seconds (Whisper's expected input length)
        audio_padded = whisper.pad_or_trim(torch.from_numpy(chunk).float())

        # Compute log-mel spectrogram
        mel = whisper.log_mel_spectrogram(audio_padded).to(self.device)

        # Detect language
        _, probs = self.whisper_model.detect_language(mel)

        # Get the top predicted language
        top_lang = max(probs, key=probs.get)
        top_conf = probs[top_lang]

        return {
            'start': window['start'],
            'end': window['end'],
            'language': top_lang,
            'confidence': round(top_conf, 4),
            'source': 'whisper'
        }
