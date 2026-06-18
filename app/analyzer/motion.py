import cv2
import numpy as np


def motion_energy(video_path: str, sample_fps: int, progress_callback=None) -> np.ndarray:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    src_fps = cap.get(cv2.CAP_PROP_FPS) or sample_fps
    step = max(1, int(round(src_fps / sample_fps)))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    energies = []
    prev = None
    idx = 0
    last_reported = -1.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (160, 120))
                if prev is None:
                    energies.append(0.0)
                else:
                    energies.append(float(np.mean(np.abs(gray.astype(np.int16) -
                                                          prev.astype(np.int16)))))
                prev = gray
            idx += 1
            if progress_callback is not None and total > 0 and idx % 30 == 0:
                frac = min(1.0, idx / total)
                if frac > last_reported:
                    last_reported = frac
                    progress_callback(frac)
    finally:
        cap.release()
    if progress_callback is not None and total > 0 and last_reported < 1.0:
        progress_callback(1.0)
    return np.asarray(energies, dtype=float)
