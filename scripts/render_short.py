#!/usr/bin/env python3
"""Create a 20-second motivational YouTube Short with Pexels footage and music."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
QUOTES_PATH = ROOT / "data" / "quotes.json"
STATE_PATH = ROOT / "data" / "state.json"
OUTPUT_DIR = ROOT / "output"
POPPINS_FONT_PATH = ROOT / "assets" / "fonts" / "Poppins-SemiBold.ttf"
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/videos/search"
OPENVERSE_AUDIO_URL = "https://api.openverse.org/v1/audio/"
OPENVERSE_TOKEN_URL = "https://api.openverse.org/v1/auth_tokens/token/"
FALLBACK_SEARCH = "calm sunrise nature"
MUSIC_SEARCHES = (
    "sad piano",
    "emotional piano",
    "melancholic piano",
    "somber piano",
)
OPENVERSE_LICENSES = {"cc0", "pdm"}
VIDEO_SECONDS = 20
WIDTH = 1080
HEIGHT = 1920
FPS = 30
HASHTAGS = "#motivation #discipline #success #mindset #shorts"
CLIP_COUNT = 3
CLIP_SECONDS = 7
TRANSITION_SECONDS = 0.5
HOOKS = {
    "discipline": ("DO IT ANYWAY.", "STOP NEGOTIATING.", "KEEP THE PROMISE.", "NO MORE EXCUSES."),
    "success": ("PLAY THE LONG GAME.", "THIS IS HOW YOU WIN.", "BUILD IT QUIETLY.", "KEEP GOING."),
    "healing": ("YOU ARE STILL HEALING.", "BE GENTLE TODAY.", "LET IT GO SLOWLY.", "YOU WILL FEEL LIGHT AGAIN."),
    "confidence": ("TRUST YOURSELF AGAIN.", "YOU ARE MORE READY.", "TAKE UP SPACE.", "BACK YOURSELF."),
    "growth": ("YOUR NEXT CHAPTER STARTS NOW.", "OUTGROW THE OLD YOU.", "CHOOSE YOUR FUTURE.", "CHANGE STARTS HERE."),
    "consistency": ("SMALL STEPS STILL COUNT.", "SHOW UP AGAIN.", "DON'T BREAK THE RHYTHM.", "REPEAT WHAT WORKS."),
}
SUPPORTED_CATEGORIES = {
    "discipline",
    "success",
    "healing",
    "confidence",
    "growth",
    "consistency",
}


class ShortsError(RuntimeError):
    """A user-actionable automation error."""


def http_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "github-youtube-shorts/1.0"})
    return session


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ShortsError(f"Required JSON file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ShortsError(f"Invalid JSON in {path}: {exc}") from exc


def load_quotes(path: Path = QUOTES_PATH) -> list[dict[str, str]]:
    payload = load_json(path)
    if not isinstance(payload, list) or not payload:
        raise ShortsError("The quote catalog is empty; add new original scripts before running again")
    seen: set[str] = set()
    quotes: list[dict[str, str]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ShortsError(f"Quote entry {index} must be an object")
        required = {"id", "quote", "insight", "pexels_search", "category"}
        if set(item) != required:
            raise ShortsError(f"Quote entry {index} must contain exactly {sorted(required)}")
        normalized = {key: str(item[key]).strip() for key in required}
        if not all(normalized.values()):
            raise ShortsError(f"Quote entry {index} contains an empty value")
        if normalized["id"] in seen:
            raise ShortsError(f"Duplicate quote id: {normalized['id']}")
        if normalized["category"] not in SUPPORTED_CATEGORIES:
            raise ShortsError(f"Unsupported quote category: {normalized['category']}")
        seen.add(normalized["id"])
        quotes.append(normalized)
    return quotes


def default_state() -> dict[str, Any]:
    return {"version": 1, "cycle": 1, "used_ids": [], "history": []}


def load_state(path: Path = STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return default_state()
    payload = load_json(path)
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ShortsError("data/state.json must be a version 1 state object")
    used_ids = payload.get("used_ids", [])
    history = payload.get("history", [])
    cycle = payload.get("cycle", 1)
    if not isinstance(cycle, int) or cycle < 1:
        raise ShortsError("state.cycle must be a positive integer")
    if not isinstance(used_ids, list) or not all(isinstance(value, str) for value in used_ids):
        raise ShortsError("state.used_ids must be a list of strings")
    if not isinstance(history, list) or not all(isinstance(value, dict) for value in history):
        raise ShortsError("state.history must be a list of objects")
    return {"version": 1, "cycle": cycle, "used_ids": used_ids, "history": history}


def select_quote(
    quotes: list[dict[str, str]],
    state: dict[str, Any],
    *,
    rng: random.Random | random.SystemRandom | None = None,
) -> dict[str, str]:
    """Choose an unused quote; reset only after the complete catalog is used."""
    if not quotes:
        raise ShortsError("The quote catalog is empty")
    chooser = rng or random.SystemRandom()
    known_ids = {entry["id"] for entry in quotes}
    used = {value for value in state.get("used_ids", []) if value in known_ids}
    candidates = [entry for entry in quotes if entry["id"] not in used]
    if not candidates:
        raise ShortsError("All remaining scripts are already marked as used; refill the catalog")
    selected = chooser.choice(candidates)
    state.setdefault("used_ids", []).append(selected["id"])
    state.setdefault("history", []).append(
        {
            "id": selected["id"],
            "used_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    state["history"] = state["history"][-200:]
    state["version"] = 1
    state.setdefault("cycle", 1)
    return selected


def save_state(state: dict[str, Any], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def wrap_quote(text: str, *, width: int = 22, max_lines: int = 5) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        raise ShortsError("Quote text cannot be empty")
    lines = textwrap.wrap(
        cleaned,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if len(lines) > max_lines:
        raise ShortsError(
            f"Quote needs {len(lines)} lines and exceeds the {max_lines}-line safe area"
        )
    if any(len(line) > width + 8 for line in lines):
        raise ShortsError("Quote contains a word too long for the text safe area")
    return "\n".join(lines)


def validate_channel_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        raise ShortsError("CHANNEL_NAME is required")
    if len(cleaned) > 40:
        raise ShortsError("CHANNEL_NAME must be 40 characters or fewer to stay in the safe area")
    return cleaned


def make_title(quote: str) -> str:
    suffix = " #shorts"
    cleaned = re.sub(r"\s+", " ", quote).strip().strip('"')
    limit = 100 - len(suffix)
    if len(cleaned) > limit:
        shortened = cleaned[: limit - 1].rsplit(" ", 1)[0].rstrip(".,;:!?")
        cleaned = (shortened or cleaned[: limit - 1]).rstrip() + "…"
    return cleaned + suffix


def make_hook(entry: dict[str, str]) -> str:
    """Return a short, stable hook so retries render the same creative."""
    choices = HOOKS[entry["category"]]
    seed = sum(ord(character) for character in entry["id"])
    return choices[seed % len(choices)]


def ass_escape(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def build_ass_subtitles(entry: dict[str, str], channel_name: str) -> str:
    """Build staged, animated subtitles for the four-part Short structure."""
    hook = ass_escape(wrap_quote(make_hook(entry), width=24, max_lines=2))
    quote = ass_escape(wrap_quote(entry["quote"], width=32, max_lines=5))
    insight = ass_escape(wrap_quote(entry["insight"], width=34, max_lines=4))
    channel = ass_escape(channel_name)
    return fr"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Poppins SemiBold,76,&H0000D7FF,&H0000D7FF,&HCC000000,&H80000000,-1,0,0,0,100,100,1,0,1,5,1,5,90,90,0,1
Style: Quote,Poppins SemiBold,52,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H78000000,-1,0,0,0,100,100,0,0,1,4,1,5,90,90,0,1
Style: Label,Poppins SemiBold,30,&H0000D7FF,&H0000D7FF,&HCC000000,&H70000000,-1,0,0,0,100,100,2,0,1,3,0,5,90,90,0,1
Style: Action,Poppins SemiBold,46,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H78000000,-1,0,0,0,100,100,0,0,1,4,1,5,90,90,0,1
Style: CTA,Poppins SemiBold,54,&H00FFFFFF,&H00FFFFFF,&HCC000000,&H80000000,-1,0,0,0,100,100,1,0,1,4,1,5,90,90,0,1
Style: Channel,Poppins SemiBold,25,&HDDFFFFFF,&HDDFFFFFF,&H90000000,&H00000000,-1,0,0,0,100,100,1,0,1,2,60,60,125,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 2,0:00:00.00,0:00:02.70,Hook,,0,0,0,,{{\fad(180,220)\fscx112\fscy112\t(0,300,\fscx100\fscy100)}}{hook}
Dialogue: 1,0:00:02.25,0:00:10.40,Quote,,0,0,0,,{{\fad(250,300)\fscx104\fscy104\t(0,350,\fscx100\fscy100)}}{quote}
Dialogue: 2,0:00:09.85,0:00:16.75,Label,,0,0,0,,{{\fad(220,250)\pos(540,690)}}DO THIS TODAY
Dialogue: 1,0:00:09.85,0:00:16.75,Action,,0,0,0,,{{\fad(220,250)\pos(540,1010)}}{insight}
Dialogue: 2,0:00:16.20,0:00:20.00,CTA,,0,0,0,,{{\fad(220,500)\fscx108\fscy108\t(0,350,\fscx100\fscy100)}}SAVE THIS FOR TOMORROW
Dialogue: 3,0:00:00.00,0:00:20.00,Channel,,0,0,0,,{{\an2\pos(540,1740)}}{channel}
"""


