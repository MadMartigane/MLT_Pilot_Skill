"""Subtitle handling: SRT import, ASS import, line-by-line creation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union

from .models import SubtitleLine, SubtitleTrack
from .utils import timecode_to_frames, parse_duration, generate_id


class SubtitleManager:
    """Manages subtitle tracks for a project."""

    def __init__(self, fps: float) -> None:
        self._fps = fps

    def import_srt(self, filepath: Union[str, Path], encoding: str = "utf-8") -> SubtitleTrack:
        """Parse an SRT file into a SubtitleTrack."""
        filepath = Path(filepath)
        content = filepath.read_text(encoding=encoding)
        return self._parse_srt_content(content, str(filepath))

    def import_ass(self, filepath: Union[str, Path], encoding: str = "utf-8") -> SubtitleTrack:
        """Parse an ASS/SSA subtitle file into a SubtitleTrack."""
        filepath = Path(filepath)
        content = filepath.read_text(encoding=encoding)
        return self._parse_ass_content(content, str(filepath))

    def create_track(
        self,
        lines: list[dict],
        font: str = "Sans",
        font_size: int = 26,
    ) -> SubtitleTrack:
        """
        Create a subtitle track from a list of line dicts.
        Each dict: {"text": str, "start": str|int|float, "duration": str|int|float}
        """
        track = SubtitleTrack(
            id=generate_id("subtitle"),
            font=font,
            font_size=font_size,
        )
        for i, line_data in enumerate(lines):
            text = line_data["text"]
            start = parse_duration(line_data["start"], self._fps)
            duration = parse_duration(line_data["duration"], self._fps)
            track.lines.append(SubtitleLine(
                index=i + 1,
                text=text,
                start_frame=start,
                end_frame=start + duration,
            ))
        return track

    def add_line(
        self,
        track: SubtitleTrack,
        text: str,
        start: Union[str, int, float],
        duration: Union[str, int, float],
        style: str = "",
    ) -> SubtitleLine:
        """Add a single line to an existing subtitle track."""
        start_frames = parse_duration(start, self._fps)
        duration_frames = parse_duration(duration, self._fps)
        line = SubtitleLine(
            index=len(track.lines) + 1,
            text=text,
            start_frame=start_frames,
            end_frame=start_frames + duration_frames,
            style=style,
        )
        track.lines.append(line)
        return line

    # ── SRT Parsing ───────────────────────────────────────────────────────

    def _parse_srt_content(self, content: str, source: Optional[str] = None) -> SubtitleTrack:
        """Parse SRT content string into a SubtitleTrack."""
        # Strip BOM if present
        content = content.lstrip("\ufeff")

        # Split into blocks by double newline
        blocks = re.split(r"\n\s*\n", content.strip())

        track = SubtitleTrack(
            id=generate_id("subtitle"),
            source_file=source,
        )

        index = 1
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            lines = block.split("\n")
            if len(lines) < 2:
                continue

            # Find the timecode line (contains -->)
            tc_line = None
            text_start_idx = 0
            for i, line in enumerate(lines):
                if "-->" in line:
                    tc_line = line.strip()
                    text_start_idx = i + 1
                    break

            if tc_line is None:
                continue

            # Parse timecodes
            tc_match = re.match(
                r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})",
                tc_line,
            )
            if not tc_match:
                continue

            start_tc = tc_match.group(1).replace(",", ".")
            end_tc = tc_match.group(2).replace(",", ".")

            start_frame = timecode_to_frames(start_tc, self._fps)
            end_frame = timecode_to_frames(end_tc, self._fps)

            # Get text (may span multiple lines)
            text_lines = lines[text_start_idx:]
            text = "\n".join(text_lines).strip()
            if not text:
                continue

            text = self._clean_srt_text(text)

            track.lines.append(SubtitleLine(
                index=index,
                text=text,
                start_frame=start_frame,
                end_frame=end_frame,
            ))
            index += 1

        if not track.lines:
            raise ValueError("No valid subtitle blocks found in SRT content")

        return track

    def _parse_ass_content(self, content: str, source: Optional[str] = None) -> SubtitleTrack:
        """Parse ASS content string into a SubtitleTrack."""
        track = SubtitleTrack(
            id=generate_id("subtitle"),
            source_file=source,
        )

        in_events = False
        index = 1

        for line in content.splitlines():
            line = line.strip()

            if line.startswith("[Events]"):
                in_events = True
                continue
            if line.startswith("["):
                in_events = False
                continue

            if not in_events:
                continue

            if not line.startswith("Dialogue:"):
                continue

            # Format: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
            # The Text field may contain commas, so split only first 9
            parts = line[len("Dialogue:"):].strip().split(",", 9)
            if len(parts) < 10:
                continue

            start_ass = parts[1].strip()
            end_ass = parts[2].strip()
            style = parts[3].strip()
            text = parts[9].strip()

            # Remove ASS formatting tags
            text = re.sub(r"\{[^}]*\}", "", text)
            text = text.replace("\\N", "\n").replace("\\n", "\n")
            text = self._clean_srt_text(text)

            if not text:
                continue

            start_frame = self._parse_ass_time(start_ass)
            end_frame = self._parse_ass_time(end_ass)

            track.lines.append(SubtitleLine(
                index=index,
                text=text,
                start_frame=start_frame,
                end_frame=end_frame,
                style=style,
            ))
            index += 1

        if not track.lines:
            raise ValueError("No valid dialogue lines found in ASS content")

        return track

    def _parse_ass_time(self, time_str: str) -> int:
        """Parse ASS time 'H:MM:SS.CC' → frames. CC is centiseconds."""
        time_str = time_str.strip()
        match = re.match(r"(\d+):(\d{2}):(\d{2})\.(\d{2})", time_str)
        if not match:
            return 0
        h, m, s, cs = match.groups()
        total_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100.0
        return int(round(total_seconds * self._fps))

    def _clean_srt_text(self, text: str) -> str:
        """Strip SRT formatting tags (<i>, <b>, <font>, etc.). Keep text content."""
        # Remove HTML-like tags
        text = re.sub(r"</?[^>]+>", "", text)
        # Normalize whitespace
        text = " ".join(text.split())
        return text.strip()
