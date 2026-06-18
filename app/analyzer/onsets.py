import wave
import numpy as np
from app.config import DetectionParams


def _read_wav(wav_path: str):
    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
    return samples, rate


def _bandpass(x: np.ndarray, rate: int, low: float, high: float) -> np.ndarray:
    n = x.size
    if n == 0:
        return x
    freqs = np.fft.rfftfreq(n, d=1.0 / rate)
    spec = np.fft.rfft(x)
    mask = (freqs >= low) & (freqs <= high)
    return np.fft.irfft(spec * mask, n=n)


def _pick_peaks(env: np.ndarray, thr: float, min_sep: int) -> np.ndarray:
    n = env.size
    if n == 0:
        return np.zeros(0)
    above = env >= thr
    peaks = []
    last = -min_sep - 1
    i = 0
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            local = i + int(np.argmax(env[i:j]))
            if local - last >= min_sep:
                peaks.append(local)
                last = local
            i = j
        else:
            i += 1
    return np.asarray(peaks, dtype=float)


def detect_onsets(wav_path: str, params: DetectionParams) -> np.ndarray:
    samples, rate = _read_wav(wav_path)
    if samples.size == 0:
        return np.zeros(0)
    band = _bandpass(samples, rate, params.onset_low_hz, params.onset_high_hz)
    env = np.abs(band)
    win = max(1, int(rate * 0.01))  # ~10ms envelope smoothing
    env = np.convolve(env, np.ones(win) / win, mode="same")
    floor = float(np.median(env))
    mad = float(np.median(np.abs(env - floor))) * 1.4826  # robust std
    if mad < 1e-9:
        return np.zeros(0)
    thr = floor + params.onset_sensitivity * mad
    min_sep = max(1, int(rate * params.onset_min_separation_s))
    peak_idx = _pick_peaks(env, thr, min_sep)
    return np.sort(peak_idx / rate)
