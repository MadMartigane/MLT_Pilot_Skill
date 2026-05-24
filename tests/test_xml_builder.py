"""Tests for mlt_pilot.xml_builder module."""

import xml.etree.ElementTree as ET
import pytest
from mlt_pilot.models import *
from mlt_pilot.profiles import get_profile
from mlt_pilot.xml_builder import MLTXMLBuilder


def _make_minimal_project():
    """Create a minimal MLTProjectData for testing."""
    profile = get_profile("atsc_1080p_30")
    media = MediaRef(id="producer0", filename="clip1.mp4", path="videos/clip1.mp4", media_type="video", duration_frames=300)
    clip = Clip(id="clip0", media_ref=media, track_index=0, position=0, in_point=0, out_point=299)
    track = Track(id="playlist0", index=0, track_type=TrackType.VIDEO, clips=[clip])
    return MLTProjectData(
        metadata=ProjectMetadata(title="Builder Test"),
        media_refs={"producer0": media},
        tracks=[track],
        fps=profile.fps, width=profile.width, height=profile.height,
        sample_aspect_num=profile.sample_aspect_num, sample_aspect_den=profile.sample_aspect_den,
        display_aspect_num=profile.display_aspect_num, display_aspect_den=profile.display_aspect_den,
        progressive=profile.progressive, colorspace=profile.colorspace,
    )


class TestXMLBuilder:
    def test_build_returns_valid_xml(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        assert root.tag == "mlt"

    def test_build_has_profile(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        profile = root.find("profile")
        assert profile is not None
        assert profile.get("width") == "1920"
        assert profile.get("height") == "1080"

    def test_build_has_producer(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        producer = root.find("producer")
        assert producer is not None
        assert producer.get("id") == "producer0"
        assert producer.get("out") == "299"

    def test_producer_has_resource(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        producer = root.find("producer")
        resource = producer.find("property[@name='resource']")
        assert resource is not None
        assert resource.get("name") == "resource"
        assert "clip1.mp4" in resource.text

    def test_build_has_playlist(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        playlist = root.find("playlist")
        assert playlist is not None
        assert playlist.get("id") == "playlist0"

    def test_playlist_has_entry(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        playlist = root.find("playlist")
        entry = playlist.find("entry")
        assert entry is not None
        assert entry.get("producer") == "producer0"

    def test_build_has_tractor(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        tractor = root.find("tractor")
        assert tractor is not None

    def test_tractor_has_tracks(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        tractor = root.find("tractor")
        tracks = list(tractor.findall("track"))
        assert len(tracks) >= 1

    def test_paths_are_relative(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        assert "/videos/" not in xml_str
        assert "videos/clip1.mp4" in xml_str

    def test_root_attribute(self):
        data = _make_minimal_project()
        builder = MLTXMLBuilder(data)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        assert root.get("root") == "./"
