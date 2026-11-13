#!/usr/bin/env python3
"""Map animator for historical documentaries."""

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


class MapAnimator:
    """Creates animated historical maps."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        output_dir: str = "output/maps",
    ):
        """Initialize map animator.

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

        # Map colors
        self.colors = {
            "background": "#1A1A2E",
            "ocean": "#2C3E50",
            "land": "#34495E",
            "highlight": "#E74C3C",
            "secondary": "#3498DB",
            "border": "#7F8C8D",
            "text": "#FFFFFF",
        }

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def create_world_map_background(self) -> Tuple[plt.Figure, plt.Axes]:
        """Create base world map figure."""
        fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
        fig.patch.set_facecolor(self.colors["background"])
        ax.set_facecolor(self.colors["ocean"])

        # Simple world outline (approximate coordinates)
        # This creates a stylized map without requiring geopandas
        continents = {
            "europe": [
                (-10, 35), (35, 35), (40, 45), (30, 60), (25, 70),
                (10, 70), (5, 60), (-5, 45), (-10, 35)
            ],
            "africa": [
                (-20, 35), (50, 35), (50, 5), (40, -35), (20, -35),
                (10, -5), (-20, 15), (-20, 35)
            ],
            "asia": [
                (35, 35), (140, 35), (145, 45), (130, 65), (170, 65),
                (170, 55), (140, 45), (100, 10), (80, 10), (65, 35),
                (35, 35)
            ],
            "north_america": [
                (-170, 65), (-60, 65), (-55, 45), (-80, 25), (-100, 25),
                (-120, 35), (-125, 45), (-170, 65)
            ],
            "south_america": [
                (-80, 10), (-35, 5), (-35, -55), (-75, -55), (-80, -5),
                (-80, 10)
            ],
            "australia": [
                (115, -10), (155, -10), (155, -45), (115, -45), (115, -10)
            ],
        }

        for continent, coords in continents.items():
            x, y = zip(*coords)
            ax.fill(x, y, color=self.colors["land"], edgecolor=self.colors["border"])

        ax.set_xlim(-180, 180)
        ax.set_ylim(-60, 80)
        ax.axis("off")

        return fig, ax

    def create_territory_animation(
        self,
        empire_name: str,
        territories: List[Dict],
        duration_seconds: float = 10.0,
    ) -> str:
        """Create animated territory expansion map.

        Args:
            empire_name: Empire name
            territories: List of territories with coordinates and year
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating territory animation for: {empire_name}")

        total_frames = int(duration_seconds * self.fps)

        def animate(frame):
            fig, ax = self.create_world_map_background()
            progress = frame / total_frames

            # Calculate which territories to show
            num_territories = len(territories)
            territories_shown = int(progress * num_territories)

            # Draw territories progressively
            for i, territory in enumerate(territories[:territories_shown]):
                coords = territory.get("coordinates", [])
                year = territory.get("year", "Unknown")

                if len(coords) >= 3:
                    x, y = zip(*coords)
                    alpha = 1.0 if i < territories_shown - 1 else (progress * num_territories - territories_shown + 1)
                    ax.fill(
                        x, y,
                        color=self.colors["highlight"],
                        alpha=min(0.7, alpha * 0.7),
                        edgecolor=self.colors["text"],
                        linewidth=1,
                    )

            # Add title and year
            current_year = territories[territories_shown - 1].get("year", "") if territories_shown > 0 else ""
            ax.text(
                0.5, 0.95,
                f"{empire_name} - {current_year}",
                ha="center",
                va="top",
                fontsize=32,
                fontweight="bold",
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            # Add legend
            ax.text(
                0.02, 0.02,
                f"Territories: {territories_shown}/{num_territories}",
                ha="left",
                va="bottom",
                fontsize=16,
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            # Convert to image
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

            plt.close(fig)
            return img

        # Generate frames
        frames = [animate(i) for i in range(total_frames)]

        # Save video
        safe_name = "".join(c if c.isalnum() else "_" for c in empire_name)
        output_path = self.output_dir / f"map_{safe_name}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def create_battle_map(
        self,
        battle_name: str,
        location: Tuple[float, float],
        combatants: Dict,
        troop_movements: List[Dict],
        duration_seconds: float = 8.0,
    ) -> str:
        """Create animated battle map.

        Args:
            battle_name: Battle name
            location: (lat, lon) coordinates
            combatants: Dict with 'side1' and 'side2' info
            troop_movements: List of movement data
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info(f"Creating battle map: {battle_name}")

        total_frames = int(duration_seconds * self.fps)

        def animate(frame):
            fig, ax = self.create_world_map_background()
            progress = frame / total_frames

            # Zoom to battle location
            lat, lon = location
            margin = 20
            ax.set_xlim(lon - margin, lon + margin)
            ax.set_ylim(lat - margin, lat + margin)

            # Draw troop positions with animation
            for i, movement in enumerate(troop_movements):
                start = movement.get("start", (lon, lat))
                end = movement.get("end", (lon, lat))
                side = movement.get("side", "side1")

                # Interpolate position
                current_x = start[0] + (end[0] - start[0]) * progress
                current_y = start[1] + (end[1] - start[1]) * progress

                color = self.colors["highlight"] if side == "side1" else self.colors["secondary"]

                # Draw unit
                ax.plot(
                    current_x, current_y,
                    "o",
                    markersize=15,
                    color=color,
                    markeredgecolor=self.colors["text"],
                    markeredgewidth=2,
                )

                # Draw movement path
                ax.annotate(
                    "",
                    xy=end,
                    xytext=start,
                    arrowprops=dict(
                        arrowstyle="->",
                        color=color,
                        alpha=0.5,
                    ),
                )

            # Add battle info
            ax.text(
                0.5, 0.95,
                f"Battle of {battle_name}",
                ha="center",
                va="top",
                fontsize=28,
                fontweight="bold",
                color=self.colors["text"],
                transform=ax.transAxes,
            )

            # Add combatants legend
            ax.text(
                0.02, 0.98,
                combatants.get("side1", "Side 1"),
                ha="left",
                va="top",
                fontsize=16,
                color=self.colors["highlight"],
                transform=ax.transAxes,
            )
            ax.text(
                0.98, 0.98,
                combatants.get("side2", "Side 2"),
                ha="right",
                va="top",
                fontsize=16,
                color=self.colors["secondary"],
                transform=ax.transAxes,
            )

            # Convert to image
            fig.canvas.draw()
            img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
            img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

            plt.close(fig)
            return img

        # Generate frames
        frames = [animate(i) for i in range(total_frames)]

        # Save video
        safe_name = "".join(c if c.isalnum() else "_" for c in battle_name)
        output_path = self.output_dir / f"battle_{safe_name}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def _save_video(self, frames: List[np.ndarray], output_path: Path):
        """Save frames as video using ffmpeg."""
        import tempfile
        import os

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

        logger.info(f"Map animation saved to {output_path}")

    def generate_maps(
        self,
        script_data: Dict,
        research_data: Dict,
        output_path: Optional[str] = None,
    ) -> List[str]:
        """Generate map animations for documentary.

        Args:
            script_data: Script data
            research_data: Research data
            output_path: Optional output path

        Returns:
            List of generated map paths
        """
        generated = []

        # Extract empire/territory info from title
        title = script_data.get("title", "")
        empire_name = title.replace("The Rise and Fall of ", "").replace(" | Full Documentary", "")

        # Create default territory expansion
        # This would normally use actual historical data
        default_territories = [
            {"coordinates": [(-10, 35), (35, 35), (35, 45), (-10, 45), (-10, 35)], "year": "500 BC"},
            {"coordinates": [(0, 35), (40, 35), (40, 55), (0, 55), (0, 35)], "year": "400 BC"},
            {"coordinates": [(-5, 30), (45, 30), (45, 60), (-5, 60), (-5, 30)], "year": "300 BC"},
        ]

        try:
            territory_map = self.create_territory_animation(
                empire_name=empire_name,
                territories=default_territories,
                duration_seconds=10.0,
            )
            generated.append(territory_map)
        except Exception as e:
            logger.warning(f"Failed to create territory map: {e}")

        logger.info(f"Generated {len(generated)} map animations")

        # Save list if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(generated, indent=2))

        return generated


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate map animations")
    parser.add_argument("--input", type=str, required=True, help="Input script JSON")
    parser.add_argument("--research", type=str, required=True, help="Research JSON")
    parser.add_argument("--output", type=str, default="output/maps/")
    args = parser.parse_args()

    # Load data
    with open(args.input, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    with open(args.research, "r", encoding="utf-8") as f:
        research_data = json.load(f)

    # Generate maps
    animator = MapAnimator(output_dir=args.output)
    generated = animator.generate_maps(script_data, research_data)

    print(f"Generated {len(generated)} map animations")


if __name__ == "__main__":
    main()
