# Empire Histories - Vox-Style Documentary Automation

Automated YouTube documentary channel producing Vox-style historical documentaries using GitHub Actions.

## Features

- **Fully Automated Pipeline**: Topic → Research → Script → Visuals → Video → YouTube
- **Vox-Style Editing**: Animated infographics, maps, timelines, motion graphics
- **Copyright-Safe Content**: Public domain historical sources
- **Global Audience**: English narration, worldwide topics
- **Weekly Production**: One 8–12 minute documentary per week

## Tech Stack

- **Python 3.11** - Core automation
- **FFmpeg** - Video rendering and effects
- **MoviePy** - Video editing
- **Pillow/PIL** - Image processing
- **Matplotlib** - Charts and visualizations
- **Wikipedia API** - Research source
- **TTS (OpenAI/ElevenLabs)** - Narration
- **GitHub Actions** - CI/CD pipeline
- **YouTube Data API** - Upload automation

## Project Structure

```
lofi-documentary/
├── .github/
│   └── workflows/
│       └── generate-documentary.yml
├── src/
│   ├── research/
│   │   ├── topic_selector.py
│   │   ├── wikipedia_researcher.py
│   │   └── fact_checker.py
│   ├── content/
│   │   ├── script_generator.py
│   │   └── metadata_generator.py
│   ├── assets/
│   │   ├── image_collector.py
│   │   ├── video_collector.py
│   │   └── music_generator.py
│   ├── visuals/
│   │   ├── infographic_generator.py
│   │   ├── map_animator.py
│   │   ├── timeline_generator.py
│   │   └── image_processor.py
│   ├── audio/
│   │   ├── tts_generator.py
│   │   └── audio_mixer.py
│   ├── video/
│   │   ├── video_assembler.py
│   │   └── effects.py
│   └── upload/
│       ├── youtube_uploader.py
│       └── thumbnail_generator.py
├── templates/
│   ├── visual_templates/
│   └── audio_templates/
├── tests/
├── config/
│   ├── settings.yaml
│   └── topics.json
├── output/
├── requirements.txt
└── README.md
```

## Setup

### Prerequisites

1. Python 3.11+
2. FFmpeg installed on system
3. GitHub account
4. YouTube channel with API access

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd lofi-documentary

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### YouTube API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials
5. Get refresh token for automation

### GitHub Secrets

Add these secrets to your repository:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `OPENAI_API_KEY` (optional, for TTS and script enhancement)

## Usage

### Manual Trigger

Go to Actions → Generate Documentary → Run workflow

Enter topic or leave blank for random selection.

### Scheduled Runs

Automatically runs every Monday at 6 AM UTC.

### Local Testing

```bash
# Generate a documentary
python main.py --topic "Rise and Fall of the Roman Empire"

# Test specific component
python -m src.research.wikipedia_researcher --topic "Mongol Empire"
```

## Topics Coverage

Initial series focus on **"Empire Histories"**:

- Ancient empires (Roman, Persian, Mongol, etc.)
- Rise and fall narratives
- Geographic changes over time
- Cultural and technological impacts
- Key historical figures

## Video Format

- **Duration**: 8–12 minutes
- **Resolution**: 1920x1080 (1080p)
- **FPS**: 30
- **Format**: MP4 (H.264 + AAC)
- **Style**: Vox-style documentary

## Monetization Path

1. **Phase 1** (0–6 months): Build content library, establish audience
2. **Phase 2** (6–12 months): Apply for YouTube Partner Program
3. **Phase 3** (12+ months): Expand to multiple series, sponsorships

## License

MIT License - See LICENSE file for details

## Contributing

This is a personal automation project. Contributions welcome via issues and pull requests.

## Disclaimer

This project uses public domain and properly licensed content only. All historical footage and images are sourced from copyright-safe archives. AI-generated content is used responsibly for educational purposes.
