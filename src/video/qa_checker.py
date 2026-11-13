#!/usr/bin/env python3
"""Quality assurance checker for documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import os

from loguru import logger


class QAChecker:
    """Checks documentary quality."""

    def __init__(
        self,
        min_duration_minutes: float = 8.0,
        max_duration_minutes: float = 12.0,
        min_resolution: tuple = (1920, 1080),
        min_fps: int = 24,
        max_file_size_mb: int = 500,
    ):
        """Initialize QA checker.

        Args:
            min_duration_minutes: Minimum duration
            max_duration_minutes: Maximum duration
            min_resolution: Minimum resolution (width, height)
            min_fps: Minimum FPS
            max_file_size_mb: Maximum file size in MB
        """
        self.min_duration = min_duration_minutes * 60
        self.max_duration = max_duration_minutes * 60
        self.min_resolution = min_resolution
        self.min_fps = min_fps
        self.max_file_size = max_file_size_mb * 1024 * 1024

    def check_video_properties(
        self,
        video_path: str,
    ) -> Dict:
        """Check video file properties.

        Args:
            video_path: Video file path

        Returns:
            Dictionary with video properties
        """
        logger.info(f"Checking video properties: {video_path}")

        # Use ffprobe to get video info
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path,
            ],
            capture_output=True,
            text=True,
        )

        probe_data = json.loads(result.stdout)

        # Extract properties
        video_stream = next(
            (s for s in probe_data.get("streams", []) if s["codec_type"] == "video"),
            {},
        )
        audio_stream = next(
            (s for s in probe_data.get("streams", []) if s["codec_type"] == "audio"),
            {},
        )

        properties = {
            "duration": float(probe_data.get("format", {}).get("duration", 0)),
            "file_size": int(probe_data.get("format", {}).get("size", 0)),
            "bit_rate": int(probe_data.get("format", {}).get("bit_rate", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": self._parse_fps(video_stream.get("r_frame_rate", "0/1")),
            "video_codec": video_stream.get("codec_name", ""),
            "audio_codec": audio_stream.get("codec_name", ""),
            "audio_sample_rate": int(audio_stream.get("sample_rate", 0)),
            "audio_channels": int(audio_stream.get("channels", 0)),
        }

        return properties

    def _parse_fps(self, fps_str: str) -> float:
        """Parse FPS string like '30/1' to float."""
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return float(num) / float(den) if float(den) != 0 else 0
        return float(fps_str)

    def check_duration(
        self,
        duration: float,
    ) -> Dict:
        """Check video duration.

        Args:
            duration: Duration in seconds

        Returns:
            Check result
        """
        passed = self.min_duration <= duration <= self.max_duration

        return {
            "check": "duration",
            "passed": passed,
            "value": duration,
            "min": self.min_duration,
            "max": self.max_duration,
            "message": (
                f"Duration: {duration / 60:.2f} minutes "
                f"({'PASS' if passed else 'FAIL'})"
            ),
        }

    def check_resolution(
        self,
        width: int,
        height: int,
    ) -> Dict:
        """Check video resolution.

        Args:
            width: Video width
            height: Video height

        Returns:
            Check result
        """
        passed = width >= self.min_resolution[0] and height >= self.min_resolution[1]

        return {
            "check": "resolution",
            "passed": passed,
            "value": f"{width}x{height}",
            "min": f"{self.min_resolution[0]}x{self.min_resolution[1]}",
            "message": (
                f"Resolution: {width}x{height} "
                f"({'PASS' if passed else 'FAIL'})"
            ),
        }

    def check_fps(
        self,
        fps: float,
    ) -> Dict:
        """Check video FPS.

        Args:
            fps: Frames per second

        Returns:
            Check result
        """
        passed = fps >= self.min_fps

        return {
            "check": "fps",
            "passed": passed,
            "value": fps,
            "min": self.min_fps,
            "message": f"FPS: {fps:.2f} ({'PASS' if passed else 'FAIL'})",
        }

    def check_file_size(
        self,
        file_size: int,
    ) -> Dict:
        """Check file size.

        Args:
            file_size: File size in bytes

        Returns:
            Check result
        """
        passed = file_size <= self.max_file_size

        return {
            "check": "file_size",
            "passed": passed,
            "value": file_size / (1024 * 1024),  # MB
            "max": self.max_file_size / (1024 * 1024),  # MB
            "message": (
                f"File size: {file_size / (1024 * 1024):.2f} MB "
                f"({'PASS' if passed else 'FAIL'})"
            ),
        }

    def check_audio_quality(
        self,
        audio_codec: str,
        sample_rate: int,
        channels: int,
    ) -> Dict:
        """Check audio quality.

        Args:
            audio_codec: Audio codec name
            sample_rate: Sample rate
            channels: Number of channels

        Returns:
            Check result
        """
        checks = []

        # Check codec
        codec_passed = audio_codec in ["aac", "mp3", "opus"]
        checks.append({
            "subcheck": "codec",
            "passed": codec_passed,
            "value": audio_codec,
        })

        # Check sample rate
        sample_rate_passed = sample_rate >= 44100
        checks.append({
            "subcheck": "sample_rate",
            "passed": sample_rate_passed,
            "value": sample_rate,
        })

        # Check channels
        channels_passed = channels >= 2
        checks.append({
            "subcheck": "channels",
            "passed": channels_passed,
            "value": channels,
        })

        all_passed = all(c["passed"] for c in checks)

        return {
            "check": "audio_quality",
            "passed": all_passed,
            "details": checks,
            "message": (
                f"Audio: {audio_codec}, {sample_rate}Hz, {channels}ch "
                f"({'PASS' if all_passed else 'FAIL'})"
            ),
        }

    def check_script_alignment(
        self,
        video_duration: float,
        script_data: Dict,
    ) -> Dict:
        """Check if video matches script.

        Args:
            video_duration: Video duration in seconds
            script_data: Script data

        Returns:
            Check result
        """
        # Calculate expected duration from script
        segments = script_data.get("segments", [])
        expected_duration = sum(s.get("duration_seconds", 0) for s in segments)

        # Allow 10% tolerance
        tolerance = 0.10
        duration_diff = abs(video_duration - expected_duration)
        passed = duration_diff <= expected_duration * tolerance

        return {
            "check": "script_alignment",
            "passed": passed,
            "video_duration": video_duration,
            "expected_duration": expected_duration,
            "difference": duration_diff,
            "message": (
                f"Script alignment: {video_duration:.1f}s vs {expected_duration:.1f}s "
                f"({'PASS' if passed else 'FAIL'})"
            ),
        }

    def run_all_checks(
        self,
        video_path: str,
        script_path: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> Dict:
        """Run all QA checks.

        Args:
            video_path: Video file path
            script_path: Optional script file path
            output_path: Optional output path for report

        Returns:
            Complete QA report
        """
        logger.info(f"Running QA checks on {video_path}")

        # Get video properties
        properties = self.check_video_properties(video_path)

        # Run checks
        checks = []

        # Duration check
        checks.append(self.check_duration(properties["duration"]))

        # Resolution check
        checks.append(self.check_resolution(
            properties["width"],
            properties["height"],
        ))

        # FPS check
        checks.append(self.check_fps(properties["fps"]))

        # File size check
        checks.append(self.check_file_size(properties["file_size"]))

        # Audio quality check
        checks.append(self.check_audio_quality(
            properties["video_codec"],
            properties["audio_sample_rate"],
            properties["audio_channels"],
        ))

        # Script alignment check
        if script_path:
            with open(script_path, "r", encoding="utf-8") as f:
                script_data = json.load(f)
            checks.append(self.check_script_alignment(
                properties["duration"],
                script_data,
            ))

        # Overall result
        all_passed = all(c["passed"] for c in checks)

        report = {
            "video_path": video_path,
            "overall_status": "PASS" if all_passed else "FAIL",
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks if c["passed"]),
            "failed_checks": sum(1 for c in checks if not c["passed"]),
            "properties": properties,
            "checks": checks,
        }

        logger.info(
            f"QA complete: {report['passed_checks']}/{report['total_checks']} checks passed"
        )

        # Save report if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="QA check documentary")
    parser.add_argument("--video", type=str, required=True, help="Video file path")
    parser.add_argument("--script", type=str, help="Script JSON path")
    parser.add_argument("--output", type=str, default="output/qa_report.json")
    args = parser.parse_args()

    checker = QAChecker()
    report = checker.run_all_checks(
        args.video,
        args.script,
        args.output,
    )

    print(f"\nQA Report: {report['overall_status']}")
    print(f"Checks: {report['passed_checks']}/{report['total_checks']} passed\n")

    for check in report["checks"]:
        status = "✓" if check["passed"] else "✗"
        print(f"  {status} {check['message']}")


if __name__ == "__main__":
    main()
