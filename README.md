# GitHub-only cinematic motivational quote automation

Create and upload original, concise English motivational impact quotes using only GitHub Actions, the free Pexels Videos API, CC0/Public Domain energetic music from Openverse, FFmpeg, and the official YouTube Data API.

The project does not require n8n, a VM, a database, paid rendering services, or paid AI APIs. Scheduled uploads are public; manual runs remain private by default.

## What it does

- Runs every day at 5:00 AM, 8:00 AM, 11:00 AM, and 2:00 PM in `Asia/Yangon`, with manual runs supported.
- Selects from an original motivational quote bank and renders each quote as a unique 8–14 second Short.
- Rotates discipline, success, healing, confidence, growth, and consistency themes.
- Permanently removes each quote only after its YouTube upload succeeds, so uploaded scripts never repeat.
- Uses one coherent portrait clip per Short, with monochrome contrast and phrase-synchronized punch-ins instead of unrelated scene changes.
- Creates English narration locally with Piper's `en_US-joe-medium` CC0 voice, varying pace, energy, and emphasis phrase by phrase.
- Downloads uplifting, epic, or cinematic motivational music from Openverse, restricted to CC0 or Public Domain audio, then ducks it under narration.
- Renders 1080×1920 H.264/AAC Shorts with minimal centered white captions, subtle `ORDERLESS` branding, and a final audio target near -14 LUFS.
- Saves analytics-ready metadata including theme, duration, title, script, music source, and visual searches.
- Uploads through the official YouTube Data API using resumable upload and retries.
- Saves two-day debugging artifacts and persists rich anti-repetition history safely.

The established schedule, secrets, OAuth flow, YouTube uploader, Pexels/Openverse integrations, public/private behavior, and success-only consumption logic are preserved. The project does not add a paid API.

## Start here

Follow [SETUP.md](SETUP.md) from beginning to end and configure the required GitHub Secrets and `CHANNEL_NAME` repository variable. Openverse credentials are free and keep scheduled searches within authenticated rate limits.

Run local feature tests with:

```bash
pip install -r requirements.txt
pytest -q
python -m scripts.preview_stories --count 3
```

No real YouTube upload is performed by the tests.
