"""
Minimal example: create a two-clip timeline and export.

Usage:
    python -m examples.basic_timeline
"""

from mlt_pilot import MLTProject


def main():
    project = MLTProject(profile="atsc_1080p_30", title="Basic Demo")

    # Register media (adjust paths to your actual files)
    project.add_media("videos/clip1.mp4")
    project.add_media("videos/clip2.mp4")

    # Build timeline
    project.add_clip(track=0, media="clip1.mp4", start=0, duration="10s")
    project.add_clip(track=0, media="clip2.mp4", start="10s", duration="5s")

    # Inspect
    print(project.describe())

    # Export
    project.export_mlt("basic_demo.mlt")
    print("Saved: basic_demo.mlt")


if __name__ == "__main__":
    main()
