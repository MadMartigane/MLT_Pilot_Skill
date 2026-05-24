"""Data models for MLT project structure. All models are plain dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


class TrackType(Enum):
    VIDEO = "video"
    AUDIO = "audio"


class TransitionType(Enum):
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    OVERLAY = "overlay"


@dataclass
class KeyframePoint:
    """Single keyframe point for animated properties."""
    frame: int
    value: float


@dataclass
class MediaRef:
    """Reference to a media file (video, audio, image)."""
    id: str                        # MLT producer ID (e.g., "producer0")
    filename: str                  # Original filename (e.g., "clip1.mp4")
    path: str                      # Relative path within project dir
    media_type: str                # "video", "audio", "image"
    duration_frames: int           # Total duration in frames
    in_point: int = 0              # Default in point (frames)
    out_point: int = 0             # Default out point (frames, 0 = use duration_frames)


@dataclass
class Clip:
    """A clip placed on a track timeline."""
    id: str                        # Unique clip ID
    media_ref: MediaRef            # Reference to source media
    track_index: int               # Which track this clip belongs to
    position: int                  # Start position on timeline (frames)
    in_point: int = 0              # In point in source media (frames)
    out_point: int = 0             # Out point in source media (frames, 0 = auto)
    duration: int = 0              # Duration on timeline (frames, 0 = auto from in/out)

    def get_duration(self) -> int:
        """Return effective duration. If duration==0, derive from out-in."""
        if self.duration > 0:
            return self.duration
        out = self.out_point if self.out_point > 0 else self.media_ref.duration_frames
        return out - self.in_point


@dataclass
class Blank:
    """A blank/gap on a track timeline."""
    duration: int                  # Duration in frames


@dataclass
class Filter:
    """An MLT filter applied to a track or clip."""
    id: str                        # Unique filter ID
    service: str                   # MLT service name (e.g., "volume", "brightness")
    properties: dict[str, str] = field(default_factory=dict)
    in_point: Optional[int] = None
    out_point: Optional[int] = None


@dataclass
class Transition:
    """An MLT transition between two tracks."""
    id: str                        # Unique transition ID
    service: str                   # MLT service name (e.g., "composite", "mix")
    a_track: int                   # Index of track A
    b_track: int                   # Index of track B
    in_point: int = 0              # Start frame of transition
    out_point: int = 0             # End frame of transition
    properties: dict[str, str] = field(default_factory=dict)


@dataclass
class SubtitleLine:
    """A single subtitle entry."""
    index: int                     # Sequential index (1-based)
    text: str                      # Subtitle text content
    start_frame: int               # Start frame
    end_frame: int                 # End frame
    style: str = ""                # Optional style name (for ASS)


@dataclass
class SubtitleTrack:
    """A collection of subtitle lines."""
    id: str                        # Track ID
    lines: list[SubtitleLine] = field(default_factory=list)
    font: str = "Sans"
    font_size: int = 26
    encoding: str = "utf-8"
    source_file: Optional[str] = None


@dataclass
class Track:
    """A single track on the timeline."""
    id: str                        # MLT playlist ID (e.g., "playlist0")
    index: int                     # Track index (0-based)
    track_type: TrackType = TrackType.VIDEO
    name: str = ""                 # Human-readable name
    clips: list[Union[Clip, Blank]] = field(default_factory=list)
    filters: list[Filter] = field(default_factory=list)
    muted: bool = False
    hidden: bool = False


@dataclass
class ProjectMetadata:
    """Project-level metadata."""
    title: str = "Untitled Project"
    profile_name: str = "atsc_1080p_30"
    root_dir: str = "./"
    created_with: str = "mlt-pilot"


@dataclass
class MLTProjectData:
    """
    Complete internal representation of an MLT project.
    """
    metadata: ProjectMetadata = field(default_factory=ProjectMetadata)
    media_refs: dict[str, MediaRef] = field(default_factory=dict)
    tracks: list[Track] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    subtitle_tracks: list[SubtitleTrack] = field(default_factory=list)
    fps: float = 30.0
    width: int = 1920
    height: int = 1080
    sample_aspect_num: int = 1
    sample_aspect_den: int = 1
    display_aspect_num: int = 16
    display_aspect_den: int = 9
    progressive: int = 1
    colorspace: int = 709
