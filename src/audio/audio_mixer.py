#!/usr/bin/env python3
"""Audio mixer for documentary soundtracks."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import tempfile
import os

from pydub import AudioSegment

from loguru import logger


class AudioMixer:
    """Mixes narration, music, and sound effects."""

    def __init__(
        self,
        output_dir: str = "output",
        sample_rate: int = 44100,
        channels: int = 2,
    ):
        """Initialize audio mixer.

        Args:
            output_dir: Output directory
            sample_rate: Audio sample rate
            channels: Number of audio channels
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sample_rate = sample_rate
        self.channels = channels

    def load_audio(self, path: str) -> AudioSegment:
        """Load audio file.

        Args:
            path: Audio file path

        Returns:
            AudioSegment object
        """
        return AudioSegment.from_file(path)

    def normalize_audio(
        self,
        audio: AudioSegment,
        target_db: float = -14.0,
    ) -> AudioSegment:
        """Normalize audio to target dB.

        Args:
            audio: AudioSegment to normalize
            target_db: Target dB level

        Returns:
            Normalized AudioSegment
        """
        change_in_dB = target_db - audio.dBFS
        return audio.apply_gain(change_in_dB)

    def mix_narration_with_music(
        self,
        narration_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.15,
        fade_in_seconds: float = 2.0,
        fade_out_seconds: float = 3.0,
    ) -> str:
        """Mix narration with background music.

        Args:
            narration_path: Path to narration audio
            music_path: Path to background music
            output_path: Output file path
            music_volume: Music volume (0.0 to 1.0)
            fade_in_seconds: Music fade in duration
            fade_out_seconds: Music fade out duration

        Returns:
            Path to mixed audio
        """
        logger.info("Mixing narration with background music")

        # Load audio
        narration = self.load_audio(narration_path)
        music = self.load_audio(music_path)

        # Normalize narration
        narration = self.normalize_audio(narration, target_db=-14.0)

        # Adjust music length to match narration
        duration_diff = len(narration) - len(music)

        if duration_diff > 0:
            # Music is shorter, loop it
            loops_needed = (len(narration) // len(music)) + 1
            music = music * loops_needed

        # Trim music to narration length
        music = music[: len(narration)]

        # Lower music volume
        music_reduction_db = 20 * (1 - music_volume)
        music = music - music_reduction_db

        # Apply fades to music
        music = music.fade_in(int(fade_in_seconds * 1000)).fade_out(
            int(fade_out_seconds * 1000)
        )

        # Mix
        mixed = narration.overlay(music)

        # Export
        mixed.export(output_path, format="mp3", bitrate="192k")

        logger.info(f"Mixed audio saved to {output_path}")
        return output_path

    def concatenate_segments(
        self,
        segment_paths: List[str],
        output_path: str,
        crossfade_ms: int = 500,
    ) -> str:
        """Concatenate audio segments with crossfade.

        Args:
            segment_paths: List of segment file paths
            output_path: Output file path
            crossfade_ms: Crossfade duration in milliseconds

        Returns:
            Path to concatenated audio
        """
        logger.info(f"Concatenating {len(segment_paths)} segments")

        if not segment_paths:
            raise ValueError("No segments provided")

        # Load first segment
        combined = self.load_audio(segment_paths[0])

        # Add remaining segments with crossfade
        for path in segment_paths[1:]:
            segment = self.load_audio(path)
            combined = combined.append(segment, crossfade=crossfade_ms)

        # Export
        combined.export(output_path, format="mp3", bitrate="192k")

        logger.info(f"Concatenated audio saved to {output_path}")
        return output_path

    def add_sound_effects(
        self,
        base_audio_path: str,
        sfx_list: List[Dict],
        output_path: str,
    ) -> str:
        """Add sound effects at specific timestamps.

        Args:
            base_audio_path: Base audio file path
            sfx_list: List of SFX with 'path', 'timestamp_ms', 'volume'
            output_path: Output file path

        Returns:
            Path to mixed audio
        """
        logger.info(f"Adding {len(sfx_list)} sound effects")

        base = self.load_audio(base_audio_path)

        for sfx in sfx_list:
            sfx_path = sfx.get("path")
            timestamp_ms = sfx.get("timestamp_ms", 0)
            volume = sfx.get("volume", 1.0)

            # Load sound effect
            sfx_audio = self.load_audio(sfx_path)

            # Adjust volume
            volume_db = 20 * (1 - volume)
            sfx_audio = sfx_audio - volume_db

            # Overlay at timestamp
            base = base.overlay(sfx_audio, position=timestamp_ms)

        # Export
        base.export(output_path, format="mp3", bitrate="192k")

        return output_path

    def create_documentary_audio(
        self,
        narration_dir: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.15,
    ) -> str:
        """Create complete documentary audio track.

        Args:
            narration_dir: Directory with narration segments
            music_path: Path to background music
            output_path: Output file path
            music_volume: Background music volume

        Returns:
            Path to final audio
        """
        logger.info("Creating documentary audio track")

        # Find all narration segments
        narration_dir = Path(narration_dir)
        segment_files = sorted(narration_dir.glob("*.mp3"))

        if not segment_files:
            raise ValueError(f"No narration segments found in {narration_dir}")

        # Concatenate narration segments
        with tempfile.TemporaryDirectory() as temp_dir:
            concat_path = os.path.join(temp_dir, "narration_concat.mp3")
            narration_path = self.concatenate_segments(
                [str(f) for f in segment_files],
                concat_path,
            )

            # Mix with music
            self.mix_narration_with_music(
                narration_path,
                music_path,
                output_path,
                music_volume=music_volume,
            )

        logger.info(f"Documentary audio created: {output_path}")
        return output_path

    def generate_silence(
        self,
        duration_seconds: float,
        output_path: str,
    ) -> str:
        """Generate silence audio.

        Args:
            duration_seconds: Duration in seconds
            output_path: Output file path

        Returns:
            Path to silence audio
        """
        silence = AudioSegment.silent(
            duration=int(duration_seconds * 1000),
            frame_rate=self.sample_rate,
        )
        silence.export(output_path, format="mp3")
        return output_path

    def get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds.

        Args:
            audio_path: Audio file path

        Returns:
            Duration in seconds
        """
        audio = self.load_audio(audio_path)
        return len(audio) / 1000.0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mix audio for documentary")
    parser.add_argument("--narration", type=str, required=True, help="Narration directory")
    parser.add_argument("--music", type=str, required=True, help="Background music file")
    parser.add_argument("--output", type=str, default="output/final_audio.mp3")
    parser.add_argument("--music-volume", type=float, default=0.15)
    args = parser.parse_args()

    mixer = AudioMixer()
    output = mixer.create_documentary_audio(
        args.narration,
        args.music,
        args.output,
        music_volume=args.music_volume,
    )

    print(f"Final audio: {output}")
    print(f"Duration: {mixer.get_audio_duration(output):.2f} seconds")


if __name__ == "__main__":
    main()
