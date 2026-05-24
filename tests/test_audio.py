"""Tests for mlt_pilot.audio module."""

import pytest
from mlt_pilot.audio import AudioManager
from mlt_pilot.models import MLTProjectData


@pytest.fixture
def audio_mgr():
    data = MLTProjectData(fps=30.0)
    return AudioManager(data)


class TestSetVolume:
    def test_basic(self, audio_mgr):
        f = audio_mgr.set_volume(0, 0.5)
        assert f.service == "volume"
        assert f.properties["gain"] == "0.5"

    def test_with_time_range(self, audio_mgr):
        f = audio_mgr.set_volume(0, 0.8, start="5s", end="10s")
        assert f.in_point == 150
        assert f.out_point == 300


class TestFadeIn:
    def test_creates_keyframed_volume(self, audio_mgr):
        f = audio_mgr.fade_in(0, "2s")
        assert f.service == "volume"
        assert f.in_point == 0
        assert f.out_point == 60
        assert "0=0.0" in f.properties.get("gain", "")

    def test_duration_correct(self, audio_mgr):
        f = audio_mgr.fade_in(0, "3s")
        assert f.out_point == 90


class TestFadeOut:
    def test_creates_keyframed_volume(self, audio_mgr):
        f = audio_mgr.fade_out(0, "3s", track_duration="15s")
        assert f.service == "volume"
        assert "360~=1.0" in f.properties.get("gain", "")
        assert "450=0.0" in f.properties.get("gain", "")


class TestNormalize:
    def test_creates_volume_filter(self, audio_mgr):
        f = audio_mgr.normalize(0)
        assert f.service == "volume"
        assert f.properties.get("normalise") == "1"


class TestBackgroundMusicSetup:
    def test_basic(self, audio_mgr):
        setup = audio_mgr.create_background_music_setup("music.mp3", volume=0.3)
        assert setup["volume_filter"] is not None
        assert setup["volume_filter"].properties["gain"] == "0.3"

    def test_with_fade_in(self, audio_mgr):
        setup = audio_mgr.create_background_music_setup("music.mp3", volume=0.3, fade_in="2s")
        assert setup["fade_in_filter"] is not None

    def test_with_fade_out(self, audio_mgr):
        setup = audio_mgr.create_background_music_setup("music.mp3", volume=0.3, fade_out="3s")
        assert setup["fade_out_filter"] is not None


class TestFFprobe:
    def test_is_available_returns_bool(self):
        result = AudioManager.is_ffprobe_available()
        assert isinstance(result, bool)

    def test_probe_nonexistent_raises(self):
        with pytest.raises(RuntimeError):
            AudioManager.probe_audio("/nonexistent/file.mp3")
