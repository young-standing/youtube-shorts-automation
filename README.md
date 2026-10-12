# Reddit K-pop idol facts Shorts automation

This repository creates 55–65 second English YouTube Shorts about K-pop idols using Reddit for both discussion leads and hosted video clips. GitHub Actions performs discovery, narration, editing, direct public upload, and source-rotation persistence.

## Output format

The renderer is modeled on the supplied 1080×1920 reference:

- 1080×1920 H.264/AAC at 30 fps
- three or four idol facts per Short
- one-word-at-a-time hot-pink Poppins captions with black outline
- yellow or red emphasis for numbers and hook words
- a new visual treatment roughly every 4.6 seconds
- blurred vertical fill behind clips that do not match 9:16
- local Piper narration and ducked CC0/Public Domain music
- 55–65 second target duration

## Source policy

- Facts are selected from high-signal Reddit post titles after rejecting NSFW, deleted, stickied, question, rumor, leak, sasaeng, and unconfirmed posts.
- Reddit popularity is a lead, not independent verification. Generated metadata records every fact URL and marks the facts for human review.
- Video downloads are restricted to Reddit-hosted HTTPS media and capped at 150 MB per clip.
- Reddit hosting is not a copyright license. The workflow now publishes directly as public at the user's instruction, so the operator remains responsible for permission, attribution, and YouTube policy compliance.
- Scheduled and manual uploads are always `public`.

## GitHub Actions

The workflow at `.github/workflows/create-short.yml` runs at 05:00, 08:00, 11:00, and 14:00 Myanmar time and can also be run manually. Manual inputs allow an idol name, three or four facts, a subreddit list, privacy status, and a clip-rights confirmation.

Reddit access is credential-free. The source layer tries public Reddit JSON first, then RSS and Old Reddit HTML, and finally a public Reddit archive when Reddit rate-limits GitHub runners.

Required repository secrets:

- `OPENVERSE_CLIENT_ID`
- `OPENVERSE_CLIENT_SECRET`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Required repository variable:

- `CHANNEL_NAME`

Optional repository variable:

- `REDDIT_USER_AGENT` (defaults to this project's identifying user agent)

See `SETUP.md` for credential and first-run instructions.

## Main files

- `scripts/reddit_source.py` — credential-free Reddit web fetching, fallback parsing, filtering, ranking, and hosted-video extraction
- `scripts/render_idol_short.py` — narration, one-word captions, rapid-cut blurred-fill render, metadata, and rights gate
- `scripts/merge_reddit_state.py` — conflict-safe source rotation persistence
- `data/idols.json` — scheduled idol rotation
- `data/reddit_state.json` — previously used fact URLs, clip URLs, and idols

The previous motivational quote renderer remains in `scripts/render_short.py` for legacy local use, but GitHub Actions now calls `scripts.render_idol_short`.

## Validation

```bash
pip install -r requirements.txt
pytest -q
python -m scripts.validate_config --mode reddit-idol --require-youtube
```

Tests do not contact Reddit or upload to YouTube.
