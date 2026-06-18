import numpy as np
from app.analyzer import audio
from tests.conftest import requires_ffmpeg


@requires_ffmpeg
def test_extract_wav_creates_file(sample_video, tmp_path):
    wav = tmp_path / "a.wav"
    out = audio.extract_wav(sample_video, str(wav))
    assert wav.exists() and out == str(wav)


@requires_ffmpeg
def test_audio_energy_higher_during_sine(sample_video, tmp_path):
    wav = tmp_path / "a.wav"
    audio.extract_wav(sample_video, str(wav))
    energy = audio.audio_energy(str(wav), hop_seconds=0.5)
    # ~12 hops over 6s; sine is in the middle 2s (hops ~4..8)
    assert len(energy) >= 10
    middle = energy[4:8].mean()
    edges = np.concatenate([energy[:3], energy[-3:]]).mean()
    assert middle > edges
