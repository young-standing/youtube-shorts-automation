# GitHub-only YouTube Shorts automation

Create and upload original English motivational YouTube Shorts using only GitHub Actions, the free Pexels Videos API, CC0/Public Domain piano from Openverse, FFmpeg, and the official YouTube Data API.

The project does not require n8n, a VM, a database, paid rendering services, or paid AI APIs. Scheduled uploads are public; manual runs remain private by default.

## What it does

- Runs every day at 7:07 AM, 1:07 PM, and 7:07 PM in `Asia/Yangon`, with manual runs supported.
- Starts with 500 original motivation/life scripts, each combining a quote with a short actionable insight.
- Permanently removes each script from the available catalog only after its YouTube upload succeeds, so uploaded text never repeats.
- Downloads suitable portrait footage through the official Pexels Videos API.
- Downloads a sad or emotional piano track from Openverse, restricted to CC0 or Public Domain audio at least 20 seconds long.
- Renders a 20-second 1080×1920 H.264/AAC Short with FFmpeg.
- Adds a safely wrapped quote in bundled Poppins SemiBold, a readable dark text box, and the repository-configured channel name.
- Uploads through the official YouTube Data API using resumable upload and retries.
- Saves two-day debugging artifacts and persists quote usage safely.

## Start here

Follow [SETUP.md](SETUP.md) from beginning to end and configure the required GitHub Secrets and `CHANNEL_NAME` repository variable. Openverse credentials are free and keep scheduled searches within authenticated rate limits.

Run local feature tests with:

```bash
pip install -r requirements.txt
pytest -q
```

No real YouTube upload is performed by the tests.
