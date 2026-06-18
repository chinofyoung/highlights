# Cherry.Pickle

Local tool that detects rallies in fixed-camera pickleball videos, lets you
review/trim them in the browser, and exports per-rally clips plus one stitched
highlight video.

## Requirements
- Python 3.10+
- ffmpeg + ffprobe on your PATH (`brew install ffmpeg`)

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

First-time setup (build the frontend):
```bash
cd frontend
npm install
npm run build
cd ..
```

Then run the app:
```bash
uvicorn app.main:app --reload
```
Open http://localhost:8000, upload a match video, review the detected rallies,
adjust sensitivity, then Export. Outputs land in `workdir/<video_id>/output/`.

## Test
```bash
pytest -v
```
(Tests that need ffmpeg auto-skip if it isn't installed.)

## Frontend (Vite + React)

The UI lives in `frontend/` (Vite + React + TypeScript + Tailwind) and builds to
`frontend/dist/`, which the FastAPI server serves automatically.

### One-time build (required before running normally)
```bash
cd frontend
npm install
npm run build
```
Then run the app as usual from the repo root: `uvicorn app.main:app` and open
http://localhost:8000.

### Frontend development (hot reload)
Run the backend and the Vite dev server in two terminals:
```bash
# terminal 1 (repo root)
source .venv/bin/activate && uvicorn app.main:app

# terminal 2
cd frontend && npm run dev
```
Open http://localhost:5173 — Vite proxies `/api/*` to the backend on :8000.

Or run both servers at once from the repo root:

    ./dev.sh

### Frontend tests
```bash
cd frontend && npm run test
```

## Tuning detection
Defaults live in `app/config.py` (`DetectionParams`): `sample_fps`, `threshold`,
`merge_gap_seconds`, `min_rally_seconds`, `pad_seconds`.
# highlights
# highlights
# highlights
