import wave
import numpy as np
from app.config import DetectionParams
from app.analyzer.onsets import detect_onsets


def _write_wav(path, samples, rate=16000):
    data = np.clip(samples, -1, 1)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def _click(rate, t, dur=0.005, freq=3000.0):
    n = int(rate * dur)
    idx = np.arange(n)
    env = np.exp(-idx / (n / 4))
    return np.sin(2 * np.pi * freq * idx / rate) * env


def test_detects_clicks_at_expected_times(tmp_path):
    rate = 16000
    sig = np.zeros(int(rate * 3.0))
    for t in (0.5, 1.5, 2.5):
        start = int(rate * t)
        c = _click(rate, t)
        sig[start:start + c.size] += c
    wav = tmp_path / "clicks.wav"
    _write_wav(wav, sig, rate)

    onsets = detect_onsets(str(wav), DetectionParams())
    assert len(onsets) == 3
    for expected, got in zip((0.5, 1.5, 2.5), sorted(onsets)):
        assert abs(got - expected) < 0.05


def test_silence_yields_no_onsets(tmp_path):
    wav = tmp_path / "silence.wav"
    _write_wav(wav, np.zeros(16000), 16000)
    onsets = detect_onsets(str(wav), DetectionParams())
    assert len(onsets) == 0


def test_empty_audio_returns_empty(tmp_path):
    wav = tmp_path / "empty.wav"
    _write_wav(wav, np.zeros(0), 16000)
    assert detect_onsets(str(wav), DetectionParams()).size == 0
