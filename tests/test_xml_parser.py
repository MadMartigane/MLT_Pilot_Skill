"""Tests for mlt_pilot.xml_parser module."""

import pytest
from mlt_pilot.xml_parser import MLTXMLParser


class TestXMLParser:
    def test_parse_basic_structure(self, simple_mlt_string):
        parser = MLTXMLParser()
        data = parser.parse_string(simple_mlt_string)
        assert data.metadata.title == "Simple Test Project"
        assert data.fps == 30.0
        assert data.width == 1920
        assert data.height == 1080

    def test_parse_producers(self, simple_mlt_string):
        parser = MLTXMLParser()
        data = parser.parse_string(simple_mlt_string)
        assert len(data.media_refs) == 2
        assert "producer0" in data.media_refs
        assert "producer1" in data.media_refs
        assert data.media_refs["producer0"].filename == "clip1.mp4"
        assert data.media_refs["producer0"].media_type == "video"
        assert data.media_refs["producer1"].media_type == "audio"

    def test_parse_tracks(self, simple_mlt_string):
        parser = MLTXMLParser()
        data = parser.parse_string(simple_mlt_string)
        assert len(data.tracks) == 2
        assert len(data.tracks[0].clips) == 3  # entry, blank, entry
        assert len(data.tracks[1].clips) == 1

    def test_parse_blank(self, simple_mlt_string):
        from mlt_pilot.models import Blank
        parser = MLTXMLParser()
        data = parser.parse_string(simple_mlt_string)
        assert isinstance(data.tracks[0].clips[1], Blank)
        assert data.tracks[0].clips[1].duration == 30

    def test_parse_clip_positions(self, simple_mlt_string):
        from mlt_pilot.models import Clip
        parser = MLTXMLParser()
        data = parser.parse_string(simple_mlt_string)
        clips = [c for c in data.tracks[0].clips if isinstance(c, Clip)]
        assert clips[0].in_point == 0
        assert clips[0].out_point == 149  # MLT out is inclusive: out="149"
        assert clips[1].in_point == 150
        assert clips[1].out_point == 299

    def test_round_trip(self, simple_mlt_string):
        """Parse → build → parse should preserve core data."""
        from mlt_pilot.xml_builder import MLTXMLBuilder
        parser = MLTXMLParser()
        data1 = parser.parse_string(simple_mlt_string)
        
        builder = MLTXMLBuilder(data1)
        xml_str = builder.build()
        
        data2 = parser.parse_string(xml_str)
        assert data2.metadata.title == data1.metadata.title
        assert data2.fps == data1.fps
        assert len(data2.media_refs) == len(data1.media_refs)
        assert len(data2.tracks) == len(data1.tracks)

    def test_parse_missing_profile_graceful(self):
        parser = MLTXMLParser()
        xml = '<?xml version="1.0"?><mlt root="./" title="No Profile"><producer id="p0" in="0" out="99"/></mlt>'
        data = parser.parse_string(xml)
        assert data.metadata.title == "No Profile"
        # Should use default fps
        assert data.fps > 0
