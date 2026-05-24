"""CLI module for mlt-pilot — provides 19 commands across 2 groups."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Union

from . import __version__
from . import skill_builder
from .effects import list_filters, list_transitions
from .export import RENDER_PRESETS, check_melt_available
from .profiles import PROFILES, get_profile, list_profiles
from .project import MLTProject
from .utils import frames_to_timecode


def _load_project(filepath: Union[str, Path]) -> MLTProject:
    """Load an existing MLT project from file."""
    return MLTProject.load(filepath)


def _save_project(project: MLTProject, filepath: Union[str, Path]) -> None:
    """Save project, overwriting the original file."""
    project.save(filepath)


# ── Handler functions ──────────────────────────────────────────────────────

def _handle_skill_build(args: argparse.Namespace) -> int:
    """Handler for `skill build`."""
    skill_builder.build_skill()
    print("Skill built successfully.")
    return 0


def _handle_skill_install(args: argparse.Namespace) -> int:
    """Handler for `skill install <target_repo>`."""
    target = Path(args.target_repo)
    if not target.is_dir():
        print(f"Error: {target} is not a directory", file=sys.stderr)
        return 1
    try:
        skill_builder.install_skill(target)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Skill installed to {target.resolve() / '.opencode' / 'skills' / 'mlt-pilot'}")
    return 0


def _handle_create(args: argparse.Namespace) -> int:
    """Handler for `create <file>`."""
    project = MLTProject(
        profile=args.profile or "atsc_1080p_30",
        title=args.title or "Untitled Project",
    )
    project.save(args.file)
    print(f"Project created: {args.file}")
    return 0


def _handle_add_media(args: argparse.Namespace) -> int:
    """Handler for `add-media <file> --media <path>`."""
    project = _load_project(args.file)
    alias = project.add_media(args.media, alias=args.alias)
    _save_project(project, args.file)
    print(f"Media registered as: {alias}")
    return 0


def _handle_list_media(args: argparse.Namespace) -> int:
    """Handler for `list-media <file>`."""
    project = _load_project(args.file)
    media_list = project.list_media()
    if not media_list:
        print("No media registered.")
        return 0
    for m in media_list:
        print(f"  [{m['type']:5s}] {m['id']}  {m['filename']}  ({m['path']})")
    return 0


def _handle_add_clip(args: argparse.Namespace) -> int:
    """Handler for `add-clip <file> --track INT --media ALIAS --start TIME --duration TIME`."""
    project = _load_project(args.file)
    project.add_clip(
        track=args.track,
        media=args.media,
        start=args.start,
        duration=args.duration,
    )
    _save_project(project, args.file)
    print(f"Clip added to track {args.track}")
    return 0


def _handle_insert_clip(args: argparse.Namespace) -> int:
    """Handler for `insert-clip <file> --track INT --position INT --media ALIAS`."""
    project = _load_project(args.file)
    project.insert_clip(
        track=args.track,
        position=args.position,
        media=args.media,
        duration=args.duration,
    )
    _save_project(project, args.file)
    print(f"Clip inserted on track {args.track} at position {args.position}")
    return 0


def _handle_remove_clip(args: argparse.Namespace) -> int:
    """Handler for `remove-clip <file> --track INT --position INT`."""
    project = _load_project(args.file)
    found = project.remove_clip(track=args.track, position=args.position)
    if not found:
        print(f"Error: no clip found on track {args.track} at position {args.position}", file=sys.stderr)
        return 1
    _save_project(project, args.file)
    print(f"Clip removed from track {args.track} at position {args.position}")
    return 0


def _handle_add_filter(args: argparse.Namespace) -> int:
    """Handler for `add-filter <file> --track INT --filter NAME [key=val ...]`."""
    params = {}
    for pair in (args.params or []):
        if "=" not in pair:
            print(f"Error: invalid parameter '{pair}', expected key=value", file=sys.stderr)
            return 1
        key, _, value = pair.partition("=")
        params[key] = value

    project = _load_project(args.file)
    project.add_filter(track=args.track, filter_name=args.filter, **params)
    _save_project(project, args.file)
    print(f"Filter '{args.filter}' added to track {args.track}")
    return 0


def _handle_add_transition(args: argparse.Namespace) -> int:
    """Handler for `add-transition <file> --track-a INT --track-b INT --start TIME --duration TIME --type STR`."""
    project = _load_project(args.file)
    project.add_transition(
        track_a=args.track_a,
        track_b=args.track_b,
        start=args.start,
        duration=args.duration,
        type=args.type,
    )
    _save_project(project, args.file)
    print(f"Transition '{args.type}' added between tracks {args.track_a} and {args.track_b}")
    return 0


def _handle_add_subtitle(args: argparse.Namespace) -> int:
    """Handler for `add-subtitle <file> --text STR --start TIME --duration TIME`."""
    project = _load_project(args.file)
    project.add_subtitle_line(
        text=args.text,
        start=args.start,
        duration=args.duration,
        style=args.style or "",
    )
    _save_project(project, args.file)
    print("Subtitle line added.")
    return 0


def _handle_add_subtitles_file(args: argparse.Namespace) -> int:
    """Handler for `add-subtitles-file <file> --file <path>`."""
    project = _load_project(args.file)
    track_id = project.add_subtitles(args.subtitle_file)
    _save_project(project, args.file)
    print(f"Subtitles imported from {args.subtitle_file} (track: {track_id})")
    return 0


def _handle_add_bgm(args: argparse.Namespace) -> int:
    """Handler for `add-bgm <file> --file <path>`."""
    project = _load_project(args.file)
    track_index = project.add_background_music(
        path=args.file_bgm,
        volume=args.volume,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
    )
    _save_project(project, args.file)
    print(f"Background music added on track {track_index}")
    return 0


def _handle_set_audio(args: argparse.Namespace) -> int:
    """Handler for `set-audio <file> --track INT --gain FLOAT`."""
    project = _load_project(args.file)
    project.set_audio_level(track=args.track, gain=args.gain)
    _save_project(project, args.file)
    print(f"Audio level set to {args.gain} on track {args.track}")
    return 0


def _handle_render(args: argparse.Namespace) -> int:
    """Handler for `render <file> --output PATH [--preset NAME]`."""
    available, message = check_melt_available()
    if not available:
        print(f"Error: {message}", file=sys.stderr)
        return 1

    project = _load_project(args.file)

    if args.preset:
        if args.preset not in RENDER_PRESETS:
            available_presets = ", ".join(sorted(RENDER_PRESETS.keys()))
            print(f"Error: unknown preset '{args.preset}'. Available: {available_presets}", file=sys.stderr)
            return 1
        project.render_preset(output_path=args.output, preset=args.preset)
    else:
        project.render(output_path=args.output)

    print(f"Rendered to {args.output}")
    return 0


def _handle_info(args: argparse.Namespace) -> int:
    """Handler for `info <file>` — show project metadata as JSON."""
    project = _load_project(args.file)
    data = project.data
    info = {
        "title": data.metadata.title,
        "profile": data.metadata.profile_name,
        "fps": data.fps,
        "width": data.width,
        "height": data.height,
        "tracks": len(data.tracks),
        "media": len(data.media_refs),
        "transitions": len(data.transitions),
        "subtitle_tracks": len(data.subtitle_tracks),
        "duration": frames_to_timecode(project.get_timeline_duration(), data.fps),
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0


def _handle_describe(args: argparse.Namespace) -> int:
    """Handler for `describe <file>` — show human-readable timeline."""
    project = _load_project(args.file)
    print(project.describe())
    return 0


def _handle_list_profiles(args: argparse.Namespace) -> int:
    """Handler for `list-profiles`."""
    names = list_profiles()
    print(f"{'Profile':<20s} {'Width':>6s} {'Height':>6s} {'FPS':>8s}  Description")
    print("-" * 70)
    for name in names:
        p = get_profile(name)
        print(f"{p.name:<20s} {p.width:>6d} {p.height:>6d} {p.fps:>8.3f}  {p.description}")
    return 0


def _handle_list_filters(args: argparse.Namespace) -> int:
    """Handler for `list-filters [--category STR]`."""
    filters = list_filters(category=args.category)
    if not filters:
        print("No filters found." if not args.category else f"No filters found for category: {args.category}")
        return 0
    print(f"{'Filter':<15s} {'Category':<12s} {'Display Name':<20s}  Description")
    print("-" * 80)
    for f in filters:
        print(f"{f.service:<15s} {f.category:<12s} {f.display_name:<20s}  {f.description}")
    return 0


def _handle_list_transitions(args: argparse.Namespace) -> int:
    """Handler for `list-transitions`."""
    transitions = list_transitions()
    if not transitions:
        print("No transitions found.")
        return 0
    print(f"{'Transition':<15s} {'Category':<12s} {'Display Name':<20s}  Description")
    print("-" * 80)
    for t in transitions:
        print(f"{t.service:<15s} {t.category:<12s} {t.display_name:<20s}  {t.description}")
    return 0


# ── Handler dispatch ───────────────────────────────────────────────────────

_HANDLERS = {
    "skill.build": _handle_skill_build,
    "skill.install": _handle_skill_install,
    "create": _handle_create,
    "add-media": _handle_add_media,
    "list-media": _handle_list_media,
    "add-clip": _handle_add_clip,
    "insert-clip": _handle_insert_clip,
    "remove-clip": _handle_remove_clip,
    "add-filter": _handle_add_filter,
    "add-transition": _handle_add_transition,
    "add-subtitle": _handle_add_subtitle,
    "add-subtitles-file": _handle_add_subtitles_file,
    "add-bgm": _handle_add_bgm,
    "set-audio": _handle_set_audio,
    "render": _handle_render,
    "info": _handle_info,
    "describe": _handle_describe,
    "list-profiles": _handle_list_profiles,
    "list-filters": _handle_list_filters,
    "list-transitions": _handle_list_transitions,
}


# ── Parser builders ────────────────────────────────────────────────────────

def _add_skill_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `skill` command group with `build` and `install` subcommands."""
    skill_parser = subparsers.add_parser("skill", help="Skill management commands")
    skill_subs = skill_parser.add_subparsers(dest="skill_command")

    # skill build
    build_parser = skill_subs.add_parser("build", help="Build the MLT Pilot skill definition")
    build_parser.set_defaults(func=_handle_skill_build)

    # skill install
    install_parser = skill_subs.add_parser("install", help="Install the MLT Pilot skill into a target repository")
    install_parser.add_argument("target_repo", help="Target repository directory")
    install_parser.set_defaults(func=_handle_skill_install)


