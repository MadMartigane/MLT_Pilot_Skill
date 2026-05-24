"""Tests for mlt_pilot.effects module."""

import pytest
from mlt_pilot.effects import (
    get_filter, get_transition, list_filters, list_transitions,
    resolve_transition_type, build_filter_properties,
)


class TestFilterCatalog:
    def test_volume_filter_exists(self):
        f = get_filter("volume")
        assert f.display_name == "Volume"
        assert f.category == "audio"
        assert len(f.parameters) >= 1

    def test_brightness_filter_exists(self):
        f = get_filter("brightness")
        assert f.category == "color"
        assert any(p.name == "brightness" for p in f.parameters)

    def test_unknown_filter(self):
        with pytest.raises(KeyError):
            get_filter("nonexistent_filter")

    def test_list_all_filters(self):
        filters = list_filters()
        assert len(filters) >= 10

    def test_list_filters_by_category(self):
        audio = list_filters("audio")
        assert len(audio) >= 1
        assert any(f.service == "volume" for f in audio)

    def test_list_filters_by_color(self):
        color = list_filters("color")
        assert len(color) >= 3


class TestTransitionCatalog:
    def test_transitions_exist(self):
        trans = list_transitions()
        assert len(trans) >= 2

    def test_get_transition(self):
        t = get_transition("composite")
        assert t.category == "transition"

    def test_unknown_transition(self):
        with pytest.raises(KeyError):
            get_transition("nonexistent")


class TestResolveTransitionType:
    def test_crossfade(self):
        result = resolve_transition_type("crossfade")
        assert result["service"] == "composite"
        assert "properties" in result

    def test_dissolve(self):
        result = resolve_transition_type("dissolve")
        assert result["service"] == "luma"

    def test_mix(self):
        result = resolve_transition_type("mix")
        assert result["service"] == "mix"

    def test_wipe(self):
        result = resolve_transition_type("wipe")
        assert result["service"] == "luma"

    def test_overlay(self):
        result = resolve_transition_type("overlay")
        assert result["service"] == "composite"

    def test_unknown(self):
        with pytest.raises(ValueError):
            resolve_transition_type("unknown_type")


class TestBuildFilterProperties:
    def test_basic(self):
        props = build_filter_properties("volume", gain=0.5)
        assert props == {"gain": "0.5"}

    def test_values_are_strings(self):
        props = build_filter_properties("volume", gain=0.5)
        assert isinstance(props["gain"], str)

    def test_unknown_param_passed_through(self):
        props = build_filter_properties("volume", gain=0.5, custom_param="test")
        assert "custom_param" in props

    def test_unknown_service(self):
        props = build_filter_properties("unknown_filter", any_key="any_value")
        assert props == {"any_key": "any_value"}
