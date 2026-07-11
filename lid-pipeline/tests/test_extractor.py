import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline.stages.audio_extractor import AudioExtractor

def main():
    print("=== Testing AudioExtractor ===")
    
    # Initialize the extractor (it will now use the lid-pipeline/data/processed_audio folder)
    extractor = AudioExtractor()
    print(f"Output directory initialized at: {extractor.output_dir}")
    
    print("\n--- URL Extraction Test ---")
    test_url = input("Please paste the YouTube/Instagram URL you want to test: ").strip()
    
    if not test_url:
        print("No URL provided. Exiting test.")
        return

    output_path = None
    try:
        print(f"\nDownloading from URL: {test_url}")
        print("This will download the audio using yt-dlp and convert to 16kHz Mono WAV using ffmpeg...")
        output_path = extractor.process_input(test_url)
        print(f"Success! Audio saved to: {output_path}")
        print(f"File exists: {output_path.exists()}")
        print(f"File size: {output_path.stat().st_size} bytes")
    except Exception as e:
        print(f"Error testing URL: {e}")
        import traceback
        traceback.print_exc()

    if output_path and output_path.exists():
        print("\n--- Local File Extraction Test ---")
        print("Now we will test the local file extraction logic by passing the newly created WAV file back into the extractor.")
        
        try:
            local_output = extractor.process_input(str(output_path))
            print(f"Success! Local file processed and saved to: {local_output}")
            print(f"File exists: {local_output.exists()}")
        except Exception as e:
            print(f"Error testing local file: {e}")

if __name__ == "__main__":
    main()
