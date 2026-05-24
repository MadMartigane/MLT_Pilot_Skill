"""Tests for mlt_pilot.models module."""

import pytest
from mlt_pilot.models import (
    TrackType, TransitionType, KeyframePoint, MediaRef, Clip, Blank,
    Filter, Transition, SubtitleLine, SubtitleTrack, Track,
    ProjectMetadata, MLTProjectData,
)


class TestTrackType:
    def test_values(self):
        assert TrackType.VIDEO.value == "video"
        assert TrackType.AUDIO.value == "audio"


class TestClip:
    def test_explicit_duration(self):
        media = MediaRef(id="p0", filename="t.mp4", path="t.mp4", media_type="video", duration_frames=300)
        clip = Clip(id="c0", media_ref=media, track_index=0, position=0, duration=150)
        assert clip.get_duration() == 150

    def test_auto_duration_from_out_point(self):
        media = MediaRef(id="p0", filename="t.mp4", path="t.mp4", media_type="video", duration_frames=300)
        clip = Clip(id="c0", media_ref=media, track_index=0, position=0, in_point=50, out_point=200)
        assert clip.get_duration() == 150

    def test_auto_duration_from_media(self):
        media = MediaRef(id="p0", filename="t.mp4", path="t.mp4", media_type="video", duration_frames=300)
        clip = Clip(id="c0", media_ref=media, track_index=0, position=0, in_point=0)
        assert clip.get_duration() == 300


class TestMLTProjectData:
    def test_default_construction(self):
        data = MLTProjectData()
        assert data.fps == 30.0
        assert data.width == 1920
        assert data.height == 1080
        assert data.tracks == []
        assert data.media_refs == {}
        assert data.transitions == []

    def test_with_metadata(self):
        meta = ProjectMetadata(title="Test", profile_name="atsc_1080p_25")
        data = MLTProjectData(metadata=meta, fps=25.0)
        assert data.metadata.title == "Test"
        assert data.fps == 25.0


class TestTrack:
    def test_default_construction(self):
        t = Track(id="pl0", index=0)
        assert t.track_type == TrackType.VIDEO
        assert t.clips == []
        assert t.filters == []
        assert t.muted is False
