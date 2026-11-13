#!/usr/bin/env python3
"""Topic selector for documentary generation."""

import json
import random
import argparse
from pathlib import Path
from typing import Optional, Dict, List

from loguru import logger


class TopicSelector:
    """Selects documentary topics from configured series."""

    def __init__(self, topics_config_path: str = "config/topics.json"):
        self.topics_config_path = Path(topics_config_path)
        self.topics_data = self._load_topics()

    def _load_topics(self) -> Dict:
        """Load topics configuration."""
        if not self.topics_config_path.exists():
            logger.warning(
                f"Topics config not found at {self.topics_config_path}, using default"
            )
            return self._get_default_topics()

        with open(self.topics_config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_default_topics(self) -> Dict:
        """Get default topics if config file is missing."""
        return {
            "series": [
                {
                    "name": "Empire Histories",
                    "topics": [
                        {
                            "title": "The Rise and Fall of the Roman Empire",
                            "keywords": ["rome", "roman empire", "caesar"],
                            "time_period": "753 BC - 476 AD",
                            "difficulty": "beginner",
                        }
                    ],
                }
            ]
        }

    def get_random_topic(self, series_name: Optional[str] = None) -> Dict:
        """Get a random topic from the topics database.

        Args:
            series_name: Optional specific series to select from

        Returns:
            Topic dictionary with title, keywords, etc.
        """
        series_list = self.topics_data.get("series", [])

        if series_name:
            series = next(
                (s for s in series_list if s["name"] == series_name), None
            )
            if not series:
                logger.warning(
                    f"Series '{series_name}' not found, selecting randomly"
                )
                series = random.choice(series_list)
        else:
            series = random.choice(series_list)

        topics = series.get("topics", [])
        if not topics:
            raise ValueError(f"No topics found in series '{series['name']}'")

        topic = random.choice(topics)
        topic["series"] = series["name"]

        logger.info(f"Selected topic: {topic['title']} (Series: {series['name']})")
        return topic

    def get_all_topics(self) -> List[Dict]:
        """Get all available topics."""
        all_topics = []
        for series in self.topics_data.get("series", []):
            for topic in series.get("topics", []):
                topic_copy = topic.copy()
                topic_copy["series"] = series["name"]
                all_topics.append(topic_copy)
        return all_topics

    def get_topic_by_title(self, title: str) -> Optional[Dict]:
        """Get a specific topic by title.

        Args:
            title: Topic title to search for

        Returns:
            Topic dictionary or None if not found
        """
        for series in self.topics_data.get("series", []):
            for topic in series.get("topics", []):
                if topic["title"].lower() == title.lower():
                    topic_copy = topic.copy()
                    topic_copy["series"] = series["name"]
                    return topic_copy
        return None


def main():
    """Main entry point for topic selection."""
    parser = argparse.ArgumentParser(description="Select documentary topic")
    parser.add_argument(
        "--series", type=str, help="Specific series to select from"
    )
    parser.add_argument(
        "--list", action="store_true", help="List all available topics"
    )
    args = parser.parse_args()

    selector = TopicSelector()

    if args.list:
        topics = selector.get_all_topics()
        print(f"Available topics ({len(topics)}):\n")
        for i, topic in enumerate(topics, 1):
            print(f"{i}. {topic['title']} ({topic['series']})")
        return

    topic = selector.get_random_topic(series_name=args.series)
    print(topic["title"])


if __name__ == "__main__":
    main()
