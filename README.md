# MLT Pilot

Python module for AI-driven video editing via [MLT](https://www.mltframework.org/) (Media Lovin Toolkit).

MLT Pilot enables AI agents to create, modify, and render MLT video projects
programmatically. It generates standard `.mlt` XML files compatible with
[Flowblade](https://jliljebl.github.io/flowblade/), [Shotcut](https://shotcut.org/), and `melt-7`.

## Features (MVP)

- Multi-track timeline construction
- Media management with relative paths
- MLT XML generation and parsing (round-trip)
- Filter and transition application
- Subtitle import (SRT/ASS) and creation
- Audio level control, fade in/out, background music
- Rendering via `melt-7` (H.264, WebM, ProRes)
- Snapshot-based project versioning
- Editor interoperability (Flowblade, Shotcut, melt)

## Installation

```bash
pip install -e .
```

For rendering, install melt:

```bash
# Fedora
sudo dnf install mlt

# Ubuntu/Debian
sudo apt install melt
```

## Quick Start

```python
from mlt_pilot import MLTProject

# Create project
project = MLTProject(profile="atsc_1080p_30", title="My Video")

# Add media files
project.add_media("videos/intro.mp4")
project.add_media("videos/main.mp4")
project.add_media("audio/music.mp3")

# Build timeline
project.add_clip(track=0, media="intro.mp4", start=0, duration="5s")
project.add_clip(track=0, media="main.mp4", start="5s", duration="20s")

# Add background music
project.add_background_music("audio/music.mp3", volume=0.3, fade_in="2s", fade_out="3s")

# Add subtitles
project.add_subtitle_line(text="Welcome!", start="0s", duration="3s")

# Apply a filter
project.add_filter(track=0, filter="brightness", brightness=0.1)

# Add a transition
project.add_transition(track_a=0, track_b=1, start="3s", duration="2s", type="dissolve")

# Inspect the project
print(project.describe())

# Export as .mlt (open in Flowblade, Shotcut, etc.)
project.export_mlt("my_project.mlt")

# Render to video (requires melt-7)
# project.render("output.mp4")
```

## Architecture

**XML-first approach** — no Python MLT bindings required. The module manipulates
MLT XML directly using `xml.etree.ElementTree` (stdlib). Rendering is done via
`melt-7` subprocess. Zero runtime dependencies.

```
src/mlt_pilot/
├── __init__.py       # Public API exports
├── project.py        # MLTProject — main entry point
├── xml_builder.py    # MLTProjectData → .mlt XML
├── xml_parser.py     # .mlt XML → MLTProjectData
├── models.py         # Data models (Clip, Track, Filter, etc.)
├── profiles.py       # Video profile definitions
├── effects.py        # Filter/transition catalog
├── audio.py          # Audio management
├── subtitles.py      # SRT/ASS subtitle handling
├── export.py         # Render via melt-7
└── utils.py          # Timecodes, frames, paths, IDs
```

## Workflow

The intended workflow is iterative:

1. Agent creates/modifies the project programmatically
2. Human opens the `.mlt` file in their preferred editor (Flowblade, Shotcut)
3. Human makes manual adjustments
4. Agent loads the modified project and continues working

## Profiles

| Name | Resolution | FPS |
|------|-----------|-----|
| `atsc_1080p_30` | 1920×1080 | 30 |
| `atsc_1080p_25` | 1920×1080 | 25 |
| `atsc_1080p_24` | 1920×1080 | 24 |
| `atsc_720p_30` | 1280×720 | 30 |
| `dv_ntsc` | 720×480 | 29.97 |
| `dv_pal` | 720×576 | 25 |

## Render Presets

| Preset | Codec | Quality |
|--------|-------|---------|
| `youtube_1080p` | H.264 | CRF 20, slow |
| `web_webm` | VP9 | CRF 30 |
| `archive_prores` | ProRes | Lossless |
| `preview` | H.264 | CRF 28, ultrafast |

## License

MIT
