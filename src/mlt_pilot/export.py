"""Export MLT projects and render via melt-7 subprocess."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional


def check_melt_available() -> tuple[bool, str]:
    """
    Check if melt-7 (or melt) is available on the system.
    Returns: (available, path_or_error_message)
    """
    melt_cmd = shutil.which("melt-7") or shutil.which("melt")
    if melt_cmd:
        return (True, melt_cmd)
    return (False, "melt-7 (or melt) is not installed. Install via: sudo dnf install mlt (Fedora) or sudo apt install melt (Ubuntu)")


def get_melt_command() -> str:
    """Return the path to the melt command. Raises RuntimeError if not available."""
    available, path_or_msg = check_melt_available()
    if not available:
        raise RuntimeError(path_or_msg)
    return path_or_msg


def render(
    project_path: str | Path,
    output_path: str | Path,
    profile: Optional[str] = None,
    vcodec: str = "libx264",
    acodec: str = "aac",
    crf: int = 23,
    preset: str = "medium",
    audio_bitrate: str = "192k",
    additional_args: Optional[list[str]] = None,
    melt_cmd: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """
    Render an MLT project file to a video file using melt-7.

    Constructs:
        melt {profile_arg} {project_path} -consumer avformat:{output_path} \
            vcodec={vcodec} acodec={acodec} crf={crf} ...

    Auto-selects codecs based on output extension:
        .webm → libvpx-vp9 / libvorbis
        .mov  → prores_ks / pcm_s16le
    """
    project_path = Path(project_path)
    output_path = Path(output_path)

    if not project_path.exists():
        raise FileNotFoundError(f"Project file not found: {project_path}")

    if melt_cmd is None:
        melt_cmd = get_melt_command()

    # Auto-select codecs for specific extensions
    ext = output_path.suffix.lower()
    if ext == ".webm" and vcodec == "libx264":
        vcodec = "libvpx-vp9"
        acodec = "libvorbis"
    elif ext == ".mov" and vcodec == "libx264":
        vcodec = "prores_ks"
        acodec = "pcm_s16le"

    cmd = [melt_cmd]

    if profile:
        cmd.extend(["-profile", profile])

    cmd.append(str(project_path))

    consumer = f"avformat:{output_path}"
    cmd.extend([
        "-consumer", consumer,
        f"vcodec={vcodec}",
        f"acodec={acodec}",
    ])

    if vcodec in ("libx264",):
        cmd.extend([
            f"crf={crf}",
            f"preset={preset}",
        ])

    if vcodec not in ("prores_ks", "pcm_s16le"):
        cmd.append(f"audio_bitrate={audio_bitrate}")

    if additional_args:
        cmd.extend(additional_args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    return result


def probe_render_capabilities() -> dict:
    """
    Probe available codecs and formats via melt-7.
    Returns dict with: "vcodecs", "acodec", "formats" (lists).
    """
    available, _ = check_melt_available()
    if not available:
        return {"vcodecs": [], "acodec": [], "formats": []}

    try:
        result = subprocess.run(
            ["melt", "-query", "codecs"],
            capture_output=True, text=True, timeout=5,
        )
        # Parse output (simplified)
        output = result.stdout + result.stderr
        return {
            "vcodecs": [],
            "acodec": [],
            "formats": [],
            "raw_output": output,
        }
    except Exception:
        return {"vcodecs": [], "acodec": [], "formats": []}


# ── Predefined render presets ─────────────────────────────────────────────

RENDER_PRESETS: dict[str, dict] = {
    "youtube_1080p": {
        "vcodec": "libx264", "acodec": "aac", "crf": 20,
        "preset": "slow", "audio_bitrate": "256k",
    },
    "web_webm": {
        "vcodec": "libvpx-vp9", "acodec": "libvorbis", "crf": 30,
        "audio_bitrate": "192k",
    },
    "archive_prores": {
        "vcodec": "prores_ks", "acodec": "pcm_s16le",
    },
    "preview": {
        "vcodec": "libx264", "acodec": "aac", "crf": 28,
        "preset": "ultrafast", "audio_bitrate": "128k",
    },
}


def render_preset(
    project_path: str | Path,
    output_path: str | Path,
    preset_name: str,
    additional_args: Optional[list[str]] = None,
) -> subprocess.CompletedProcess:
    """Render using a named preset from RENDER_PRESETS."""
    if preset_name not in RENDER_PRESETS:
        available = ", ".join(sorted(RENDER_PRESETS.keys()))
        raise ValueError(f"Unknown preset: {preset_name!r}. Available: {available}")

    preset = RENDER_PRESETS[preset_name]
    return render(
        project_path=project_path,
        output_path=output_path,
        additional_args=additional_args,
        **preset,
    )
