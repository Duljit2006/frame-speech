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
                from faster_whisper import WhisperModel
                compute_type = "int8" if self.device == "cuda" else "int8"
                self.whisper_model = WhisperModel("base", device=self.device, compute_type=compute_type)
                print("  faster-whisper LID fallback model loaded.")
            except Exception as e:
                print(f"  Warning: Could not load Whisper fallback model: {e}")

    def process(self, audio_path: str, windows: List[Dict[str, float]], region: str = "global", progress_callback=None) -> List[Dict]:
        """
        Runs LID inference on each sliding window.

        Args:
            audio_path: Path to the full 16kHz Mono WAV file.
            windows: List of window dicts from SegmentationEngine.
            region: "global" (all languages) or "indian" (whitelist subset).
            progress_callback: Optional callback for progress updates.

        Returns:
            List of result dicts
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
            if progress_callback and ((i + 1) % max(1, total // 10) == 0 or i == 0 or i == total - 1):
                progress_callback(f"LID: Processing segment {i+1}/{total}")
            elif (i + 1) % 25 == 0 or i == 0 or i == total - 1:
                print(f"  Processing window {i+1}/{total}...")

            result = self._classify_chunk(chunk, sr, window, region=region)
            results.append(result)

        return results

    def _classify_chunk(self, chunk: np.ndarray, sr: int, window: Dict[str, float], region: str = "global") -> Dict:
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
            log_posteriors = prediction[0].squeeze(0)  # Shape: [num_languages]

            # Apply Region Whitelisting Mask
            if region == "indian":
                whitelist = set(settings.INDIAN_REGION_LANGUAGES)
                # Find valid indices
                for idx, label in self.sb_model.hparams.label_encoder.ind2lab.items():
                    lang_code = label.split(':')[0].strip() if ':' in label else label.strip()
                    if lang_code not in whitelist:
                        log_posteriors[idx] = -float('inf')  # Zero out probability

            probabilities = torch.exp(log_posteriors)   # Convert to real probabilities (0-1)

            # Get the top prediction
            top_prob, top_idx = probabilities.max(dim=-1)
            confidence = top_prob.item()
            language = self.sb_model.hparams.label_encoder.ind2lab[top_idx.item()]

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
                return self._whisper_fallback(chunk, sr, window, region=region)
            except Exception as e:
                import traceback
                print(f"  Whisper fallback error on window {window['start']}-{window['end']}: {e}")
                traceback.print_exc()

        # If both fail, return unknown
        return {
            'start': window['start'],
            'end': window['end'],
            'language': 'unknown',
            'confidence': 0.0,
            'source': 'failed'
        }

    def _whisper_fallback(self, chunk: np.ndarray, sr: int, window: Dict[str, float], region: str = "global") -> Dict:
        """
        Uses faster-whisper's built-in language detection as a fallback.
        """
        if not self.whisper_model:
            return {'start': window['start'], 'end': window['end'], 'language': 'unknown', 'confidence': 0.0, 'source': 'failed'}

        chunk_f32 = chunk.astype(np.float32)
        top_lang, top_conf, all_probs = self.whisper_model.detect_language(chunk_f32)

        # Apply Region Whitelisting Mask
        if region == "indian":
            whitelist = set(settings.INDIAN_REGION_LANGUAGES)
            probs_dict = {lang: p for lang, p in all_probs if lang in whitelist}
            if not probs_dict:
                return {
                    'start': window['start'],
                    'end': window['end'],
                    'language': 'unknown',
                    'confidence': 0.0,
                    'source': 'whisper_filtered'
                }
            top_lang = max(probs_dict, key=probs_dict.get)
            top_conf = probs_dict[top_lang]

        return {
            'start': window['start'],
            'end': window['end'],
            'language': top_lang,
            'confidence': round(float(top_conf), 4),
            'source': 'whisper'
        }