def build_metadata(
    entry: dict[str, str],
    *,
    creator_name: str,
    source_url: str,
    channel_name: str,
    privacy_status: str,
    music_name: str,
    music_creator: str = "Unknown creator",
    music_source_url: str = "",
    music_license: str = "CC0",
) -> dict[str, Any]:
    if privacy_status not in {"private", "unlisted", "public"}:
        raise ShortsError(f"Invalid privacy status: {privacy_status}")
    quote = entry["quote"].strip()
    insight = entry["insight"].strip()
    return {
        "quote_id": entry["id"],
        "quote": quote,
        "insight": insight,
        "category": entry["category"],
        "pexels_search": entry["pexels_search"],
        "pexels_creator": creator_name,
        "pexels_source_url": source_url,
        "music_file": music_name,
        "music_creator": music_creator,
        "music_source_url": music_source_url,
        "music_license": music_license,
        "channel_name": channel_name,
        "title": make_title(quote),
        "description": (
            f"{quote}\n\nTakeaway: {insight}\n\n"
            f"Footage by {creator_name} on Pexels: {source_url}\n"
            f"Music: {music_name} by {music_creator} "
            f"({music_license}): {music_source_url}\n\n"
            f"{HASHTAGS}"
        ),
        "tags": [
            "motivation",
            "discipline",
            "success",
            "mindset",
            "self improvement",
            entry["category"],
            "shorts",
        ],
        "category_id": "22",
        "made_for_kids": False,
        "privacy_status": privacy_status,
        "duration_seconds": VIDEO_SECONDS,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def valid_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def video_file_score(item: dict[str, Any]) -> tuple[float, float]:
    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    ratio_penalty = abs((width / height if height else 99) - (9 / 16))
    size_penalty = abs(width - WIDTH) + abs(height - HEIGHT)
    landscape_penalty = 10 if width >= height else 0
    return (landscape_penalty + ratio_penalty, size_penalty)


def suitable_video_files(videos: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for video in videos:
        creator = video.get("user") or {}
        files: list[dict[str, Any]] = []
        for media in video.get("video_files") or []:
            link = str(media.get("link") or "")
            file_type = str(media.get("file_type") or "")
            width = int(media.get("width") or 0)
            height = int(media.get("height") or 0)
            if (
                not valid_https_url(link)
                or file_type != "video/mp4"
                or width < 540
                or height < 960
            ):
                continue
            files.append(
                {
                    "download_url": link,
                    "width": width,
                    "height": height,
                    "creator_name": str(creator.get("name") or "Pexels contributor"),
                    "source_url": str(video.get("url") or "https://www.pexels.com/videos/"),
                    "score": video_file_score(media),
                }
            )
        if files:
            candidates.append(min(files, key=lambda value: value["score"]))
    return sorted(candidates, key=lambda value: value["score"])


def search_pexels_clips(
    phrase: str,
    *,
    api_key: str,
    count: int = CLIP_COUNT,
    rng: random.Random | random.SystemRandom | None = None,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    chooser = rng or random.SystemRandom()
    client = session or http_session()
    errors: list[str] = []
    phrases = [phrase]
    if phrase.casefold() != FALLBACK_SEARCH.casefold():
        phrases.append(FALLBACK_SEARCH)
    selected_assets: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    seen_creators: set[str] = set()
    for query in phrases:
        try:
            response = client.get(
                PEXELS_SEARCH_URL,
                headers={"Authorization": api_key},
                params={
                    "query": query,
                    "orientation": "portrait",
                    "size": "medium",
                    "locale": "en-US",
                    "per_page": 40,
                },
                timeout=(10, 45),
            )
            response.raise_for_status()
            response.encoding = "utf-8"
            payload = response.json()
            candidates = suitable_video_files(payload.get("videos") or [])
            pool = [item for item in candidates[:20] if item["source_url"] not in seen_sources]
            chooser.shuffle(pool)
            for prefer_new_creator in (True, False):
                for selected in pool:
                    creator_key = selected["creator_name"].casefold()
                    if selected["source_url"] in seen_sources:
                        continue
                    if prefer_new_creator and creator_key in seen_creators:
                        continue
                    selected["search_used"] = query
                    selected_assets.append(selected)
                    seen_sources.add(selected["source_url"])
                    seen_creators.add(creator_key)
                    if len(selected_assets) == count:
                        return selected_assets
            errors.append(f"no suitable portrait MP4 results for {query!r}")
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{query!r}: {exc}")
    raise ShortsError(
        f"Pexels search found only {len(selected_assets)} of {count} distinct clips; "
        + "; ".join(errors)
    )


def search_pexels(
    phrase: str,
    *,
    api_key: str,
    rng: random.Random | random.SystemRandom | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """Backward-compatible single-result helper."""
    return search_pexels_clips(
        phrase, api_key=api_key, count=1, rng=rng, session=session
    )[0]


def download_file(url: str, destination: Path, *, session: requests.Session | None = None) -> None:
    if not valid_https_url(url):
        raise ShortsError("Pexels returned an invalid download URL")
    client = session or http_session()
    try:
        with client.get(url, stream=True, timeout=(10, 120)) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "video" not in content_type and "octet-stream" not in content_type:
                raise ShortsError(f"Pexels download returned unexpected content type: {content_type}")
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    except requests.RequestException as exc:
        raise ShortsError(f"Unable to download Pexels footage: {exc}") from exc
    if not destination.exists() or destination.stat().st_size < 1024:
        raise ShortsError("Downloaded Pexels footage is empty or invalid")


def suitable_openverse_audio(results: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in results:
        download_url = str(item.get("url") or "")
        source_url = str(item.get("foreign_landing_url") or "")
        license_code = str(item.get("license") or "").casefold()
        duration_ms = int(item.get("duration") or 0)
        if (
            not valid_https_url(download_url)
            or not valid_https_url(source_url)
            or license_code not in OPENVERSE_LICENSES
            or duration_ms < VIDEO_SECONDS * 1000
        ):
            continue
        candidates.append(
            {
                "id": str(item.get("id") or ""),
                "download_url": download_url,
                "title": str(item.get("title") or "Sad piano").strip(),
                "creator": str(item.get("creator") or "Openverse contributor").strip(),
                "source_url": source_url,
                "license": license_code.upper(),
                "duration_ms": duration_ms,
            }
        )
    return candidates


def search_openverse_audio(
    *,
    rng: random.Random | random.SystemRandom | None = None,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    chooser = rng or random.SystemRandom()
    client = session or http_session()
    client_id = os.environ.get("OPENVERSE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("OPENVERSE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ShortsError("OPENVERSE_CLIENT_ID and OPENVERSE_CLIENT_SECRET are required")
    try:
        token_response = client.post(
            OPENVERSE_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=(10, 30),
        )
        token_response.raise_for_status()
        access_token = str(token_response.json().get("access_token") or "").strip()
    except (requests.RequestException, ValueError) as exc:
        raise ShortsError(f"Openverse authentication failed: {exc}") from exc
    if not access_token:
        raise ShortsError("Openverse authentication returned no access token")

    queries = list(MUSIC_SEARCHES)
    chooser.shuffle(queries)
    errors: list[str] = []
    for query in queries:
        try:
            response = client.get(
                OPENVERSE_AUDIO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": query,
                    "license": "cc0,pdm",
                    "page_size": 50,
                    "mature": "false",
                    "filter_dead": "true",
                },
                timeout=(10, 45),
            )
            response.raise_for_status()
            response.encoding = "utf-8"
            candidates = suitable_openverse_audio(response.json().get("results") or [])
            if candidates:
                selected = chooser.choice(candidates)
                selected["search_used"] = query
                return selected
            errors.append(f"no suitable CC0/Public Domain results for {query!r}")
        except (requests.RequestException, ValueError, TypeError) as exc:
            errors.append(f"{query!r}: {exc}")
    raise ShortsError("Openverse sad-piano search failed; " + "; ".join(errors))


def download_audio(
    url: str,
    destination: Path,
    *,
    session: requests.Session | None = None,
) -> None:
    if not valid_https_url(url):
        raise ShortsError("Openverse returned an invalid audio URL")
    client = session or http_session()
    try:
        with client.get(url, stream=True, timeout=(10, 120)) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "audio" not in content_type and "octet-stream" not in content_type:
                raise ShortsError(
                    f"Openverse audio download returned unexpected content type: {content_type}"
                )
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    except requests.RequestException as exc:
        raise ShortsError(f"Unable to download Openverse audio: {exc}") from exc
    if not destination.exists() or destination.stat().st_size < 4096:
        raise ShortsError("Downloaded Openverse audio is empty or invalid")


def locate_font() -> Path:
    if POPPINS_FONT_PATH.is_file():
        return POPPINS_FONT_PATH
    raise ShortsError(f"Bundled Poppins font is missing: {POPPINS_FONT_PATH}")


def ffmpeg_filter_path(path: Path) -> str:
    value = path.resolve().as_posix()
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def run_ffmpeg(
    footage: list[Path],
    music: Path,
    subtitles_file: Path,
    output: Path,
) -> None:
    if len(footage) != CLIP_COUNT:
        raise ShortsError(f"Exactly {CLIP_COUNT} footage clips are required")
    font = locate_font()
    subtitles_path = ffmpeg_filter_path(subtitles_file)
    fonts_dir = ffmpeg_filter_path(font.parent)
    video_filter = (
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},trim=duration={CLIP_SECONDS},setpts=PTS-STARTPTS[v0];"
        f"[1:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},trim=duration={CLIP_SECONDS},setpts=PTS-STARTPTS[v1];"
        f"[2:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},trim=duration={CLIP_SECONDS},setpts=PTS-STARTPTS[v2];"
        f"[v0][v1]xfade=transition=fade:duration={TRANSITION_SECONDS}:offset=6.5[v01];"
        f"[v01][v2]xfade=transition=fade:duration={TRANSITION_SECONDS}:offset=13.0,"
        "eq=brightness=-0.10:saturation=0.90,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.12:t=fill,"
        f"subtitles='{subtitles_path}':fontsdir='{fonts_dir}',"
        "drawbox=x=0:y=ih-8:w=iw:h=8:color=0xFFD700@0.90:t=fill,"
        f"trim=duration={VIDEO_SECONDS},format=yuv420p[v];"
        f"[3:a]volume=0.16,afade=t=in:st=0:d=1,"
        f"afade=t=out:st={VIDEO_SECONDS - 2}:d=2,"
        f"atrim=duration={VIDEO_SECONDS},asetpts=PTS-STARTPTS[a]"
    )
    command = ["ffmpeg", "-hide_banner", "-y"]
    for clip in footage:
        command.extend(["-stream_loop", "-1", "-i", str(clip)])
    command.extend([
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        video_filter,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-t",
        str(VIDEO_SECONDS),
        "-r",
        str(FPS),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "21",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output),
    ])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.splitlines()[-40:])
        raise ShortsError(f"FFmpeg rendering failed:\n{tail}")
    if not output.exists() or output.stat().st_size < 10_000:
        raise ShortsError("FFmpeg completed without producing a valid MP4")


def write_metadata(metadata: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quote", default=os.environ.get("INPUT_QUOTE", ""))
    parser.add_argument("--search", default=os.environ.get("INPUT_PEXELS_SEARCH", ""))
    parser.add_argument(
        "--privacy",
        default=os.environ.get("INPUT_PRIVACY_STATUS", "private"),
        choices=("private", "unlisted", "public"),
    )
    parser.add_argument("--footage-file", type=Path, help="Local footage for offline smoke tests")
    parser.add_argument("--music-file", type=Path, help="Specific music for offline smoke tests")
    parser.add_argument("--seed", type=int, help="Deterministic selection for tests")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng: random.Random | random.SystemRandom = (
        random.Random(args.seed) if args.seed is not None else random.SystemRandom()
    )
    channel_name = validate_channel_name(os.environ.get("CHANNEL_NAME", ""))
    if not shutil.which("ffmpeg"):
        raise ShortsError("ffmpeg is not installed or not on PATH")

    quotes = load_quotes()
    state = load_state()
    quote_override = re.sub(r"\s+", " ", args.quote).strip()
    if quote_override:
        selected = {
            "id": "manual",
            "quote": quote_override,
            "insight": "Choose one useful action and complete it today.",
            "pexels_search": args.search.strip() or FALLBACK_SEARCH,
            "category": "growth",
        }
        state_changed = False
    else:
        selected = select_quote(quotes, state, rng=rng)
        if args.search.strip():
            selected = {**selected, "pexels_search": args.search.strip()}
        state_changed = True

    if args.music_file:
        if not args.music_file.is_file():
            raise ShortsError(f"Music file does not exist: {args.music_file}")
        music = args.music_file
        music_asset = {
            "title": music.name,
            "creator": "Local smoke test",
            "source_url": "https://openverse.org/",
            "license": "Local test file",
            "search_used": "local override",
        }
    else:
        music_asset = search_openverse_audio(rng=rng)
        music = Path()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_video = OUTPUT_DIR / "short.mp4"
    output_metadata = OUTPUT_DIR / "metadata.json"

    with tempfile.TemporaryDirectory(prefix="youtube-short-") as temp_name:
        temporary = Path(temp_name)
        if args.footage_file:
            if not args.footage_file.is_file():
                raise ShortsError(f"Footage file does not exist: {args.footage_file}")
            footage = [args.footage_file] * CLIP_COUNT
            assets = [{
                "creator_name": "Local smoke test",
                "source_url": "https://www.pexels.com/",
                "search_used": selected["pexels_search"],
            }] * CLIP_COUNT
        else:
            api_key = os.environ.get("PEXELS_API_KEY", "").strip()
            if not api_key:
                raise ShortsError("PEXELS_API_KEY is required")
            assets = search_pexels_clips(selected["pexels_search"], api_key=api_key, rng=rng)
            footage = []
            for index, asset in enumerate(assets, start=1):
                clip = temporary / f"pexels-{index}.mp4"
                download_file(asset["download_url"], clip)
                footage.append(clip)

        if not args.music_file:
            music = temporary / "openverse-music.mp3"
            download_audio(music_asset["download_url"], music)

        subtitles_file = temporary / "captions.ass"
        subtitles_file.write_text(
            build_ass_subtitles(selected, channel_name), encoding="utf-8", newline="\n"
        )
        run_ffmpeg(footage, music, subtitles_file, output_video)

    metadata = build_metadata(
        selected,
        creator_name=assets[0]["creator_name"],
        source_url=assets[0]["source_url"],
        channel_name=channel_name,
        privacy_status=args.privacy,
        music_name=music_asset["title"],
        music_creator=music_asset["creator"],
        music_source_url=music_asset["source_url"],
        music_license=music_asset["license"],
    )
    metadata["hook"] = make_hook(selected)
    metadata["pexels_search_used"] = sorted({asset["search_used"] for asset in assets})
    metadata["pexels_assets"] = [
        {"creator": asset["creator_name"], "source_url": asset["source_url"]}
        for asset in assets
    ]
    footage_credits = "\n".join(
        f"Footage {index}: {asset['creator_name']} on Pexels: {asset['source_url']}"
        for index, asset in enumerate(assets, start=1)
    )
    metadata["description"] = metadata["description"].replace(
        f"Footage by {assets[0]['creator_name']} on Pexels: {assets[0]['source_url']}",
        footage_credits,
    )
    metadata["music_search_used"] = music_asset["search_used"]
    write_metadata(metadata, output_metadata)
    if state_changed:
        save_state(state)
    print(f"Rendered {output_video.relative_to(ROOT)}")
    print(f"Metadata {output_metadata.relative_to(ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except ShortsError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
