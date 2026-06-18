"""Run rally detection over labeled videos and report precision/recall/F1/IoU.

Usage:
  python scripts/eval.py --videos eval/videos --labels eval/labels [--cutoff 0.5]

Each label file is eval/labels/<video_id>.json = [{"start": s, "end": s}, ...].
The matching video is eval/videos/<video_id>.<ext>.
"""
import argparse
import json
import sys
from pathlib import Path

# allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DetectionParams           # noqa: E402
from app.analyzer import pipeline                 # noqa: E402
from app.eval.metrics import score                # noqa: E402


def _find_video(videos_dir: Path, video_id: str) -> Path | None:
    for p in videos_dir.glob(f"{video_id}.*"):
        if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"}:
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", default="eval/videos")
    ap.add_argument("--labels", default="eval/labels")
    ap.add_argument("--cutoff", type=float, default=0.5)
    args = ap.parse_args()

    labels_dir = Path(args.labels)
    videos_dir = Path(args.videos)
    label_files = sorted(labels_dir.glob("*.json"))
    if not label_files:
        print(f"No label files in {labels_dir}")
        return 1

    params = DetectionParams()
    agg = {"tp": 0, "fp": 0, "fn": 0}
    for lf in label_files:
        video_id = lf.stem
        video = _find_video(videos_dir, video_id)
        if video is None:
            print(f"[skip] no video for {video_id}")
            continue
        labels = json.loads(lf.read_text())
        detected = pipeline.analyze(video_id, str(video), params)
        s = score(detected, labels, cutoff=args.cutoff)
        agg["tp"] += s["tp"]; agg["fp"] += s["fp"]; agg["fn"] += s["fn"]
        print(f"{video_id}: P={s['precision']:.2f} R={s['recall']:.2f} "
              f"F1={s['f1']:.2f} IoU={s['mean_iou']:.2f} "
              f"(tp={s['tp']} fp={s['fp']} fn={s['fn']})")

    tp, fp, fn = agg["tp"], agg["fp"], agg["fn"]
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    print(f"\nOVERALL: P={p:.3f} R={r:.3f} F1={f1:.3f} (tp={tp} fp={fp} fn={fn})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
