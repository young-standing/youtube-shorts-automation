#!/usr/bin/env python3
"""Image processor for documentary visuals."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import tempfile
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2

from loguru import logger


class ImageProcessor:
    """Processes images for documentary use."""

    def __init__(
        self,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        output_dir: str = "output/processed_images",
    ):
        """Initialize image processor.

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

    def apply_ken_burns(
        self,
        image_path: str,
        duration_seconds: float = 8.0,
        zoom_direction: str = "in",
        pan_direction: str = "center",
    ) -> str:
        """Apply Ken Burns effect to image.

        Args:
            image_path: Path to source image
            duration_seconds: Duration in seconds
            zoom_direction: 'in' or 'out'
            pan_direction: 'left', 'right', 'center', 'up', 'down'

        Returns:
            Path to generated video
        """
        logger.info(f"Applying Ken Burns effect to {image_path}")

        # Load image
        img = Image.open(image_path)

        # Resize to larger than output for zoom
        scale_factor = 1.5
        new_size = (int(self.width * scale_factor), int(self.height * scale_factor))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

        total_frames = int(duration_seconds * self.fps)

        # Zoom parameters
        if zoom_direction == "in":
            start_scale = 1.0
            end_scale = 1.3
        else:
            start_scale = 1.3
            end_scale = 1.0

        # Pan parameters
        pan_offsets = {
            "left": (0.1, 0),
            "right": (-0.1, 0),
            "up": (0, 0.1),
            "down": (0, -0.1),
            "center": (0, 0),
        }
        pan_x, pan_y = pan_offsets.get(pan_direction, (0, 0))

        frames = []

        for frame_num in range(total_frames):
            progress = frame_num / total_frames

            # Calculate current scale
            current_scale = start_scale + (end_scale - start_scale) * progress

            # Calculate crop position
            crop_width = int(self.width / current_scale)
            crop_height = int(self.height / current_scale)

            # Apply pan
            center_x = img.width // 2 + int(pan_x * img.width * progress)
            center_y = img.height // 2 + int(pan_y * img.height * progress)

            # Calculate crop box
            left = max(0, center_x - crop_width // 2)
            top = max(0, center_y - crop_height // 2)
            right = min(img.width, left + crop_width)
            bottom = min(img.height, top + crop_height)

            # Ensure crop dimensions are valid
            if right - left < crop_width:
                left = max(0, right - crop_width)
            if bottom - top < crop_height:
                top = max(0, bottom - crop_height)

            # Crop and resize
            cropped = img.crop((left, top, right, bottom))
            frame = cropped.resize((self.width, self.height), Image.Resampling.LANCZOS)

            frames.append(np.array(frame))

        # Save video
        safe_name = Path(image_path).stem[:30]
        output_path = self.output_dir / f"kenburns_{safe_name}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def apply_parallax(
        self,
        background_path: str,
        foreground_path: str,
        duration_seconds: float = 10.0,
    ) -> str:
        """Apply parallax effect with foreground and background.

        Args:
            background_path: Path to background image
            foreground_path: Path to foreground image (with transparency)
            duration_seconds: Duration in seconds

        Returns:
            Path to generated video
        """
        logger.info("Applying parallax effect")

        # Load images
        background = Image.open(background_path).resize(
            (self.width, self.height), Image.Resampling.LANCZOS
        )
        foreground = Image.open(foreground_path)

        # Ensure foreground has alpha channel
        if foreground.mode != "RGBA":
            foreground = foreground.convert("RGBA")

        # Scale foreground to fit
        fg_width = int(self.width * 0.8)
        fg_height = int(foreground.height * (fg_width / foreground.width))
        foreground = foreground.resize((fg_width, fg_height), Image.Resampling.LANCZOS)

        total_frames = int(duration_seconds * self.fps)
        frames = []

        for frame_num in range(total_frames):
            progress = frame_num / total_frames

            # Background moves slower
            bg_offset = int(50 * np.sin(progress * 2 * np.pi))

            # Foreground moves faster
            fg_offset = int(100 * np.sin(progress * 2 * np.pi))

            # Create frame
            frame = background.copy()

            # Shift background slightly
            bg_shifted = Image.new("RGB", (self.width, self.height))
            bg_shifted.paste(background, (bg_offset, 0))

            # Paste foreground
            fg_x = (self.width - fg_width) // 2 + fg_offset
            fg_y = (self.height - fg_height) // 2

            frame.paste(foreground, (fg_x, fg_y), foreground)

            frames.append(np.array(frame))

        # Save video
        output_path = self.output_dir / f"parallax_{Path(background_path).stem[:20]}.mp4"
        self._save_video(frames, output_path)

        return str(output_path)

    def enhance_image(
        self,
        image_path: str,
        brightness: float = 1.1,
        contrast: float = 1.2,
        saturation: float = 1.0,
        sharpness: float = 1.1,
    ) -> str:
        """Enhance image quality.

        Args:
            image_path: Path to source image
            brightness: Brightness factor
            contrast: Contrast factor
            saturation: Saturation factor
            sharpness: Sharpness factor

        Returns:
            Path to enhanced image
        """
        logger.info(f"Enhancing image: {image_path}")

        img = Image.open(image_path)

        # Apply enhancements
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(brightness)

        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(contrast)

        if saturation != 1.0:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(saturation)

        if sharpness != 1.0:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(sharpness)

        # Save enhanced image
        output_path = self.output_dir / f"enhanced_{Path(image_path).stem[:30]}.jpg"
        img.save(output_path, quality=95)

        return str(output_path)

    def add_vignette(
        self,
        image_path: str,
        intensity: float = 0.5,
    ) -> str:
        """Add vignette effect to image.

        Args:
            image_path: Path to source image
            intensity: Vignette intensity (0-1)

        Returns:
            Path to processed image
        """
        logger.info(f"Adding vignette to {image_path}")

        img = Image.open(image_path).convert("RGB")

        # Create vignette mask
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)

        # Draw gradient ellipse
        center_x, center_y = img.width // 2, img.height // 2
        radius_x = img.width // 2
        radius_y = img.height // 2

        for i in range(100):
            alpha = int(255 * (1 - i / 100) * intensity)
            rx = radius_x - int(radius_x * i / 100 * 0.8)
            ry = radius_y - int(radius_y * i / 100 * 0.8)
            draw.ellipse(
                [center_x - rx, center_y - ry, center_x + rx, center_y + ry],
                fill=alpha,
            )

        # Apply mask
        result = img.copy()
        result.putalpha(mask)

        # Composite with black background
        black = Image.new("RGB", img.size, (0, 0, 0))
        result = Image.composite(img, black, mask)

        # Save
        output_path = self.output_dir / f"vignette_{Path(image_path).stem[:30]}.jpg"
        result.save(output_path, quality=95)

        return str(output_path)

    def add_text_overlay(
        self,
        image_path: str,
        text: str,
        position: str = "bottom",
        font_size: int = 48,
        color: str = "#FFFFFF",
        bg_color: str = "#00000080",
    ) -> str:
        """Add text overlay to image.

        Args:
            image_path: Path to source image
            text: Text to overlay
            position: Position ('top', 'bottom', 'center')
            font_size: Font size
            color: Text color (hex)
            bg_color: Background color (hex with alpha)

        Returns:
            Path to processed image
        """
        logger.info(f"Adding text overlay to {image_path}")

        img = Image.open(image_path).convert("RGBA")
        draw = ImageDraw.Draw(img)

        # Load font
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        # Calculate text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Position
        positions = {
            "top": (10, 10),
            "center": ((img.width - text_width) // 2, (img.height - text_height) // 2),
            "bottom": (10, img.height - text_height - 20),
        }
        x, y = positions.get(position, positions["bottom"])

        # Draw background
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=bg_color,
        )

        # Draw text
        hex_color = color.lstrip("#")
        rgb_color = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        draw.text((x, y), text, fill=rgb_color + (255,), font=font)

        # Save
        output_path = self.output_dir / f"text_{Path(image_path).stem[:30]}.png"
        img.convert("RGB").save(output_path, quality=95)

        return str(output_path)

    def create_color_grade(
        self,
        image_path: str,
        style: str = "vintage",
    ) -> str:
        """Apply color grading style.

        Args:
            image_path: Path to source image
            style: Grading style ('vintage', 'dramatic', 'warm', 'cool')

        Returns:
            Path to processed image
        """
        logger.info(f"Applying {style} color grade")

        img = Image.open(image_path).convert("RGB")

        if style == "vintage":
            # Sepia-like tone
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.8)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.1)

        elif style == "dramatic":
            # High contrast, slightly desaturated
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(0.9)

        elif style == "warm":
            # Warm color temperature
            r, g, b = img.split()
            r = r.point(lambda x: min(255, x + 20))
            b = b.point(lambda x: max(0, x - 20))
            img = Image.merge("RGB", (r, g, b))

        elif style == "cool":
            # Cool color temperature
            r, g, b = img.split()
            r = r.point(lambda x: max(0, x - 20))
            b = b.point(lambda x: min(255, x + 20))
            img = Image.merge("RGB", (r, g, b))

        # Save
        output_path = self.output_dir / f"graded_{style}_{Path(image_path).stem[:25]}.jpg"
        img.save(output_path, quality=95)

        return str(output_path)

    def _save_video(self, frames: List[np.ndarray], output_path: Path):
        """Save frames as video using ffmpeg."""
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

        logger.info(f"Video saved to {output_path}")

    def process_images(
        self,
        input_dir: str,
        output_path: Optional[str] = None,
    ) -> List[str]:
        """Process all images in directory.

        Args:
            input_dir: Input directory path
            output_path: Optional output path for processing log

        Returns:
            List of processed image/video paths
        """
        processed = []

        input_path = Path(input_dir)
        image_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        for image_file in input_path.glob("*"):
            if image_file.suffix.lower() in image_extensions:
                try:
                    # Apply Ken Burns effect
                    video_path = self.apply_ken_burns(
                        str(image_file),
                        duration_seconds=8.0,
                        zoom_direction="in",
                        pan_direction="center",
                    )
                    processed.append(video_path)
                except Exception as e:
                    logger.warning(f"Failed to process {image_file}: {e}")

        logger.info(f"Processed {len(processed)} images")

        if output_path:
            output_file = Path(output_path)
            output_file.write_text(json.dumps(processed, indent=2))

        return processed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Process images for documentary")
    parser.add_argument("--input", type=str, required=True, help="Input directory")
    parser.add_argument("--output", type=str, default="output/processed_images/")
    args = parser.parse_args()

    processor = ImageProcessor(output_dir=args.output)
    processed = processor.process_images(args.input)

    print(f"Processed {len(processed)} images")


if __name__ == "__main__":
    main()
