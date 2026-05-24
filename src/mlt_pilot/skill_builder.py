"""Skill builder: generate and install opencode SKILL.md for mlt-pilot."""

from __future__ import annotations

import shutil
from pathlib import Path
from string import Template

from . import __version__

DEFAULT_OUTPUT_DIR = "dist/mlt-pilot-skill"

SKILL_TEMPLATE = Template('''---
name: mlt-pilot
description: MLT video editing commands for AI-driven non-linear editing via CLI.
version: $version
---

# Skill: MLT Pilot — Video Editing CLI

AI agent skill for creating and manipulating MLT video projects using the `mlt-pilot` CLI.

## 1. Quick Reference

| Command | Purpose |
|---------|---------|
| `mlt-pilot create <file> --profile <name> --title <str>` | Create new project |
| `mlt-pilot add-media <file> --media <path> [--alias <name>]` | Register media file |
| `mlt-pilot list-media <file>` | List registered media |
| `mlt-pilot add-clip <file> --track <int> --media <alias> --start <time> --duration <time>` | Place clip on track |
| `mlt-pilot insert-clip <file> --track <int> --position <int> --media <alias> [--duration <time>]` | Insert clip, shifting others |
| `mlt-pilot remove-clip <file> --track <int> --position <int>` | Remove clip (replaced by blank) |
| `mlt-pilot add-filter <file> --track <int> --filter <name> [key=val ...]` | Add filter to track |
| `mlt-pilot add-transition <file> --track-a <int> --track-b <int> --start <time> --duration <time> --type <str>` | Add transition |
| `mlt-pilot add-subtitle <file> --text <str> --start <time> --duration <time> [--style <str>]` | Add subtitle line |
| `mlt-pilot add-subtitles-file <file> --file <path>` | Import SRT/ASS subtitles |
| `mlt-pilot add-bgm <file> --file <path> [--volume <float>] [--fade-in <time>] [--fade-out <time>]` | Add background music |
| `mlt-pilot set-audio <file> --track <int> --gain <float>` | Set track audio level |
| `mlt-pilot render <file> --output <path> [--preset <name>]` | Render to video |
| `mlt-pilot info <file>` | Show project metadata (JSON) |
| `mlt-pilot describe <file>` | Human-readable timeline |
| `mlt-pilot list-profiles` | List available profiles |
| `mlt-pilot list-filters [--category <str>]` | List available filters |
| `mlt-pilot list-transitions` | List available transitions |

## 2. Time Format

Time values accept multiple formats:
- Frames: `300` (integer)
- Seconds: `10s` or `10.5s`
- Timecode: `00:01:30.000` (HH:MM:SS.mmm)

## 3. Available Profiles

$profiles

## 4. Available Filters

$filters

## 5. Available Transitions

$transitions

## 6. Render Presets

$presets

## 7. Workflow: Creating a Video Project

### 7.1 Basic Project

```bash
# Create project
mlt-pilot create my_video.mlt --profile atsc_1080p_30 --title "My Video"

# Add media files
mlt-pilot add-media my_video.mlt --media /path/to/clip1.mp4 --alias clip1
mlt-pilot add-media my_video.mlt --media /path/to/clip2.mp4 --alias clip2

# Build timeline
mlt-pilot add-clip my_video.mlt --track 0 --media clip1 --start 0 --duration 10s
mlt-pilot add-clip my_video.mlt --track 0 --media clip2 --start 10s --duration 10s

# Preview project structure
mlt-pilot describe my_video.mlt

# Render to video (requires melt-7)
mlt-pilot render my_video.mlt --output output.mp4 --preset youtube_1080p
```

### 7.2 Adding Effects

```bash
mlt-pilot add-filter my_video.mlt --track 0 --filter brightness brightness=0.2 contrast=1.5
mlt-pilot set-audio my_video.mlt --track 0 --gain 0.8
```

### 7.3 Adding Background Music

```bash
mlt-pilot add-bgm my_video.mlt --file /path/to/music.mp3 --volume 0.3 --fade-in 2s --fade-out 3s
```

### 7.4 Adding Subtitles

```bash
# Single line
mlt-pilot add-subtitle my_video.mlt --text "Hello World" --start 1s --duration 4s

# Import from file
mlt-pilot add-subtitles-file my_video.mlt --file subtitles.srt
```

### 7.5 Crossfade Transition

```bash
mlt-pilot add-clip my_video.mlt --track 1 --media clip2 --start 8s --duration 10s
mlt-pilot add-transition my_video.mlt --track-a 0 --track-b 1 --start 8s --duration 2s --type crossfade
```

## 8. Inspecting Projects

```bash
mlt-pilot info my_video.mlt
mlt-pilot describe my_video.mlt
mlt-pilot list-media my_video.mlt
```

## 9. Important Notes

- **Media paths**: Use absolute paths or paths relative to the project file location.
- **Track indexing**: Tracks are 0-indexed. The first `add-clip` to a track index auto-creates it.
- **Render requirement**: The `render` command requires `melt-7` (or `melt`) installed on the system.
- **Project files**: Operations modify the `.mlt` file in place.
- **Subtitles**: SRT and ASS formats are supported for import.
- **Filters**: Parameters are passed as `key=value` pairs after `--filter <name>`.
''')


