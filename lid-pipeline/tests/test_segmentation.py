import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.stages.audio_extractor import AudioExtractor
from src.pipeline.stages.vad import VADProcessor
from src.pipeline.stages.segmentation import SegmentationEngine
from src.config import settings

def main():
    print("=== Testing Segmentation Engine (Full Chain) ===")
    
    test_input = input("Please paste a YouTube URL or a local video/audio file path: ").strip()
    if not test_input:
        print("No input provided. Exiting.")
        return
        
    # 1. Extract Audio
    extractor = AudioExtractor()
    print(f"\n[1] Extracting audio from: {test_input}")
    try:
        audio_path = extractor.process_input(test_input)
        print(f"Audio ready at: {audio_path}")
    except Exception as e:
        print(f"Extraction failed: {e}")
        return
        
    # 2. Run Voice Activity Detection
    print("\n[2] Running Voice Activity Detection...")
    vad = VADProcessor()
    try:
        vad_intervals = vad.process(str(audio_path))
        print(f"Detected {len(vad_intervals)} speech segments.")
        for i, iv in enumerate(vad_intervals):
             print(f"  VAD {i+1}: {iv['start']}s -> {iv['end']}s")
    except Exception as e:
        print(f"VAD failed: {e}")
        import traceback
        traceback.print_exc()
        return
        
    # 3. Run Segmentation Engine
    print(f"\n[3] Running Sliding Window Segmentation... (Size: {settings.WINDOW_SIZE_SECONDS}s, Step: {settings.WINDOW_STEP_SECONDS}s)")
    engine = SegmentationEngine()
    windows = engine.process(vad_intervals)
    
    print("\n[Output] Sliding Windows Generated:")
    for i, w in enumerate(windows):
        duration = round(w['end'] - w['start'], 3)
        print(f"  Window {i+1}: {w['start']:0.3f}s -> {w['end']:0.3f}s (Duration: {duration:0.3f}s)")
        
if __name__ == "__main__":
    main()
