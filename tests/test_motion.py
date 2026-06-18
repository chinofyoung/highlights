import numpy as np
from app.analyzer import motion
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_motion_energy_higher_during_movement(sample_video):
    energy = motion.motion_energy(sample_video, sample_fps=8)
    # 6s @ 8fps ≈ 48 samples; motion segment is middle 2s (samples ~16..32)
    assert len(energy) >= 40
    middle = energy[18:30].mean()
    edges = np.concatenate([energy[2:12], energy[-12:-2]]).mean()
    assert middle > edges
