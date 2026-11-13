#!/usr/bin/env python3
"""Script generator for Vox-style documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import os

from loguru import logger


@dataclass
class ScriptSegment:
    """A segment of the documentary script."""
    segment_type: str  # intro, main, transition, conclusion
    title: str
    narration: str
    duration_seconds: float
    visual_suggestions: List[str]
    key_facts: List[str]


@dataclass
class DocumentaryScript:
    """Complete documentary script."""
    title: str
    total_duration_minutes: float
    segments: List[ScriptSegment]
    keywords: List[str]
    chapter_markers: List[Dict]


class ScriptGenerator:
    """Generates documentary scripts from research data."""

    def __init__(
        self,
        target_duration_minutes: float = 10,
        style: str = "vox",
        words_per_minute: int = 150,
    ):
        """Initialize script generator.

        Args:
            target_duration_minutes: Target video duration
            style: Script style (vox, narrative, educational)
            words_per_minute: Narration speed
        """
        self.target_duration_minutes = target_duration_minutes
        self.style = style
        self.words_per_minute = words_per_minute
        self.target_words = int(target_duration_minutes * words_per_minute)

    def generate_intro(
        self,
        title: str,
        summary: str,
        key_facts: List[str],
    ) -> ScriptSegment:
        """Generate introduction segment.

        Args:
            title: Documentary title
            summary: Research summary
            key_facts: Key facts to highlight

        Returns:
            Introduction segment
        """
        # Create engaging hook
        hook_sentences = [
            f"What if I told you {key_facts[0].lower() if key_facts else 'this story changed everything'}?",
            f"Today, we're exploring {title.lower()}.",
            f"This is the story that shaped history.",
        ]

        narration = " ".join(hook_sentences)
        narration += f" {summary[:300]}..."

        word_count = len(narration.split())
        duration = (word_count / self.words_per_minute) * 60

        return ScriptSegment(
            segment_type="intro",
            title="Introduction",
            narration=narration,
            duration_seconds=duration,
            visual_suggestions=[
                "Dramatic opening shot",
                "Map or timeline introduction",
                "Title card with animated text",
            ],
            key_facts=key_facts[:3] if key_facts else [],
        )

    def generate_main_segments(
        self,
        sections: List[Dict],
        available_words: int,
    ) -> List[ScriptSegment]:
        """Generate main content segments.

        Args:
            sections: Research sections
            available_words: Word budget for main content

        Returns:
            List of main segments
        """
        segments = []
        words_per_section = available_words // max(len(sections), 1)

        for i, section in enumerate(sections[:6]):  # Limit to 6 main sections
            title = section.get("title", f"Section {i + 1}")
            content = section.get("content", "")

            # Extract key content
            sentences = content.split(". ")
            key_content = ". ".join(sentences[: words_per_section // 15])

            if not key_content.strip():
                continue

            # Add transition phrase
            if i > 0:
                transition = f"Now, let's explore {title.lower()}. "
            else:
                transition = ""

            narration = transition + key_content

            # Clean up narration
            narration = self._clean_narration(narration)

            word_count = len(narration.split())
            duration = (word_count / self.words_per_minute) * 60

            # Extract key facts
            key_facts = self._extract_key_facts(content)

            # Generate visual suggestions
            visual_suggestions = self._generate_visual_suggestions(title, content)

            segment = ScriptSegment(
                segment_type="main",
                title=title,
                narration=narration,
                duration_seconds=duration,
                visual_suggestions=visual_suggestions,
                key_facts=key_facts,
            )
            segments.append(segment)

        return segments

    def generate_conclusion(
        self,
        title: str,
        key_facts: List[str],
        total_duration: float,
    ) -> ScriptSegment:
        """Generate conclusion segment.

        Args:
            title: Documentary title
            key_facts: Key facts to summarize
            total_duration: Total video duration so far

        Returns:
            Conclusion segment
        """
        narration = f"So what have we learned about {title.lower()}? "

        if key_facts:
            narration += "Let's recap. "
            for i, fact in enumerate(key_facts[:3], 1):
                narration += f"First, {fact.lower()}. " if i == 1 else f"And {fact.lower()}. "

        narration += "Thanks for watching. Don't forget to subscribe for more historical documentaries."

        word_count = len(narration.split())
        duration = (word_count / self.words_per_minute) * 60

        return ScriptSegment(
            segment_type="conclusion",
            title="Conclusion",
            narration=narration,
            duration_seconds=duration,
            visual_suggestions=[
                "Summary infographic",
                "Timeline of key events",
                "Subscribe prompt",
            ],
            key_facts=key_facts[:3] if key_facts else [],
        )

    def generate_transitions(
        self,
        segments: List[ScriptSegment],
    ) -> List[ScriptSegment]:
        """Add transition segments between main segments.

        Args:
            segments: Existing segments

        Returns:
            Updated segments with transitions
        """
        transitions = []
        transition_templates = [
            "But that's not the whole story.",
            "Now, here's where things get interesting.",
            "Let's take a step back.",
            "But why does this matter?",
        ]

        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]

            # Create transition
            template = transition_templates[i % len(transition_templates)]
            narration = f"{template} Next, {next_seg.title.lower()}."

            transition = ScriptSegment(
                segment_type="transition",
                title=f"Transition {i + 1}",
                narration=narration,
                duration_seconds=3.0,
                visual_suggestions=["Transition graphic", "Animated map"],
                key_facts=[],
            )

            transitions.append(current)
            transitions.append(transition)

        if segments:
            transitions.append(segments[-1])

        return transitions

    def _clean_narration(self, text: str) -> str:
        """Clean narration text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        import re

        # Remove citations
        text = re.sub(r"\[\d+\]", "", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove broken sentences
        text = re.sub(r"\.\s*\.", ".", text)

        return text.strip()

    def _extract_key_facts(self, content: str) -> List[str]:
        """Extract key facts from content.

        Args:
            content: Text content

        Returns:
            List of key facts
        """
        import re

        facts = []

        # Find sentences with numbers (often key facts)
        sentences = content.split(". ")
        for sentence in sentences:
            if re.search(r"\d+", sentence) and len(sentence) > 20:
                facts.append(sentence.strip())

        return facts[:5]

    def _generate_visual_suggestions(
        self,
        title: str,
        content: str,
    ) -> List[str]:
        """Generate visual suggestions for a segment.

        Args:
            title: Segment title
            content: Segment content

        Returns:
            List of visual suggestions
        """
        suggestions = []

        # Title-based suggestions
        title_lower = title.lower()

        if "battle" in title_lower or "war" in title_lower:
            suggestions.extend([
                "Battle map animation",
                "Troop movement visualization",
                "Historical artwork of battle",
            ])
        elif "rise" in title_lower or "growth" in title_lower:
            suggestions.extend([
                "Expanding territory map",
                "Population growth chart",
                "Timeline of conquests",
            ])
        elif "fall" in title_lower or "decline" in title_lower:
            suggestions.extend([
                "Shrinking territory animation",
                "Decline timeline",
                "Key defeat locations",
            ])
        else:
            suggestions.extend([
                "Historical image montage",
                "Location map",
                "Period artwork",
            ])

        # Content-based suggestions
        if "king" in content.lower() or "emperor" in content.lower():
            suggestions.append("Portrait of ruler")

        if any(year in content for year in [" BC", " AD", " BCE", " CE"]):
            suggestions.append("Timeline graphic")

        return suggestions[:5]

    def generate_script(
        self,
        research_data: Dict,
        output_path: Optional[str] = None,
    ) -> DocumentaryScript:
        """Generate complete documentary script.

        Args:
            research_data: Research data dictionary
            output_path: Optional path to save script

        Returns:
            DocumentaryScript object
        """
        title = research_data.get("title", "Untitled Documentary")
        summary = research_data.get("summary", "")
        sections = research_data.get("sections", [])

        logger.info(f"Generating script for: {title}")

        # Calculate word budgets
        intro_words = int(self.target_words * 0.1)  # 10% for intro
        conclusion_words = int(self.target_words * 0.1)  # 10% for conclusion
        main_words = self.target_words - intro_words - conclusion_words

        # Extract key facts from all sections
        all_content = " ".join(s.get("content", "") for s in sections)
        key_facts = self._extract_key_facts(all_content)

        # Generate segments
        intro = self.generate_intro(title, summary, key_facts)
        main_segments = self.generate_main_segments(sections, main_words)
        main_segments = self.generate_transitions(main_segments)

        # Calculate duration so far
        current_duration = sum(s.duration_seconds for s in [intro] + main_segments)
        conclusion = self.generate_conclusion(title, key_facts, current_duration)

        # Combine all segments
        all_segments = [intro] + main_segments + [conclusion]

        # Generate chapter markers
        chapter_markers = self._generate_chapter_markers(all_segments)

        # Calculate total duration
        total_duration = sum(s.duration_seconds for s in all_segments) / 60

        # Extract keywords
        keywords = self._extract_keywords(research_data)

        script = DocumentaryScript(
            title=title,
            total_duration_minutes=total_duration,
            segments=all_segments,
            keywords=keywords,
            chapter_markers=chapter_markers,
        )

        logger.info(
            f"Script generated: {len(all_segments)} segments, "
            f"{total_duration:.1f} minutes"
        )

        # Save if output path provided
        if output_path:
            self.save_script(script, output_path)

        return script

    def _generate_chapter_markers(
        self,
        segments: List[ScriptSegment],
    ) -> List[Dict]:
        """Generate YouTube chapter markers.

        Args:
            segments: Script segments

        Returns:
            List of chapter markers
        """
        chapters = []
        current_time = 0

        for segment in segments:
            if segment.segment_type in ["intro", "main", "conclusion"]:
                chapters.append({
                    "time_seconds": int(current_time),
                    "time_formatted": self._format_time(current_time),
                    "title": segment.title,
                })
            current_time += segment.duration_seconds

        return chapters

    def _format_time(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _extract_keywords(self, research_data: Dict) -> List[str]:
        """Extract keywords from research data."""
        keywords = []

        # From categories
        categories = research_data.get("categories", [])
        for cat in categories[:5]:
            # Clean category name
            keyword = cat.replace("Category:", "").strip()
            if keyword:
                keywords.append(keyword)

        # From title
        title = research_data.get("title", "")
        title_words = title.split()
        keywords.extend([w for w in title_words if len(w) > 3][:3])

        return list(set(keywords))[:10]

    def save_script(self, script: DocumentaryScript, output_path: str):
        """Save script to JSON file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        script_dict = {
            "title": script.title,
            "total_duration_minutes": script.total_duration_minutes,
            "segments": [asdict(s) for s in script.segments],
            "keywords": script.keywords,
            "chapter_markers": script.chapter_markers,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(script_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Script saved to {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate documentary script")
    parser.add_argument("--input", type=str, required=True, help="Input research JSON")
    parser.add_argument("--output", type=str, default="output/script.json")
    parser.add_argument("--style", type=str, default="vox", help="Script style")
    parser.add_argument(
        "--duration", type=float, default=10, help="Target duration in minutes"
    )
    args = parser.parse_args()

    # Load research data
    with open(args.input, "r", encoding="utf-8") as f:
        research_data = json.load(f)

    # Generate script
    generator = ScriptGenerator(
        target_duration_minutes=args.duration,
        style=args.style,
    )
    script = generator.generate_script(research_data, output_path=args.output)

    print(f"Script: {script.title}")
    print(f"Duration: {script.total_duration_minutes:.1f} minutes")
    print(f"Segments: {len(script.segments)}")


if __name__ == "__main__":
    main()
