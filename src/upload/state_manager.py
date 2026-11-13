#!/usr/bin/env python3
"""State manager for tracking published documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from loguru import logger


class StateManager:
    """Manages publication state for documentaries."""

    def __init__(
        self,
        state_file: str = "state/publication_history.json",
    ):
        """Initialize state manager.

        Args:
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load state from file."""
        if self.state_file.exists():
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "publications": [],
            "used_topics": [],
            "statistics": {
                "total_videos": 0,
                "total_views": 0,
                "total_duration_minutes": 0,
            },
        }

    def _save_state(self):
        """Save state to file."""
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def save_publication(
        self,
        topic: str,
        upload_result: Dict,
        research_file: Optional[str] = None,
        script_file: Optional[str] = None,
        video_file: Optional[str] = None,
    ) -> Dict:
        """Save publication to state.

        Args:
            topic: Documentary topic
            upload_result: Upload result from YouTube
            research_file: Path to research file
            script_file: Path to script file
            video_file: Path to video file

        Returns:
            Publication record
        """
        publication = {
            "id": upload_result.get("video_id", ""),
            "topic": topic,
            "title": upload_result.get("title", ""),
            "url": upload_result.get("video_url", ""),
            "uploaded_at": upload_result.get("uploaded_at", datetime.now().isoformat()),
            "privacy_status": upload_result.get("privacy_status", "public"),
            "files": {
                "research": research_file,
                "script": script_file,
                "video": video_file,
            },
            "analytics": {
                "views": 0,
                "likes": 0,
                "comments": 0,
            },
        }

        # Add to publications
        self.state["publications"].append(publication)

        # Add to used topics
        if topic not in self.state["used_topics"]:
            self.state["used_topics"].append(topic)

        # Update statistics
        self.state["statistics"]["total_videos"] += 1

        # Save
        self._save_state()

        logger.info(f"Publication saved: {topic}")

        return publication

    def is_topic_used(self, topic: str) -> bool:
        """Check if topic has been used.

        Args:
            topic: Topic to check

        Returns:
            True if topic already used
        """
        return topic in self.state.get("used_topics", [])

    def get_unused_topics(self, topics: List[str]) -> List[str]:
        """Get topics that haven't been used.

        Args:
            topics: List of all topics

        Returns:
            List of unused topics
        """
        used = set(self.state.get("used_topics", []))
        return [t for t in topics if t not in used]

    def get_publications(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict]:
        """Get recent publications.

        Args:
            limit: Maximum number to return
            offset: Offset from start

        Returns:
            List of publications
        """
        publications = self.state.get("publications", [])
        return publications[offset : offset + limit]

    def get_publication_by_id(self, video_id: str) -> Optional[Dict]:
        """Get publication by video ID.

        Args:
            video_id: YouTube video ID

        Returns:
            Publication or None
        """
        for pub in self.state.get("publications", []):
            if pub.get("id") == video_id:
                return pub
        return None

    def update_analytics(
        self,
        video_id: str,
        views: int,
        likes: int,
        comments: int,
    ) -> bool:
        """Update analytics for a publication.

        Args:
            video_id: YouTube video ID
            views: View count
            likes: Like count
            comments: Comment count

        Returns:
            True if updated successfully
        """
        for pub in self.state.get("publications", []):
            if pub.get("id") == video_id:
                pub["analytics"] = {
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    "updated_at": datetime.now().isoformat(),
                }

                self._save_state()
                logger.info(f"Analytics updated for {video_id}")
                return True

        return False

    def get_statistics(self) -> Dict:
        """Get overall statistics.

        Returns:
            Statistics dictionary
        """
        stats = self.state.get("statistics", {})

        # Calculate actual totals from publications
        publications = self.state.get("publications", [])
        total_views = sum(p.get("analytics", {}).get("views", 0) for p in publications)

        stats["total_views"] = total_views
        stats["total_videos"] = len(publications)

        return stats

    def export_history(self, output_path: str) -> str:
        """Export publication history.

        Args:
            output_path: Output file path

        Returns:
            Path to exported file
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

        logger.info(f"History exported to {output_path}")
        return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Manage publication state")
    parser.add_argument("--save", action="store_true", help="Save publication")
    parser.add_argument("--topic", type=str, help="Topic")
    parser.add_argument("--upload-result", type=str, help="Upload result JSON")
    parser.add_argument("--list", action="store_true", help="List publications")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    args = parser.parse_args()

    manager = StateManager()

    if args.save:
        if not args.topic or not args.upload_result:
            print("Error: --topic and --upload-result required for save")
            return

        with open(args.upload_result, "r") as f:
            upload_result = json.load(f)

        publication = manager.save_publication(args.topic, upload_result)
        print(f"Saved: {publication['url']}")

    elif args.list:
        publications = manager.get_publications(limit=20)
        print(f"\nRecent Publications ({len(publications)}):\n")
        for i, pub in enumerate(publications, 1):
            print(f"{i}. {pub['title']}")
            print(f"   URL: {pub['url']}")
            print(f"   Uploaded: {pub['uploaded_at']}")
            print()

    elif args.stats:
        stats = manager.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total Videos: {stats.get('total_videos', 0)}")
        print(f"  Total Views: {stats.get('total_views', 0)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
