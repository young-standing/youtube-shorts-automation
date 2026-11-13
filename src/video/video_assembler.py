#!/usr/bin/env python3
"""Video assembler for documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import tempfile
import os

from loguru import logger


class VideoAssembler:
    """Assembles final documentary video."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        output_dir: str = "output",
    ):
        """Initialize video assembler.

        Args:
            width: Output width
            height: Output height
            fps: Frames per second
            output_dir: Output directory
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_segment_clip(
        self,
        visuals: List[str],
        narration: str,
        duration: float,
        output_path: str,
    ) -> str:
        """Create a video segment from visuals and narration.

        Args:
            visuals: List of visual file paths (images/videos)
            narration: Narration audio path
            duration: Duration in seconds
            output_path: Output file path

        Returns:
            Path to created segment
        """
        logger.info(f"Creating segment: {output_path}")

        if not visuals:
            # Create blank segment with narration
            return self._create_blank_segment(narration, duration, output_path)

        # Determine visual duration per item
        visual_duration = duration / len(visuals)

        with tempfile.TemporaryDirectory() as temp_dir:
            processed_visuals = []

            for i, visual in enumerate(visuals):
                visual_path = Path(visual)

                if visual_path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    # Convert image to video with Ken Burns effect
                    processed = self._image_to_video(
                        str(visual_path),
                        visual_duration,
                        os.path.join(temp_dir, f"visual_{i:03d}.mp4"),
                    )
                    processed_visuals.append(processed)
                else:
                    # Already a video
                    processed_visuals.append(str(visual_path))

            # Concatenate visuals
            concat_path = os.path.join(temp_dir, "concat.txt")
            with open(concat_path, "w") as f:
                for visual in processed_visuals:
                    f.write(f"file '{os.path.abspath(visual)}'\n")

            concat_video = os.path.join(temp_dir, "concat.mp4")

            # Concatenate
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_path,
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    "-r", str(self.fps),
                    concat_video,
                ],
                capture_output=True,
                check=True,
            )

            # Add narration audio
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", concat_video,
                    "-i", narration,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    output_path,
                ],
                capture_output=True,
                check=True,
            )

        logger.info(f"Segment created: {output_path}")
        return output_path

    def _image_to_video(
        self,
        image_path: str,
        duration: float,
        output_path: str,
    ) -> str:
        """Convert static image to video with animation.

        Args:
            image_path: Image file path
            duration: Duration in seconds
            output_path: Output video path

        Returns:
            Path to created video
        """
        # Use zoompan filter for Ken Burns effect
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop", "1",
                "-i", image_path,
                "-vf",
                f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,"
                f"pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,"
                f"zoompan=z='min(zoom+0.0003,1.2)':d={int(duration * self.fps)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}:fps={self.fps}",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-t", str(duration),
                "-r", str(self.fps),
                output_path,
            ],
            capture_output=True,
            check=True,
        )

        return output_path

    def _create_blank_segment(
        self,
        narration: str,
        duration: float,
        output_path: str,
    ) -> str:
        """Create blank video segment with narration.

        Args:
            narration: Narration audio path
            duration: Duration in seconds
            output_path: Output file path

        Returns:
            Path to created segment
        """
        # Create colored background
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x1a1a2e:s={self.width}x{self.height}:d={duration}:r={self.fps}",
                "-i", narration,
                "-c:v", "libx264",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                output_path,
            ],
            capture_output=True,
            check=True,
        )

        return output_path

    def assemble_documentary(
        self,
        script: Dict,
        narration: str,
        images: List[str],
        videos: List[str],
        infographics: List[str],
        maps: List[str],
        timelines: List[str],
        output_path: str,
    ) -> str:
        """Assemble complete documentary.

        Args:
            script: Script data
            narration: Final narration audio path
            images: List of image paths
            videos: List of video paths
            infographics: List of infographic video paths
            maps: List of map animation paths
            timelines: List of timeline paths
            output_path: Output file path

        Returns:
            Path to final documentary
        """
        logger.info("Assembling documentary")

        segments = script.get("segments", [])
        title = script.get("title", "documentary")

        # Get total narration duration
        narration_duration = self._get_audio_duration(narration)

        # Collect all visuals
        all_visuals = {
            "images": images,
            "videos": videos,
            "infographics": infographics,
            "maps": maps,
            "timelines": timelines,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create segments
            segment_paths = []
            visual_index = 0

            for i, segment in enumerate(segments):
                segment_duration = segment.get("duration_seconds", 30)
                segment_type = segment.get("segment_type", "main")

                # Select visuals for this segment
                segment_visuals = []

                # Use title card for intro
                if segment_type == "intro" and infographics:
                    segment_visuals.append(infographics[0])

                # Use maps for geography-related segments
                elif "territory" in segment.get("title", "").lower() and maps:
                    segment_visuals.extend(maps[:2])

                # Use timelines for chronological segments
                elif "timeline" in segment.get("title", "").lower() and timelines:
                    segment_visuals.extend(timelines[:2])

                # Use images/videos for main content
                else:
                    # Add images
                    while (
                        visual_index < len(images)
                        and len(segment_visuals) < 3
                    ):
                        segment_visuals.append(images[visual_index])
                        visual_index += 1

                    # Add videos
                    video_idx = 0
                    while (
                        video_idx < len(videos)
                        and len(segment_visuals) < 5
                    ):
                        segment_visuals.append(videos[video_idx])
                        video_idx += 1

                    # Add infographics
                    if infographics and i < len(infographics):
                        segment_visuals.append(infographics[i])

                # Create segment
                segment_path = os.path.join(temp_dir, f"segment_{i:02d}.mp4")

                try:
                    # Extract segment audio (simplified - in production, split by timestamps)
                    segment_audio = narration  # Use full narration for now

                    if segment_visuals:
                        self.create_segment_clip(
                            segment_visuals,
                            segment_audio,
                            min(segment_duration, narration_duration / len(segments)),
                            segment_path,
                        )
                        segment_paths.append(segment_path)

                except Exception as e:
                    logger.warning(f"Failed to create segment {i}: {e}")

            if not segment_paths:
                raise ValueError("No segments created")

            # Concatenate all segments
            concat_list = os.path.join(temp_dir, "concat.txt")
            with open(concat_list, "w") as f:
                for path in segment_paths:
                    f.write(f"file '{os.path.abspath(path)}'\n")

            # Final concatenation
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list,
                    "-i", narration,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:v", "8000k",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-map", "0:v",
                    "-map", "1:a",
                    "-shortest",
                    output_path,
                ],
                capture_output=True,
                check=True,
            )

        logger.info(f"Documentary assembled: {output_path}")
        return output_path

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds."""
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Assemble documentary video")
    parser.add_argument("--script", type=str, required=True)
    parser.add_argument("--narration", type=str, required=True)
    parser.add_argument("--images", type=str, nargs="*", default=[])
    parser.add_argument("--videos", type=str, nargs="*", default=[])
    parser.add_argument("--infographics", type=str, nargs="*", default=[])
    parser.add_argument("--maps", type=str, nargs="*", default=[])
    parser.add_argument("--timelines", type=str, nargs="*", default=[])
    parser.add_argument("--output", type=str, default="output/documentary.mp4")
    args = parser.parse_args()

    # Load script
    with open(args.script, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    assembler = VideoAssembler()
    output = assembler.assemble_documentary(
        script_data,
        args.narration,
        args.images,
        args.videos,
        args.infographics,
        args.maps,
        args.timelines,
        args.output,
    )

    print(f"Documentary: {output}")


if __name__ == "__main__":
    main()
