import subprocess
from pathlib import Path


def cut_clip(src: str, start: float, end: float, out_path: str) -> str:
    duration = max(0.0, end - start)
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{start:.3f}", "-i", src,
         "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
         "-pix_fmt", "yuv420p", out_path],
        check=True, capture_output=True,
    )
    return out_path


def concat_clips(clip_paths: list[str], out_path: str) -> str:
    listfile = Path(out_path).with_suffix(".txt")
    listfile.write_text("".join(f"file '{p}'\n" for p in clip_paths))
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
             "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac",
             "-pix_fmt", "yuv420p", out_path],
            check=True, capture_output=True,
        )
    finally:
        listfile.unlink(missing_ok=True)
    return out_path


def export(src: str, ranges: list[dict], out_dir: str,
           progress_callback=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not ranges:
        return {"clips": [], "stitched": None}
    total = len(ranges) + 1            # clips + concat step
    clips = []
    for i, r in enumerate(ranges, start=1):
        clip_path = str(out / f"clip_{i:03d}.mp4")
        cut_clip(src, float(r["start"]), float(r["end"]), clip_path)
        clips.append(clip_path)
        if progress_callback is not None:
            progress_callback(i / total)
    stitched = str(out / "highlights.mp4")
    concat_clips(clips, stitched)
    if progress_callback is not None:
        progress_callback(1.0)
    return {"clips": clips, "stitched": stitched}
