"""Tests for mlt_pilot.utils module."""

import pytest
from mlt_pilot.utils import (
    timecode_to_seconds, seconds_to_timecode, seconds_to_frames, frames_to_seconds,
    frames_to_timecode, timecode_to_frames, parse_duration,
    build_keyframe_string, make_relative_path, resolve_media_path,
    validate_media_exists, generate_id, reset_id_counters, sanitize_name,
)


class TestTimecodeConversions:
    def test_timecode_to_seconds_hhmmss(self):
        assert timecode_to_seconds("00:00:10.000") == pytest.approx(10.0)
        assert timecode_to_seconds("01:30:45.500") == pytest.approx(5445.5)

    def test_timecode_to_seconds_with_comma(self):
        assert timecode_to_seconds("00:00:10,000") == pytest.approx(10.0)

    def test_timecode_to_seconds_mmss(self):
        assert timecode_to_seconds("01:30.000") == pytest.approx(90.0)

    def test_timecode_to_seconds_with_s_suffix(self):
        assert timecode_to_seconds("10s") == pytest.approx(10.0)
        assert timecode_to_seconds("5.5s") == pytest.approx(5.5)

    def test_timecode_to_seconds_plain_number(self):
        assert timecode_to_seconds("10") == pytest.approx(10.0)
        assert timecode_to_seconds(10) == 10.0

    def test_timecode_to_seconds_invalid(self):
        with pytest.raises(ValueError):
            timecode_to_seconds("not_a_time")

    def test_seconds_to_timecode_default(self):
        assert seconds_to_timecode(10.0) == "00:00:10.000"

    def test_seconds_to_timecode_comma(self):
        assert seconds_to_timecode(10.0, fmt="hh:mm:ss,mmm") == "00:00:10,000"

    def test_seconds_to_timecode_large(self):
        assert seconds_to_timecode(3661.5) == "01:01:01.500"

    def test_seconds_to_timecode_negative(self):
        assert seconds_to_timecode(-1.0) == "00:00:00.000"


class TestFrameConversions:
    def test_seconds_to_frames(self):
        assert seconds_to_frames(10.0, 30.0) == 300
        assert seconds_to_frames(1.0, 25.0) == 25

    def test_frames_to_seconds(self):
        assert frames_to_seconds(300, 30.0) == pytest.approx(10.0)

    def test_frames_to_timecode(self):
        assert frames_to_timecode(300, 30.0) == "00:00:10.000"

    def test_timecode_to_frames(self):
        assert timecode_to_frames("00:00:10.000", 30.0) == 300
        assert timecode_to_frames("00:00:01,000", 25.0) == 25


class TestParseDuration:
    def test_string_seconds(self):
        assert parse_duration("10s", 30.0) == 300

    def test_timecode(self):
        assert parse_duration("00:00:05.000", 30.0) == 150

    def test_int_frames(self):
        assert parse_duration(300, 30.0) == 300

    def test_float_seconds(self):
        assert parse_duration(5.0, 30.0) == 150

    def test_none(self):
        assert parse_duration(None, 30.0) == 0

    def test_invalid(self):
        with pytest.raises(ValueError):
            parse_duration("abc", 30.0)


class TestKeyframes:
    def test_single_point(self):
        assert build_keyframe_string([(0, 1.0)]) == "0=1.0"

    def test_two_points(self):
        assert build_keyframe_string([(0, 1.0), (30, 0.5)]) == "0=1.0;30~=0.5"

    def test_three_points(self):
        result = build_keyframe_string([(0, 0.0), (15, 1.0), (30, 0.0)])
        assert "0=0.0;15~=1.0;30~=0.0" == result

    def test_empty(self):
        assert build_keyframe_string([]) == ""


class TestIdGeneration:
    def test_sequential(self):
        reset_id_counters()
        assert generate_id("producer") == "producer0"
        assert generate_id("producer") == "producer1"
        assert generate_id("playlist") == "playlist0"

    def test_reset(self):
        reset_id_counters()
        generate_id("x")
        reset_id_counters()
        assert generate_id("x") == "x0"

    def test_different_prefixes(self):
        reset_id_counters()
        assert generate_id("a") == "a0"
        assert generate_id("b") == "b0"
        assert generate_id("a") == "a1"


class TestPathUtils:
    def test_make_relative_subdirectory(self, tmp_path):
        file_path = tmp_path / "videos" / "clip.mp4"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("")
        result = make_relative_path(file_path, tmp_path)
        assert result == "videos/clip.mp4"

    def test_make_relative_same_dir(self, tmp_path):
        file_path = tmp_path / "clip.mp4"
        file_path.write_text("")
        result = make_relative_path(file_path, tmp_path)
        assert result == "clip.mp4"

    def test_validate_media_exists(self, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_text("")
        result = validate_media_exists(f)
        assert result == f.resolve()

    def test_validate_media_not_found(self):
        with pytest.raises(FileNotFoundError):
            validate_media_exists("/nonexistent/file.mp4")


class TestSanitize:
    def test_basic(self):
        assert sanitize_name("hello world") == "hello_world"

    def test_special_chars(self):
        result = sanitize_name("test!@#$%file")
        assert result == "test_____file"

    def test_leading_trailing(self):
        assert sanitize_name("_test_") == "test"
