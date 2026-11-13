#!/usr/bin/env python3
"""Metadata generator for YouTube videos."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import re

from loguru import logger


@dataclass
class VideoMetadata:
    """YouTube video metadata."""
    title: str
    description: str
    tags: List[str]
    category_id: int
    privacy_status: str
    made_for_kids: bool
    language: str
    chapters: List[Dict]
    thumbnail_suggestions: List[str]


class MetadataGenerator:
    """Generates metadata for YouTube videos."""

    def __init__(
        self,
        max_title_length: int = 70,
        max_description_length: int = 5000,
        max_tags: int = 30,
    ):
        """Initialize metadata generator.

        Args:
            max_title_length: Maximum title length
            max_description_length: Maximum description length
            max_tags: Maximum number of tags
        """
        self.max_title_length = max_title_length
        self.max_description_length = max_description_length
        self.max_tags = max_tags

    def generate_title(
        self,
        base_title: str,
        keywords: List[str],
        style: str = "documentary",
    ) -> str:
        """Generate optimized video title.

        Args:
            base_title: Base title from research
            keywords: Relevant keywords
            style: Title style

        Returns:
            Optimized title
        """
        # Templates for different styles
        templates = {
            "documentary": [
                "{title} | Full Documentary",
                "The Rise and Fall of {title}",
                "{title}: The Complete Story",
                "How {title} Changed History",
                "{title} Explained in 10 Minutes",
            ],
            "vox": [
                "The Untold Story of {title}",
                "{title}: What History Forgot",
                "Why {title} Still Matters",
                "{title} | Empire Histories",
            ],
        }

        # Select template
        template_options = templates.get(style, templates["documentary"])
        template = template_options[0]

        # Format title
        if "{title}" in template:
            title = template.format(title=base_title)
        else:
            title = f"{base_title} | Documentary"

        # Add keyword if space allows
        if keywords and len(title) < self.max_title_length - 15:
            keyword = keywords[0]
            if keyword.lower() not in title.lower():
                title = f"{title} | {keyword}"

        # Ensure length limit
        if len(title) > self.max_title_length:
            title = title[: self.max_title_length - 3] + "..."

        return title

    def generate_description(
        self,
        title: str,
        summary: str,
        chapters: List[Dict],
        keywords: List[str],
        series_name: str = "Empire Histories",
    ) -> str:
        """Generate video description.

        Args:
            title: Video title
            summary: Content summary
            chapters: Chapter markers
            keywords: Relevant keywords
            series_name: Series name

        Returns:
            Formatted description
        """
        description_parts = []

        # Opening hook
        hook = f"Discover the fascinating story of {title}. "
        description_parts.append(hook)

        # Summary (truncated if needed)
        if len(summary) > 300:
            summary = summary[:297] + "..."
        description_parts.append(summary)
        description_parts.append("")

        # Chapters
        if chapters:
            description_parts.append("📌 CHAPTERS:")
            for chapter in chapters[:10]:
                description_parts.append(
                    f"  {chapter['time_formatted']} - {chapter['title']}"
                )
            description_parts.append("")

        # Series info
        description_parts.append(f"📺 Series: {series_name}")
        description_parts.append(
            "🔔 Subscribe for weekly historical documentaries!"
        )
        description_parts.append("")

        # Sources disclaimer
        description_parts.append("📚 Sources:")
        description_parts.append("This video is based on publicly available historical sources.")
        description_parts.append("")

        # Keywords as hashtags
        if keywords:
            hashtags = " ".join(f"#{kw.replace(' ', '')}" for kw in keywords[:5])
            description_parts.append(hashtags)

        # Standard footer
        description_parts.append("")
        description_parts.append("---")
        description_parts.append(
            "© Empire Histories | All historical footage used under fair use "
            "or public domain license."
        )

        description = "\n".join(description_parts)

        # Truncate if needed
        if len(description) > self.max_description_length:
            description = description[: self.max_description_length - 3] + "..."

        return description

    def generate_tags(
        self,
        title: str,
        keywords: List[str],
        categories: List[str],
    ) -> List[str]:
        """Generate video tags.

        Args:
            title: Video title
            keywords: Relevant keywords
            categories: Wikipedia categories

        Returns:
            List of tags
        """
        tags = []

        # Essential tags
        tags.extend([
            "history",
            "documentary",
            "historical documentary",
            "world history",
            "education",
            "explained",
        ])

        # Title-based tags
        title_words = title.split()
        for word in title_words:
            if len(word) > 3 and word.lower() not in ["the", "and", "for"]:
                tags.append(word)

        # Keywords
        tags.extend(keywords[:10])

        # Categories (cleaned)
        for cat in categories[:5]:
            clean_cat = cat.replace("Category:", "").strip()
            if clean_cat:
                tags.append(clean_cat)

        # Remove duplicates and limit
        tags = list(dict.fromkeys(tags))[:self.max_tags]

        return tags

    def generate_thumbnail_suggestions(
        self,
        title: str,
        key_facts: List[str],
        keywords: List[str],
    ) -> List[str]:
        """Generate thumbnail design suggestions.

        Args:
            title: Video title
            key_facts: Key facts from content
            keywords: Relevant keywords

        Returns:
            List of thumbnail suggestions
        """
        suggestions = []

        # Title-based suggestions
        suggestions.append(f"Bold text: '{title}' on dramatic background")

        # Fact-based suggestions
        if key_facts:
            fact = key_facts[0]
            if len(fact) < 30:
                suggestions.append(f"Highlight fact: '{fact}'")

        # Style suggestions
        suggestions.extend([
            "Historical map or territory illustration",
            "Portrait of key historical figure",
            "Timeline graphic with key dates",
            "Dramatic contrast: before/after comparison",
            "Question hook: 'What happened to...?'",
        ])

        # Keyword-based suggestions
        for keyword in keywords[:3]:
            keyword_lower = keyword.lower()

            if "empire" in keyword_lower:
                suggestions.append("Expanding empire map animation")
            elif "war" in keyword_lower or "battle" in keyword_lower:
                suggestions.append("Battle scene illustration")
            elif "king" in keyword_lower or "emperor" in keyword_lower:
                suggestions.append("Crown or royal symbol with portrait")

        return suggestions[:8]

    def generate_metadata(
        self,
        script_data: Dict,
        research_data: Optional[Dict] = None,
        output_path: Optional[str] = None,
    ) -> VideoMetadata:
        """Generate complete video metadata.

        Args:
            script_data: Script data dictionary
            research_data: Optional research data
            output_path: Optional output path

        Returns:
            VideoMetadata object
        """
        title = script_data.get("title", "Untitled")
        keywords = script_data.get("keywords", [])
        chapters = script_data.get("chapter_markers", [])
        segments = script_data.get("segments", [])

        # Get summary from segments
        summary = ""
        for segment in segments:
            if segment.get("segment_type") == "intro":
                summary = segment.get("narration", "")[:300]
                break

        # Get categories from research
        categories = []
        if research_data:
            categories = research_data.get("categories", [])

        # Extract key facts
        key_facts = []
        for segment in segments:
            if segment.get("key_facts"):
                key_facts.extend(segment.get("key_facts", []))

        logger.info(f"Generating metadata for: {title}")

        # Generate components
        video_title = self.generate_title(title, keywords, style="vox")
        description = self.generate_description(
            title, summary, chapters, keywords
        )
        tags = self.generate_tags(title, keywords, categories)
        thumbnail_suggestions = self.generate_thumbnail_suggestions(
            title, key_facts[:3], keywords
        )

        metadata = VideoMetadata(
            title=video_title,
            description=description,
            tags=tags,
            category_id=27,  # Education
            privacy_status="public",
            made_for_kids=False,
            language="en",
            chapters=chapters,
            thumbnail_suggestions=thumbnail_suggestions,
        )

        logger.info(f"Metadata generated: {len(tags)} tags, {len(chapters)} chapters")

        # Save if output path provided
        if output_path:
            self.save_metadata(metadata, output_path)

        return metadata

    def save_metadata(self, metadata: VideoMetadata, output_path: str):
        """Save metadata to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)

        logger.info(f"Metadata saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate video metadata")
    parser.add_argument("--input", type=str, required=True, help="Input script JSON")
    parser.add_argument("--output", type=str, default="output/metadata.json")
    parser.add_argument(
        "--research", type=str, help="Optional research JSON for additional context"
    )
    args = parser.parse_args()

    # Load script data
    with open(args.input, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    # Load research data if provided
    research_data = None
    if args.research:
        with open(args.research, "r", encoding="utf-8") as f:
            research_data = json.load(f)

    # Generate metadata
    generator = MetadataGenerator()
    metadata = generator.generate_metadata(
        script_data, research_data, output_path=args.output
    )

    print(f"Title: {metadata.title}")
    print(f"Tags: {len(metadata.tags)}")
    print(f"Chapters: {len(metadata.chapters)}")


if __name__ == "__main__":
    main()
