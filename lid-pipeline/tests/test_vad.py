import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.stages.audio_extractor import AudioExtractor
from src.pipeline.stages.vad import VADProcessor

def main():
    print("=== Testing Silero VAD ===")
    
    test_url = input("Please paste the YouTube/Instagram URL you want to test for VAD: ").strip()
    if not test_url:
        print("No URL provided. Exiting.")
        return
        
    # 1. Grab some audio
    extractor = AudioExtractor()
    print(f"\nDownloading audio from: {test_url}")
    try:
        audio_path = extractor.process_input(test_url)
        print(f"Audio successfully downloaded to: {audio_path}")
    except Exception as e:
        print(f"Failed to extract audio: {e}")
        return
    
    # 2. Run VAD
    print("\nInitializing VADProcessor (loading Silero model)...")
    vad = VADProcessor()
    
    print("\nRunning Voice Activity Detection...")
    intervals = []
    try:
        intervals = vad.process(str(audio_path))
        print(f"\nDetected {len(intervals)} speech segments:")
        for i, interval in enumerate(intervals):
            duration = round(interval['end'] - interval['start'], 3)
            print(f"  Segment {i+1}: {interval['start']:0.3f}s -> {interval['end']:0.3f}s (Duration: {duration:0.3f}s)")
    except Exception as e:
        print(f"Error running VAD: {e}")
        import traceback
        traceback.print_exc()
        return

    # Offer to slice and export the segments for manual verification
    if intervals:
        export_choice = input("\nWould you like to export these segments as separate WAV files to listen and verify? (y/n): ").strip().lower()
        if export_choice == 'y':
            try:
                import soundfile as sf
                
                # Load the full audio file
                audio_data, sr = sf.read(audio_path)
                
                # Create output directory for segments
                segments_dir = Path(audio_path).parent / "segments"
                segments_dir.mkdir(parents=True, exist_ok=True)
                
                # Clean old segments
                for f in segments_dir.glob("*.wav"):
                    f.unlink()
                
                print(f"\nExporting segments to: {segments_dir}")
                for i, interval in enumerate(intervals):
                    start_sample = int(interval['start'] * sr)
                    end_sample = int(interval['end'] * sr)
                    segment_data = audio_data[start_sample:end_sample]
                    
                    segment_file = segments_dir / f"segment_{i+1}.wav"
                    sf.write(str(segment_file), segment_data, sr)
                    print(f"  Saved: [segment_{i+1}.wav](file:///{segment_file.as_posix()}) ({round(interval['end'] - interval['start'], 3)}s)")
                
                print("\nVerification files generated! You can Ctrl+Click the links above to open and listen to them directly in VS Code.")
            except Exception as e:
                print(f"Failed to export segments: {e}")

if __name__ == "__main__":
    main()
