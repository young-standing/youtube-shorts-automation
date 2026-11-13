#!/usr/bin/env python3
"""Wikipedia research module for gathering historical content."""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import wikipedia
from loguru import logger
from bs4 import BeautifulSoup


@dataclass
class WikipediaSection:
    """Represents a Wikipedia section."""
    title: str
    content: str
    level: int
    subsections: List["WikipediaSection"]


@dataclass
class WikipediaResearch:
    """Container for Wikipedia research data."""
    title: str
    url: str
    summary: str
    sections: List[WikipediaSection]
    images: List[str]
    categories: List[str]
    links: List[str]
    references: List[str]


class WikipediaResearcher:
    """Research historical topics using Wikipedia API."""

    def __init__(
        self,
        language: str = "en",
        max_sections: int = 10,
        rate_limit: float = 1.0,
    ):
        """Initialize Wikipedia researcher.

        Args:
            language: Wikipedia language code
            max_sections: Maximum number of sections to retrieve
            rate_limit: Seconds between requests
        """
        self.language = language
        self.max_sections = max_sections
        self.rate_limit = rate_limit

        wikipedia.set_lang(language)

    def search_topic(self, query: str) -> Optional[str]:
        """Search for a Wikipedia page by query.

        Args:
            query: Search query

        Returns:
            Page title or None if not found
        """
        try:
            results = wikipedia.search(query, results=5)
            if results:
                logger.info(f"Found Wikipedia pages: {results[:5]}")
                return results[0]
        except wikipedia.exceptions.WikipediaException as e:
            logger.error(f"Wikipedia search error: {e}")
        return None

    def get_page_content(self, title: str) -> Optional[wikipedia.WikipediaPage]:
        """Get Wikipedia page content.

        Args:
            title: Page title

        Returns:
            WikipediaPage object or None
        """
        try:
            page = wikipedia.page(
                title,
                auto_suggest=True,
                redirect=True,
                preload=False,
            )
            logger.info(f"Retrieved page: {page.title} ({len(page.content)} chars)")
            return page
        except wikipedia.exceptions.DisambiguationError as e:
            logger.warning(f"Disambiguation needed for '{title}': {e.options}")
            if e.options:
                return self.get_page_content(e.options[0])
        except wikipedia.exceptions.PageError:
            logger.error(f"Page not found: {title}")
        except Exception as e:
            logger.error(f"Error retrieving page '{title}': {e}")
        return None

    def extract_sections(self, content: str) -> List[WikipediaSection]:
        """Extract sections from Wikipedia content.

        Args:
            content: Raw Wikipedia content

        Returns:
            List of WikipediaSection objects
        """
        sections = []
        lines = content.split("\n")
        current_section = None
        current_content = []
        section_count = 0

        for line in lines:
            # Check for section headers (== Title ==, === Subtitle ===)
            header_match = re.match(r"^(={2,})\s*(.+?)\s*\1$", line)

            if header_match:
                # Save previous section
                if current_section and section_count < self.max_sections:
                    current_section.content = "\n".join(
                        current_content
                    ).strip()
                    sections.append(current_section)
                    section_count += 1

                # Start new section
                level = len(header_match.group(1)) // 2
                title = header_match.group(2)

                current_section = WikipediaSection(
                    title=title,
                    content="",
                    level=level,
                    subsections=[],
                )
                current_content = []
            else:
                if current_section:
                    # Skip empty lines at the start
                    if current_content or line.strip():
                        current_content.append(line)

        # Add final section
        if current_section and section_count < self.max_sections:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    def clean_content(self, content: str) -> str:
        """Clean Wikipedia content.

        Args:
            content: Raw content

        Returns:
            Cleaned content
        """
        # Remove reference markers [1], [2], etc.
        content = re.sub(r"\[\d+\]", "", content)
        # Remove file/image links
        content = re.sub(r"\[\[File:.*?\]\]", "", content, flags=re.IGNORECASE)
        # Remove category links
        content = re.sub(r"\[\[Category:.*?\]\]", "", content, flags=re.IGNORECASE)
        # Clean up extra whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def research(
        self,
        topic: Dict,
        output_path: Optional[str] = None,
    ) -> WikipediaResearch:
        """Conduct research on a topic.

        Args:
            topic: Topic dictionary with title and keywords
            output_path: Optional path to save research results

        Returns:
            WikipediaResearch object
        """
        # Use keywords to search
        keywords = topic.get("keywords", [])
        search_query = keywords[0] if keywords else topic.get("title", "")

        logger.info(f"Researching topic: {topic['title']}")
        logger.info(f"Search query: {search_query}")

        # Search for page
        page_title = self.search_topic(search_query)
        if not page_title:
            # Fall back to topic title
            page_title = topic.get("title", "").split(":")[-1].strip()

        # Get page content
        page = self.get_page_content(page_title)
        if not page:
            raise ValueError(f"Could not retrieve Wikipedia page for '{page_title}'")

        # Extract sections
        sections = self.extract_sections(page.content)

        # Clean and structure research
        research = WikipediaResearch(
            title=page.title,
            url=page.url,
            summary=self.clean_content(page.summary),
            sections=[
                WikipediaSection(
                    title=s.title,
                    content=self.clean_content(s.content),
                    level=s.level,
                    subsections=s.subsections,
                )
                for s in sections
            ],
            images=page.images[:20] if hasattr(page, "images") else [],
            categories=page.categories[:10] if hasattr(page, "categories") else [],
            links=page.links[:20] if hasattr(page, "links") else [],
            references=[],
        )

        logger.info(f"Research complete: {len(research.sections)} sections, {len(research.images)} images")

        # Save if output path provided
        if output_path:
            self.save_research(research, output_path)

        return research

    def save_research(self, research: WikipediaResearch, output_path: str):
        """Save research to JSON file.

        Args:
            research: WikipediaResearch object
            output_path: Output file path
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary
        research_dict = {
            "title": research.title,
            "url": research.url,
            "summary": research.summary,
            "sections": [asdict(s) for s in research.sections],
            "images": research.images,
            "categories": research.categories,
            "links": research.links,
            "references": research.references,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(research_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Research saved to {output_file}")


def main():
    """Main entry point for Wikipedia researcher."""
    parser = argparse.ArgumentParser(description="Research topic on Wikipedia")
    parser.add_argument("--topic", type=str, help="Topic to research")
    parser.add_argument("--output", type=str, default="output/research.json")
    parser.add_argument("--language", type=str, default="en")
    args = parser.parse_args()

    if not args.topic:
        # Get topic from topic selector
        from topic_selector import TopicSelector

        selector = TopicSelector()
        topic_data = selector.get_random_topic()
        args.topic = topic_data.get("title", "Roman Empire")
    else:
        topic_data = {"title": args.topic, "keywords": [args.topic]}

    researcher = WikipediaResearcher(language=args.language)
    research = researcher.research(topic_data, output_path=args.output)

    print(f"Research complete: {research.title}")
    print(f"Sections: {len(research.sections)}")
    print(f"Images: {len(research.images)}")


if __name__ == "__main__":
    main()
