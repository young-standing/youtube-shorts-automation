#!/usr/bin/env python3
"""Validate GitHub Shorts configuration before network or rendering work."""

from __future__ import annotations

import argparse
import os
import shutil

from scripts.reddit_source import load_idols, parse_subreddits
from scripts.render_idol_short import OUTPUT_DIR, STATE_PATH, load_state
from scripts.render_short import QUOTES_PATH, ShortsError, load_quotes, load_state as load_legacy_state
from scripts.render_short import validate_channel_name


def require_environment(names: list[str]) -> list[str]:
    return [name for name in names if not os.environ.get(name, "").strip()]


def check_tools() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise ShortsError("ffmpeg and ffprobe must both be installed")


def check_output_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    probe = OUTPUT_DIR / ".write-test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()


def validate_reddit_idol(require_youtube: bool) -> None:
    required = [
        "OPENVERSE_CLIENT_ID",
        "OPENVERSE_CLIENT_SECRET",
        "CHANNEL_NAME",
    ]
    if require_youtube:
        required.extend(["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"])
    missing = require_environment(required)
    if missing:
        raise ShortsError("Missing required configuration: " + ", ".join(missing))
    validate_channel_name(os.environ["CHANNEL_NAME"])
    parse_subreddits(
        os.environ.get("INPUT_SUBREDDITS", "kpop,kpopthoughts,kpop_uncensored")
    )
    idols = load_idols()
    load_state(STATE_PATH)
    check_tools()
    check_output_directory()
    print(
        f"Configuration is valid; {len(idols)} idols are available for Reddit rotation. "
        "Facts and footage will come from Reddit; music will use CC0/Public Domain Openverse audio."
    )


def validate_legacy(require_youtube: bool) -> None:
    required = ["PEXELS_API_KEY", "OPENVERSE_CLIENT_ID", "OPENVERSE_CLIENT_SECRET", "CHANNEL_NAME"]
    if require_youtube:
        required.extend(["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"])
    missing = require_environment(required)
    if missing:
        raise ShortsError("Missing required configuration: " + ", ".join(missing))
    validate_channel_name(os.environ["CHANNEL_NAME"])
    check_tools()
    quotes = load_quotes(QUOTES_PATH)
    load_legacy_state()
    check_output_directory()
    print(f"Legacy configuration is valid; {len(quotes)} quote(s) remain.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("reddit-idol", "legacy"), default="legacy")
    parser.add_argument("--require-youtube", action="store_true")
    args = parser.parse_args()
    if args.mode == "reddit-idol":
        validate_reddit_idol(args.require_youtube)
    else:
        validate_legacy(args.require_youtube)


if __name__ == "__main__":
    try:
        main()
    except (ShortsError, RuntimeError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
