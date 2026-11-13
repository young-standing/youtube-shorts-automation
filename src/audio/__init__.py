"""Audio module for documentary generation."""
from .tts_generator import TTSGenerator
from .audio_mixer import AudioMixer

__all__ = [
    "TTSGenerator",
    "AudioMixer",
]
