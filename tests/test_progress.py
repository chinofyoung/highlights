import numpy as np
from app.config import DetectionParams
from app import workdir
from app.analyzer import motion, pipeline
from app.exporter import ffmpeg as exporter
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_motion_reports_monotonic_progress(sample_video):
    seen = []
    motion.motion_energy(sample_video, sample_fps=8,
                         progress_callback=lambda f: seen.append(f))
    assert seen, "callback was never called"
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)               # non-decreasing
    assert seen[-1] <= 1.0


@requires_ffmpeg
def test_motion_without_callback_unchanged(sample_video):
    e = motion.motion_energy(sample_video, sample_fps=8)
    assert len(e) >= 40                        # same as before


@requires_ffmpeg
def test_analyze_reports_progress_ending_at_one(tmp_path, monkeypatch, sample_video):
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    seen = []
    pipeline.analyze("vidp", sample_video, DetectionParams(),
                     progress_callback=lambda f: seen.append(f))
    assert seen and seen[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)


@requires_ffmpeg
def test_export_reports_progress(sample_video, tmp_path):
    seen = []
    exporter.export(sample_video,
                    [{"start": 0.5, "end": 2.0}, {"start": 3.0, "end": 5.0}],
                    str(tmp_path), progress_callback=lambda f: seen.append(f))
    assert seen and seen[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen == sorted(seen)


@requires_ffmpeg
def test_export_empty_ranges_no_progress_crash(sample_video, tmp_path):
    res = exporter.export(sample_video, [], str(tmp_path),
                          progress_callback=lambda f: None)
    assert res == {"clips": [], "stitched": None}
