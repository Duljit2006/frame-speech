import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline import LIDPipeline

def main():
    print("=" * 70)
    print("  Testing End-to-End LID Orchestrator (Phase 1 Final)")
    print("=" * 70)
    
    test_input = input("\nPaste a YouTube URL or local audio file path: ").strip()
    if not test_input:
        print("No input provided. Exiting.")
        return
        
    print("\n[System] Booting up LID Pipeline and loading AI models into GPU...")
    # Initialize the orchestrator (this loads the models once)
    pipeline = LIDPipeline()
    
    print(f"\n[System] Processing audio from: {test_input}")
    print("[System] This runs extraction, VAD, sliding windows, AI inference, and smoothing automatically...")
    
    # Run the entire pipeline with one command!
    timeline = pipeline.process(test_input)
    
    # Print the final results
    print("\n" + "=" * 70)
    print("  FINAL SMOOTHED LANGUAGE TIMELINE")
    print("=" * 70)
    
    if not timeline:
        print("  No speech detected or pipeline failed.")
        return
        
    print(f"{'#':<6} {'Time Range (MM:SS)':<26} {'Language':<14} {'Avg Conf':<10}")
    print("-" * 70)
    for i, block in enumerate(timeline):
        m_s, s_s = int(block['start'] // 60), block['start'] % 60
        m_e, s_e = int(block['end'] // 60), block['end'] % 60
        duration = block['end'] - block['start']
        
        time_range = f"{m_s:02d}:{s_s:05.2f} -> {m_e:02d}:{s_e:05.2f} ({duration:.1f}s)"
        print(f"  {i+1:<4} {time_range:<26} {block['language']:<14} {block.get('confidence', 0):<10.4f}")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
