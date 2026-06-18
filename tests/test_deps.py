from app.deps import ffmpeg_available, probe_duration
from tests.conftest import requires_ffmpeg


def test_ffmpeg_available_returns_bool():
    assert isinstance(ffmpeg_available(), bool)


@requires_ffmpeg
def test_probe_duration_reads_length(sample_video):
    dur = probe_duration(sample_video)
    assert 5.0 < dur < 7.0


@requires_ffmpeg
def test_probe_duration_rejects_non_video(tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("not a video")
    import pytest
    with pytest.raises(ValueError):
        probe_duration(str(bad))