def _add_create_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `create` command."""
    p = subparsers.add_parser("create", help="Create a new MLT project")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--profile", help="MLT profile name (default: atsc_1080p_30)", default=None)
    p.add_argument("--title", help="Project title", default=None)


def _add_add_media_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-media` command."""
    p = subparsers.add_parser("add-media", help="Register a media file with the project")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--media", required=True, help="Path to the media file")
    p.add_argument("--alias", help="Alias name for referencing the media", default=None)


def _add_list_media_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `list-media` command."""
    p = subparsers.add_parser("list-media", help="List registered media in the project")
    p.add_argument("file", help="Path to the .mlt project file")


def _add_add_clip_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-clip` command."""
    p = subparsers.add_parser("add-clip", help="Place a clip on a track")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    p.add_argument("--media", required=True, help="Media alias or filename")
    p.add_argument("--start", required=True, help="Start time (e.g., 0, 5s, 00:01:30.000)")
    p.add_argument("--duration", required=True, help="Duration (e.g., 10s, 300, 00:00:05.000)")


def _add_insert_clip_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `insert-clip` command."""
    p = subparsers.add_parser("insert-clip", help="Insert a clip at a position, shifting existing clips")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    p.add_argument("--position", required=True, help="Insertion position (frames, seconds, or timecode)")
    p.add_argument("--media", required=True, help="Media alias or filename")
    p.add_argument("--duration", help="Duration (auto-derived from media if omitted)", default=None)


def _add_remove_clip_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `remove-clip` command."""
    p = subparsers.add_parser("remove-clip", help="Remove a clip (replaced by a blank)")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    p.add_argument("--position", required=True, help="Position of the clip to remove (frames or timecode)")