def _build_profiles_table() -> str:
    """Generate the profiles section from live catalog."""
    from .profiles import PROFILES
    lines = []
    for name in sorted(PROFILES):
        p = PROFILES[name]
        lines.append(f"- `{name}`: {p.description} ({p.width}x{p.height} @ {p.fps}fps)")
    return "\n".join(lines)


def _build_filters_table() -> str:
    """Generate the filters section from live catalog."""
    from .effects import FILTERS
    lines = []
    for name in sorted(FILTERS):
        f = FILTERS[name]
        params = ", ".join(p.name for p in f.parameters) if f.parameters else "(none)"
        lines.append(f"- `{name}` ({f.category}): {f.display_name} — params: {params}")
    return "\n".join(lines)


def _build_transitions_table() -> str:
    """Generate the transitions section from live catalog."""
    from .effects import TRANSITIONS
    lines = []
    for name in sorted(TRANSITIONS):
        t = TRANSITIONS[name]
        lines.append(f"- `{name}`: {t.display_name} — {t.description}")
    return "\n".join(lines)


def _build_presets_table() -> str:
    """Generate the render presets section from live catalog."""
    from .export import RENDER_PRESETS
    lines = []
    for name in sorted(RENDER_PRESETS):
        p = RENDER_PRESETS[name]
        details = ", ".join(f"{k}={v}" for k, v in p.items())
        lines.append(f"- `{name}`: {details}")
    return "\n".join(lines)


def build_skill(output_dir: Path | None = None) -> Path:
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent.parent / DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    content = SKILL_TEMPLATE.substitute(
        version=__version__,
        profiles=_build_profiles_table(),
        filters=_build_filters_table(),
        transitions=_build_transitions_table(),
        presets=_build_presets_table(),
    )
    skill_path = output_dir / "SKILL.md"
    skill_path.write_text(content, encoding="utf-8")
    return output_dir


def install_skill(target_repo: Path, source_dir: Path | None = None) -> Path:
    if source_dir is None:
        source_dir = Path(__file__).resolve().parent.parent.parent / DEFAULT_OUTPUT_DIR
    skill_source = source_dir / "SKILL.md"
    if not skill_source.exists():
        raise FileNotFoundError(
            f"SKILL.md not found at {skill_source}. Run 'mlt-pilot skill build' first."
        )
    install_dir = target_repo.resolve() / ".opencode" / "skills" / "mlt-pilot"
    install_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, install_dir / item.name)
    return install_dir
