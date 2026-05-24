"""MLTProject: High-level API for MLT video project manipulation."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .models import (
    MLTProjectData, ProjectMetadata, MediaRef, Track, TrackType,
    Clip, Blank, Filter, Transition, SubtitleTrack,
)
from .profiles import get_profile, resolve_profile, MLTProfile
from .xml_builder import MLTXMLBuilder
from .xml_parser import MLTXMLParser
from .utils import (
    parse_duration, generate_id, reset_id_counters,
    make_relative_path, validate_media_exists,
)


class MLTProject:
    def __init__(
        self,
        profile: str = "atsc_1080p_30",
        title: str = "Untitled Project",
        project_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        """
        Initialize a new MLT project.
        
        Args:
            profile: MLT profile name.
            title: Project title.
            project_dir: Optional project directory for relative path resolution.
        """
        self._profile = resolve_profile(profile)
        self._project_dir = Path(project_dir) if project_dir else None
        self._saved_path: Optional[Path] = None
        
        self._data = MLTProjectData(
            metadata=ProjectMetadata(title=title, profile_name=self._profile.name),
            fps=self._profile.fps,
            width=self._profile.width,
            height=self._profile.height,
            sample_aspect_num=self._profile.sample_aspect_num,
            sample_aspect_den=self._profile.sample_aspect_den,
            display_aspect_num=self._profile.display_aspect_num,
            display_aspect_den=self._profile.display_aspect_den,
            progressive=self._profile.progressive,
            colorspace=self._profile.colorspace,
        )
        
        # Internal tracking: alias → MediaRef mapping
        self._media_aliases: dict[str, str] = {}  # alias/filename → media_ref id

        # Managers (lazily imported to avoid circular deps)
        self._audio_mgr = None
        self._subtitle_mgr = None

    @property
    def _audio(self):
        if self._audio_mgr is None:
            from .audio import AudioManager
            self._audio_mgr = AudioManager(self._data)
        return self._audio_mgr

    @property
    def _subtitles(self):
        if self._subtitle_mgr is None:
            from .subtitles import SubtitleManager
            self._subtitle_mgr = SubtitleManager(self._data.fps)
        return self._subtitle_mgr

    # ── Media Management ───────────────────────────────────────────────────

    def add_media(
        self,
        path: Union[str, Path],
        alias: Optional[str] = None,
        copy_to_project: bool = False,
    ) -> str:
        """
        Register a media file with the project.
        Returns the alias/filename string for referencing.
        """
        path = Path(path)
        if not path.is_absolute() and self._project_dir:
            path = self._project_dir / path
        
        if copy_to_project and self._project_dir:
            dest = self._project_dir / path.name
            if not dest.exists():
                shutil.copy2(path, dest)
            path = dest
        
        resolved = validate_media_exists(path)
        
        # Determine relative path
        base = self._project_dir or resolved.parent
        rel_path = make_relative_path(resolved, base)
        
        # Detect media type from extension
        ext = path.suffix.lower()
        if ext in (".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"):
            media_type = "audio"
        elif ext in (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".svg"):
            media_type = "image"
        else:
            media_type = "video"
        
        # Determine duration (set to 0 for now — will be probed or set by user)
        # For MVP, default to 10 seconds worth of frames
        duration_frames = int(10 * self._data.fps)
        
        alias = alias or path.name
        media_id = generate_id("producer")
        
        media_ref = MediaRef(
            id=media_id,
            filename=path.name,
            path=rel_path,
            media_type=media_type,
            duration_frames=duration_frames,
        )
        
        self._data.media_refs[media_id] = media_ref
        self._media_aliases[alias] = media_id
        # Also register by filename
        if alias != path.name:
            self._media_aliases[path.name] = media_id
        
        return alias

    def list_media(self) -> list[dict]:
        """Return list of registered media."""
        result = []
        for mid, ref in self._data.media_refs.items():
            result.append({
                "id": ref.id,
                "filename": ref.filename,
                "path": ref.path,
                "type": ref.media_type,
            })
        return result

    def set_media_duration(self, media: str, duration: Union[str, int, float]) -> None:
        """Set the duration of a registered media in frames."""
        ref = self._resolve_media(media)
        frames = parse_duration(duration, self._data.fps)
        ref.duration_frames = frames
        if ref.out_point == 0 or ref.out_point > frames:
            ref.out_point = frames

    # ── Timeline Construction ──────────────────────────────────────────────

    def add_track(
        self,
        track_type: Union[str, TrackType] = TrackType.VIDEO,
        name: str = "",
    ) -> int:
        """Add a new track. Returns track index (0-based)."""
        if isinstance(track_type, str):
            track_type = TrackType(track_type)
        index = len(self._data.tracks)
        track = Track(
            id=generate_id("playlist"),
            index=index,
            track_type=track_type,
            name=name,
        )
        self._data.tracks.append(track)
        return index

    def add_clip(
        self,
        track: int,
        media: str,
        start: Union[str, int, float] = 0,
        duration: Optional[Union[str, int, float]] = None,
        in_point: Union[str, int, float] = 0,
        out_point: Optional[Union[str, int, float]] = None,
    ) -> str:
        """Add a clip to a track. Returns clip ID."""
        media_ref = self._resolve_media(media)
        t = self._ensure_track(track)
        
        start_frames = self._normalize_time(start)
        in_frames = self._normalize_time(in_point)
        
        if out_point is not None:
            out_frames = self._normalize_time(out_point)
        else:
            out_frames = 0
        
        if duration is not None:
            dur_frames = self._normalize_time(duration)
        else:
            if out_frames > 0:
                dur_frames = out_frames - in_frames
            else:
                dur_frames = media_ref.duration_frames - in_frames
        
        clip_id = generate_id("clip")
        clip = Clip(
            id=clip_id,
            media_ref=media_ref,
            track_index=track,
            position=start_frames,
            in_point=in_frames,
            out_point=out_frames,
            duration=dur_frames,
        )
        t.clips.append(clip)
        return clip_id

    def insert_clip(
        self,
        track: int,
        position: Union[str, int, float],
        media: str,
        duration: Optional[Union[str, int, float]] = None,
        in_point: Union[str, int, float] = 0,
    ) -> str:
        """
        Insert a clip at a position, pushing existing clips to the right.
        Returns clip ID.
        """
        pos_frames = self._normalize_time(position)
        media_ref = self._resolve_media(media)
        t = self._ensure_track(track)
        in_frames = self._normalize_time(in_point)
        
        if duration is not None:
            dur_frames = self._normalize_time(duration)
        else:
            dur_frames = media_ref.duration_frames - in_frames
        
        clip_id = generate_id("clip")
        new_clip = Clip(
            id=clip_id,
            media_ref=media_ref,
            track_index=track,
            position=pos_frames,
            in_point=in_frames,
            duration=dur_frames,
        )
        
        # Shift all clips at or after position
        for item in t.clips:
            if isinstance(item, Clip) and item.position >= pos_frames:
                item.position += dur_frames
            elif isinstance(item, Blank):
                # Blanks don't have position; they're ordered implicitly
                pass
        
        t.clips.append(new_clip)
        # Sort clips by position for consistency
        t.clips.sort(key=lambda x: x.position if isinstance(x, Clip) else -1)
        
        return clip_id

    def remove_clip(
        self,
        track: int,
        position: Union[str, int, float],
    ) -> bool:
        """Remove clip at position, replace with blank. Returns True if found."""
        pos_frames = self._normalize_time(position)
        t = self._ensure_track(track)
        
        for i, item in enumerate(t.clips):
            if isinstance(item, Clip) and item.position == pos_frames:
                blank = Blank(duration=item.get_duration())
                t.clips[i] = blank
                return True
        return False

    # ── Effects & Filters ─────────────────────────────────────────────────

    def add_filter(self, track: int, filter_name: str, **params) -> str:
        """Add a filter to a track. Returns filter ID."""
        from .effects import build_filter_properties
        t = self._ensure_track(track)

        properties = build_filter_properties(filter_name, **params)
        filter_id = generate_id("filter")

        filt = Filter(
            id=filter_id,
            service=filter_name,
            properties=properties,
        )
        t.filters.append(filt)
        return filter_id

    def add_transition(
        self,
        track_a: int,
        track_b: int,
        start: Union[str, int, float],
        duration: Union[str, int, float],
        type: str = "crossfade",
        **params,
    ) -> str:
        """Add a transition between two tracks. Returns transition ID."""
        from .effects import resolve_transition_type

        start_frames = self._normalize_time(start)
        duration_frames = self._normalize_time(duration)

        mapping = resolve_transition_type(type)
        service = mapping["service"]
        default_props = mapping.get("properties", {})

        # Merge default props with user params
        merged_props = {**default_props}
        for k, v in params.items():
            merged_props[k] = str(v)

        trans_id = generate_id("transition")
        trans = Transition(
            id=trans_id,
            service=service,
            a_track=track_a,
            b_track=track_b,
            in_point=start_frames,
            out_point=start_frames + duration_frames,
            properties=merged_props,
        )
        self._data.transitions.append(trans)
        return trans_id

    # ── Subtitles ──────────────────────────────────────────────────────────

    def add_subtitles(self, filepath: Union[str, Path], encoding: str = "utf-8") -> str:
        """Import subtitles from an SRT or ASS file. Returns subtitle track ID."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()

        if ext == ".srt":
            track = self._subtitles.import_srt(filepath, encoding)
        elif ext in (".ass", ".ssa"):
            track = self._subtitles.import_ass(filepath, encoding)
        else:
            raise ValueError(f"Unsupported subtitle format: {ext}. Supported: .srt, .ass, .ssa")

        self._data.subtitle_tracks.append(track)
        return track.id

    def add_subtitle_line(
        self,
        text: str,
        start: Union[str, int, float],
        duration: Union[str, int, float],
        style: str = "",
        track_index: int = 0,
    ) -> str:
        """Add a single subtitle line. Returns line index."""
        # Ensure a subtitle track exists
        while len(self._data.subtitle_tracks) <= track_index:
            from .models import SubtitleTrack
            self._data.subtitle_tracks.append(SubtitleTrack(
                id=generate_id("subtitle"),
            ))

        sub_track = self._data.subtitle_tracks[track_index]
        line = self._subtitles.add_line(sub_track, text, start, duration, style)
        return str(line.index)

    # ── Audio ──────────────────────────────────────────────────────────────

    def set_audio_level(self, track: int, gain: float) -> str:
        """Set audio level for a track. Returns filter ID."""
        filt = self._audio.set_volume(track, gain)
        t = self._ensure_track(track)
        t.filters.append(filt)
        return filt.id

    def add_background_music(
        self,
        path: Union[str, Path],
        volume: float = 0.3,
        fade_in: Optional[Union[str, int, float]] = None,
        fade_out: Optional[Union[str, int, float]] = None,
    ) -> int:
        """Add background music. Returns track index of the new music track."""
        # Create a new audio track
        track_index = self.add_track(track_type=TrackType.AUDIO, name="Background Music")

        # Add the media to the project
        alias = self.add_media(path)

        # Get timeline duration for music
        timeline_dur = self.get_timeline_duration()
        if timeline_dur == 0:
            timeline_dur = self._normalize_time("30s")  # default 30s

        # Add clip spanning the timeline
        self.add_clip(track=track_index, media=alias, start=0, duration=timeline_dur)

        # Apply volume filter
        vol_filt = self._audio.set_volume(track_index, volume)
        t = self._ensure_track(track_index)
        t.filters.append(vol_filt)

        # Apply fade in/out
        if fade_in is not None:
            fi = self._audio.fade_in(track_index, fade_in)
            t.filters.append(fi)

        if fade_out is not None:
            fo = self._audio.fade_out(track_index, fade_out, track_duration=timeline_dur)
            t.filters.append(fo)

        return track_index

    # ── Rendering ──────────────────────────────────────────────────────────

    def render(
        self,
        output_path: Union[str, Path],
        profile: Optional[str] = None,
        vcodec: str = "libx264",
        acodec: str = "aac",
        crf: int = 23,
        preset: str = "medium",
        audio_bitrate: str = "192k",
        additional_args: Optional[list[str]] = None,
    ) -> Path:
        """
        Render the project to a video file.
        First saves a temporary .mlt file (if not already saved),
        then calls export.render() to execute melt-7.
        Returns Path to the rendered output file.
        """
        from .export import render as do_render

        output_path = Path(output_path)

        # Save temp .mlt if not already saved
        if self._saved_path is None:
            tmp_path = output_path.parent / f"_temp_{output_path.stem}.mlt"
            self.save(tmp_path, snapshot=False)
            project_path = tmp_path
        else:
            project_path = self._saved_path

        result = do_render(
            project_path=project_path,
            output_path=output_path,
            profile=profile,
            vcodec=vcodec,
            acodec=acodec,
            crf=crf,
            preset=preset,
            audio_bitrate=audio_bitrate,
            additional_args=additional_args,
        )

        return output_path

    def render_preset(
        self,
        output_path: Union[str, Path],
        preset: str,
    ) -> Path:
        """Render using a named preset. See export.RENDER_PRESETS."""
        from .export import render_preset as do_render_preset

        output_path = Path(output_path)

        if self._saved_path is None:
            tmp_path = output_path.parent / f"_temp_{output_path.stem}.mlt"
            self.save(tmp_path, snapshot=False)
            project_path = tmp_path
        else:
            project_path = self._saved_path

        do_render_preset(
            project_path=project_path,
            output_path=output_path,
            preset_name=preset,
        )

        return output_path

    @staticmethod
    def check_melt() -> tuple[bool, str]:
        """Check if melt-7 is available."""
        from .export import check_melt_available
        return check_melt_available()

    # ── Save / Load ────────────────────────────────────────────────────────

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> MLTProject:
        """Load an existing .mlt project file."""
        filepath = Path(filepath)
        parser = MLTXMLParser()
        data = parser.parse_file(filepath)
        
        project = cls.__new__(cls)
        project._data = data
        project._project_dir = filepath.parent
        project._saved_path = filepath
        project._profile = resolve_profile(data.metadata.profile_name)
        
        # Rebuild media aliases
        project._media_aliases = {}
        project._audio_mgr = None
        project._subtitle_mgr = None
        for mid, ref in data.media_refs.items():
            project._media_aliases[ref.filename] = mid
        
        return project

    def save(self, filepath: Union[str, Path], snapshot: bool = True) -> Path:
        """
        Save the project as .mlt file.
        If snapshot=True, also save a timestamped copy to snapshots/.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        builder = MLTXMLBuilder(self._data)
        xml_str = builder.build()
        filepath.write_text(xml_str, encoding="utf-8")
        self._saved_path = filepath
        
        if snapshot:
            snapshot_dir = filepath.parent / "snapshots"
            snapshot_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_path = snapshot_dir / f"{filepath.stem}_{ts}.mlt"
            snapshot_path.write_text(xml_str, encoding="utf-8")
        
        return filepath

    def export_mlt(self, filepath: Union[str, Path]) -> Path:
        """Alias for save() — explicit MLT export."""
        return self.save(filepath, snapshot=True)

    # ── Description / Inspection ───────────────────────────────────────────

    def describe(self) -> str:
        """Generate a human-readable text description of the project timeline."""
        lines = []
        lines.append(f"Project: {self._data.metadata.title}")
        lines.append(f"Profile: {self._data.metadata.profile_name} ({self._data.width}x{self._data.height} @ {self._data.fps}fps)")
        
        total = self.get_timeline_duration()
        from .utils import frames_to_timecode
        lines.append(f"Duration: {total} frames ({frames_to_timecode(total, self._data.fps)})")
        lines.append("")
        
        for t in self._data.tracks:
            type_str = t.track_type.value
            name_str = f' "{t.name}"' if t.name else ""
            lines.append(f"Track {t.index} ({type_str}){name_str}:")
            
            current_pos = 0
            for item in t.clips:
                if isinstance(item, Clip):
                    start_tc = frames_to_timecode(item.position, self._data.fps)
                    end_tc = frames_to_timecode(item.position + item.get_duration(), self._data.fps)
                    lines.append(f"  [{start_tc} → {end_tc}] {item.media_ref.filename} ({item.media_ref.id})")
                    current_pos = item.position + item.get_duration()
                elif isinstance(item, Blank):
                    lines.append(f"  [blank: {item.duration} frames]")
            lines.append("")
        
        # Filters section
        has_filters = False
        for t in self._data.tracks:
            if t.filters:
                if not has_filters:
                    lines.append("Filters:")
                    has_filters = True
                for f in t.filters:
                    props_str = ", ".join(f"{k}={v}" for k, v in f.properties.items())
                    lines.append(f"  Track {t.index}: {f.service} {props_str}")
        if has_filters:
            lines.append("")
        
        if self._data.transitions:
            lines.append("Transitions:")
            for tr in self._data.transitions:
                from .utils import frames_to_timecode
                start_tc = frames_to_timecode(tr.in_point, self._data.fps)
                end_tc = frames_to_timecode(tr.out_point, self._data.fps)
                lines.append(f"  Track {tr.a_track}→{tr.b_track}: {tr.service} [{start_tc} → {end_tc}]")
            lines.append("")
        
        if self._data.subtitle_tracks:
            for st in self._data.subtitle_tracks:
                src = f" from {st.source_file}" if st.source_file else ""
                lines.append(f"Subtitles: {len(st.lines)} lines{src}")
        
        return "\n".join(lines)

    def get_timeline_duration(self) -> int:
        """Return total timeline duration in frames (max across all tracks)."""
        max_dur = 0
        for t in self._data.tracks:
            for item in t.clips:
                if isinstance(item, Clip):
                    end = item.position + item.get_duration()
                    if end > max_dur:
                        max_dur = end
                elif isinstance(item, Blank):
                    pass  # blanks don't extend the track
        return max_dur

    # ── Internal helpers ───────────────────────────────────────────────────

    def _resolve_media(self, media: str) -> MediaRef:
        """Find a MediaRef by alias or filename."""
        # Exact alias match
        if media in self._media_aliases:
            return self._data.media_refs[self._media_aliases[media]]
        # Filename match
        for mid, ref in self._data.media_refs.items():
            if ref.filename == media:
                return ref
        # Partial match (filename without extension)
        for mid, ref in self._data.media_refs.items():
            if ref.filename.startswith(media):
                return ref
        raise ValueError(f"Media not found: {media!r}. Registered: {list(self._media_aliases.keys())}")

    def _ensure_track(self, track_index: int, track_type: TrackType = TrackType.VIDEO) -> Track:
        """Get or create a track at the given index."""
        while len(self._data.tracks) <= track_index:
            idx = len(self._data.tracks)
            self._data.tracks.append(Track(
                id=generate_id("playlist"),
                index=idx,
                track_type=track_type,
            ))
        return self._data.tracks[track_index]

    def _normalize_time(self, value: Union[str, int, float, None]) -> int:
        """Convert any time value to frames. Returns 0 for None."""
        if value is None:
            return 0
        return parse_duration(value, self._data.fps)

    @property
    def data(self) -> MLTProjectData:
        """Access the underlying project data."""
        return self._data

    @property
    def fps(self) -> float:
        """Project frame rate."""
        return self._data.fps