def _add_add_filter_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-filter` command."""
    p = subparsers.add_parser("add-filter", help="Add a filter to a track")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    p.add_argument("--filter", required=True, help="Filter name (e.g., brightness, volume)")
    p.add_argument("params", nargs="*", help="Filter parameters as key=value pairs")


def _add_add_transition_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-transition` command."""
    p = subparsers.add_parser("add-transition", help="Add a transition between two tracks")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--track-a", type=int, required=True, dest="track_a", help="First track index")
    p.add_argument("--track-b", type=int, required=True, dest="track_b", help="Second track index")
    p.add_argument("--start", required=True, help="Transition start time")
    p.add_argument("--duration", required=True, help="Transition duration")
    p.add_argument("--type", required=True, help="Transition type (crossfade, dissolve, wipe, overlay, mix)")


def _add_add_subtitle_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-subtitle` command."""
    p = subparsers.add_parser("add-subtitle", help="Add a subtitle line")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--text", required=True, help="Subtitle text")
    p.add_argument("--start", required=True, help="Start time")
    p.add_argument("--duration", required=True, help="Duration")
    p.add_argument("--style", help="Optional style name (for ASS)", default=None)


def _add_add_subtitles_file_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-subtitles-file` command."""
    p = subparsers.add_parser("add-subtitles-file", help="Import subtitles from an SRT or ASS file")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--file", dest="subtitle_file", required=True, help="SRT or ASS subtitle file")


def _add_add_bgm_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `add-bgm` command."""
    p = subparsers.add_parser("add-bgm", help="Add background music")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--file", dest="file_bgm", required=True, help="Audio file path")
    p.add_argument("--volume", type=float, default=0.3, help="Volume level (default: 0.3)")
    p.add_argument("--fade-in", default=None, help="Fade-in duration")
    p.add_argument("--fade-out", default=None, help="Fade-out duration")


def _add_set_audio_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `set-audio` command."""
    p = subparsers.add_parser("set-audio", help="Set audio level for a track")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--track", type=int, required=True, help="Track index (0-based)")
    p.add_argument("--gain", type=float, required=True, help="Gain value (e.g., 0.8, 1.0, 2.0)")


def _add_render_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `render` command."""
    p = subparsers.add_parser("render", help="Render project to a video file")
    p.add_argument("file", help="Path to the .mlt project file")
    p.add_argument("--output", required=True, help="Output video file path")
    p.add_argument("--preset", help="Render preset name (youtube_1080p, web_webm, archive_prores, preview)", default=None)


def _add_info_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `info` command."""
    p = subparsers.add_parser("info", help="Show project metadata as JSON")
    p.add_argument("file", help="Path to the .mlt project file")


def _add_describe_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `describe` command."""
    p = subparsers.add_parser("describe", help="Show human-readable timeline description")
    p.add_argument("file", help="Path to the .mlt project file")


def _add_list_profiles_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `list-profiles` command."""
    subparsers.add_parser("list-profiles", help="List available MLT profiles")


def _add_list_filters_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `list-filters` command."""
    p = subparsers.add_parser("list-filters", help="List available MLT filters")
    p.add_argument("--category", help="Filter by category (audio, color, transform, blur)", default=None)


def _add_list_transitions_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the `list-transitions` command."""
    subparsers.add_parser("list-transitions", help="List available MLT transitions")


# ── Main parser ────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    """Build the full argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="mlt-pilot",
        description=f"MLT Pilot v{__version__} — AI-driven MLT video editing CLI",
    )
    parser.add_argument("--version", action="version", version=f"mlt-pilot {__version__}")
    subparsers = parser.add_subparsers(dest="command", title="commands")

    # Group A — Skill management
    _add_skill_subparser(subparsers)

    # Group B — MLT manipulation
    _add_create_parser(subparsers)
    _add_add_media_parser(subparsers)
    _add_list_media_parser(subparsers)
    _add_add_clip_parser(subparsers)
    _add_insert_clip_parser(subparsers)
    _add_remove_clip_parser(subparsers)
    _add_add_filter_parser(subparsers)
    _add_add_transition_parser(subparsers)
    _add_add_subtitle_parser(subparsers)
    _add_add_subtitles_file_parser(subparsers)
    _add_add_bgm_parser(subparsers)
    _add_set_audio_parser(subparsers)
    _add_render_parser(subparsers)
    _add_info_parser(subparsers)
    _add_describe_parser(subparsers)
    _add_list_profiles_parser(subparsers)
    _add_list_filters_parser(subparsers)
    _add_list_transitions_parser(subparsers)

    return parser


# ── Entry points ───────────────────────────────────────────────────────────

def main(argv: Optional[list[str]] = None) -> int:
    """Entry point. Returns exit code (testable without subprocess)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Resolve skill subcommands (e.g., "skill" + "build" → "skill.build")
    if args.command == "skill":
        if args.skill_command is None:
            # No subcommand given for skill — print help for the skill group
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction) and action.dest == "command":
                    for choice, sub in action.choices.items():
                        if choice == "skill":
                            sub.print_help()
                            return 0
            return 0
        cmd = f"skill.{args.skill_command}"
    else:
        cmd = args.command

    try:
        return _HANDLERS[cmd](args)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 2


def entry_point() -> None:
    """Console-script wrapper — calls sys.exit(main())."""
    sys.exit(main())
