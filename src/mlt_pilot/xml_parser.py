"""Parse existing MLT XML files into internal project data models."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from .models import (
    Blank,
    Clip,
    Filter,
    MediaRef,
    MLTProjectData,
    ProjectMetadata,
    SubtitleLine,
    SubtitleTrack,
    Track,
    TrackType,
    Transition,
)
from .profiles import PROFILES
from .utils import generate_id

# ── Media type detection constants ────────────────────────────────────────

AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"})
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".svg"})


class MLTXMLParser:
    """Parses MLT XML files into MLTProjectData objects."""

    def parse_file(self, filepath: str | Path) -> MLTProjectData:
        """Parse an .mlt file from disk. Raises FileNotFoundError if missing."""
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"MLT file not found: {filepath}")
        tree = ET.parse(str(filepath))
        return self._parse_root(tree.getroot())

    def parse_string(self, xml_string: str) -> MLTProjectData:
        """Parse an MLT XML string."""
        root = ET.fromstring(xml_string)
        return self._parse_root(root)

    # ── Internal parsing methods ─────────────────────────────────────────

    def _parse_root(self, root: ET.Element) -> MLTProjectData:
        """Extract title from root attributes, then delegate to sub-parsers."""
        title = root.get("title", "Untitled Project")
        data = MLTProjectData(metadata=ProjectMetadata(title=title))

        self._parse_profile(root, data)
        self._parse_subtitle_producers(root, data)
        self._parse_producers(root, data)
        self._parse_playlists(root, data)
        self._parse_tractor(root, data)

        return data

    def _parse_profile(self, root: ET.Element, data: MLTProjectData) -> None:
        """Find first <profile> element and set fps/width/height/etc."""
        profile_elem = root.find("profile")
        if profile_elem is None:
            return

        width = int(profile_elem.get("width", str(data.width)))
        height = int(profile_elem.get("height", str(data.height)))
        progressive = int(profile_elem.get("progressive", str(data.progressive)))
        sample_aspect_num = int(
            profile_elem.get("sample_aspect_num", str(data.sample_aspect_num))
        )
        sample_aspect_den = int(
            profile_elem.get("sample_aspect_den", str(data.sample_aspect_den))
        )
        display_aspect_num = int(
            profile_elem.get("display_aspect_num", str(data.display_aspect_num))
        )
        display_aspect_den = int(
            profile_elem.get("display_aspect_den", str(data.display_aspect_den))
        )
        frame_rate_num = int(profile_elem.get("frame_rate_num", "30"))
        frame_rate_den = int(profile_elem.get("frame_rate_den", "1"))
        colorspace = int(profile_elem.get("colorspace", str(data.colorspace)))
        fps = frame_rate_num / frame_rate_den if frame_rate_den else 30.0

        # Try to match against known profiles by comparing all fields
        matched_name = ""
        for name, prof in PROFILES.items():
            if (
                prof.width == width
                and prof.height == height
                and prof.progressive == progressive
                and prof.sample_aspect_num == sample_aspect_num
                and prof.sample_aspect_den == sample_aspect_den
                and prof.display_aspect_num == display_aspect_num
                and prof.display_aspect_den == display_aspect_den
                and prof.frame_rate_num == frame_rate_num
                and prof.frame_rate_den == frame_rate_den
                and prof.colorspace == colorspace
            ):
                matched_name = name
                break

        data.width = width
        data.height = height
        data.fps = fps
        data.progressive = progressive
        data.sample_aspect_num = sample_aspect_num
        data.sample_aspect_den = sample_aspect_den
        data.display_aspect_num = display_aspect_num
        data.display_aspect_den = display_aspect_den
        data.colorspace = colorspace

        if matched_name:
            data.metadata.profile_name = matched_name

    def _parse_producers(self, root: ET.Element, data: MLTProjectData) -> None:
        """Parse all <producer> elements. Skip pango producers (subtitles)."""
        for producer in root.findall("producer"):
            service = self._get_property(producer, "mlt_service") or ""
            if service == "pango":
                continue

            producer_id = producer.get("id", generate_id("producer"))
            resource = self._get_property(producer, "resource") or ""
            in_point = int(producer.get("in", "0"))
            out_point = int(producer.get("out", "0"))
            duration = (out_point - in_point + 1) if out_point > in_point else 0
            media_type = self._guess_media_type(resource, service)
            filename = os.path.basename(resource)

            data.media_refs[producer_id] = MediaRef(
                id=producer_id,
                filename=filename,
                path=resource,
                media_type=media_type,
                duration_frames=duration,
                in_point=in_point,
                out_point=out_point,
            )

    def _parse_playlists(self, root: ET.Element, data: MLTProjectData) -> None:
        """Parse all <playlist> elements. Skip subtitle playlists."""
        track_index = 0
        for playlist in root.findall("playlist"):
            playlist_id = playlist.get("id", "")
            if "subtitle" in playlist_id:
                continue

            track_type = TrackType.VIDEO
            position = 0

            track = Track(
                id=playlist_id,
                index=track_index,
                track_type=track_type,
                name=playlist_id,
            )

            for entry in playlist:
                if entry.tag == "entry":
                    producer_id = entry.get("producer", "")
                    media_ref = data.media_refs.get(producer_id)

                    entry_in = int(entry.get("in", "0"))
                    entry_out = int(entry.get("out", "0"))
                    # MLT in/out are inclusive frame indices
                    clip_duration = (entry_out - entry_in + 1) if entry_out >= entry_in else 0

                    if media_ref is not None:
                        # Determine track type from the first clip's media type
                        if track_type == TrackType.VIDEO and media_ref.media_type == "audio":
                            track_type = TrackType.AUDIO

                        clip = Clip(
                            id=generate_id("clip"),
                            media_ref=media_ref,
                            track_index=track_index,
                            position=position,
                            in_point=entry_in,
                            out_point=entry_out,
                            duration=clip_duration,
                        )
                        track.clips.append(clip)
                    position += clip_duration

                elif entry.tag == "blank":
                    length = int(entry.get("length", "0"))
                    track.clips.append(Blank(duration=length))
                    position += length

            track.track_type = track_type
            data.tracks.append(track)
            track_index += 1

    def _parse_tractor(self, root: ET.Element, data: MLTProjectData) -> None:
        """Find main tractor, extract filters and transitions."""
        tractor = root.find("tractor")
        if tractor is None:
            return

        for elem in tractor:
            if elem.tag == "filter":
                service = self._get_property(elem, "mlt_service") or "unknown"
                properties = {}
                for prop in elem.findall("property"):
                    name = prop.get("name", "")
                    if name and name != "mlt_service":
                        properties[name] = (prop.text or "")

                in_point = elem.get("in")
                out_point = elem.get("out")

                filt = Filter(
                    id=generate_id("filter"),
                    service=service,
                    properties=properties,
                    in_point=int(in_point) if in_point is not None else None,
                    out_point=int(out_point) if out_point is not None else None,
                )
                data.transitions  # ensure list exists — filters go on tracks later
                # Attach filter to the first track if tracks exist
                if data.tracks:
                    data.tracks[0].filters.append(filt)

            elif elem.tag == "transition":
                service = self._get_property(elem, "mlt_service") or "composite"
                a_track = int(elem.get("a_track", "0"))
                b_track = int(elem.get("b_track", "1"))
                in_point = int(elem.get("in", "0"))
                out_point = int(elem.get("out", "0"))

                properties = {}
                for prop in elem.findall("property"):
                    name = prop.get("name", "")
                    if name and name != "mlt_service":
                        properties[name] = (prop.text or "")

                trans = Transition(
                    id=generate_id("transition"),
                    service=service,
                    a_track=a_track,
                    b_track=b_track,
                    in_point=in_point,
                    out_point=out_point,
                    properties=properties,
                )
                data.transitions.append(trans)

    def _parse_subtitle_producers(
        self, root: ET.Element, data: MLTProjectData
    ) -> None:
        """Find pango producers and create SubtitleTrack with SubtitleLine objects."""
        lines: list[SubtitleLine] = []
        font = "Sans"
        font_size = 26

        for producer in root.findall("producer"):
            service = self._get_property(producer, "mlt_service") or ""
            if service != "pango":
                continue

            text = self._get_property(producer, "text") or ""
            markup = self._get_property(producer, "markup")
            if markup:
                text = markup

            in_point = int(producer.get("in", "0"))
            out_point = int(producer.get("out", "0"))

            prop_font = self._get_property(producer, "font")
            if prop_font:
                font = prop_font

            prop_size = self._get_property(producer, "size")
            if prop_size:
                try:
                    font_size = int(prop_size)
                except ValueError:
                    pass

            lines.append(
                SubtitleLine(
                    index=len(lines) + 1,
                    text=text,
                    start_frame=in_point,
                    end_frame=out_point,
                )
            )

        if lines:
            sub_track = SubtitleTrack(
                id=generate_id("subtitle"),
                lines=lines,
                font=font,
                font_size=font_size,
            )
            data.subtitle_tracks.append(sub_track)

    @staticmethod
    def _guess_media_type(resource: str, service: str) -> str:
        """Guess media type from file extension and/or mlt_service."""
        ext = os.path.splitext(resource)[1].lower()
        if ext in AUDIO_EXTENSIONS:
            return "audio"
        if ext in IMAGE_EXTENSIONS:
            return "image"
        if service == "pixbuf":
            return "image"
        if ext or service == "avformat":
            return "video"
        return "video"

    @staticmethod
    def _get_property(element: ET.Element, name: str) -> Optional[str]:
        """Extract a named property value from an MLT element."""
        for prop in element.findall("property"):
            if prop.get("name") == name:
                return prop.text or ""
        return None
