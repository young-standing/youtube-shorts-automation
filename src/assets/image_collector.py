#!/usr/bin/env python3
"""Image collector that downloads images from Wikimedia Commons."""

import json
import argparse
import requests
import time
from pathlib import Path
from urllib.parse import quote
from loguru import logger


def search_wikimedia_images(query: str, limit: int = 5) -> list:
    """Search for images on Wikimedia Commons.
    
    Args:
        query: Search query
        limit: Maximum number of images to return
        
    Returns:
        List of image info dictionaries
    """
    try:
        # Wikimedia Commons API
        url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{query} filetype:bitmap",
            "srnamespace": "6",  # File namespace
            "srlimit": limit * 2,  # Request more to account for filtering
            "format": "json",
            "origin": "*",
        }
        
        headers = {
            "User-Agent": "VoxEditBot/1.0 (https://github.com/young-standing/vox-edit)"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        images = []
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            if title.startswith("File:"):
                # Get image URL
                image_info = get_image_url(title, headers)
                if image_info:
                    images.append(image_info)
                    if len(images) >= limit:
                        break
        
        return images
    except Exception as e:
        logger.warning(f"Error searching Wikimedia for '{query}': {e}")
        return []


def get_image_url(filename: str, headers: dict) -> dict:
    """Get the direct URL for a Wikimedia Commons file.
    
    Args:
        filename: The filename including "File:" prefix
        headers: Request headers
        
    Returns:
        Dictionary with image info or None if failed
    """
    try:
        url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": filename,
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "format": "json",
            "origin": "*",
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                continue
            imageinfo = page.get("imageinfo", [])
            if imageinfo:
                info = imageinfo[0]
                mime = info.get("mime", "")
                # Only accept common image formats
                if mime in ["image/jpeg", "image/png", "image/webp"]:
                    return {
                        "title": page.get("title", ""),
                        "url": info.get("url", ""),
                        "mime": mime,
                        "width": info.get("width", 0),
                        "height": info.get("height", 0),
                    }
        return None
    except Exception as e:
        logger.warning(f"Error getting image URL for {filename}: {e}")
        return None


def download_image(url: str, output_path: Path, headers: dict) -> bool:
    """Download an image from URL.
    
    Args:
        url: Image URL
        output_path: Path to save image
        headers: Request headers
        
    Returns:
        True if successful
    """
    try:
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Collect images from Wikimedia Commons")
    parser.add_argument("--input", required=True, help="Path to script JSON file")
    parser.add_argument("--output", required=True, help="Output directory for images")
    parser.add_argument("--limit", type=int, default=3, help="Max images per segment")
    args = parser.parse_args()
    
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Load script
    with open(args.input, "r", encoding="utf-8") as f:
        script = json.load(f)
    
    headers = {
        "User-Agent": "VoxEditBot/1.0 (https://github.com/young-standing/vox-edit)"
    }
    
    collected_images = []
    
    # Extract keywords from title and segments
    title = script.get("title", "history")
    keywords = [title]
    
    for segment in script.get("segments", []):
        seg_keywords = segment.get("keywords", [])
        keywords.extend(seg_keywords[:2])  # Take first 2 keywords per segment
    
    # Remove duplicates and limit
    keywords = list(dict.fromkeys(keywords))[:10]
    
    logger.info(f"Searching for images with keywords: {keywords}")
    
    image_index = 0
    for keyword in keywords:
        if image_index >= 15:  # Limit total images
            break
            
        logger.info(f"Searching for: {keyword}")
        images = search_wikimedia_images(keyword, limit=args.limit)
        
        for img in images:
            if image_index >= 15:
                break
                
            # Determine file extension
            ext = ".jpg"
            if "png" in img["mime"]:
                ext = ".png"
            elif "webp" in img["mime"]:
                ext = ".webp"
            
            # Download image
            img_path = output_path / f"image_{image_index:03d}{ext}"
            
            if download_image(img["url"], img_path, headers):
                collected_images.append({
                    "path": str(img_path),
                    "source": img["url"],
                    "title": img["title"],
                    "keyword": keyword,
                })
                logger.info(f"Downloaded: {img_path.name}")
                image_index += 1
                time.sleep(0.5)  # Rate limiting
    
    # Save metadata
    result_file = output_path / "images.json"
    with open(result_file, "w") as f:
        json.dump(collected_images, f, indent=2)
    
    logger.info(f"Collected {len(collected_images)} images")
    print(f"Collected {len(collected_images)} images")


if __name__ == "__main__":
    main()
