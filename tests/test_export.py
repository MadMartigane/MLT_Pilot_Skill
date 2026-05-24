"""Tests for mlt_pilot.export module."""

from unittest.mock import patch, MagicMock
import pytest
from mlt_pilot.export import check_melt_available, render, render_preset, RENDER_PRESETS


class TestCheckMelt:
    def test_returns_tuple(self):
        available, info = check_melt_available()
        assert isinstance(available, bool)
        assert isinstance(info, str)


class TestRenderPresets:
    def test_presets_exist(self):
        assert "youtube_1080p" in RENDER_PRESETS
        assert "web_webm" in RENDER_PRESETS
        assert "archive_prores" in RENDER_PRESETS
        assert "preview" in RENDER_PRESETS

    def test_youtube_preset_values(self):
        p = RENDER_PRESETS["youtube_1080p"]
        assert p["vcodec"] == "libx264"
        assert p["crf"] == 20

    def test_webm_preset_values(self):
        p = RENDER_PRESETS["web_webm"]
        assert p["vcodec"] == "libvpx-vp9"

    def test_render_preset_unknown(self):
        with pytest.raises(ValueError):
            render_preset("test.mlt", "out.mp4", "nonexistent_preset")


class TestRender:
    def test_render_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            render("/nonexistent/project.mlt", "out.mp4")

    def test_render_constructs_command(self, tmp_path):
        """Test that render builds correct melt command (mock subprocess)."""
        project_file = tmp_path / "test.mlt"
        project_file.write_text('<?xml version="1.0"?><mlt/>')
        output = tmp_path / "out.mp4"

        with patch("mlt_pilot.export.subprocess.run") as mock_run, \
             patch("mlt_pilot.export.get_melt_command", return_value="melt"):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            render(project_file, output, vcodec="libx264")

            assert mock_run.called
            cmd = mock_run.call_args[0][0]
            assert "melt" in cmd[0]
            assert str(project_file) in cmd

    def test_render_webm_auto_codec(self, tmp_path):
        project_file = tmp_path / "test.mlt"
        project_file.write_text('<?xml version="1.0"?><mlt/>')
        output = tmp_path / "out.webm"

        with patch("mlt_pilot.export.subprocess.run") as mock_run, \
             patch("mlt_pilot.export.get_melt_command", return_value="melt"):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            render(project_file, output)
            cmd = mock_run.call_args[0][0]
            assert any("libvpx-vp9" in part for part in cmd)

    def test_render_mov_auto_codec(self, tmp_path):
        project_file = tmp_path / "test.mlt"
        project_file.write_text('<?xml version="1.0"?><mlt/>')
        output = tmp_path / "out.mov"

        with patch("mlt_pilot.export.subprocess.run") as mock_run, \
             patch("mlt_pilot.export.get_melt_command", return_value="melt"):
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            render(project_file, output)
            cmd = mock_run.call_args[0][0]
            assert any("prores_ks" in part for part in cmd)
