# Rename Task A — Report

## Status

COMPLETE — all 5 files edited, build green, 111 tests passed, title=Cherry.Pickle.

---

## Exact Edits Made

### 1. `frontend/src/App.tsx` (line 140)

```diff
-          Pickleball<span className="text-[var(--teal)]">.</span>highlights
+          Cherry<span className="text-[var(--teal)]">.</span>Pickle
```

Surrounding button markup and teal-dot className left unchanged.

---

### 2. `frontend/index.html` (line 6)

```diff
-    <title>Pickleball Highlights — find the rallies</title>
+    <title>Cherry.Pickle — find the rallies</title>
```

---

### 3. `app/main.py` (line 7)

```diff
-app = FastAPI(title="Pickleball Highlights")
+app = FastAPI(title="Cherry.Pickle")
```

---

### 4. `app/desktop.py` (lines 42 and 45)

```diff
-        raise RuntimeError("Highlights server failed to start")
+        raise RuntimeError("Cherry.Pickle server failed to start")

-    webview.create_window("Highlights", f"http://127.0.0.1:{port}/",
+    webview.create_window("Cherry.Pickle", f"http://127.0.0.1:{port}/",
```

URL argument and width/height args left unchanged.

---

### 5. `README.md` (line 1)

```diff
-# Pickleball Highlights
+# Cherry.Pickle
```

Rest of README body left unchanged.

---

## Verification Results

| Check | Result |
|---|---|
| `npm run build` (TS + Vite) | PASS — 0 errors, built in 1.00s |
| `.venv/bin/python -m pytest -q` | PASS — 111 passed, 3 warnings (pre-existing deprecation warnings unrelated to this change) |
| `python -c "from app.main import app; print(app.title)"` | `Cherry.Pickle` |

---

## Out-of-Scope Items Confirmed Untouched

- `app/workdir.py`, `HIGHLIGHTS_HOME` env var, `~/Documents/Highlights` path — not modified.
- `highlights.mp4` filename string — not modified.
- Filename regex in `app/api/routes.py` — not modified.
- `app/exporter/ffmpeg.py` — not modified.
- "Highlights" section heading, "Export highlights" button, `HighlightsView` component — not modified.
- `pyproject.toml` package name — not modified.
- `packaging/` directory — not touched.

---

## Concerns

None. The three pre-existing `DeprecationWarning` entries in pytest output (`on_event` deprecated in FastAPI, `httpx` with `starlette.testclient`) were present before this change and are unrelated to the rename.
