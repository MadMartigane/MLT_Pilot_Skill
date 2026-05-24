"""Tests for mlt_pilot CLI."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mlt_pilot.cli import main

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def project_file(tmp_path, tmp_media):
    """Create a minimal .mlt project with one registered media file."""
    from mlt_pilot.project import MLTProject

    project = MLTProject(profile="atsc_1080p_30", title="Test Project")
    project.add_media(tmp_media["video1"])
    mlt_path = tmp_path / "test_project.mlt"
    project.save(mlt_path)
    return mlt_path


# ── TestVersion ─────────────────────────────────────────────────────────────


class TestVersion:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "mlt-pilot" in output
        assert "0.1.0" in output


# ── TestNoCommand ───────────────────────────────────────────────────────────


class TestNoCommand:
    def test_no_args_returns_0(self, capsys):
        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "mlt-pilot" in captured.out


# ── TestCreate ──────────────────────────────────────────────────────────────


class TestCreate:
    def test_create_project(self, tmp_path):
        mlt_path = tmp_path / "new_project.mlt"
        result = main(["create", str(mlt_path), "--title", "My Project"])
        assert result == 0
        assert mlt_path.exists()

    def test_create_with_profile(self, tmp_path):
        mlt_path = tmp_path / "profiled.mlt"
        result = main(["create", str(mlt_path), "--profile", "atsc_720p_30"])
        assert result == 0

    def test_create_default_profile(self, tmp_path):
        mlt_path = tmp_path / "default.mlt"
        result = main(["create", str(mlt_path)])
        assert result == 0
        assert mlt_path.exists()


# ── TestMedia ───────────────────────────────────────────────────────────────


class TestMedia:
    def test_add_media(self, project_file, tmp_media):
        result = main(["add-media", str(project_file), "--media", str(tmp_media["video2"])])
        assert result == 0

    def test_add_media_with_alias(self, project_file, tmp_media):
        result = main([
            "add-media", str(project_file),
            "--media", str(tmp_media["video2"]),
            "--alias", "myclip",
        ])
        assert result == 0

    def test_add_media_nonexistent(self, project_file):
        result = main([
            "add-media", str(project_file),
            "--media", "/nonexistent/path/video.mp4",
        ])
        assert result != 0

    def test_list_media_empty(self, tmp_path, capsys):
        mlt_path = tmp_path / "empty2.mlt"
        main(["create", str(mlt_path)])
        main(["list-media", str(mlt_path)])
        captured = capsys.readouterr()
        assert "No media registered." in captured.out

    def test_list_media_with_files(self, project_file, capsys):
        main(["list-media", str(project_file)])
        captured = capsys.readouterr()
        assert "clip1.mp4" in captured.out


# ── TestClips ───────────────────────────────────────────────────────────────


class TestClips:
    def test_add_clip(self, project_file):
        result = main([
            "add-clip", str(project_file),
            "--track", "0",
            "--media", "clip1.mp4",
            "--start", "0",
            "--duration", "5s",
        ])
        assert result == 0

    def test_insert_clip(self, project_file):
        main([
            "add-clip", str(project_file),
            "--track", "0",
            "--media", "clip1.mp4",
            "--start", "0",
            "--duration", "5s",
        ])
        result = main([
            "insert-clip", str(project_file),
            "--track", "0",
            "--position", "0",
            "--media", "clip1.mp4",
            "--duration", "3s",
        ])
        assert result == 0

    def test_remove_clip(self, project_file):
        main([
            "add-clip", str(project_file),
            "--track", "0",
            "--media", "clip1.mp4",
            "--start", "0",
            "--duration", "5s",
        ])
        result = main([
            "remove-clip", str(project_file),
            "--track", "0",
            "--position", "0",
        ])
        assert result == 0


# ── TestFilters ─────────────────────────────────────────────────────────────


class TestFilters:
    def test_add_filter(self, project_file):
        result = main([
            "add-filter", str(project_file),
            "--track", "0",
            "--filter", "brightness",
            "brightness=0.5",
        ])
        assert result == 0

    def test_add_filter_invalid_param(self, project_file, capsys):
        result = main([
            "add-filter", str(project_file),
            "--track", "0",
            "--filter", "brightness",
            "badparam",
        ])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err


# ── TestTransitions ─────────────────────────────────────────────────────────


class TestTransitions:
    def test_add_transition(self, project_file):
        result = main([
            "add-transition", str(project_file),
            "--track-a", "0",
            "--track-b", "1",
            "--start", "0",
            "--duration", "2s",
            "--type", "crossfade",
        ])
        assert result == 0


# ── TestSubtitles ───────────────────────────────────────────────────────────


class TestSubtitles:
    def test_add_subtitle(self, project_file):
        result = main([
            "add-subtitle", str(project_file),
            "--text", "Hello World",
            "--start", "1s",
            "--duration", "4s",
        ])
        assert result == 0

    def test_add_subtitles_file(self, project_file, tmp_path):
        srt_path = tmp_path / "subtitles.srt"
        srt_path.write_text(
            "1\n00:00:01,000 --> 00:00:04,000\nHello World\n\n"
            "2\n00:00:05,000 --> 00:00:08,500\nSecond line\n"
        )
        result = main([
            "add-subtitles-file", str(project_file),
            "--file", str(srt_path),
        ])
        assert result == 0


# ── TestAudio ───────────────────────────────────────────────────────────────


class TestAudio:
    def test_set_audio(self, project_file):
        result = main([
            "set-audio", str(project_file),
            "--track", "0",
            "--gain", "0.5",
        ])
        assert result == 0

    def test_add_bgm(self, project_file, tmp_media):
        result = main([
            "add-bgm", str(project_file),
            "--file", str(tmp_media["audio"]),
        ])
        assert result == 0

    def test_add_bgm_with_fades(self, project_file, tmp_media):
        result = main([
            "add-bgm", str(project_file),
            "--file", str(tmp_media["audio"]),
            "--fade-in", "2s",
            "--fade-out", "3s",
        ])
        assert result == 0


# ── TestRender ──────────────────────────────────────────────────────────────


class TestRender:
    def test_render_no_melt(self, project_file, tmp_path, capsys):
        out_path = tmp_path / "output.mp4"
        with patch("mlt_pilot.cli.check_melt_available") as mock_check:
            mock_check.return_value = (False, "melt-7 not installed")
            result = main([
                "render", str(project_file),
                "--output", str(out_path),
            ])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_render_with_preset(self, project_file, tmp_path):
        out_path = tmp_path / "output.mp4"
        mock_run = MagicMock(returncode=0)
        with patch("mlt_pilot.cli.check_melt_available") as mock_check, \
             patch("mlt_pilot.export.subprocess.run", return_value=mock_run):
            mock_check.return_value = (True, "/usr/bin/melt-7")
            result = main([
                "render", str(project_file),
                "--output", str(out_path),
                "--preset", "preview",
            ])
        assert result == 0


# ── TestInfoDescribe ────────────────────────────────────────────────────────


class TestInfoDescribe:
    def test_info_json(self, project_file, capsys):
        result = main(["info", str(project_file)])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "title" in data
        assert "profile" in data
        assert "fps" in data

    def test_describe(self, project_file, capsys):
        result = main(["describe", str(project_file)])
        assert result == 0
        captured = capsys.readouterr()
        assert "Test Project" in captured.out


# ── TestListCommands ────────────────────────────────────────────────────────


class TestListCommands:
    def test_list_profiles(self, capsys):
        result = main(["list-profiles"])
        assert result == 0
        captured = capsys.readouterr()
        assert "atsc_1080p_30" in captured.out

    def test_list_filters(self, capsys):
        result = main(["list-filters"])
        assert result == 0
        captured = capsys.readouterr()
        assert "brightness" in captured.out

    def test_list_filters_category(self, capsys):
        result = main(["list-filters", "--category", "color"])
        assert result == 0

    def test_list_transitions(self, capsys):
        result = main(["list-transitions"])
        assert result == 0
        captured = capsys.readouterr()
        assert "composite" in captured.out


# ── TestSkillCommands ───────────────────────────────────────────────────────


class TestSkillCommands:
    def test_skill_build(self):
        from mlt_pilot.skill_builder import build_skill

        output_dir = build_skill()
        skill_path = output_dir / "SKILL.md"
        assert skill_path.exists()
        content = skill_path.read_text(encoding="utf-8")
        assert "mlt-pilot" in content
        assert "0.1.0" in content

    def test_skill_install(self, tmp_path):
        from mlt_pilot.skill_builder import build_skill, install_skill

        source_dir = build_skill()
        install_skill(tmp_path, source_dir=source_dir)
        installed = tmp_path.resolve() / ".opencode" / "skills" / "mlt-pilot"
        assert installed.exists()
        assert (installed / "SKILL.md").exists()

    def test_skill_install_not_built(self, tmp_path):
        from mlt_pilot.skill_builder import install_skill

        nonexistent = tmp_path / "nonexistent_skill_dir"
        with pytest.raises(FileNotFoundError):
            install_skill(tmp_path, source_dir=nonexistent)


# ── TestErrorHandling ───────────────────────────────────────────────────────


class TestErrorHandling:
    def test_missing_mlt_file(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist.mlt"
        result = main(["info", str(nonexistent)])
        assert result != 0

    def test_missing_required_args(self):
        with pytest.raises(SystemExit):
            main(["create"])


# ── TestEntryPoint ──────────────────────────────────────────────────────────


class TestEntryPoint:
    def test_module_execution(self):
        result = subprocess.run(
            [sys.executable, "-m", "mlt_pilot", "--version"],
            capture_output=True,
            text=True,
        )
        assert "0.1.0" in (result.stdout + result.stderr)
