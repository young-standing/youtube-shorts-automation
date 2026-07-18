# GitHub-only YouTube Shorts automation

Create and upload one original English motivational YouTube Short every day using only GitHub Actions, the free Pexels Videos API, FFmpeg, repository-supplied royalty-free music, and the official YouTube Data API.

The project does not require n8n, a VM, a database, paid rendering services, or paid AI APIs. Uploads are private by default.

## What it does

- Runs daily at 7:07 PM in `Asia/Yangon`, with manual runs supported.
- Rotates through 102 original quotes without repeating the current cycle.
- Downloads suitable portrait footage through the official Pexels Videos API.
- Randomly selects any `.mp3` file placed in `music/`.
- Renders a 20-second 1080×1920 H.264/AAC Short with FFmpeg.
- Adds a safely wrapped quote in bundled Poppins SemiBold, a readable dark text box, and the repository-configured channel name.
- Uploads through the official YouTube Data API using resumable upload and retries.
- Saves two-day debugging artifacts and persists quote usage safely.

## Start here

Follow [SETUP.md](SETUP.md) from beginning to end. Before the first run, add at least one properly licensed MP3 file under `music/` and configure the required GitHub Secrets and `CHANNEL_NAME` repository variable.

Run local feature tests with:

```bash
pip install -r requirements.txt
pytest -q
```

No real YouTube upload is performed by the tests.
