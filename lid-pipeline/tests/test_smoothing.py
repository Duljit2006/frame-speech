import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.stages.audio_extractor import AudioExtractor
from src.pipeline.stages.vad import VADProcessor
from src.pipeline.stages.segmentation import SegmentationEngine
from src.pipeline.stages.lid_processor import LIDProcessor
from src.pipeline.stages.smoothing import LanguageSmoother
from src.config import settings

def main():
    print("=" * 70)
    print("  Language Identification Pipeline (Steps 1-6)")
    print("=" * 70)
    
    test_input = input("\nPaste a YouTube URL or local audio file path: ").strip()
    if not test_input:
        print("No input provided. Exiting.")
        return
        
    # Step 1: Extract Audio
    extractor = AudioExtractor()
    print(f"\n[Step 1] Extracting audio from: {test_input}")
    try:
        audio_path = extractor.process_input(test_input)
        print(f"  ✓ Audio ready at: {audio_path}")
    except Exception as e:
        print(f"  ✗ Extraction failed: {e}")
        return
        
    # Step 2: VAD
    print("\n[Step 2] Running Voice Activity Detection...")
    vad = VADProcessor()
    try:
        vad_intervals = vad.process(str(audio_path))
        print(f"  ✓ Detected {len(vad_intervals)} speech segments.")
    except Exception as e:
        print(f"  ✗ VAD failed: {e}")
        return
        
    # Step 3: Segmentation
    print(f"\n[Step 3] Sliding Window Segmentation (Window: {settings.WINDOW_SIZE_SECONDS}s, Step: {settings.WINDOW_STEP_SECONDS}s)")
    engine = SegmentationEngine()
    windows = engine.process(vad_intervals)
    print(f"  ✓ Generated {len(windows)} windows.")
    
    # Step 4: LID Inference
    print("\n[Step 4] Loading Language ID models...")
    try:
        lid = LIDProcessor()
    except Exception as e:
        print(f"  ✗ Failed to load LID models: {e}")
        return
    
    print(f"\n[Step 5] Running Language Identification on {len(windows)} windows...")
    try:
        raw_results = lid.process(str(audio_path), windows)
        print(f"  ✓ Got {len(raw_results)} raw predictions.")
    except Exception as e:
        print(f"  ✗ LID inference failed: {e}")
        return
    
    # Step 6: Smoothing
    print(f"\n[Step 6] Smoothing predictions...")
    smoother = LanguageSmoother()
    smoothed = smoother.process(raw_results)
    print(f"  ✓ Smoothed {len(raw_results)} raw predictions into {len(smoothed)} clean language blocks.")
    
    # ===== Print Raw Results (collapsed) =====
    show_raw = input("\nShow raw (unsmoothed) predictions? (y/n): ").strip().lower()
    if show_raw == 'y':
        print("\n" + "=" * 70)
        print("  RAW PREDICTIONS (before smoothing)")
        print("=" * 70)
        print(f"{'#':<6} {'Time (MM:SS)':<24} {'Language':<14} {'Conf':<10} {'Source':<12}")
        print("-" * 70)
        for i, r in enumerate(raw_results):
            m_s, s_s = int(r['start'] // 60), r['start'] % 60
            m_e, s_e = int(r['end'] // 60), r['end'] % 60
            time_range = f"{m_s:02d}:{s_s:05.2f} -> {m_e:02d}:{s_e:05.2f}"
            print(f"  {i+1:<4} {time_range:<24} {r['language']:<14} {r['confidence']:<10.4f} {r['source']:<12}")
    
    # ===== Print Smoothed Results =====
    print("\n" + "=" * 70)
    print("  SMOOTHED LANGUAGE TIMELINE")
    print("=" * 70)
    print(f"{'#':<6} {'Time Range (MM:SS)':<26} {'Language':<14} {'Avg Conf':<10} {'Windows':<10}")
    print("-" * 70)
    for i, block in enumerate(smoothed):
        m_s, s_s = int(block['start'] // 60), block['start'] % 60
        m_e, s_e = int(block['end'] // 60), block['end'] % 60
        duration = block['end'] - block['start']
        time_range = f"{m_s:02d}:{s_s:05.2f} -> {m_e:02d}:{s_e:05.2f} ({duration:.1f}s)"
        print(f"  {i+1:<4} {time_range:<26} {block['language']:<14} {block['confidence']:<10.4f} {block['window_count']:<10}")
    print("=" * 70)
    
    # Summary statistics
    total_duration = sum(b['end'] - b['start'] for b in smoothed)
    lang_durations = {}
    for b in smoothed:
        lang = b['language']
        lang_durations[lang] = lang_durations.get(lang, 0) + (b['end'] - b['start'])
    
    print(f"\n  Summary:")
    print(f"  Total speech analyzed: {total_duration:.1f}s")
    for lang, dur in sorted(lang_durations.items(), key=lambda x: x[1], reverse=True):
        pct = (dur / total_duration) * 100 if total_duration > 0 else 0
        print(f"    {lang:<14} {dur:6.1f}s  ({pct:.1f}%)")
    
if __name__ == "__main__":
    main()
