"""Audio management: volume, normalization, background music, mixing."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

from .models import Filter, MLTProjectData
from .utils import parse_duration, generate_id, build_keyframe_string


class AudioManager:
    """Manages audio levels, mixing, and background music for a project."""

    def __init__(self, project_data: MLTProjectData) -> None:
        self._data = project_data

    @property
    def fps(self) -> float:
        return self._data.fps

    def set_volume(
        self,
        track_index: int,
        gain: float,
        start: Optional[Union[str, int, float]] = None,
        end: Optional[Union[str, int, float]] = None,
    ) -> Filter:
        """Set volume level for a track. Returns Filter object."""
        filter_id = generate_id("filter")
        properties = {"gain": str(gain)}

        in_pt = None
        out_pt = None
        if start is not None:
            in_pt = parse_duration(start, self.fps)
        if end is not None:
            out_pt = parse_duration(end, self.fps)

        filt = Filter(
            id=filter_id,
            service="volume",
            properties=properties,
            in_point=in_pt,
            out_point=out_pt,
        )
        return filt

    def fade_in(
        self,
        track_index: int,
        duration: Union[str, int, float],
    ) -> Filter:
        """Apply fade-in using keyframed volume: 0 → 1."""
        duration_frames = parse_duration(duration, self.fps)
        keyframes = [
            (0, 0.0),
            (duration_frames, 1.0),
        ]

        filter_id = generate_id("filter")
        filt = Filter(
            id=filter_id,
            service="volume",
            properties={
                "gain": build_keyframe_string(keyframes),
                "end": str(duration_frames),
            },
            in_point=0,
            out_point=duration_frames,
        )
        return filt

    def fade_out(
        self,
        track_index: int,
        duration: Union[str, int, float],
        track_duration: Optional[Union[str, int, float]] = None,
    ) -> Filter:
        """Apply fade-out: 1 → 0."""
        duration_frames = parse_duration(duration, self.fps)

        if track_duration is not None:
            total_frames = parse_duration(track_duration, self.fps)
        else:
            # Try to compute from track
            total_frames = self._get_track_duration(track_index)

        start_frame = max(0, total_frames - duration_frames)
        end_frame = total_frames

        keyframes = [
            (start_frame, 1.0),
            (end_frame, 0.0),
        ]

        filter_id = generate_id("filter")
        gain_str = f"{start_frame}~=1.0;{end_frame}=0.0"
        filt = Filter(
            id=filter_id,
            service="volume",
            properties={
                "gain": gain_str,
                "end": str(end_frame),
            },
            in_point=start_frame,
            out_point=end_frame,
        )
        return filt

    def normalize(
        self,
        track_index: int,
        target_lufs: float = -23.0,
    ) -> Filter:
        """Apply loudness normalization to a track."""
        filter_id = generate_id("filter")
        filt = Filter(
            id=filter_id,
            service="volume",
            properties={
                "normalise": "1",
            },
        )
        return filt

    def create_background_music_setup(
        self,
        media_path: str,
        volume: float = 0.3,
        fade_in: Optional[Union[str, int, float]] = None,
        fade_out: Optional[Union[str, int, float]] = None,
        loop: bool = True,
    ) -> dict:
        """Create full background music setup. Returns dict with filter info."""
        vol_filter = None
        fade_in_filter = None
        fade_out_filter = None

        # Volume filter
        vol_filter = Filter(
            id=generate_id("filter"),
            service="volume",
            properties={"gain": str(volume)},
        )

        # Fade in
        if fade_in is not None:
            fade_frames = parse_duration(fade_in, self.fps)
            keyframes = [(0, 0.0), (fade_frames, volume)]
            fade_in_filter = Filter(
                id=generate_id("filter"),
                service="volume",
                properties={"gain": build_keyframe_string(keyframes)},
                in_point=0,
                out_point=fade_frames,
            )

        # Fade out
        if fade_out is not None:
            fade_frames = parse_duration(fade_out, self.fps)
            # We can't compute start without total duration; leave as template
            fade_out_filter = Filter(
                id=generate_id("filter"),
                service="volume",
                properties={
                    "gain": f"0=0~={volume};{fade_frames}=0",
                    "end": str(fade_frames),
                },
            )

        return {
            "volume_filter": vol_filter,
            "fade_in_filter": fade_in_filter,
            "fade_out_filter": fade_out_filter,
        }

    def _get_track_duration(self, track_index: int) -> int:
        """Get the total duration of a track in frames."""
        if track_index >= len(self._data.tracks):
            return 0
        track = self._data.tracks[track_index]
        max_end = 0
        for item in track.clips:
            if hasattr(item, "position") and hasattr(item, "get_duration"):
                end = item.position + item.get_duration()
                if end > max_end:
                    max_end = end
        return max_end

    @staticmethod
    def probe_audio(filepath: Union[str, Path]) -> dict:
        """
        Probe an audio file using ffprobe.
        Returns dict with: duration, codec, sample_rate, channels, bit_rate.
        Raises RuntimeError if ffprobe is not available or file cannot be probed.
        """
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe is not available. Install it via your package manager.")

        cmd = [
            ffprobe, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams",
            str(filepath),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffprobe timed out")
        except FileNotFoundError:
            raise RuntimeError("ffprobe not found")

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"ffprobe returned invalid JSON: {result.stdout[:200]}")

        # Find audio stream
        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        if audio_stream is None:
            raise RuntimeError("No audio stream found")

        format_info = data.get("format", {})

        return {
            "duration": float(format_info.get("duration", 0)),
            "codec": audio_stream.get("codec_name", "unknown"),
            "sample_rate": int(audio_stream.get("sample_rate", 0)),
            "channels": int(audio_stream.get("channels", 0)),
            "bit_rate": int(format_info.get("bit_rate", 0)),
        }

    @staticmethod
    def is_ffprobe_available() -> bool:
        """Check if ffprobe is available on the system."""
        return shutil.which("ffprobe") is not None
