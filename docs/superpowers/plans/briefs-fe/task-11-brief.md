# Task 11 (modern-frontend)

## Global Constraints

- **Backend Python floor:** 3.10+ (interpreter is 3.10.8). Activate `.venv` before any pytest.
- **No new backend dependencies** — background work uses stdlib `threading`.
- **Backward-compatible analyzer/exporter signatures:** new `progress_callback` params MUST default to `None` so existing callers/tests keep working.
- **Existing backend suite (24 tests) must stay green** except the two `/api/detect` & `/api/export` tests in `tests/test_api.py`, which are intentionally updated in Task 4 to the new job flow.
- **Git is disabled** (not a git repo; user policy forbids state-changing git). Wherever a step says "Commit", instead run the task's tests (and build, where relevant) and confirm green. Never run a state-changing git command.
- **Node 22 / npm 10** are installed. Frontend commands run from `frontend/`.
- **Sensitivity semantics:** higher slider = more sensitive = more rallies; the client sends `threshold = 1 - sliderValue`.
- **Job record shape (canonical, used across backend + frontend):** `{ "status": "running"|"done"|"error", "progress": float 0.0–1.0, "result": object|null, "error": string|null }`.
- **Detect job result shape:** `{ "rallies": [{start, end, confidence}] }`. **Export job result shape:** `{ "clips": [string], "stitched": string|null }`.
- **If a pinned npm version fails to resolve,** install the latest compatible version and note it in the task report.



---

## Task 11: Serve the SPA from FastAPI + remove old UI

**Files:**
- Modify: `app/main.py`
- Delete: `app/web/index.html`, `app/web/app.js`, `app/web/style.css`

**Interfaces:**
- Consumes: built `frontend/dist/`.
- Produces: FastAPI serving the SPA at `/` with `/api/*` still routed.

- [ ] **Step 1: Modify `app/main.py`** — repoint the static mount

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg
from app.api.routes import router

app = FastAPI(title="Pickleball Highlights")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


app.include_router(router)

WEB_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

- [ ] **Step 2: Delete the old vanilla UI**

Remove `app/web/index.html`, `app/web/app.js`, `app/web/style.css` (and the `app/web/` directory if empty).

- [ ] **Step 3: Build the frontend so dist exists**

Run: `cd frontend && npm run build`
Expected: `frontend/dist/index.html` present.

- [ ] **Step 4: Verify FastAPI serves the SPA and API together**

Run (repo root):
```bash
source .venv/bin/activate
uvicorn app.main:app --port 8000   # background
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/            # expect 200
curl -s http://localhost:8000/ | grep -c "root"                          # expect >=1 (SPA mount div)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/jobs/nope   # expect 404 (API not shadowed)
# stop the server
```

- [ ] **Step 5: Backend regression check**

Run: `source .venv/bin/activate && pytest -v`
Expected: full backend suite green.

- [ ] **Step 6: Manual end-to-end verification**

With ffmpeg installed and the server running, open `http://localhost:8000`, upload a real fixed-camera pickleball clip, and confirm: a real progress bar advances during detection; rallies render on the timeline; dragging a rally's handles trims it and the player seeks to the edge; the sensitivity slider changes the rally set; Export shows a progress bar then the result panel with output paths; light/dark toggle works. Note any issues in the report. (No bundled sample match video — this final check needs a real clip.)

- [ ] **Step 7: Checkpoint** — backend `pytest -v` green and `frontend npm run test` green.

---

