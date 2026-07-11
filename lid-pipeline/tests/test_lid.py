import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.stages.audio_extractor import AudioExtractor
from src.pipeline.stages.vad import VADProcessor
from src.pipeline.stages.segmentation import SegmentationEngine
from src.pipeline.stages.lid_processor import LIDProcessor
from src.config import settings

def main():
    print("=== Testing LID Pipeline (Steps 1-5) ===")
    
    test_input = input("Please paste a YouTube URL or a local audio file path: ").strip()
    if not test_input:
        print("No input provided. Exiting.")
        return
        
    # Step 1: Extract Audio
    extractor = AudioExtractor()
    print(f"\n[Step 1] Extracting audio from: {test_input}")
    try:
        audio_path = extractor.process_input(test_input)
        print(f"  Audio ready at: {audio_path}")
    except Exception as e:
        print(f"  Extraction failed: {e}")
        return
        
    # Step 2: VAD
    print("\n[Step 2] Running Voice Activity Detection...")
    vad = VADProcessor()
    try:
        vad_intervals = vad.process(str(audio_path))
        print(f"  Detected {len(vad_intervals)} speech segments.")
    except Exception as e:
        print(f"  VAD failed: {e}")
        return
        
    # Step 3: Segmentation
    print(f"\n[Step 3] Sliding Window Segmentation (Window: {settings.WINDOW_SIZE_SECONDS}s, Step: {settings.WINDOW_STEP_SECONDS}s)")
    engine = SegmentationEngine()
    windows = engine.process(vad_intervals)
    print(f"  Generated {len(windows)} windows.")
    
    # Step 4: LID Inference
    print("\n[Step 4] Loading Language ID models...")
    try:
        lid = LIDProcessor()
    except Exception as e:
        print(f"  Failed to load LID models: {e}")
        return
    
    print(f"\n[Step 5] Running Language Identification on {len(windows)} windows...")
    try:
        results = lid.process(str(audio_path), windows)
    except Exception as e:
        print(f"  LID inference failed: {e}")
        return
    
    # Print Results
    print("\n" + "=" * 70)
    print(f"{'Window':<10} {'Time Range (MM:SS)':<22} {'Language':<12} {'Confidence':<12} {'Source':<12}")
    print("=" * 70)
    for i, r in enumerate(results):
        m_start, s_start = int(r['start'] // 60), r['start'] % 60
        m_end, s_end = int(r['end'] // 60), r['end'] % 60
        time_range = f"{m_start:02d}:{s_start:05.2f} -> {m_end:02d}:{s_end:05.2f}"
        print(f"  {i+1:<8} {time_range:<22} {r['language']:<12} {r['confidence']:<12.4f} {r['source']:<12}")
    print("=" * 70)
    
if __name__ == "__main__":
    main()
