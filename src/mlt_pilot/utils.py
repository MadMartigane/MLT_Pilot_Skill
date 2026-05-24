"""Timecode conversions, frame math, path validation, and MLT string utilities."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Union


# ── Timecode / Frame Conversions ──────────────────────────────────────────

def timecode_to_seconds(tc: str) -> float:
    """
    Convert a timecode string to seconds.
    Accepts formats:
      - "HH:MM:SS.mmm" or "HH:MM:SS,mmm"
      - "MM:SS.mmm"
      - "SSs" / "SS.mmm" (suffixed with 's')
      - Pure float string → seconds directly
      - Pure number (int/float) → pass through
    Raises ValueError for unparseable input.
    """
    if isinstance(tc, (int, float)):
        return float(tc)

    tc = str(tc).strip()

    # "10s" or "10.5s" format
    if tc.endswith("s"):
        try:
            return float(tc[:-1])
        except ValueError:
            raise ValueError(f"Cannot parse duration: {tc!r}")

    # HH:MM:SS.mmm or HH:MM:SS,mmm or MM:SS.mmm
    if ":" in tc:
        parts = tc.replace(",", ".").split(":")
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        else:
            raise ValueError(f"Cannot parse timecode: {tc!r}")

    # Plain number
    try:
        return float(tc)
    except ValueError:
        raise ValueError(f"Cannot parse timecode: {tc!r}")


def seconds_to_timecode(seconds: float, fmt: str = "hh:mm:ss.mmm") -> str:
    """
    Convert seconds to timecode string.
    fmt: "hh:mm:ss.mmm" (default), "hh:mm:ss,mmm"
    """
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    remainder = seconds - h * 3600
    m = int(remainder // 60)
    s = remainder - m * 60
    sep = "," if fmt == "hh:mm:ss,mmm" else "."
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", sep, 1)


def seconds_to_frames(seconds: float, fps: float) -> int:
    """Round seconds to nearest frame count. Returns int."""
    return int(round(seconds * fps))


def frames_to_seconds(frames: int, fps: float) -> float:
    """Convert frame count to seconds."""
    return frames / fps


def frames_to_timecode(frames: int, fps: float, fmt: str = "hh:mm:ss.mmm") -> str:
    """Convert frame count to timecode string."""
    return seconds_to_timecode(frames / fps, fmt)


def timecode_to_frames(tc: str, fps: float) -> int:
    """Parse timecode to frame count at given fps."""
    return seconds_to_frames(timecode_to_seconds(tc), fps)


def parse_duration(value: Union[str, int, float, None], fps: float) -> int:
    """
    Parse a duration value into frames.
    - String ending with 's' → parse as seconds, convert to frames.
    - Timecode string → parse to frames.
    - int → treat as frames directly.
    - float → treat as seconds, convert to frames.
    - None → 0
    """
    if value is None:
        return 0
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return seconds_to_frames(value, fps)
    if isinstance(value, str):
        value = value.strip()
        if value.endswith("s"):
            return seconds_to_frames(float(value[:-1]), fps)
        if ":" in value:
            return timecode_to_frames(value, fps)
        try:
            return int(value)
        except ValueError:
            try:
                return seconds_to_frames(float(value), fps)
            except ValueError:
                raise ValueError(f"Cannot parse duration: {value!r}")
    return 0


# ── Keyframe String Builder ───────────────────────────────────────────────

def build_keyframe_string(keyframes: list[tuple[int, float]]) -> str:
    """
    Build MLT keyframe property string.
    Input: [(frame, value), ...] sorted by frame.
    Output: "0=val0;30~=val1;..." (smooth interpolation: ~ for second+ entries)
    """
    if not keyframes:
        return ""
    parts = []
    for i, (frame, val) in enumerate(keyframes):
        val_str = str(val)
        if i == 0:
            parts.append(f"{frame}={val_str}")
        else:
            parts.append(f"{frame}~={val_str}")
    return ";".join(parts)


# ── Path Utilities ────────────────────────────────────────────────────────

def make_relative_path(file_path: str | Path, base_dir: str | Path) -> str:
    """
    Compute a relative path from base_dir to file_path.
    Returns a POSIX-style relative path (forward slashes).
    """
    file_path = Path(file_path).resolve()
    base_dir = Path(base_dir).resolve()
    try:
        rel = file_path.relative_to(base_dir)
        return rel.as_posix()
    except ValueError:
        return file_path.as_posix()


def resolve_media_path(filename: str, project_dir: str | Path) -> Path | None:
    """
    Search for a media file by name within the project directory tree.
    Returns absolute Path if found, None otherwise.
    """
    project_dir = Path(project_dir)
    # Direct child
    candidate = project_dir / filename
    if candidate.exists():
        return candidate.resolve()
    # Recursive search
    for p in project_dir.rglob(filename):
        if p.is_file():
            return p.resolve()
    return None


def validate_media_exists(path: str | Path) -> Path:
    """
    Validate that a media file exists and is readable.
    Returns the resolved absolute Path.
    Raises FileNotFoundError with helpful message if not found.
    """
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Media file not found: {p}")
    if not p.is_file():
        raise FileNotFoundError(f"Not a file: {p}")
    return p


# ── ID Generation ─────────────────────────────────────────────────────────

_id_counters: dict[str, int] = {}


def generate_id(prefix: str) -> str:
    """
    Generate a unique MLT-style ID: "producer0", "playlist1", etc.
    """
    count = _id_counters.get(prefix, 0)
    _id_counters[prefix] = count + 1
    return f"{prefix}{count}"


def reset_id_counters() -> None:
    """Reset all ID counters. Useful between tests."""
    _id_counters.clear()


# ── Sanitization ──────────────────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    """
    Sanitize a string for use as MLT property or filename.
    Replace non-alphanumeric chars with underscore, strip leading/trailing underscores.
    """
    return re.sub(r"[^a-zA-Z0-9_]", "_", name).strip("_")
