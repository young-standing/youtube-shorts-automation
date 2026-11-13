#!/usr/bin/env python3
"""YouTube uploader for documentaries."""

import json
import argparse
from pathlib import Path
from typing import Dict, Optional
import os
import pickle
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from loguru import logger


class YouTubeUploader:
    """Uploads documentaries to YouTube."""

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        refresh_token: str = None,
        token_path: str = "token.pickle",
    ):
        """Initialize YouTube uploader.

        Args:
            client_id: YouTube API client ID
            client_secret: YouTube API client secret
            refresh_token: OAuth refresh token
            token_path: Path to store token
        """
        self.client_id = client_id or os.environ.get("YOUTUBE_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = refresh_token or os.environ.get("YOUTUBE_REFRESH_TOKEN")
        self.token_path = token_path
        self.youtube = None

    def authenticate(self) -> bool:
        """Authenticate with YouTube API.

        Returns:
            True if authentication successful
        """
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        # If credentials exist and are valid, use them
        if creds and creds.valid:
            pass
        # If credentials exist but expired, refresh
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # If we have refresh token directly, create credentials
        elif self.client_id and self.client_secret and self.refresh_token:
            creds = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES,
            )
            creds.refresh(Request())
        else:
            raise ValueError(
                "YouTube credentials not configured. "
                "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN "
                "environment variables."
            )

        # Save token
        with open(self.token_path, "wb") as token:
            pickle.dump(creds, token)

        # Build YouTube service
        self.youtube = build("youtube", "v3", credentials=creds)

        logger.info("YouTube API authenticated")
        return True

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        category_id: int = 27,  # Education
        privacy_status: str = "public",
        thumbnail_path: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
    ) -> Dict:
        """Upload video to YouTube.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags
            category_id: YouTube category ID
            privacy_status: 'public', 'private', or 'unlisted'
            thumbnail_path: Path to thumbnail image
            scheduled_at: Scheduled publish time

        Returns:
            Upload result with video ID
        """
        if not self.youtube:
            self.authenticate()

        logger.info(f"Uploading video: {title}")

        # Prepare video metadata
        body = {
            "snippet": {
                "title": title[:100],  # YouTube limit
                "description": description[:5000],  # YouTube limit
                "tags": tags[:500],  # YouTube limit
                "categoryId": str(category_id),
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                "madeForKids": False,
            },
        }

        # Add scheduled time
        if scheduled_at and privacy_status != "private":
            body["status"]["publishAt"] = scheduled_at.isoformat()

        # Upload video
        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024,
            resumable=True,
            mimetype="video/*",
        )

        request = self.youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        # Execute upload with progress
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                logger.info(f"Upload progress: {progress}%")

        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        logger.info(f"Video uploaded: {video_url}")

        # Upload thumbnail
        if thumbnail_path:
            try:
                self.upload_thumbnail(video_id, thumbnail_path)
            except Exception as e:
                logger.warning(f"Failed to upload thumbnail: {e}")

        return {
            "video_id": video_id,
            "video_url": video_url,
            "title": title,
            "privacy_status": privacy_status,
            "uploaded_at": datetime.now().isoformat(),
        }

    def upload_thumbnail(
        self,
        video_id: str,
        thumbnail_path: str,
    ) -> Dict:
        """Upload thumbnail for video.

        Args:
            video_id: YouTube video ID
            thumbnail_path: Path to thumbnail image

        Returns:
            Thumbnail upload result
        """
        if not self.youtube:
            self.authenticate()

        logger.info(f"Uploading thumbnail for video {video_id}")

        media = MediaFileUpload(
            thumbnail_path,
            resumable=True,
            mimetype="image/jpeg",
        )

        request = self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=media,
        )

        response = request.execute()
        logger.info("Thumbnail uploaded")

        return response

    def upload_documentary(
        self,
        video_path: str,
        thumbnail_path: str,
        metadata_path: str,
        output_path: Optional[str] = None,
    ) -> Dict:
        """Upload documentary with metadata.

        Args:
            video_path: Video file path
            thumbnail_path: Thumbnail image path
            metadata_path: Metadata JSON file path
            output_path: Output JSON file path

        Returns:
            Upload result
        """
        # Load metadata
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        title = metadata.get("title", "Historical Documentary")
        description = metadata.get("description", "")
        tags = metadata.get("tags", ["history", "documentary", "education"])
        category_id = metadata.get("category_id", 27)
        privacy_status = os.environ.get("DEFAULT_PRIVACY", "public")

        # Upload video
        result = self.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            privacy_status=privacy_status,
            thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None,
        )

        # Save result
        if output_path:
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)

        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Upload documentary to YouTube")
    parser.add_argument("--video", type=str, required=True)
    parser.add_argument("--thumbnail", type=str, required=False)
    parser.add_argument("--metadata", type=str, required=True)
    parser.add_argument("--output", type=str, default="output/upload_result.json")
    args = parser.parse_args()

    uploader = YouTubeUploader()

    result = uploader.upload_documentary(
        video_path=args.video,
        thumbnail_path=args.thumbnail,
        metadata_path=args.metadata,
        output_path=args.output,
    )

    print(f"Uploaded: {result['video_url']}")


if __name__ == "__main__":
    main()
