"""Build MLT XML documents from internal project data models."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString

from .models import (
    MLTProjectData,
    MediaRef,
    Track,
    Clip,
    Blank,
    Filter,
    Transition,
    SubtitleTrack,
    SubtitleLine,
    TrackType,
)
from .profiles import MLTProfile, PROFILES

# ── Constants ─────────────────────────────────────────────────────────────────

_MLT_SERVICE_AVCODEC = "avformat"
_MLT_SERVICE_PIXBUF = "pixbuf"
_MLT_SERVICE_PANGO = "pango"

_PANGO_SIZE_MULTIPLIER = 1024

_XML_DECLARATION = '<?xml version="1.0"?>'


# ── Builder ───────────────────────────────────────────────────────────────────


class MLTXMLBuilder:
    """Constructs an MLT XML document from an MLTProjectData instance."""

    def __init__(self, project_data: MLTProjectData) -> None:
        self.data = project_data
        self._subtitle_producer_ids: dict[str, str] = {}

    # ── Public API ────────────────────────────────────────────────────────

    def build(self) -> str:
        """Build the complete MLT XML string. Returns pretty-printed XML with declaration."""
        root = self._build_root()
        self._build_profile(root)
        self._build_producers(root)
        self._build_subtitle_producers(root)
        self._build_playlists(root)
        self._build_main_tractor(root)
        return self._pretty_print(root)

    def build_xml_tree(self) -> ET.ElementTree:
        """Build and return the ElementTree (for testing)."""
        root = self._build_root()
        self._build_profile(root)
        self._build_producers(root)
        self._build_subtitle_producers(root)
        self._build_playlists(root)
        self._build_main_tractor(root)
        return ET.ElementTree(root)

    # ── Root element ──────────────────────────────────────────────────────

    def _build_root(self) -> ET.Element:
        """Create the <mlt> root element with root and title attributes."""
        return ET.Element(
            "mlt",
            attrib={
                "root": self.data.metadata.root_dir,
                "title": self.data.metadata.title,
            },
        )

    # ── Profile ───────────────────────────────────────────────────────────

    def _build_profile(self, parent: ET.Element) -> None:
        """Add <profile> with all attributes from project data fields."""
        fps_num, fps_den = _fraction_from_float(self.data.fps)
        ET.SubElement(
            parent,
            "profile",
            attrib={
                "description": self.data.metadata.profile_name,
                "width": str(self.data.width),
                "height": str(self.data.height),
                "progressive": str(self.data.progressive),
                "sample_aspect_num": str(self.data.sample_aspect_num),
                "sample_aspect_den": str(self.data.sample_aspect_den),
                "display_aspect_num": str(self.data.display_aspect_num),
                "display_aspect_den": str(self.data.display_aspect_den),
                "frame_rate_num": str(fps_num),
                "frame_rate_den": str(fps_den),
                "colorspace": str(self.data.colorspace),
            },
        )

    # ── Producers ─────────────────────────────────────────────────────────

    def _build_producers(self, parent: ET.Element) -> None:
        """Create <producer> elements for each MediaRef."""
        for media_ref in self.data.media_refs.values():
            self._add_producer_element(parent, media_ref)

    def _add_producer_element(self, parent: ET.Element, ref: MediaRef) -> None:
        """Add a single <producer> element from a MediaRef."""
        service = (
            _MLT_SERVICE_PIXBUF
            if ref.media_type == "image"
            else _MLT_SERVICE_AVCODEC
        )
        out = ref.duration_frames - 1

        producer = ET.SubElement(
            parent,
            "producer",
            attrib={"id": ref.id, "in": "0", "out": str(out)},
        )
        self._add_property(producer, "resource", ref.path)
        self._add_property(producer, "mlt_service", service)

    # ── Playlists ─────────────────────────────────────────────────────────

    def _build_playlists(self, parent: ET.Element) -> None:
        """Create <playlist> elements for each Track."""
        for track in self.data.tracks:
            playlist = ET.SubElement(parent, "playlist", attrib={"id": track.id})
            for item in track.clips:
                if isinstance(item, Clip):
                    self._add_entry(playlist, item)
                elif isinstance(item, Blank):
                    self._add_blank(playlist, item)

        # Subtitle playlists
        for sub_track in self.data.subtitle_tracks:
            self._add_subtitle_playlist(parent, sub_track)

    def _add_entry(self, playlist: ET.Element, clip: Clip) -> None:
        """Add an <entry> element for a Clip."""
        out = clip.in_point + clip.get_duration() - 1
        ET.SubElement(
            playlist,
            "entry",
            attrib={
                "producer": clip.media_ref.id,
                "in": str(clip.in_point),
                "out": str(out),
            },
        )

    def _add_blank(self, playlist: ET.Element, blank: Blank) -> None:
        """Add a <blank> element."""
        ET.SubElement(playlist, "blank", attrib={"length": str(blank.duration)})

    # ── Main tractor ──────────────────────────────────────────────────────

    def _build_main_tractor(self, parent: ET.Element) -> None:
        """Create the main <tractor> with tracks, transitions, and filters."""
        tractor = ET.SubElement(parent, "tractor", attrib={"id": "tractor_main"})

        # Tracks in reverse order: track index 0 = bottom (last in list)
        reversed_tracks = list(reversed(self.data.tracks))
        for tractor_track_index, track in enumerate(reversed_tracks):
            ET.SubElement(
                tractor,
                "track",
                attrib={"producer": track.id},
            )

        # Add subtitle track references
        for sub_track in self.data.subtitle_tracks:
            sub_playlist_id = f"playlist_{sub_track.id}"
            ET.SubElement(tractor, "track", attrib={"producer": sub_playlist_id})

        # Transitions
        for trans in self.data.transitions:
            self._build_transition_element(tractor, trans)

        # Filters from all tracks
        for track in self.data.tracks:
            for filt in track.filters:
                self._build_filter_element(tractor, filt)

    # ── Filter ────────────────────────────────────────────────────────────

    def _build_filter_element(self, parent: ET.Element, filt: Filter) -> None:
        """Add a <filter> element."""
        attrib: dict[str, str] = {"id": filt.id, "service": filt.service}
        if filt.in_point is not None:
            attrib["in"] = str(filt.in_point)
        if filt.out_point is not None:
            attrib["out"] = str(filt.out_point)

        filter_el = ET.SubElement(parent, "filter", attrib=attrib)
        for key, value in filt.properties.items():
            self._add_property(filter_el, key, value)

    # ── Transition ────────────────────────────────────────────────────────

    def _build_transition_element(
        self, parent: ET.Element, trans: Transition
    ) -> None:
        """Add a <transition> element."""
        attrib: dict[str, str] = {
            "id": trans.id,
            "service": trans.service,
            "a_track": str(trans.a_track),
            "b_track": str(trans.b_track),
            "in": str(trans.in_point),
            "out": str(trans.out_point),
        }
        trans_el = ET.SubElement(parent, "transition", attrib=attrib)
        for key, value in trans.properties.items():
            self._add_property(trans_el, key, value)

    # ── Subtitles ─────────────────────────────────────────────────────────

    def _build_subtitle_producers(self, parent: ET.Element) -> None:
        """Create pango producers and a playlist for each SubtitleTrack."""
        for sub_track in self.data.subtitle_tracks:
            pango_size = sub_track.font_size * _PANGO_SIZE_MULTIPLIER
            for line in sub_track.lines:
                producer_id = f"subtitle_{sub_track.id}_{line.index}"
                self._subtitle_producer_ids[producer_id] = producer_id

                out = line.end_frame - 1
                producer = ET.SubElement(
                    parent,
                    "producer",
                    attrib={
                        "id": producer_id,
                        "in": str(line.start_frame),
                        "out": str(out),
                    },
                )
                self._add_property(producer, "mlt_service", _MLT_SERVICE_PANGO)
                markup = f"<span font_family=\"{sub_track.font}\" size=\"{pango_size}\">{line.text}</span>"
                self._add_property(producer, "markup", markup)

    def _add_subtitle_playlist(
        self, parent: ET.Element, sub_track: SubtitleTrack
    ) -> None:
        """Add a playlist sequencing subtitle producers for a SubtitleTrack."""
        playlist_id = f"playlist_{sub_track.id}"
        playlist = ET.SubElement(parent, "playlist", attrib={"id": playlist_id})

        sorted_lines = sorted(sub_track.lines, key=lambda line: line.start_frame)
        current_frame = 0
        for line in sorted_lines:
            # Insert blank gap before this line if needed
            if line.start_frame > current_frame:
                blank_length = line.start_frame - current_frame
                self._add_blank(playlist, Blank(duration=blank_length))

            producer_id = f"subtitle_{sub_track.id}_{line.index}"
            duration = line.end_frame - line.start_frame
            out = line.start_frame + duration - 1
            ET.SubElement(
                playlist,
                "entry",
                attrib={
                    "producer": producer_id,
                    "in": str(line.start_frame),
                    "out": str(out),
                },
            )
            current_frame = line.start_frame + duration

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _add_property(parent: ET.Element, name: str, value: str) -> None:
        """Add a <property name="...">value</property> child element."""
        prop = ET.SubElement(parent, "property", attrib={"name": name})
        prop.text = value

    @staticmethod
    def _pretty_print(root: ET.Element) -> str:
        """Pretty-print an ElementTree root using minidom."""
        raw_xml = ET.tostring(root, encoding="unicode", xml_declaration=False)
        dom = parseString(raw_xml)
        pretty = dom.toprettyxml(indent="  ")
        # minidom prepends its own declaration; replace with ours
        if pretty.startswith("<?xml"):
            newline_pos = pretty.index("\n") + 1
            pretty = _XML_DECLARATION + "\n" + pretty[newline_pos:]
        return pretty


# ── Module helpers ────────────────────────────────────────────────────────────


def _fraction_from_float(value: float) -> tuple[int, int]:
    """Convert a float to a simple integer fraction (numerator, denominator).

    Handles common frame rates like 30.0 → (30, 1), 23.976 → (24000, 1001).
    """
    # Check common MLT frame rate fractions first
    common_fractions = [
        (30000, 1001),  # 29.97
        (24000, 1001),  # 23.976
        (25000, 1001),  # 24.975
    ]
    for num, den in common_fractions:
        if abs(value - num / den) < 0.002:
            return num, den

    # Integer fps
    rounded = round(value)
    if abs(value - rounded) < 0.001:
        return rounded, 1

    # Fallback: scale to integer
    denominator = 1000
    numerator = round(value * denominator)
    # Reduce
    gcd = _gcd(numerator, denominator)
    return numerator // gcd, denominator // gcd


def _gcd(a: int, b: int) -> int:
    """Compute greatest common divisor."""
    while b:
        a, b = b, a % b
    return a
