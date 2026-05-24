"""Tests for mlt_pilot.profiles module."""

import pytest
from mlt_pilot.profiles import get_profile, list_profiles, resolve_profile, MLTProfile, PROFILES


class TestGetProfile:
    def test_known_profile(self):
        p = get_profile("atsc_1080p_30")
        assert p.fps == 30.0
        assert p.width == 1920
        assert p.height == 1080

    def test_unknown_profile(self):
        with pytest.raises(KeyError) as exc:
            get_profile("nonexistent")
        assert "nonexistent" in str(exc.value)
        assert "Available" in str(exc.value)


class TestListProfiles:
    def test_returns_list(self):
        profiles = list_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) >= 8

    def test_contains_expected(self):
        profiles = list_profiles()
        assert "atsc_1080p_30" in profiles
        assert "dv_pal" in profiles


class TestResolveProfile:
    def test_string(self):
        p = resolve_profile("atsc_1080p_30")
        assert isinstance(p, MLTProfile)

    def test_instance(self):
        original = get_profile("atsc_1080p_30")
        resolved = resolve_profile(original)
        assert resolved is original


class TestMLTProfile:
    def test_frozen(self):
        p = get_profile("atsc_1080p_30")
        with pytest.raises(Exception):  # FrozenInstanceError
            p.width = 3840

    def test_fps_property(self):
        assert get_profile("atsc_1080p_30").fps == 30.0
        assert get_profile("atsc_1080p_25").fps == 25.0
        assert get_profile("dv_ntsc").fps == pytest.approx(30000/1001)
