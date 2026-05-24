"""Shared test fixtures."""

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_ids():
    from mlt_pilot.utils import reset_id_counters
    reset_id_counters()
    yield
    reset_id_counters()


@pytest.fixture
def simple_mlt_path():
    return FIXTURES_DIR / "simple_project.mlt"


@pytest.fixture
def simple_mlt_string():
    return (FIXTURES_DIR / "simple_project.mlt").read_text()


@pytest.fixture
def sample_srt_string():
    return "1\n00:00:01,000 --> 00:00:04,000\nHello World\n\n2\n00:00:05,000 --> 00:00:08,500\nSecond subtitle line\n"


@pytest.fixture
def sample_srt_bom():
    return "\ufeff" + "1\n00:00:01,000 --> 00:00:04,000\nHello World\n\n2\n00:00:05,000 --> 00:00:08,500\nSecond subtitle line\n"


@pytest.fixture
def project_30fps():
    from mlt_pilot.project import MLTProject
    return MLTProject(profile="atsc_1080p_30", title="Test Project")


@pytest.fixture
def tmp_media(tmp_path):
    files = {}
    files["video1"] = tmp_path / "clip1.mp4"
    files["video2"] = tmp_path / "clip2.mp4"
    files["audio"] = tmp_path / "music.mp3"
    for f in files.values():
        f.write_text("")
    return files
