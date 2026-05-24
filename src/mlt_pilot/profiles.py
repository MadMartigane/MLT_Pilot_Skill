"""MLT profile definitions (resolution, framerate, aspect ratio)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class MLTProfile:
    """Immutable MLT profile descriptor."""
    name: str
    description: str
    width: int
    height: int
    progressive: int               # 1 = progressive, 0 = interlaced
    sample_aspect_num: int
    sample_aspect_den: int
    display_aspect_num: int
    display_aspect_den: int
    frame_rate_num: int
    frame_rate_den: int
    colorspace: int                # 709 for HD, 601 for SD

    @property
    def fps(self) -> float:
        """Computed frame rate as float."""
        return self.frame_rate_num / self.frame_rate_den


PROFILES: dict[str, MLTProfile] = {
    "atsc_1080p_30": MLTProfile(
        name="atsc_1080p_30", description="ATSC 1080p 30fps",
        width=1920, height=1080, progressive=1,
        sample_aspect_num=1, sample_aspect_den=1,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=30, frame_rate_den=1, colorspace=709,
    ),
    "atsc_1080p_25": MLTProfile(
        name="atsc_1080p_25", description="ATSC 1080p 25fps",
        width=1920, height=1080, progressive=1,
        sample_aspect_num=1, sample_aspect_den=1,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=25, frame_rate_den=1, colorspace=709,
    ),
    "atsc_1080p_24": MLTProfile(
        name="atsc_1080p_24", description="ATSC 1080p 24fps",
        width=1920, height=1080, progressive=1,
        sample_aspect_num=1, sample_aspect_den=1,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=24, frame_rate_den=1, colorspace=709,
    ),
    "atsc_1080i_60": MLTProfile(
        name="atsc_1080i_60", description="ATSC 1080i 60fps",
        width=1920, height=1080, progressive=0,
        sample_aspect_num=1, sample_aspect_den=1,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=30000, frame_rate_den=1001, colorspace=709,
    ),
    "atsc_720p_30": MLTProfile(
        name="atsc_720p_30", description="ATSC 720p 30fps",
        width=1280, height=720, progressive=1,
        sample_aspect_num=1, sample_aspect_den=1,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=30, frame_rate_den=1, colorspace=709,
    ),
    "atsc_720p_25": MLTProfile(
        name="atsc_720p_25", description="ATSC 720p 25fps",
        width=1280, height=720, progressive=1,
        sample_aspect_num=1, sample_aspect_den=1,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=25, frame_rate_den=1, colorspace=709,
    ),
    "dv_ntsc": MLTProfile(
        name="dv_ntsc", description="DV NTSC 4:3",
        width=720, height=480, progressive=0,
        sample_aspect_num=10, sample_aspect_den=11,
        display_aspect_num=4, display_aspect_den=3,
        frame_rate_num=30000, frame_rate_den=1001, colorspace=601,
    ),
    "dv_pal": MLTProfile(
        name="dv_pal", description="DV PAL 4:3",
        width=720, height=576, progressive=0,
        sample_aspect_num=12, sample_aspect_den=11,
        display_aspect_num=4, display_aspect_den=3,
        frame_rate_num=25, frame_rate_den=1, colorspace=601,
    ),
    "hdv_1080i_25": MLTProfile(
        name="hdv_1080i_25", description="HDV 1080i 25fps",
        width=1440, height=1080, progressive=0,
        sample_aspect_num=4, sample_aspect_den=3,
        display_aspect_num=16, display_aspect_den=9,
        frame_rate_num=25, frame_rate_den=1, colorspace=709,
    ),
}


def get_profile(name: str) -> MLTProfile:
    """
    Get a profile by name.
    Raises KeyError with list of available profiles if not found.
    """
    if name not in PROFILES:
        available = ", ".join(sorted(PROFILES.keys()))
        raise KeyError(f"Unknown profile: {name!r}. Available: {available}")
    return PROFILES[name]


def list_profiles() -> list[str]:
    """Return sorted list of available profile names."""
    return sorted(PROFILES.keys())


def resolve_profile(name_or_profile: Union[str, MLTProfile]) -> MLTProfile:
    """Accept either a name string or an MLTProfile instance, return MLTProfile."""
    if isinstance(name_or_profile, MLTProfile):
        return name_or_profile
    return get_profile(name_or_profile)
