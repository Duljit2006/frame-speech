import sys
import os
from pathlib import Path

# Add the LID Pipeline to Python path so we can import its modules
PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "lid-pipeline"
sys.path.append(str(PIPELINE_ROOT))

from src.pipeline import LIDPipeline
from src.pipeline.stages.audio_extractor import AudioExtractor

class AppState:
    """Holds global instances of our heavy AI models so they only load once."""
    lid_pipeline: LIDPipeline = None
    extractor: AudioExtractor = None

state = AppState()
