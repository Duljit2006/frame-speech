class PipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass

class AudioExtractionError(PipelineError):
    """Raised when audio extraction from file or URL fails."""
    pass

class URLDownloadError(AudioExtractionError):
    """Raised when URL download via yt-dlp fails (e.g. private, unsupported)."""
    pass

class VADError(PipelineError):
    """Raised when Voice Activity Detection fails."""
    pass

class WindowingError(PipelineError):
    """Raised when audio chunking/windowing fails."""
    pass

class LIDInferenceError(PipelineError):
    """Raised when language identification inference fails."""
    pass

class TranscriptionError(PipelineError):
    """Raised when audio transcription fails."""
    pass
