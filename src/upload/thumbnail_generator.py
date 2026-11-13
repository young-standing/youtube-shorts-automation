#!/usr/bin/env python3
"""Thumbnail generator for YouTube videos."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import tempfile
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

from loguru import logger


class ThumbnailGenerator:
    """Generates thumbnails for YouTube videos."""

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        output_dir: str = "output",
    ):
        """Initialize thumbnail generator.

        Args:
            width: Thumbnail width (YouTube recommends 1280)
            height: Thumbnail height (YouTube recommends 720)
            output_dir: Output directory
        """
        self.width = width
        self.height = height
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Design colors
        self.colors = {
            "background": "#1A1A2E",
            "primary": "#E74C3C",
            "secondary": "#3498DB",
            "text": "#FFFFFF",
            "highlight": "#F39C12",
        }

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def create_thumbnail_from_video(
        self,
        video_path: str,
        timestamp: float = 0.0,
        output_path: str = None,
    ) -> str:
        """Extract thumbnail from video.

        Args:
            video_path: Video file path
            timestamp: Timestamp in seconds
            output_path: Output file path

        Returns:
            Path to thumbnail
        """
        if not output_path:
            output_path = self.output_dir / "thumbnail_frame.jpg"

        # Use ffmpeg to extract frame
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-s", f"{self.width}x{self.height}",
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

        logger.info(f"Thumbnail extracted: {output_path}")
        return str(output_path)

    def create_text_overlay_thumbnail(
        self,
        title: str,
        subtitle: str = "",
        background_color: str = None,
        text_color: str = None,
        output_path: str = None,
    ) -> str:
        """Create thumbnail with text overlay.

        Args:
            title: Main title text
            subtitle: Subtitle text
            background_color: Background color (hex)
            text_color: Text color (hex)
            output_path: Output file path

        Returns:
            Path to thumbnail
        """
        if not output_path:
            output_path = self.output_dir / "thumbnail_text.jpg"

        # Create background
        bg_color = self.hex_to_rgb(background_color or self.colors["background"])
        img = Image.new("RGB", (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
            subtitle_font = ImageFont.truetype("arial.ttf", 36)
        except OSError:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()

        text_col = self.hex_to_rgb(text_color or self.colors["text"])

        # Draw title
        # Wrap title if too long
        title_lines = self._wrap_text(title, title_font, self.width - 100)

        y_offset = self.height // 2 - 50
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            line_width = bbox[2] - bbox[0]
            x = (self.width - line_width) // 2

            # Draw shadow
            draw.text((x + 3, y_offset + 3), line, fill=(0, 0, 0), font=title_font)
            # Draw text
            draw.text((x, y_offset), line, fill=text_col, font=title_font)

            y_offset += 80

        # Draw subtitle
        if subtitle:
            bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            sub_width = bbox[2] - bbox[0]
            x = (self.width - sub_width) // 2

            draw.text(
                (x + 2, y_offset + 22),
                subtitle,
                fill=(0, 0, 0),
                font=subtitle_font,
            )
            draw.text(
                (x, y_offset + 20),
                subtitle,
                fill=self.hex_to_rgb(self.colors["highlight"]),
                font=subtitle_font,
            )

        # Save
        img.save(output_path, quality=95)

        logger.info(f"Text thumbnail created: {output_path}")
        return str(output_path)

    def create_composite_thumbnail(
        self,
        video_path: str,
        title: str,
        subtitle: str = "",
        overlay_opacity: float = 0.3,
        output_path: str = None,
    ) -> str:
        """Create composite thumbnail from video + text.

        Args:
            video_path: Video file path
            title: Main title
            subtitle: Subtitle
            overlay_opacity: Dark overlay opacity (0-1)
            output_path: Output file path

        Returns:
            Path to thumbnail
        """
        if not output_path:
            output_path = self.output_dir / "thumbnail.jpg"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract frame from video
            frame_path = os.path.join(temp_dir, "frame.jpg")
            self.create_thumbnail_from_video(video_path, 0.0, frame_path)

            # Load frame
            background = Image.open(frame_path).convert("RGB")
            background = background.resize((self.width, self.height), Image.Resampling.LANCZOS)

            # Apply color enhancement
            enhancer = ImageEnhance.Contrast(background)
            background = enhancer.enhance(1.2)

            enhancer = ImageEnhance.Color(background)
            background = enhancer.enhance(0.9)

            # Create dark overlay
            overlay = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            overlay.putalpha(int(255 * overlay_opacity))

            # Composite
            background = background.convert("RGBA")
            background = Image.alpha_composite(background, overlay)

            # Add text
            draw = ImageDraw.Draw(background)

            try:
                title_font = ImageFont.truetype("arial.ttf", 64)
                subtitle_font = ImageFont.truetype("arial.ttf", 32)
            except OSError:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()

            # Title with shadow
            title_lines = self._wrap_text(title, title_font, self.width - 100)
            y_offset = self.height // 2 - len(title_lines) * 40

            for line in title_lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                line_width = bbox[2] - bbox[0]
                x = (self.width - line_width) // 2

                # Shadow
                draw.text((x + 3, y_offset + 3), line, fill=(0, 0, 0, 200), font=title_font)
                # Text
                draw.text((x, y_offset), line, fill=(255, 255, 255, 255), font=title_font)

                y_offset += 70

            # Subtitle
            if subtitle:
                bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
                sub_width = bbox[2] - bbox[0]
                x = (self.width - sub_width) // 2

                draw.text((x, y_offset + 20), subtitle, fill=(255, 200, 50, 255), font=subtitle_font)

            # Convert to RGB and save
            background.convert("RGB").save(output_path, quality=95)

        logger.info(f"Composite thumbnail created: {output_path}")
        return str(output_path)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wrap text to fit within max width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines[:3]  # Max 3 lines

    def generate_thumbnail(
        self,
        video_path: str,
        metadata_path: str,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate thumbnail from video and metadata.

        Args:
            video_path: Video file path
            metadata_path: Metadata JSON path
            output_path: Optional output path

        Returns:
            Path to thumbnail
        """
        # Load metadata
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        title = metadata.get("title", "Documentary")
        subtitle = "Empire Histories"

        # Generate composite thumbnail
        if not output_path:
            output_path = str(self.output_dir / "thumbnail.jpg")

        return self.create_composite_thumbnail(
            video_path,
            title,
            subtitle,
            overlay_opacity=0.4,
            output_path=output_path,
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate YouTube thumbnail")
    parser.add_argument("--video", type=str, required=True, help="Video file path")
    parser.add_argument("--metadata", type=str, required=True, help="Metadata JSON")
    parser.add_argument("--output", type=str, default="output/thumbnail.jpg")
    args = parser.parse_args()

    generator = ThumbnailGenerator()
    thumbnail = generator.generate_thumbnail(
        args.video,
        args.metadata,
        args.output,
    )

    print(f"Thumbnail: {thumbnail}")


if __name__ == "__main__":
    main()
