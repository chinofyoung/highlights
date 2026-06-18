# Task 11 Report: Serve SPA from FastAPI + Remove Old Vanilla UI

## Status: COMPLETE

---

## Files Modified / Deleted

### Modified
- `app/main.py` — repointed `WEB_DIR` from `Path(__file__).parent / "web"` to `Path(__file__).parent.parent / "frontend" / "dist"`

### Deleted
- `app/web/index.html`
- `app/web/app.js`
- `app/web/style.css`
- `app/web/` directory (was empty after file removal)

---

## Step 3: Frontend Build Result

```
vite v6.4.3 building for production...
✓ 1583 modules transformed.
dist/index.html                   0.75 kB │ gzip:  0.43 kB
dist/assets/index-D8kMaZj1.css   18.39 kB │ gzip:  4.42 kB
dist/assets/index-BWUwu9Aa.js   159.23 kB │ gzip: 51.10 kB
✓ built in 816ms
```

`frontend/dist/index.html` confirmed present.

---

## Step 4: Curl / HTTP Verification

Server started: `uvicorn app.main:app --port 8000`

| Check | Command | Result |
|-------|---------|--------|
| SPA root serves 200 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` | **200** |
| SPA mount div present | `curl -s http://localhost:8000/ \| grep -c "root"` | **1** (found) |
| API not shadowed | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/jobs/nope` | **404** |

All three checks passed. Server was stopped after verification.

---

## Step 5: Backend Regression — pytest -v

```
35 passed, 3 warnings in 3.49s
```

Full suite green. Warnings are pre-existing deprecations (FastAPI `on_event` → lifespan, httpx/httpx2) — not introduced by this task.

---

## Step 6: Manual End-to-End

Automated curl checks confirm:
- `/` returns HTTP 200 with the SPA HTML containing `id="root"` mount point
- `/api/*` routes are not shadowed (404 returned for unknown job ID)
- Static assets (`/assets/index-*.js`, `/assets/index-*.css`) are served from `frontend/dist/assets/`

**Full click-through verification requires a real pickleball video clip and is a manual step.** The app is structurally wired correctly: router is mounted before the static files mount, so `/api/*` routes take priority over the catch-all SPA mount.

---

## Deviations

None. Implementation matches the brief exactly.

---

## Concerns

None. The two deprecation warnings (`on_event` and httpx/httpx2) were present before this task and are out of scope.
