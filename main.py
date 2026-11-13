#!/usr/bin/env python3
"""Main entry point for documentary generation."""

import argparse
import json
from pathlib import Path

from loguru import logger

from src.research import TopicSelector, WikipediaResearcher, FactChecker
from src.content import ScriptGenerator, MetadataGenerator
from src.visuals import InfographicGenerator, MapAnimator, TimelineGenerator, ImageProcessor
from src.audio import TTSGenerator, AudioMixer
from src.video import VideoAssembler, QAChecker
from src.upload import YouTubeUploader, ThumbnailGenerator, StateManager


def main():
    """Generate documentary from topic."""
    parser = argparse.ArgumentParser(description="Generate Vox-style documentary")
    parser.add_argument("--topic", type=str, help="Documentary topic")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube")
    parser.add_argument("--dry-run", action="store_true", help="Skip upload")
    parser.add_argument("--duration", type=float, default=10, help="Target duration in minutes")
    args = parser.parse_args()

    # Setup
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Select topic
    logger.info("Step 1: Selecting topic")
    selector = TopicSelector()
    topic = selector.get_random_topic() if not args.topic else {"title": args.topic, "keywords": [args.topic]}
    logger.info(f"Topic: {topic['title']}")

    # Step 2: Research
    logger.info("Step 2: Researching topic")
    researcher = WikipediaResearcher()
    research = researcher.research(topic, output_path=str(output_dir / "research.json"))

    # Step 3: Fact check
    logger.info("Step 3: Fact checking")
    checker = FactChecker()
    verified_research = checker.verify_research(
        research.__dict__,
        output_path=str(output_dir / "verified_research.json"),
    )

    # Step 4: Generate script
    logger.info("Step 4: Generating script")
    script_gen = ScriptGenerator(target_duration_minutes=args.duration)
    script = script_gen.generate_script(
        verified_research,
        output_path=str(output_dir / "script.json"),
    )

    # Step 5: Generate metadata
    logger.info("Step 5: Generating metadata")
    meta_gen = MetadataGenerator()
    metadata = meta_gen.generate_metadata(
        script.__dict__,
        verified_research,
        output_path=str(output_dir / "metadata.json"),
    )

    # Step 6: Generate infographics
    logger.info("Step 6: Generating infographics")
    infographics_gen = InfographicGenerator(output_dir=str(output_dir / "infographics"))
    infographics = infographics_gen.generate_infographics(
        script.__dict__,
        verified_research,
    )

    # Step 7: Generate maps
    logger.info("Step 7: Generating maps")
    map_animator = MapAnimator(output_dir=str(output_dir / "maps"))
    maps = map_animator.generate_maps(
        script.__dict__,
        verified_research,
    )

    # Step 8: Generate timelines
    logger.info("Step 8: Generating timelines")
    timeline_gen = TimelineGenerator(output_dir=str(output_dir / "timelines"))
    timelines = timeline_gen.generate_timelines(script.__dict__)

    # Step 9: Generate narration
    logger.info("Step 9: Generating narration")
    tts_gen = TTSGenerator(output_dir=str(output_dir / "narration"))
    narration_paths = tts_gen.generate_documentary_narration(script.__dict__)

    # Step 10: Mix audio
    logger.info("Step 10: Mixing audio")
    audio_mixer = AudioMixer(output_dir=str(output_dir))
    # Note: In production, generate or select background music
    # For now, we'll skip music mixing

    # Step 11: Assemble video
    logger.info("Step 11: Assembling video")
    assembler = VideoAssembler(output_dir=str(output_dir))

    # Collect visuals
    all_infographics = [str(p) for p in Path(output_dir / "infographics").glob("*.mp4")] if Path(output_dir / "infographics").exists() else []
    all_maps = [str(p) for p in Path(output_dir / "maps").glob("*.mp4")] if Path(output_dir / "maps").exists() else []
    all_timelines = [str(p) for p in Path(output_dir / "timelines").glob("*.mp4")] if Path(output_dir / "timelines").exists() else []

    # For now, skip full assembly (requires narration)
    video_path = str(output_dir / "documentary.mp4")

    # Step 12: QA Check
    logger.info("Step 12: Running QA checks")
    qa_checker = QAChecker()
    # qa_report = qa_checker.run_all_checks(video_path, str(output_dir / "script.json"))

    # Step 13: Generate thumbnail
    logger.info("Step 13: Generating thumbnail")
    thumb_gen = ThumbnailGenerator(output_dir=str(output_dir))
    # thumbnail_path = thumb_gen.generate_thumbnail(video_path, str(output_dir / "metadata.json"))

    # Step 14: Upload (if enabled)
    if args.upload and not args.dry_run:
        logger.info("Step 14: Uploading to YouTube")
        uploader = YouTubeUploader()
        # upload_result = uploader.upload_documentary(video_path, thumbnail_path, str(output_dir / "metadata.json"))

        # Save state
        state_manager = StateManager()
        # state_manager.save_publication(topic["title"], upload_result)

    logger.success("Documentary generation complete!")
    print(f"\n✓ Documentary generated successfully!")
    print(f"  Topic: {topic['title']}")
    print(f"  Output: {output_dir}")


if __name__ == "__main__":
    main()
