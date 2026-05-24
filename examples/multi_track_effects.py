"""
Advanced example: multi-track with effects, transitions, audio, and subtitles.

Usage:
    python -m examples.multi_track_effects
"""

from mlt_pilot import MLTProject


def main():
    project = MLTProject(profile="atsc_1080p_30", title="Multi-Track Demo")

    # Media
    project.add_media("videos/intro.mp4")
    project.add_media("videos/main.mp4")
    project.add_media("audio/background_music.mp3")

    # Video track 0: main content
    project.add_clip(track=0, media="intro.mp4", start=0, duration="5s")
    project.add_clip(track=0, media="main.mp4", start="5s", duration="20s")

    # Video track 1: overlay
    project.add_clip(track=1, media="main.mp4", start="3s", duration="4s", in_point="5s")
    project.add_filter(track=1, filter="opacity", opacity=0.5)

    # Transition between tracks
    project.add_transition(track_a=0, track_b=1, start="3s", duration="2s", type="dissolve")

    # Audio track: background music
    project.add_background_music("audio/background_music.mp3", volume=0.3, fade_in="2s", fade_out="3s")

    # Subtitles
    project.add_subtitle_line(text="Welcome!", start="0s", duration="3s")
    project.add_subtitle_line(text="Main content", start="5s", duration="5s")

    # Inspect
    print(project.describe())

    # Export
    project.export_mlt("multi_track_demo.mlt")
    print("Saved: multi_track_demo.mlt")


if __name__ == "__main__":
    main()
