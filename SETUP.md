# Reddit idol Shorts setup

This guide configures `.github/workflows/create-short.yml` to create 55–65 second K-pop idol fact Shorts. Reddit supplies discussion leads and hosted clips; Piper creates narration; Openverse supplies CC0/Public Domain music; YouTube Data API performs the upload.

Do not commit client secrets, refresh tokens, Reddit credentials, or `client_secret.json`.

## 1. Reddit needs no credentials

Do not create a Reddit application and do not add Reddit client secrets. The source layer uses this fallback chain:

1. Public Reddit search JSON.
2. Reddit RSS search.
3. Old Reddit HTML search cards.
4. A public Reddit archive carrying Reddit submission metadata.

All selected source links still point to the original Reddit posts. The archive is transport fallback only. The workflow retries temporary 429 and server errors, identifies itself with a user agent, and skips one failed subreddit while continuing with the others.

Optionally add a repository variable named `REDDIT_USER_AGENT`, such as `github:youtube-shorts-automation:v1.0 (by /u/your-name)`. A built-in identifying value is used when the variable is blank.

## 2. Configure Openverse music

Register a free Openverse API client and add:

| Secret | Value |
|---|---|
| `OPENVERSE_CLIENT_ID` | Openverse client ID |
| `OPENVERSE_CLIENT_SECRET` | Openverse client secret |

The renderer searches for upbeat instrumental music, accepts only CC0 or Public Domain entries long enough for the Short, ducks the track under narration, and records attribution in `output/metadata.json` and the YouTube description.

## 3. Configure YouTube OAuth

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project and enable **YouTube Data API v3**.
3. Configure the OAuth consent screen and add your Google account as a test user if required.
4. Create a **Desktop app** OAuth client. A service account cannot upload to a normal YouTube channel.
5. Download the credentials as `client_secret.json` in the repository root on your computer.
6. Create a local virtual environment and run the token helper.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\get_refresh_token.py
```

Copy the three printed values into GitHub secrets:

| Secret | Value |
|---|---|
| `YOUTUBE_CLIENT_ID` | Value printed by the helper |
| `YOUTUBE_CLIENT_SECRET` | Value printed by the helper |
| `YOUTUBE_REFRESH_TOKEN` | Value printed by the helper |

Never paste the helper output into an issue or workflow log. Delete `client_secret.json` when it is no longer needed. OAuth apps left in Google's External **Testing** state can issue refresh tokens that expire after seven days; move the app to Production and satisfy Google's requirements before depending on unattended uploads.

## 4. Add the channel variable

Under **Settings > Secrets and variables > Actions > Variables**, add:

| Variable | Value |
|---|---|
| `CHANNEL_NAME` | Short channel brand name used in metadata |

## 5. Choose idols and subreddits

Edit `data/idols.json` to control the scheduled rotation. The default manual and scheduled subreddit list is:

```text
kpop,kpopthoughts,kpop_uncensored
```

A manual workflow run can override the idol and subreddit list. The source layer automatically adds the selected idol's relevant fan subreddit from its built-in map, then searches the configured general subreddits. It rejects malformed subreddit names and filters NSFW, deleted, stickied, speculative, rumor, leak, and question posts. It requires enough distinct high-engagement posts and Reddit-hosted clips; a run fails clearly instead of filling the Short with unrelated material.

Reddit post titles become attributed discussion summaries. They are not independent factual verification. Review each source URL in `output/metadata.json` before publication.

## 6. Run the first public upload

1. Push the branch containing this implementation to GitHub.
2. Open **Actions > Create Reddit idol fact Short > Run workflow**.
3. Enter a popular idol such as `Jungkook` for the first run.
4. Keep **fact count** at `4`.
5. Run the workflow.

The workflow installs FFmpeg, downloads and caches the Piper `en_US-joe-medium` voice, validates configuration, discovers Reddit sources, renders the Short, uploads it directly as public, and stores `output/short.mp4` plus `output/metadata.json` as a two-day artifact.

Check that the result has:

- 1080×1920 dimensions and 55–65 second duration
- three or four distinct facts
- hot-pink one-word captions centered around the lower-middle safe area
- readable yellow/red emphasis
- a visual change about every 4–5 seconds
- blurred fill rather than black bars
- clear narration with low background music
- fact and clip URLs in metadata

## 7. Public-upload responsibility

Every successful manual or scheduled run uploads directly as `public`. Reddit hosting does not itself grant reuse permission. Keep source attribution, avoid misleading claims, and ensure the chosen footage and factual statements comply with copyright, YouTube policy, and applicable permissions. Generated metadata records the original Reddit fact and clip URLs for audit.

## 8. State and concurrent runs

After a successful upload, GitHub Actions persists `data/reddit_state.json`. It records used fact URLs, used clip URLs, and recent idols so the next run does not repeat the same material. Concurrent updates are merged with `scripts/merge_reddit_state.py` and retried up to three times. A render or upload failure does not persist the new source choices.

Under **Settings > Actions > General > Workflow permissions**, allow **Read and write permissions** so the workflow can update this state file.

## 9. Local validation

Install FFmpeg and FFprobe, then run:

```powershell
pip install -r requirements.txt
pytest -q
python -m scripts.validate_config --mode reddit-idol
```

A full local render also needs the Reddit and Openverse environment variables plus the cached Piper model. Tests use synthetic post data and do not call Reddit, download media, or upload to YouTube.

## Scheduling and cost

The four cron expressions correspond to 05:00, 08:00, 11:00, and 14:00 in Myanmar. GitHub schedules can be delayed during high load. Each successful one-minute FFmpeg render uploads directly as public and can consume meaningful private-repository Actions minutes and artifact storage.

Review [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) and reduce the schedule if usage is too high.
