"""
MLT Pilot — AI-driven MLT video editing module.

Usage:
    from mlt_pilot import MLTProject

    project = MLTProject(profile="atsc_1080p_30", title="My Video")
    project.add_media("/path/to/clip.mp4")
    project.add_clip(track=0, media="clip.mp4", start=0, duration="10s")
    project.export_mlt("output.mlt")
"""

from .project import MLTProject
from .models import (
    MLTProjectData,
    Clip,
    Track,
    TrackType,
    Filter,
    Transition,
    SubtitleLine,
    SubtitleTrack,
    MediaRef,
    ProjectMetadata,
)
from .profiles import get_profile, list_profiles, MLTProfile
from .effects import list_filters, list_transitions, get_filter, get_transition
from .export import check_melt_available, RENDER_PRESETS

__version__ = "0.1.0"

__all__ = [
    "MLTProject",
    "MLTProjectData",
    "Clip",
    "Track",
    "TrackType",
    "Filter",
    "Transition",
    "SubtitleLine",
    "SubtitleTrack",
    "MediaRef",
    "ProjectMetadata",
    "get_profile",
    "list_profiles",
    "MLTProfile",
    "list_filters",
    "list_transitions",
    "get_filter",
    "get_transition",
    "check_melt_available",
    "RENDER_PRESETS",
    "__version__",
]
