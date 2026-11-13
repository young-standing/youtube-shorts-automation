#!/usr/bin/env python3
"""TTS generator for documentary narration."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import os

from loguru import logger


class TTSGenerator:
    """Generates narration audio using TTS services."""

    def __init__(
        self,
        provider: str = "openai",
        voice: str = "onyx",
        output_dir: str = "output/narration",
    ):
        """Initialize TTS generator.

        Args:
            provider: TTS provider ('openai', 'elevenlabs', 'local')
            voice: Voice name/ID
            output_dir: Output directory
        """
        self.provider = provider
        self.voice = voice
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_narration_openai(
        self,
        text: str,
        output_path: str,
        speed: float = 1.0,
    ) -> str:
        """Generate narration using OpenAI TTS.

        Args:
            text: Text to convert
            output_path: Output file path
            speed: Speech speed (0.25 to 4.0)

        Returns:
            Path to generated audio
        """
        try:
            from openai import OpenAI

            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

            response = client.audio.speech.create(
                model="tts-1-hd",
                voice=self.voice,
                input=text,
                speed=speed,
            )

            # Save audio
            with open(output_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Generated narration: {output_path}")
            return output_path

        except ImportError:
            logger.error("OpenAI package not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            raise

    def generate_narration_elevenlabs(
        self,
        text: str,
        output_path: str,
    ) -> str:
        """Generate narration using ElevenLabs.

        Args:
            text: Text to convert
            output_path: Output file path

        Returns:
            Path to generated audio
        """
        try:
            import requests

            api_key = os.environ.get("ELEVENLABS_API_KEY")
            if not api_key:
                raise ValueError("ELEVENLABS_API_KEY not set")

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice}"

            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key,
            }

            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.5},
            }

            response = requests.post(url, json=data, headers=headers)

            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Generated narration: {output_path}")
                return output_path
            else:
                raise Exception(f"ElevenLabs API error: {response.status_code}")

        except ImportError:
            logger.error("requests package not installed")
            raise

    def generate_narration_local(
        self,
        text: str,
        output_path: str,
    ) -> str:
        """Generate narration using local TTS.

        Args:
            text: Text to convert
            output_path: Output file path

        Returns:
            Path to generated audio
        """
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()

            logger.info(f"Generated local narration: {output_path}")
            return output_path

        except ImportError:
            logger.error("pyttsx3 not installed. Run: pip install pyttsx3")
            raise

    def generate_narration(
        self,
        text: str,
        output_path: str,
        speed: float = 1.0,
    ) -> str:
        """Generate narration using configured provider.

        Args:
            text: Text to convert
            output_path: Output file path
            speed: Speech speed

        Returns:
            Path to generated audio
        """
        # Ensure text is not empty
        if not text.strip():
            logger.warning("Empty text provided for narration")
            return ""

        # Truncate very long text
        max_chars = 4000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
            logger.warning(f"Text truncated to {max_chars} characters")

        # Generate based on provider
        if self.provider == "openai":
            return self.generate_narration_openai(text, output_path, speed)
        elif self.provider == "elevenlabs":
            return self.generate_narration_elevenlabs(text, output_path)
        elif self.provider == "local":
            return self.generate_narration_local(text, output_path)
        else:
            raise ValueError(f"Unknown TTS provider: {self.provider}")

    def generate_documentary_narration(
        self,
        script_data: Dict,
        output_path: Optional[str] = None,
    ) -> List[str]:
        """Generate narration for entire documentary.

        Args:
            script_data: Script data with segments
            output_path: Optional base output path

        Returns:
            List of generated audio paths
        """
        generated = []

        segments = script_data.get("segments", [])
        title = script_data.get("title", "documentary")

        for i, segment in enumerate(segments):
            narration = segment.get("narration", "")
            segment_type = segment.get("segment_type", "main")

            if not narration.strip():
                continue

            # Generate output path
            safe_title = "".join(c if c.isalnum() else "_" for c in title[:20])
            segment_path = self.output_dir / f"{safe_title}_segment_{i:02d}.mp3"

            try:
                audio_path = self.generate_narration(narration, str(segment_path))
                if audio_path:
                    generated.append(audio_path)
            except Exception as e:
                logger.error(f"Failed to generate narration for segment {i}: {e}")

        logger.info(f"Generated {len(generated)} narration segments")

        # Save list if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(generated, indent=2))

        return generated


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate TTS narration")
    parser.add_argument("--input", type=str, required=True, help="Input script JSON")
    parser.add_argument("--output", type=str, default="output/narration/")
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "elevenlabs", "local"],
    )
    parser.add_argument("--voice", type=str, default="onyx")
    args = parser.parse_args()

    # Load script
    with open(args.input, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    # Generate narration
    generator = TTSGenerator(
        provider=args.provider,
        voice=args.voice,
        output_dir=args.output,
    )
    generated = generator.generate_documentary_narration(script_data)

    print(f"Generated {len(generated)} narration segments")


if __name__ == "__main__":
    main()
