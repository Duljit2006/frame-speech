import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Dict

# Force load .env into os.environ immediately so PyTorch/HF see it before they load
load_dotenv()

class Settings(BaseSettings):
    # Audio Processing Settings
    SAMPLE_RATE: int = 16000
    
    # VAD Settings
    VAD_THRESHOLD: float = 0.5
    
    # Sliding Window Settings
    WINDOW_SIZE_SECONDS: float = 3.0
    WINDOW_STEP_SECONDS: float = 1.0
    
    # Smoothing Settings
    SMOOTHING_KERNEL_SIZE: int = 5
    SMOOTHING_TIME_BIN_SECONDS: float = 0.5       # Resolution for majority voting
    MIN_SEGMENT_DURATION: float = 1.0             # Drop segments shorter than this
    MIN_MERGED_DURATION: float = 0.5              # Drop final merged blocks shorter than this
    
    # Language Family Grouping (acoustically identical languages merged under one label)
    LANGUAGE_FAMILY_MAP: Dict[str, str] = {
        "ur": "hi",       # Urdu -> Hindi (Hindustani)
    }
    
    # LID Settings
    LID_CONFIDENCE_THRESHOLD: float = 0.70
    FALLBACK_TO_WHISPER: bool = True
    TARGET_LANGUAGES: List[str] = ["en", "hi", "as"]
    
    # URL Download Settings
    MAX_URL_DURATION_SECONDS: int = 7200  # 2 hours

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'

# Global settings instance
settings = Settings()
