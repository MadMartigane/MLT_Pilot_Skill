"""Tests for mlt_pilot.project module — full API workflow."""

import os
import xml.etree.ElementTree as ET
import pytest
from mlt_pilot.project import MLTProject
from mlt_pilot.models import Clip, Blank, TrackType


class TestProjectCreation:
    def test_create_empty(self):
        p = MLTProject(profile="atsc_1080p_30", title="Test")
        assert p.fps == 30.0
        assert p.data.metadata.title == "Test"

    def test_default_profile(self):
        p = MLTProject()
        assert p.fps == 30.0


class TestMediaManagement:
    def test_add_media(self, tmp_media):
        p = MLTProject()
        alias = p.add_media(tmp_media["video1"])
        assert len(p.list_media()) == 1

    def test_add_multiple_media(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_media(tmp_media["video2"])
        p.add_media(tmp_media["audio"])
        assert len(p.list_media()) == 3

    def test_list_media_structure(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        media = p.list_media()
        assert "id" in media[0]
        assert "filename" in media[0]
        assert "type" in media[0]

    def test_media_not_found(self):
        p = MLTProject()
        with pytest.raises(FileNotFoundError):
            p.add_media("/nonexistent/file.mp4")


class TestTimelineConstruction:
    def test_add_clip(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        clip_id = p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        assert clip_id
        assert len(p.data.tracks) == 1

    def test_add_clip_auto_creates_track(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="5s")
        p.add_clip(track=1, media="clip1.mp4", start=0, duration="5s")
        assert len(p.data.tracks) == 2

    def test_add_track_explicit(self):
        p = MLTProject()
        idx = p.add_track(track_type=TrackType.AUDIO, name="Audio")
        assert idx == 0
        assert p.data.tracks[0].name == "Audio"

    def test_insert_clip_shifts(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        p.insert_clip(track=0, position=0, media="clip1.mp4", duration="5s")
        clips = [c for c in p.data.tracks[0].clips if isinstance(c, Clip)]
        positions = sorted(c.position for c in clips)
        assert positions[0] == 0
        assert positions[1] >= 150  # shifted right

    def test_remove_clip(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        result = p.remove_clip(track=0, position=0)
        assert result is True
        assert isinstance(p.data.tracks[0].clips[0], Blank)

    def test_remove_clip_not_found(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        result = p.remove_clip(track=0, position=999)
        assert result is False


class TestSaveLoad:
    def test_save_creates_file(self, tmp_media, tmp_path):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="5s")
        out = tmp_path / "test.mlt"
        p.save(out, snapshot=False)
        assert out.exists()

    def test_save_creates_snapshot(self, tmp_media, tmp_path):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="5s")
        out = tmp_path / "test.mlt"
        p.save(out, snapshot=True)
        snapshot_dir = out.parent / "snapshots"
        assert snapshot_dir.exists()
        snapshots = list(snapshot_dir.glob("*.mlt"))
        assert len(snapshots) >= 1

    def test_load_round_trip(self, tmp_media, tmp_path):
        p1 = MLTProject(profile="atsc_1080p_30", title="Round Trip")
        p1.add_media(tmp_media["video1"])
        p1.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        out = tmp_path / "rt.mlt"
        p1.save(out, snapshot=False)

        p2 = MLTProject.load(out)
        assert p2.data.metadata.title == "Round Trip"
        assert len(p2.data.tracks) >= 1

    def test_export_mlt_is_valid_xml(self, tmp_media, tmp_path):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="5s")
        out = tmp_path / "valid.mlt"
        p.export_mlt(out)
        root = ET.fromstring(out.read_text())
        assert root.tag == "mlt"


class TestDescribe:
    def test_returns_string(self):
        p = MLTProject(title="Describe Test")
        desc = p.describe()
        assert isinstance(desc, str)
        assert "Describe Test" in desc

    def test_describe_with_clips(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        desc = p.describe()
        assert "clip1.mp4" in desc

    def test_describe_with_transitions(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        p.add_clip(track=1, media="clip1.mp4", start=0, duration="10s")
        p.add_transition(track_a=0, track_b=1, start="8s", duration="2s", type="crossfade")
        desc = p.describe()
        assert "crossfade" in desc.lower() or "composite" in desc.lower()

    def test_describe_with_filters(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        p.add_filter(0, "volume", gain=0.5)
        desc = p.describe()
        assert "volume" in desc.lower()

    def test_describe_with_subtitles(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        p.add_subtitle_line(text="Hello", start="5s", duration="3s")
        desc = p.describe()
        assert "Hello" in desc or "subtitle" in desc.lower()


class TestEffectsIntegration:
    def test_add_filter(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="5s")
        fid = p.add_filter(0, "volume", gain=0.5)
        assert fid
        assert len(p.data.tracks[0].filters) >= 1

    def test_add_transition(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        p.add_clip(track=1, media="clip1.mp4", start=0, duration="10s")
        tid = p.add_transition(0, 1, "5s", "2s", type="crossfade")
        assert tid
        assert len(p.data.transitions) >= 1

    def test_add_transition_unknown_type(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        p.add_clip(track=1, media="clip1.mp4", start=0, duration="10s")
        with pytest.raises(ValueError):
            p.add_transition(0, 1, "5s", "2s", type="unknown_type")


class TestAudioIntegration:
    def test_set_audio_level(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="5s")
        fid = p.set_audio_level(0, 0.8)
        assert fid

    def test_add_background_music(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="15s")
        idx = p.add_background_music(tmp_media["audio"], volume=0.3, fade_in="2s")
        assert isinstance(idx, int)


class TestSubtitleIntegration:
    def test_add_subtitle_line(self, tmp_media):
        p = MLTProject()
        p.add_media(tmp_media["video1"])
        p.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
        sid = p.add_subtitle_line(text="Hello", start="5s", duration="3s")
        assert sid
        assert len(p.data.subtitle_tracks) >= 1
