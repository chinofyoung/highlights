from app.exporter import ffmpeg as ex
from app.deps import probe_duration
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_cut_clip_has_expected_duration(sample_video, tmp_path):
    out = tmp_path / "clip.mp4"
    ex.cut_clip(sample_video, 2.0, 4.0, str(out))
    assert out.exists()
    assert abs(probe_duration(str(out)) - 2.0) < 0.5


@requires_ffmpeg
def test_export_produces_clips_and_stitch(sample_video, tmp_path):
    ranges = [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 5.0}]
    result = ex.export(sample_video, ranges, str(tmp_path))
    assert len(result["clips"]) == 2
    total = sum(r["end"] - r["start"] for r in ranges)
    assert abs(probe_duration(result["stitched"]) - total) < 0.8


@requires_ffmpeg
def test_export_empty_ranges(sample_video, tmp_path):
    result = ex.export(sample_video, [], str(tmp_path))
    assert result == {"clips": [], "stitched": None}
