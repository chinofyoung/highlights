import dataclasses
import json
import re
import shutil
import threading
import time
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import DetectionParams
from app.deps import probe_duration
from app import workdir
from app.api import jobs, state
from app.analyzer import pipeline
from app.exporter import ffmpeg as exporter
from app.exporter.ffmpeg import concat_clips

router = APIRouter(prefix="/api")


class _Cancelled(Exception):
    pass


class DetectBody(BaseModel):
    video_id: str
    params: dict | None = None


class ExportBody(BaseModel):
    video_id: str
    ranges: list[dict]


class RenameBody(BaseModel):
    name: str


def _params(d: dict | None) -> DetectionParams:
    allowed = {f.name for f in dataclasses.fields(DetectionParams)}
    filtered = {k: v for k, v in (d or {}).items() if k in allowed}
    return DetectionParams(**filtered)


def _require(video_id: str) -> dict:
    info = state.get(video_id)
    if not info:
        raise HTTPException(404, "Unknown video_id")
    return info


def _validate_filename(filename: str) -> str:
    """Allow only clip_NNN.mp4 or highlights.mp4; raise 400 otherwise."""
    if not re.fullmatch(r'^(clip_\d+\.mp4|highlights\.mp4)$', filename):
        raise HTTPException(400, "Invalid filename")
    return filename


def _output_dir(video_id: str) -> Path:
    _require(video_id)          # raises 404 if unknown
    return workdir.video_dir(video_id) / "clips"


@router.get("/output/{video_id}")
def list_output(video_id: str):
    out_dir = _output_dir(video_id)
    if not out_dir.exists():
        return {"clips": [], "stitched": None}
    clips = sorted([p.name for p in out_dir.glob("clip_*.mp4")])
    stitched = "highlights.mp4" if (out_dir / "highlights.mp4").exists() else None
    return {"clips": clips, "stitched": stitched}


@router.get("/output/{video_id}/{filename}")
def get_output_file(video_id: str, filename: str):
    _validate_filename(filename)
    out_dir = _output_dir(video_id)
    path = out_dir / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(path))


@router.delete("/output/{video_id}/{filename}")
def delete_output_file(video_id: str, filename: str):
    _validate_filename(filename)
    out_dir = _output_dir(video_id)
    path = out_dir / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    if filename.startswith("clip_"):
        path.unlink()
        remaining = sorted(out_dir.glob("clip_*.mp4"))
        if remaining:
            concat_clips([str(p) for p in remaining], str(out_dir / "highlights.mp4"))
        else:
            (out_dir / "highlights.mp4").unlink(missing_ok=True)
    else:
        # highlights.mp4 — delete it, leave clips intact
        path.unlink()
    clips = sorted([p.name for p in out_dir.glob("clip_*.mp4")])
    stitched = "highlights.mp4" if (out_dir / "highlights.mp4").exists() else None
    return {"clips": clips, "stitched": stitched}


@router.delete("/output/{video_id}")
def delete_all_output(video_id: str):
    out_dir = _output_dir(video_id)
    if out_dir.exists():
        for p in out_dir.glob("clip_*.mp4"):
            p.unlink()
        highlights = out_dir / "highlights.mp4"
        highlights.unlink(missing_ok=True)
    return {"clips": [], "stitched": None}


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    video_id = workdir.make_video_id(file.filename or "video")
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    dest = workdir.uploads_dir(video_id) / f"source{ext}"
    dest.write_bytes(await file.read())
    try:
        duration = probe_duration(str(dest))
    except ValueError:
        raise HTTPException(400, "Uploaded file is not a decodable video")
    state.put(video_id, {"path": str(dest), "duration": duration})
    (workdir.uploads_dir(video_id) / "meta.json").write_text(
        json.dumps({"original_filename": file.filename or "video", "uploaded_at": time.time()})
    )
    return {"video_id": video_id, "duration": duration}


def _project_meta(d: Path) -> dict:
    """Return common metadata for a project directory."""
    uploads = d / "uploads"
    source_files = list(uploads.glob("source.*"))
    meta_path = uploads / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            original_filename = meta.get(
                "original_filename",
                source_files[0].name if source_files else d.name,
            )
            uploaded_at = float(meta.get("uploaded_at", d.stat().st_mtime))
        except Exception:
            original_filename = source_files[0].name if source_files else d.name
            uploaded_at = d.stat().st_mtime
    else:
        original_filename = source_files[0].name if source_files else d.name
        uploaded_at = d.stat().st_mtime
    size_bytes = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    return {
        "video_id": d.name,
        "original_filename": original_filename,
        "uploaded_at": uploaded_at,
        "size_bytes": size_bytes,
    }


