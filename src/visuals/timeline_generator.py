#!/usr/bin/env python3
"""Timeline generator for historical documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation

from loguru import logger


class TimelineGenerator:
    """Creates animated historical timelines."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        output_dir: str = "output/timelines",
    ):
        """Initialize timeline generator.

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

        # Timeline colors
        self.colors = {
            "background": "#1A1A2E",
            "timeline": "#2C3E50",
            "marker": "#E74C3C",
            "text": "#FFFFFF",
            "highlight": "#F39C12",
            "secondary": "#3498DB",
        }

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def parse_year(self, year_str: str) -> int:
        """Parse year string to integer.

        Args:
            year_str: Year string (e.g., "500 BC", "476 AD")

        Returns:
            Integer year (negative for BC)
        """
        year_str = year_str.strip().upper()

        # Remove BC/AD suffix
        is_bc = "BC" in year_str or "BCE" in year_str
        year_num = int("".join(c for c in year_str if c.isdigit() or c == "-"))

        return -year_num if is_bc else year_num

    def create_horizontal_timeline(
        self,
        title: str,
        events: List[Dict],
        duration_seconds: float = 8.0,
    ) -> str:
        """Create animated horizontal timeline.

        Args:
            title: Timeline title
            events: List of events with 'year' and 'title'
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating horizontal timeline: {title}")

        if not events:
            logger.warning("No events provided for timeline")
            return ""

        # Sort events by year
        sorted_events = sorted(
            events,
            key=lambda e: self.parse_year(e.get("year", "0")),
        )

        total_frames = int(duration_seconds * self.fps)

        def animate(frame):
            fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
            fig.patch.set_facecolor(self.colors["background"])
            ax.set_facecolor(self.colors["background"])

            progress = frame / total_frames

            # Calculate year range
            years = [self.parse_year(e["year"]) for e in sorted_events]
            min_year = min(years) - 50
            max_year = max(years) + 50
            year_range = max_year - min_year

            # Draw timeline base
            timeline_y = 0.3
            ax.plot(
                [0, 1],
                [timeline_y, timeline_y],
                color=self.colors["timeline"],
                linewidth=4,
                transform=ax.transAxes,
            )

            # Calculate which events to show
            events_shown = int(progress * (len(sorted_events) + 1))

            # Draw events
            for i, event in enumerate(sorted_events[:events_shown]):
                year = self.parse_year(event["year"])
                x_pos = (year - min_year) / year_range

                # Event marker
                marker_alpha = 1.0 if i < events_shown - 1 else (progress * (len(sorted_events) + 1) - events_shown + 1)

                ax.plot(
                    x_pos, timeline_y,
                    "o",
                    markersize=20,
                    color=self.colors["marker"],
                    alpha=min(1.0, marker_alpha),
                    transform=ax.transAxes,
                    markeredgecolor=self.colors["text"],
                    markeredgewidth=2,
                )

                # Event label
                ax.text(
                    x_pos, timeline_y + 0.1,
                    event.get("year", ""),
                    ha="center",
                    va="bottom",
                    fontsize=16,
                    fontweight="bold",
                    color=self.colors["highlight"],
                    alpha=min(1.0, marker_alpha),
                    transform=ax.transAxes,
                )

                # Event title (wrapped)
                event_title = event.get("title", "")
                if len(event_title) > 30:
                    event_title = event_title[:27] + "..."

                ax.text(
                    x_pos, timeline_y - 0.15,
                    event_title,
                    ha="center",
                    va="top",
                    fontsize=12,
                    color=self.colors["text"],
                    alpha=min(1.0, marker_alpha),
                    transform=ax.transAxes,
                    wrap=True,
                )

                # Draw connection line
                if i > 0:
                    prev_year = self.parse_year(sorted_events[i - 1]["year"])
                    prev_x = (prev_year - min_year) / year_range

                    ax.plot(
                        [prev_x, x_pos],
                        [timeline_y - 0.05, timeline_y - 0.05],
                        color=self.colors["secondary"],
                        linewidth=2,
                        alpha=0.5,
                        transform=ax.transAxes,
                    )

            # Title
            ax.text(
                0.5, 0.9,
                title,
                ha="center",
                va="top",
                fontsize=32,
                fontweight="bold",
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            # Year range labels
            ax.text(
                0.05, 0.15,
                f"{min_year}",
                ha="left",
                fontsize=14,
                color=self.colors["text"],
                transform=ax.transAxes,
            )
            ax.text(
                0.95, 0.15,
                f"{max_year}",
                ha="right",
                fontsize=14,
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            # Convert to image
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

            plt.close(fig)
            return img

        # Generate frames
        frames = [animate(i) for i in range(total_frames)]

        # Save video
        safe_title = "".join(c if c.isalnum() else "_" for c in title[:20])
        output_path = self.output_dir / f"timeline_{safe_title}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def create_vertical_timeline(
        self,
        title: str,
        events: List[Dict],
        duration_seconds: float = 10.0,
    ) -> str:
        """Create animated vertical timeline.

        Args:
            title: Timeline title
            events: List of events
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating vertical timeline: {title}")

        if not events:
            return ""

        sorted_events = sorted(
            events,
            key=lambda e: self.parse_year(e.get("year", "0")),
        )

        total_frames = int(duration_seconds * self.fps)

        def animate(frame):
            fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
            fig.patch.set_facecolor(self.colors["background"])
            ax.set_facecolor(self.colors["background"])

            progress = frame / total_frames

            # Draw timeline base (vertical)
            timeline_x = 0.5
            ax.plot(
                [timeline_x, timeline_x],
                [0.1, 0.9],
                color=self.colors["timeline"],
                linewidth=4,
                transform=ax.transAxes,
            )

            events_shown = int(progress * (len(sorted_events) + 1))

            # Draw events alternating left and right
            for i, event in enumerate(sorted_events[:events_shown]):
                y_pos = 0.85 - (i / len(sorted_events)) * 0.7

                # Alternate sides
                side = 1 if i % 2 == 0 else -1
                x_offset = 0.15

                marker_alpha = 1.0 if i < events_shown - 1 else (progress * (len(sorted_events) + 1) - events_shown + 1)

                # Event marker
                ax.plot(
                    timeline_x, y_pos,
                    "o",
                    markersize=15,
                    color=self.colors["marker"],
                    alpha=min(1.0, marker_alpha),
                    transform=ax.transAxes,
                    markeredgecolor=self.colors["text"],
                    markeredgewidth=2,
                )

                # Connection line
                ax.plot(
                    [timeline_x, timeline_x + side * 0.05],
                    [y_pos, y_pos],
                    color=self.colors["secondary"],
                    linewidth=2,
                    transform=ax.transAxes,
                )

                # Year label
                ax.text(
                    timeline_x + side * (0.05 + 0.02),
                    y_pos + 0.02,
                    event.get("year", ""),
                    ha="left" if side == 1 else "right",
                    va="bottom",
                    fontsize=14,
                    fontweight="bold",
                    color=self.colors["highlight"],
                    alpha=min(1.0, marker_alpha),
                    transform=ax.transAxes,
                )

                # Event title
                event_title = event.get("title", "")
                if len(event_title) > 40:
                    event_title = event_title[:37] + "..."

                ax.text(
                    timeline_x + side * (0.05 + 0.02),
                    y_pos - 0.03,
                    event_title,
                    ha="left" if side == 1 else "right",
                    va="top",
                    fontsize=11,
                    color=self.colors["text"],
                    alpha=min(1.0, marker_alpha),
                    transform=ax.transAxes,
                )

            # Title
            ax.text(
                0.5, 0.95,
                title,
                ha="center",
                va="top",
                fontsize=28,
                fontweight="bold",
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

            plt.close(fig)
            return img

        frames = [animate(i) for i in range(total_frames)]

        safe_title = "".join(c if c.isalnum() else "_" for c in title[:20])
        output_path = self.output_dir / f"timeline_v_{safe_title}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def _save_video(self, frames: List[np.ndarray], output_path: Path):
        """Save frames as video using ffmpeg."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, frame in enumerate(frames):
                frame_path = os.path.join(temp_dir, f"frame_{i:05d}.png")
                Image.fromarray(frame).save(frame_path)

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

        logger.info(f"Timeline saved to {output_path}")

    def generate_timelines(
        self,
        script_data: Dict,
        output_path: Optional[str] = None,
    ) -> List[str]:
        """Generate timeline animations for documentary.

        Args:
            script_data: Script data
            output_path: Optional output path

        Returns:
            List of generated timeline paths
        """
        generated = []

        title = script_data.get("title", "Timeline")

        # Extract events from segments
        events = []
        segments = script_data.get("segments", [])

        for segment in segments:
            key_facts = segment.get("key_facts", [])
            for fact in key_facts:
                # Try to extract year from fact
                import re
                year_match = re.search(r"(\d+\s*(?:BC|AD|BCE|CE))", fact, re.IGNORECASE)
                if year_match:
                    events.append({
                        "year": year_match.group(1),
                        "title": fact[:50],
                    })

        if events:
            try:
                # Horizontal timeline
                h_timeline = self.create_horizontal_timeline(
                    title=f"Timeline: {title}",
                    events=events,
                    duration_seconds=8.0,
                )
                generated.append(h_timeline)
            except Exception as e:
                logger.warning(f"Failed to create horizontal timeline: {e}")

        logger.info(f"Generated {len(generated)} timeline animations")

        if output_path:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(generated, indent=2))

        return generated


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate timeline animations")
    parser.add_argument("--input", type=str, required=True, help="Input script JSON")
    parser.add_argument("--output", type=str, default="output/timelines/")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    generator = TimelineGenerator(output_dir=args.output)
    generated = generator.generate_timelines(script_data)

    print(f"Generated {len(generated)} timeline animations")


if __name__ == "__main__":
    main()
