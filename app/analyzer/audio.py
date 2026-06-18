import subprocess
import wave
import numpy as np


def extract_wav(video_path: str, wav_path: str, sample_rate: int = 16000) -> str:
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
         "-ar", str(sample_rate), "-f", "wav", wav_path],
        check=True, capture_output=True,
    )
    return wav_path


def audio_energy(wav_path: str, hop_seconds: float) -> np.ndarray:
    with wave.open(wav_path, "rb") as w:
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return np.zeros(0)
    hop = max(1, int(rate * hop_seconds))
    n = samples.size // hop
    if n == 0:
        return np.array([np.sqrt(np.mean(samples ** 2))])
    trimmed = samples[: n * hop].reshape(n, hop)
    return np.sqrt(np.mean(trimmed ** 2, axis=1))
