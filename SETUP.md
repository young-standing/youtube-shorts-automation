# GitHub-only YouTube Shorts setup

This guide configures the existing scheduled workflow in `.github/workflows/create-short.yml`. It renders an 8–14 second cinematic English motivational quote entirely on GitHub's `ubuntu-latest` runner and uploads it with the official YouTube Data API. Scheduled uploads are public; manual uploads remain private by default.

## What you need

- A GitHub repository with Actions enabled.
- A YouTube channel on the Google account you will authorize.
- A free Pexels API key.
- Python 3.12 for the one-time local OAuth helper.
- Internet access to retrieve CC0/Public Domain sad-piano audio through Openverse.

Do not place API keys, OAuth credentials, tokens, or `client_secret.json` in the repository.

## 1. Get a free Pexels API key

1. Create or sign in to a Pexels account.
2. Open the [Pexels API page](https://www.pexels.com/api/).
3. Request an API key and accept the API terms.
4. Keep the key available for the GitHub Secret step below.

The renderer uses the official `GET /v1/videos/search` endpoint with portrait and medium-size filters. It records the Pexels creator and source page in every YouTube description.

## 2. Create the Google Cloud OAuth client

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project or select a dedicated project for this automation.
3. Open **APIs & Services > Library**.
4. Search for **YouTube Data API v3** and enable it.
5. Configure **Google Auth Platform / OAuth consent screen**.
6. If the audience is External and the app is in Testing, add your own Google account as a test user.
7. Open **Clients** (or **Credentials > Create credentials > OAuth client ID**).
8. Choose **Desktop app**. Do not choose a service account; YouTube uploads require user OAuth authorization.
9. Download the JSON credentials file and save it in the repository root locally as `client_secret.json`.

`client_secret.json` is ignored by Git and must never be committed.

### Important seven-day Testing limitation

For an External OAuth consent screen whose publishing status remains **Testing**, Google normally issues a refresh token that expires in seven days when non-basic scopes such as YouTube upload are requested. After it expires, scheduled uploads fail until you run the helper again. Move the OAuth app to Production and complete any Google requirements that apply to your app before relying on long-term unattended uploads. See [Google OAuth refresh-token expiration](https://developers.google.com/identity/protocols/oauth2#expiration).

## 3. Generate the refresh token locally

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/get_refresh_token.py
```

Windows PowerShell activation is:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\get_refresh_token.py
```

Your browser opens Google's consent page. Sign in with the account that owns the target YouTube channel. The helper requests only `https://www.googleapis.com/auth/youtube.upload` and requests offline access. It prints:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Copy them directly to GitHub Secrets. The helper does not save the refresh token. Do not paste its terminal output into an issue, commit, screenshot, or workflow log. Delete the local `client_secret.json` after setup if you no longer need it.

## 4. Add GitHub Secrets and the channel variable

On GitHub, open **Settings > Secrets and variables > Actions**.

Under **Secrets**, create these six repository secrets:

| Secret | Value |
|---|---|
| `PEXELS_API_KEY` | Pexels API key |
| `OPENVERSE_CLIENT_ID` | Client ID from free Openverse API registration |
| `OPENVERSE_CLIENT_SECRET` | Client secret from free Openverse API registration |
| `YOUTUBE_CLIENT_ID` | Value printed by the helper |
| `YOUTUBE_CLIENT_SECRET` | Value printed by the helper |
| `YOUTUBE_REFRESH_TOKEN` | Value printed by the helper |

Under **Variables**, add:

| Variable | Value |
|---|---|
| `CHANNEL_NAME` | The short channel name displayed near the bottom of each video |

Secrets are passed only as environment variables. Upload scripts never print their values.

## 5. Automatic sad-piano music

No repository MP3 is required. Every run authenticates with the free Openverse credentials, searches for pillar-matched emotional piano, accepts only CC0/Public Domain results long enough for the selected story, downloads one result, and records its title, creator, license, and source URL in the generated metadata and YouTube description.

## 6. Push the project and check Actions permissions

Commit and push the implementation, quotes, and state to the default branch. The scheduled event only runs workflows that exist on the default branch.

The workflow needs permission to update `data/state.json` and consume entries from `data/stories.json`. Under **Settings > Actions > General > Workflow permissions**, allow **Read and write permissions** if repository or organization policy does not already permit the workflow's declared `contents: write` permission.

After a successful YouTube upload, the state update uses a temporary branch, removes the uploaded script from the available catalog, merges the rendered state with the latest remote state, and retries conflicts three times. Failed renders or uploads do not consume a script. A persistence failure is non-fatal and does not undo a completed upload.

## 7. Run the first private manual test

1. Open the repository's **Actions** tab.
2. Select **Create scheduled YouTube impact quotes**.
3. Choose **Run workflow**.
4. Leave the quote and Pexels search fields empty for a catalog-driven test.
5. Keep **privacy status** set to `private`.
6. Run the workflow.

You may optionally enter an original English quote and a Pexels search phrase. Manual input is passed through environment variables rather than inserted into shell commands.

For a deterministic non-consuming test, enter a `story_id` such as `s001`. When the run completes, open YouTube Studio and verify that the video is private, vertical, 8–14 seconds, correctly cropped, readable, visually coherent, and contains the Openverse/Pexels source details.

## 8. Inspect logs and artifacts

Open the workflow run and expand individual steps for clear validation, Pexels, FFmpeg, state, and YouTube errors. OAuth secret values are not printed.

The **Artifacts** section contains `output/short.mp4` and `output/metadata.json` even when the YouTube upload fails, as long as rendering succeeded. Artifacts are retained for two days to limit storage usage. Generated MP4 files are ignored by Git and are never committed.

## 9. Scheduled public uploads

The 5:00 AM, 8:00 AM, 11:00 AM, and 2:00 PM schedules upload as `public`. Manual runs still default to `private`, but offer `unlisted` and `public` choices. Keep reviewing footage, music licenses, metadata, and channel-policy compliance because scheduled public uploads do not include a human approval step.

New or unaudited Google API projects can have API uploads restricted to private visibility regardless of the requested setting. Follow Google's audit and verification requirements rather than attempting to bypass the restriction.

## Schedule and story rotation

GitHub runs the workflow every day at `05:00`, `08:00`, `11:00`, and `14:00` in `Asia/Yangon`. The cron expressions are stored in UTC, so their `:30` minute values become exact-hour runs in Myanmar time. GitHub schedules can still be delayed during high load.

`data/stories.json` initially contained 500 original, quality-checked micro-stories across transformation, failure/comeback, relatable pain, future-self, disappear/rebuild, and hard-truth-through-story. Every story stores hook candidates, concrete beats, matching visual searches, titles, pillar, topic, perspective, ending concept, and music mood. At four uploads per day the initial catalog lasts 125 days. A successfully uploaded entry is permanently removed instead of being recycled, so the live count decreases over time. When the catalog is empty, rendering stops with a clear refill error. Manual quotes and explicit `story_id` preview runs do not consume a catalog entry. The older `data/quotes.json` remains in the repository as a legacy catalog but scheduled runs no longer select from it.

Narration is generated locally on the GitHub runner with Piper and the `en_US-joe-medium` voice. Piper's engine is GPL-3.0 and that voice's model card identifies its dataset as CC0; no API key or paid TTS account is required. The workflow caches the model after its first download. Each phrase receives a different pace, energy, and emphasis profile. FFmpeg targets approximately -14 LUFS and automatically ducks the Openverse piano beneath speech. Voice name, source, license, and narration duration are recorded in each video's metadata.

## GitHub Actions minutes

Standard GitHub-hosted runners are free for public repositories. Private repositories consume the Actions minutes and storage included with the repository owner's plan; usage beyond the allowance may be billed or blocked. Four daily FFmpeg renders can consume a meaningful portion of a private repository's allowance. Review **Settings > Billing and licensing** regularly. See [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Copyright and repetitive-content considerations

- Pexels access does not transfer rights to trademarks, recognizable people, music, or third-party material depicted in footage. Review the asset and Pexels license before publishing.
- Openverse indexes third-party media. The workflow filters for CC0/Public Domain audio and records the source, but periodically review source links and YouTube claims.
- Do not copy famous quotations or imply endorsement by a real person.
- Automated template videos may be considered repetitive or low-value content. Meaningful human review, distinct creative editing, original commentary, and genuine variation are important, especially for monetization.
- Review every artifact and metadata file before making uploads public. Automation does not replace compliance with YouTube policies, copyright law, or license terms.

## Local checks

Run unit tests without uploading anything:

```bash
pytest -q tests/test_youtube_shorts.py
```

The test suite covers permanent script consumption, safe text wrapping, metadata/title generation, Openverse filtering, and state merging. The upload script is never invoked by these tests.
