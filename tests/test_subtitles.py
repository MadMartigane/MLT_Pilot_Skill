"""Tests for mlt_pilot.subtitles module."""

import pytest
from mlt_pilot.subtitles import SubtitleManager


@pytest.fixture
def mgr():
    return SubtitleManager(fps=30.0)


@pytest.fixture
def mgr25():
    return SubtitleManager(fps=25.0)


class TestSrtParsing:
    def test_basic(self, mgr, sample_srt_string):
        track = mgr._parse_srt_content(sample_srt_string)
        assert len(track.lines) == 2
        assert track.lines[0].text == "Hello World"
        assert track.lines[1].text == "Second subtitle line"

    def test_frame_positions_30fps(self, mgr, sample_srt_string):
        track = mgr._parse_srt_content(sample_srt_string)
        assert track.lines[0].start_frame == 30
        assert track.lines[0].end_frame == 120
        assert track.lines[1].start_frame == 150
        assert track.lines[1].end_frame == 255

    def test_frame_positions_25fps(self, mgr25, sample_srt_string):
        track = mgr25._parse_srt_content(sample_srt_string)
        assert track.lines[0].start_frame == 25
        assert track.lines[0].end_frame == 100

    def test_with_bom(self, mgr, sample_srt_bom):
        track = mgr._parse_srt_content(sample_srt_bom)
        assert len(track.lines) == 2

    def test_indexing(self, mgr, sample_srt_string):
        track = mgr._parse_srt_content(sample_srt_string)
        assert track.lines[0].index == 1
        assert track.lines[1].index == 2

    def test_formatted_tags_stripped(self, mgr):
        srt = "1\n00:00:01,000 --> 00:00:04,000\n<i>Hello</i> <b>World</b>\n"
        track = mgr._parse_srt_content(srt)
        assert track.lines[0].text == "Hello World"

    def test_empty_raises(self, mgr):
        with pytest.raises(ValueError):
            mgr._parse_srt_content("no valid content here")


class TestCreateTrack:
    def test_basic(self, mgr):
        track = mgr.create_track([
            {"text": "Hello", "start": "5s", "duration": "3s"},
            {"text": "World", "start": "10s", "duration": "2s"},
        ])
        assert len(track.lines) == 2
        assert track.lines[0].start_frame == 150
        assert track.lines[0].end_frame == 240
        assert track.font == "Sans"

    def test_custom_font(self, mgr):
        track = mgr.create_track(
            [{"text": "Hi", "start": "0s", "duration": "1s"}],
            font="Monospace", font_size=32,
        )
        assert track.font == "Monospace"
        assert track.font_size == 32


class TestAddLine:
    def test_basic(self, mgr):
        from mlt_pilot.models import SubtitleTrack
        track = SubtitleTrack(id="test_sub")
        mgr.add_line(track, "Line 1", "5s", "3s")
        assert len(track.lines) == 1
        assert track.lines[0].start_frame == 150

    def test_increments_index(self, mgr):
        from mlt_pilot.models import SubtitleTrack
        track = SubtitleTrack(id="test_sub")
        mgr.add_line(track, "A", "0s", "1s")
        mgr.add_line(track, "B", "2s", "1s")
        assert track.lines[0].index == 1
        assert track.lines[1].index == 2
