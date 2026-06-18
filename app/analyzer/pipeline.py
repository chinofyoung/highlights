import numpy as np
from app.config import DetectionParams
from app import workdir
from app.analyzer import motion as motion_mod
from app.analyzer import audio as audio_mod
from app.analyzer import segment as seg
from app.analyzer import onsets as onsets_mod
from app.analyzer import serve as serve_mod


def _resample(x: np.ndarray, length: int) -> np.ndarray:
    if x.size == 0 or length <= 0:
        return np.zeros(length)
    if x.size == length:
        return x
    src = np.linspace(0.0, 1.0, x.size)
    dst = np.linspace(0.0, 1.0, length)
    return np.interp(dst, src, x)


def analyze(video_id: str, video_path: str, params: DetectionParams,
            progress_callback=None) -> list[dict]:
    hop = 1.0 / params.sample_fps
    motion_cb = None
    if progress_callback is not None:
        motion_cb = lambda f: progress_callback(min(0.9, f * 0.9))
    motion = motion_mod.motion_energy(video_path, params.sample_fps,
                                      progress_callback=motion_cb)

    wav = str(workdir.uploads_dir(video_id) / "audio.wav")
    audio_mod.extract_wav(video_path, wav)
    audio = audio_mod.audio_energy(wav, hop_seconds=hop)
    audio = _resample(audio, len(motion))
    onsets = onsets_mod.detect_onsets(wav, params)

    workdir.save_signals(video_id, motion, audio, hop, onsets)
    result = resegment(video_id, params)
    if progress_callback is not None:
        progress_callback(1.0)
    return result


def resegment(video_id: str, params: DetectionParams) -> list[dict]:
    motion, audio, hop, onsets = workdir.load_signals(video_id)
    combined = seg.combine(motion, audio, params)
    window = max(1, int(round(0.5 / hop)))   # ~0.5s smoothing
    combined = seg.smooth(combined, window)
    thr = seg.compute_threshold(combined, params)
    rallies = seg.segment(combined, hop_seconds=hop, params=params, threshold=thr)
    rallies = seg.gate_by_onsets(rallies, onsets, params)
    return [serve_mod.derive_serve(r, params) for r in rallies]
