#!/usr/bin/env python3
"""Infographic generator for Vox-style documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from loguru import logger


class InfographicGenerator:
    """Generates animated infographics for documentaries."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        output_dir: str = "output/infographics",
    ):
        """Initialize infographic generator.

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

        # Color scheme (Vox-style)
        self.colors = {
            "background": "#1A1A2E",
            "primary": "#2C3E50",
            "secondary": "#E74C3C",
            "accent": "#3498DB",
            "text": "#FFFFFF",
            "highlight": "#F39C12",
        }

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def create_title_card(
        self,
        title: str,
        subtitle: str = "",
        duration_seconds: float = 5.0,
    ) -> str:
        """Create animated title card.

        Args:
            title: Main title
            subtitle: Optional subtitle
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating title card: {title}")

        # Create frames
        total_frames = int(duration_seconds * self.fps)
        frames = []

        for frame_num in range(total_frames):
            # Create image
            img = Image.new("RGB", (self.width, self.height), self.colors["background"])
            draw = ImageDraw.Draw(img)

            # Calculate animation progress
            progress = frame_num / total_frames
            alpha = min(1.0, progress * 2)  # Fade in

            # Try to load font, fall back to default
            try:
                title_font = ImageFont.truetype("arial.ttf", 72)
                subtitle_font = ImageFont.truetype("arial.ttf", 36)
            except OSError:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()

            # Draw title (centered)
            title_bbox = draw.textbbox((0, 0), title, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (self.width - title_width) // 2
            title_y = self.height // 2 - 50

            # Apply alpha for fade effect
            text_color = self.hex_to_rgb(self.colors["text"])
            draw.text(
                (title_x, title_y),
                title,
                fill=text_color,
                font=title_font,
            )

            # Draw subtitle
            if subtitle:
                sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
                sub_width = sub_bbox[2] - sub_bbox[0]
                sub_x = (self.width - sub_width) // 2
                sub_y = title_y + 100

                draw.text(
                    (sub_x, sub_y),
                    subtitle,
                    fill=self.hex_to_rgb(self.colors["accent"]),
                    font=subtitle_font,
                )

            frames.append(np.array(img))

        # Save as video
        output_path = self.output_dir / f"title_{title.replace(' ', '_')[:20]}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def create_fact_card(
        self,
        fact: str,
        source: str = "",
        duration_seconds: float = 6.0,
    ) -> str:
        """Create animated fact card.

        Args:
            fact: Fact text
            source: Source attribution
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating fact card: {fact[:50]}...")

        total_frames = int(duration_seconds * self.fps)
        frames = []

        for frame_num in range(total_frames):
            img = Image.new("RGB", (self.width, self.height), self.colors["background"])
            draw = ImageDraw.Draw(img)

            progress = frame_num / total_frames

            # Background shape
            if progress < 0.3:
                # Slide in animation
                slide_progress = progress / 0.3
                rect_x = int(-400 + slide_progress * 400)
            else:
                rect_x = 0

            # Draw accent rectangle
            draw.rectangle(
                [rect_x, 200, rect_x + 100, self.height - 200],
                fill=self.colors["secondary"],
            )

            # Try to load font
            try:
                fact_font = ImageFont.truetype("arial.ttf", 48)
                source_font = ImageFont.truetype("arial.ttf", 24)
            except OSError:
                fact_font = ImageFont.load_default()
                source_font = ImageFont.load_default()

            # Wrap fact text
            wrapped_fact = self._wrap_text(fact, fact_font, 1400)

            # Draw fact
            fact_bbox = draw.textbbox((0, 0), wrapped_fact, font=fact_font)
            fact_height = fact_bbox[3] - fact_bbox[1]
            fact_x = 200
            fact_y = (self.height - fact_height) // 2

            draw.text(
                (fact_x, fact_y),
                wrapped_fact,
                fill=self.hex_to_rgb(self.colors["text"]),
                font=fact_font,
            )

            # Draw source
            if source and progress > 0.7:
                draw.text(
                    (fact_x, fact_y + fact_height + 40),
                    f"Source: {source}",
                    fill=self.hex_to_rgb(self.colors["accent"]),
                    font=source_font,
                )

            frames.append(np.array(img))

        # Save as video
        safe_fact = "".join(c if c.isalnum() else "_" for c in fact[:20])
        output_path = self.output_dir / f"fact_{safe_fact}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def create_stat_comparison(
        self,
        stats: List[Dict],
        title: str,
        duration_seconds: float = 8.0,
    ) -> str:
        """Create animated stat comparison.

        Args:
            stats: List of stats with 'label' and 'value'
            title: Comparison title
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating stat comparison: {title}")

        total_frames = int(duration_seconds * self.fps)
        frames = []

        for frame_num in range(total_frames):
            progress = frame_num / total_frames

            # Use matplotlib for better charts
            fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
            fig.patch.set_facecolor(self.colors["background"])
            ax.set_facecolor(self.colors["background"])

            # Draw bars with animation
            max_value = max(s["value"] for s in stats)
            num_stats = len(stats)

            for i, stat in enumerate(stats):
                # Animate bar height
                animated_value = stat["value"] * min(1.0, progress * 1.5)
                bar_height = (animated_value / max_value) * 0.7

                bar = patches.FancyBboxPatch(
                    (i / num_stats + 0.05, 0.1),
                    0.15,
                    bar_height,
                    boxstyle="round,pad=0.01",
                    facecolor=self.colors["secondary"],
                    edgecolor="none",
                )
                ax.add_patch(bar)

                # Add label
                ax.text(
                    i / num_stats + 0.125,
                    bar_height + 0.12,
                    stat["label"],
                    ha="center",
                    va="bottom",
                    fontsize=16,
                    color=self.colors["text"],
                )

                # Add value
                ax.text(
                    i / num_stats + 0.125,
                    bar_height + 0.02,
                    f"{int(animated_value):,}",
                    ha="center",
                    va="bottom",
                    fontsize=24,
                    fontweight="bold",
                    color=self.colors["highlight"],
                )

            # Title
            ax.text(
                0.5,
                0.95,
                title,
                ha="center",
                va="top",
                fontsize=32,
                fontweight="bold",
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            # Convert to numpy array
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames.append(img)

            plt.close(fig)

        # Save as video
        safe_title = "".join(c if c.isalnum() else "_" for c in title[:20])
        output_path = self.output_dir / f"stats_{safe_title}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
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

        return "\n".join(lines)

    def _save_video(self, frames: List[np.ndarray], output_path: Path):
        """Save frames as video using ffmpeg."""
        import tempfile
        import os

        # Create temporary directory for frames
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save frames as images
            for i, frame in enumerate(frames):
                frame_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
                Image.fromarray(frame).save(frame_path)

            # Use ffmpeg to create video
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-framerate", str(self.fps),
                "-i", os.path.join(temp_dir, "frame_%05d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-crf", "18",
                str(output_path),
            ]

            subprocess.run(ffmpeg_cmd, capture_output=True)

        logger.info(f"Video saved to {output_path}")

    def generate_infographics(
        self,
        script_data: Dict,
        research_data: Dict,
        output_path: Optional[str] = None,
    ) -> List[str]:
        """Generate all infographics for a documentary.

        Args:
            script_data: Script data
            research_data: Research data
            output_path: Optional output path

        Returns:
            List of generated video paths
        """
        generated = []

        # Title card
        title = script_data.get("title", "Documentary")
        title_card = self.create_title_card(
            title=title,
            subtitle="Empire Histories",
            duration_seconds=5.0,
        )
        generated.append(title_card)

        # Fact cards from key facts
        segments = script_data.get("segments", [])
        for segment in segments:
            key_facts = segment.get("key_facts", [])
            for fact in key_facts[:2]:  # Limit to 2 facts per segment
                if len(fact) > 20:  # Skip very short facts
                    fact_card = self.create_fact_card(fact, duration_seconds=6.0)
                    generated.append(fact_card)

        logger.info(f"Generated {len(generated)} infographics")

        # Save list if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(generated, indent=2))

        return generated


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate infographics")
    parser.add_argument("--input", type=str, required=True, help="Input script JSON")
    parser.add_argument("--research", type=str, required=True, help="Research JSON")
    parser.add_argument("--output", type=str, default="output/infographics/")
    args = parser.parse_args()

    # Load data
    with open(args.input, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    with open(args.research, "r", encoding="utf-8") as f:
        research_data = json.load(f)

    # Generate infographics
    generator = InfographicGenerator(output_dir=args.output)
    generated = generator.generate_infographics(script_data, research_data)

    print(f"Generated {len(generated)} infographics")


if __name__ == "__main__":
    main()
