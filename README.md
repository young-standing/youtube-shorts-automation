# GitHub-only motivational micro-story automation

Create and upload original English motivational micro-stories using only GitHub Actions, the free Pexels Videos API, CC0/Public Domain piano from Openverse, FFmpeg, and the official YouTube Data API.

The project does not require n8n, a VM, a database, paid rendering services, or paid AI APIs. Scheduled uploads are public; manual runs remain private by default.

## What it does

- Runs every day at 5:00 AM, 8:00 AM, 11:00 AM, and 2:00 PM in `Asia/Yangon`, with manual runs supported.
- Uses 36 curated, original 25–40 second micro-stories aimed at 18–30 year olds who feel behind in life.
- Rotates six content pillars and six narrator perspectives, with concrete tension, a believable turn, and a non-cliché payoff.
- Scores multiple hooks, validates story quality/duration, and rejects stories that are too similar to recent uploads.
- Permanently removes each story only after its YouTube upload succeeds, so uploaded scripts never repeat.
- Downloads one meaningful portrait clip per 2–4 second story beat through Pexels and credits every source.
- Downloads pillar-matched piano from Openverse, restricted to CC0 or Public Domain audio long enough for the story.
- Renders variable-length 1080×1920 H.264/AAC Shorts with beat-synchronized mobile captions and soft transitions.
- Saves analytics-ready metadata: pillar, hook type/text, perspective, topic, duration, title, script, ending concept, and visual searches.
- Uploads through the official YouTube Data API using resumable upload and retries.
- Saves two-day debugging artifacts and persists rich anti-repetition history safely.

The established schedule, secrets, OAuth flow, YouTube uploader, Pexels/Openverse integrations, public/private behavior, and success-only consumption logic are preserved. The project does not add a paid API or claim fictional stories are factual accounts of real people.

## Start here

Follow [SETUP.md](SETUP.md) from beginning to end and configure the required GitHub Secrets and `CHANNEL_NAME` repository variable. Openverse credentials are free and keep scheduled searches within authenticated rate limits.

Run local feature tests with:

```bash
pip install -r requirements.txt
pytest -q
python -m scripts.preview_stories --count 3
```

No real YouTube upload is performed by the tests.
