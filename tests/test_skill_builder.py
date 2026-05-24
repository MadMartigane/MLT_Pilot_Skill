"""Tests for mlt_pilot.skill_builder module."""

import pytest
from pathlib import Path
from mlt_pilot.skill_builder import build_skill, install_skill
from mlt_pilot import __version__


class TestBuildSkill:
    def test_creates_output_dir(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        assert output == tmp_path / "out"
        assert output.exists()
        assert output.is_dir()

    def test_creates_skill_md(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        skill_md = output / "SKILL.md"
        assert skill_md.exists()
        assert skill_md.is_file()

    def test_skill_md_contains_frontmatter(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert content.startswith("---")
        assert "name: mlt-pilot" in content
        assert f"version: {__version__}" in content

    def test_skill_md_contains_commands(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert "mlt-pilot create" in content
        assert "mlt-pilot add-clip" in content
        assert "mlt-pilot render" in content
        assert "mlt-pilot add-subtitle" in content

    def test_skill_md_contains_profiles(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert "atsc_1080p_30" in content

    def test_skill_md_contains_filters(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert "brightness" in content
        assert "volume" in content

    def test_skill_md_contains_transitions(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert "composite" in content

    def test_skill_md_contains_presets(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert "youtube_1080p" in content

    def test_template_substitution(self, tmp_path):
        output = build_skill(output_dir=tmp_path / "out")
        content = (output / "SKILL.md").read_text()
        assert "$version" not in content
        assert "$profiles" not in content
        assert "$filters" not in content
        assert "$transitions" not in content
        assert "$presets" not in content

    def test_build_skill_idempotent(self, tmp_path):
        out_dir = tmp_path / "out"
        build_skill(output_dir=out_dir)
        content1 = (out_dir / "SKILL.md").read_text()
        build_skill(output_dir=out_dir)
        content2 = (out_dir / "SKILL.md").read_text()
        assert content1 == content2


class TestInstallSkill:
    def test_install_creates_directory(self, tmp_path):
        source = build_skill(output_dir=tmp_path / "build")
        target = tmp_path / "repo"
        target.mkdir()
        installed = install_skill(target, source_dir=source)
        assert installed.exists()
        assert installed.is_dir()

    def test_install_correct_path(self, tmp_path):
        source = build_skill(output_dir=tmp_path / "build")
        target = tmp_path / "repo"
        target.mkdir()
        installed = install_skill(target, source_dir=source)
        assert installed == target.resolve() / ".opencode" / "skills" / "mlt-pilot"

    def test_install_copies_skill_md(self, tmp_path):
        source = build_skill(output_dir=tmp_path / "build")
        target = tmp_path / "repo"
        target.mkdir()
        installed = install_skill(target, source_dir=source)
        installed_skill = installed / "SKILL.md"
        assert installed_skill.exists()
        assert installed_skill.read_text() == (source / "SKILL.md").read_text()

    def test_install_missing_source_raises(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        target = tmp_path / "repo"
        target.mkdir()
        with pytest.raises(FileNotFoundError, match="SKILL.md"):
            install_skill(target, source_dir=empty_dir)

    def test_install_creates_opencode_dirs(self, tmp_path):
        source = build_skill(output_dir=tmp_path / "build")
        target = tmp_path / "repo"
        target.mkdir()
        install_skill(target, source_dir=source)
        assert (target / ".opencode").exists()
        assert (target / ".opencode" / "skills").exists()
        assert (target / ".opencode" / "skills" / "mlt-pilot").exists()

    def test_install_overwrites_existing(self, tmp_path):
        source = build_skill(output_dir=tmp_path / "build")
        target = tmp_path / "repo"
        target.mkdir()
        install_skill(target, source_dir=source)
        marker = "OVERWRITTEN_MARKER_12345"
        (source / "SKILL.md").write_text(marker)
        install_skill(target, source_dir=source)
        installed_content = (
            target / ".opencode" / "skills" / "mlt-pilot" / "SKILL.md"
        ).read_text()
        assert installed_content == marker