def _list_drafts() -> list[dict]:
    if not workdir.WORKDIR.exists():
        return []
    results = []
    for d in workdir.WORKDIR.iterdir():
        if not d.is_dir():
            continue
        uploads = d / "uploads"
        source_files = list(uploads.glob("source.*"))
        has_source = len(source_files) > 0
        completed = (d / "clips" / "highlights.mp4").exists()
        if not has_source or completed:
            continue
        analyzed = (uploads / "signals.npz").exists()
        meta = _project_meta(d)
        meta["analyzed"] = analyzed
        results.append(meta)
    results.sort(key=lambda x: x["uploaded_at"], reverse=True)
    return results


def _list_library() -> list[dict]:
    if not workdir.WORKDIR.exists():
        return []
    results = []
    for d in workdir.WORKDIR.iterdir():
        if not d.is_dir():
            continue
        if not (d / "clips" / "highlights.mp4").exists():
            continue
        meta = _project_meta(d)
        meta["clip_count"] = len(list((d / "clips").glob("clip_*.mp4")))
        results.append(meta)
    results.sort(key=lambda x: x["uploaded_at"], reverse=True)
    return results


@router.patch("/projects/{video_id}/name")
def rename_project(video_id: str, body: RenameBody):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Project not found")
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Name cannot be empty")
    name = name[:200]
    meta_path = dir / "uploads" / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    else:
        meta = {}
    meta["original_filename"] = name
    if "uploaded_at" not in meta:
        meta["uploaded_at"] = dir.stat().st_mtime
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta))
    return _project_meta(dir)


@router.get("/drafts")
def list_drafts():
    return _list_drafts()


@router.delete("/drafts/{video_id}")
def delete_draft(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    d = workdir.WORKDIR / video_id
    if not d.exists():
        raise HTTPException(404, "Draft not found")
    if d.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    if (d / "clips" / "highlights.mp4").exists():
        raise HTTPException(409, "Not a draft (already exported)")
    shutil.rmtree(d)
    return _list_drafts()


@router.get("/library")
def list_library():
    return _list_library()


@router.post("/library/{video_id}/open")
def open_library_project(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Not found")
    source = next((dir / "uploads").glob("source.*"), None)
    if source is None:
        raise HTTPException(404, "Source not found")
    try:
        dur = probe_duration(str(source))
    except ValueError:
        raise HTTPException(400, "Cannot probe video duration")
    state.put(video_id, {"path": str(source), "duration": dur})
    return {"video_id": video_id, "duration": dur}


@router.delete("/library/{video_id}")
def delete_library_project(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,60}', video_id):
        raise HTTPException(400, "Invalid video_id")
    dir = workdir.WORKDIR / video_id
    if not dir.exists():
        raise HTTPException(404, "Not found")
    if dir.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    shutil.rmtree(dir)
    state._REGISTRY.pop(video_id, None)
    return _list_library()


@router.post("/detect")
def detect(body: DetectBody):
    info = _require(body.video_id)
    params = _params(body.params)
    job_id = jobs.create()

    def run():
        def _cb(f):
            rec = jobs.get(job_id)
            if rec and rec["cancelled"]:
                raise _Cancelled()
            jobs.update(job_id, progress=f)

        try:
            rallies = pipeline.analyze(
                body.video_id, info["path"], params,
                progress_callback=_cb,
            )
            jobs.update(job_id, status="done", progress=1.0,
                        result={"rallies": rallies})
        except _Cancelled:
            jobs.update(job_id, status="cancelled")
        except Exception as e:  # noqa: BLE001 - surface to client as job error
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.post("/resegment")
def resegment(body: DetectBody):
    _require(body.video_id)
    return {"rallies": pipeline.resegment(body.video_id, _params(body.params))}


@router.post("/export")
def export(body: ExportBody):
    info = _require(body.video_id)
    out_dir = str(workdir.clips_dir(body.video_id))
    job_id = jobs.create()

    def run():
        def _cb(f):
            rec = jobs.get(job_id)
            if rec and rec["cancelled"]:
                raise _Cancelled()
            jobs.update(job_id, progress=f)

        try:
            result = exporter.export(
                info["path"], body.ranges, out_dir,
                progress_callback=_cb,
            )
            jobs.update(job_id, status="done", progress=1.0, result=result)
        except _Cancelled:
            jobs.update(job_id, status="cancelled")
        except Exception as e:  # noqa: BLE001
            jobs.update(job_id, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    rec = jobs.get(job_id)
    if rec is None:
        raise HTTPException(404, "Unknown job_id")
    return rec


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    rec = jobs.get(job_id)
    if rec is None:
        raise HTTPException(404, "Unknown job_id")
    jobs.cancel(job_id)
    return jobs.get(job_id)


@router.get("/video/{video_id}")
def get_video(video_id: str):
    info = _require(video_id)
    return FileResponse(info["path"])
