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

        # Load Whisper model (lazy: only if fallback is enabled and needed)
        self.whisper_model = None

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
        # Prepare chunks for batching
        chunks_to_process = []
        valid_windows = []
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
            else:
                chunks_to_process.append(chunk)
                valid_windows.append(window)

        if not chunks_to_process:
            return sorted(results, key=lambda x: x['start'])

        # Batch processing loop
        BATCH_SIZE = 32
        total_batches = (len(chunks_to_process) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(chunks_to_process), BATCH_SIZE):
            batch_chunks = chunks_to_process[i:i + BATCH_SIZE]
            batch_windows = valid_windows[i:i + BATCH_SIZE]
            
            if progress_callback:
                progress_callback(f"LID: Processing batch {i // BATCH_SIZE + 1}/{total_batches}")
            else:
                print(f"  LID: Processing batch {i // BATCH_SIZE + 1}/{total_batches}...")

            batch_results = self._classify_batch(batch_chunks, sr, batch_windows, region=region)
            results.extend(batch_results)

        return sorted(results, key=lambda x: x['start'])

    def _classify_batch(self, chunks: List[np.ndarray], sr: int, windows: List[Dict[str, float]], region: str = "global") -> List[Dict]:
        """
        Classifies a batch of audio chunks using SpeechBrain. 
        Falls back to Whisper for individual chunks if confidence is below threshold.
        """
        # Pad chunks to max length in batch
        max_len = max(len(c) for c in chunks)
        padded_chunks = []
        for c in chunks:
            if len(c) < max_len:
                padded_chunks.append(np.pad(c, (0, max_len - len(c)), mode='constant'))
            else:
                padded_chunks.append(c)

        # Stack into single tensor: [batch_size, time]
        waveform = torch.from_numpy(np.stack(padded_chunks)).float().to(self.device)
        results = []

        try:
            # Run SpeechBrain inference
            prediction = self.sb_model.classify_batch(waveform)
            # prediction[0] is log_posteriors, shape: [batch_size, 1, num_languages] -> squeeze(1)
            log_posteriors = prediction[0].squeeze(1)

            # Apply Region Whitelisting Mask
            if region == "indian":
                whitelist = set(settings.INDIAN_REGION_LANGUAGES)
                for idx, label in self.sb_model.hparams.label_encoder.ind2lab.items():
                    lang_code = label.split(':')[0].strip() if ':' in label else label.strip()
                    if lang_code not in whitelist:
                        log_posteriors[:, idx] = -float('inf')

            probabilities = torch.exp(log_posteriors)
            top_probs, top_idxs = probabilities.max(dim=-1)

            for b in range(len(chunks)):
                confidence = top_probs[b].item()
                language = self.sb_model.hparams.label_encoder.ind2lab[top_idxs[b].item()]

                if confidence >= settings.LID_CONFIDENCE_THRESHOLD:
                    results.append({
                        'start': windows[b]['start'],
                        'end': windows[b]['end'],
                        'language': language,
                        'confidence': round(confidence, 4),
                        'source': 'speechbrain'
                    })
                else:
                    # Fallback to Whisper for this individual chunk
                    if settings.FALLBACK_TO_WHISPER:
                        try:
                            res = self._whisper_fallback(chunks[b], sr, windows[b], region=region)
                            results.append(res)
                        except Exception as e:
                            print(f"  Whisper fallback error on window {windows[b]['start']}-{windows[b]['end']}: {e}")
                            results.append({
                                'start': windows[b]['start'],
                                'end': windows[b]['end'],
                                'language': 'unknown',
                                'confidence': 0.0,
                                'source': 'failed'
                            })
                    else:
                        results.append({
                            'start': windows[b]['start'],
                            'end': windows[b]['end'],
                            'language': language,
                            'confidence': round(confidence, 4),
                            'source': 'speechbrain_low_conf'
                        })
            return results

        except Exception as e:
            print(f"  SpeechBrain batch error: {e}")
            # If SB fails completely on this batch, fallback to Whisper for all chunks
            for b in range(len(chunks)):
                if settings.FALLBACK_TO_WHISPER:
                    results.append(self._whisper_fallback(chunks[b], sr, windows[b], region=region))
                else:
                    results.append({'start': windows[b]['start'], 'end': windows[b]['end'], 'language': 'unknown', 'confidence': 0.0, 'source': 'failed'})
            return results

    def _whisper_fallback(self, chunk: np.ndarray, sr: int, window: Dict[str, float], region: str = "global") -> Dict:
        """
        Uses faster-whisper's built-in language detection as a fallback.
        """
        if self.whisper_model is None and settings.FALLBACK_TO_WHISPER:
            try:
                from faster_whisper import WhisperModel
                compute_type = "int8" if self.device == "cuda" else "int8"
                self.whisper_model = WhisperModel("base", device=self.device, compute_type=compute_type)
                print("  faster-whisper LID fallback model loaded lazily.")
            except Exception as e:
                print(f"  Warning: Could not load Whisper fallback model: {e}")

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
