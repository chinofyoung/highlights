# Continue Drafts + Home Nav + Rename-Folder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let users resume unfinished drafts, navigate back to the upload/home screen from anywhere, and have renaming a project also rename its Documents folder.

**Architecture:** Mostly frontend wiring plus one backend change. Drafts resume by reusing the existing `openProject` + `resegment`/`startDetect` (no new endpoints). Home nav is a `goHome()` state reset wired to the header logo + a "New video" button. Rename re-keys the project: the backend moves the folder (sanitized, unique id) and updates the in-memory registry, returning the new `video_id` that the list components adopt.

**Tech Stack:** Python 3.10+, FastAPI; React + TypeScript + Tailwind v4; pytest. Test command: `.venv/bin/python -m pytest`. Frontend verify: `cd frontend && npm run build`.

## Global Constraints

- Draft resume = "furthest step": analyzed drafts (have `uploads/signals.npz`) open into the review screen via `resegment` (instant); uploaded-only drafts start detection via `startDetect`.
- Navigation = clickable header logo + a "New video"/Home button; both call a single `goHome()` that resets to the upload screen.
- Rename re-keys the folder to a **sanitized** form of the typed name (`workdir._slugify`), unique within `~/Documents/Highlights` (append `_2`, `_3`… on collision). The display name (`meta.json` `original_filename`) keeps the exact typed text. New folder id stays within `[A-Za-z0-9_]{1,60}` (traversal-safe).
- Rename only ever happens from the Drafts/Library lists (never mid-edit), so re-keying is safe.
- Git disabled (not a repo): each task ends with a Checkpoint running the suite/build, no commit.
- Baseline before this plan: 101 passed.

---

### Task 1: Backend — rename re-keys (moves) the project folder

**Files:**
- Modify: `app/workdir.py` (add `unique_video_id`)
- Modify: `app/api/routes.py` (`rename_project`)
- Test: `tests/test_rename.py`

**Interfaces:**
- Produces: `workdir.unique_video_id(name: str, current: str | None = None) -> str` — sanitized, collision-free folder id. `PATCH /api/projects/{video_id}/name` now moves the folder when the sanitized id differs, re-keys `state`, and returns `_project_meta(new_dir)` (which includes the new `video_id` and `original_filename`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rename.py` (it already imports `json`, `workdir`, `TestClient`, and has `_make_draft`):

```python
def test_rename_moves_folder_and_rekeys_state(tmp_path, monkeypatch):
    from app import workdir
    from app.api import state
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    _make_draft(tmp_path, "game_abc123")
    state.put("game_abc123", {"path": str(tmp_path / "game_abc123" / "uploads" / "source.mp4"),
                              "duration": 1.0})
    from app.main import app
    client = TestClient(app)

    r = client.patch("/api/projects/game_abc123/name", json={"name": "My Match"})
    assert r.status_code == 200
    body = r.json()
    assert body["video_id"] == "My_Match"
    assert body["original_filename"] == "My Match"
    assert (tmp_path / "My_Match" / "uploads" / "source.mp4").exists()
    assert not (tmp_path / "game_abc123").exists()
    # state re-keyed: old gone, new present with path inside the moved folder
    assert state.get("game_abc123") is None
    assert state.get("My_Match") is not None
    assert "My_Match" in state.get("My_Match")["path"]


def test_rename_collision_appends_suffix(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    _make_draft(tmp_path, "existing_one")
    # pre-create a folder that the sanitized target would collide with
    (tmp_path / "My_Match").mkdir(parents=True, exist_ok=True)
    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/existing_one/name", json={"name": "My Match"})
    assert r.status_code == 200
    assert r.json()["video_id"] == "My_Match_2"
    assert (tmp_path / "My_Match_2").exists()


def test_rename_same_sanitized_name_no_move(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)
    _make_draft(tmp_path, "My_Match")
    from app.main import app
    client = TestClient(app)
    r = client.patch("/api/projects/My_Match/name", json={"name": "My Match"})
    assert r.status_code == 200
    assert r.json()["video_id"] == "My_Match"   # unchanged, no _2
    assert (tmp_path / "My_Match" / "uploads").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_rename.py -k "moves_folder or collision or same_sanitized" -v`
Expected: FAIL — rename currently never moves the folder; `video_id` stays `game_abc123`.

- [ ] **Step 3: Add `unique_video_id` to `app/workdir.py`**

```python
def unique_video_id(name: str, current: str | None = None) -> str:
    """A sanitized, collision-free folder id derived from a display name.
    Returns `current` unchanged if the sanitized base already equals it."""
    base = _slugify(name)
    candidate = base
    i = 2
    while candidate != current and (WORKDIR / candidate).exists():
        candidate = f"{base}_{i}"
        i += 1
    return candidate
```

- [ ] **Step 4: Rewrite `rename_project` in `app/api/routes.py`**

Replace the body of `rename_project` (currently `routes.py:200-224`) with:

```python
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

    new_id = workdir.unique_video_id(name, current=video_id)
    new_dir = dir
    if new_id != video_id:
        new_dir = workdir.WORKDIR / new_id
        shutil.move(str(dir), str(new_dir))
        # re-key in-memory state so an open session follows the moved folder
        info = state.get(video_id)
        state._REGISTRY.pop(video_id, None)
        if info is not None:
            source = next((new_dir / "uploads").glob("source.*"), None)
            state.put(new_id, {**info, "path": str(source) if source else info.get("path")})

    meta_path = new_dir / "uploads" / "meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    else:
        meta = {}
    meta["original_filename"] = name
    if "uploaded_at" not in meta:
        meta["uploaded_at"] = new_dir.stat().st_mtime
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta))
    return _project_meta(new_dir)
```

(`shutil` and `state` are already imported in `routes.py`.)

- [ ] **Step 5: Run the new tests**

Run: `.venv/bin/python -m pytest tests/test_rename.py -v`
Expected: the 3 new tests PASS. If any PRE-EXISTING `test_rename.py` test now fails because it asserted the old folder path after a rename, reconcile it to use the returned `video_id`/new folder (the rename now moves the folder when the sanitized name differs). Do NOT weaken assertions — update the path expectations to the new id. Report any such change.

- [ ] **Step 6: Checkpoint**

Run: `.venv/bin/python -m pytest -q`
Expected: fully green. Report the count.

---

### Task 2: Frontend — rename adopts the new video_id

**Files:**
- Modify: `frontend/src/components/DraftsSection.tsx` (`commitEdit`)
- Modify: `frontend/src/components/LibrarySection.tsx` (`commitEdit`)

**Interfaces:**
- Consumes: `renameProject(videoId, name)` → `{ video_id, original_filename }` (Task 1 now returns a possibly-changed `video_id`).

- [ ] **Step 1: Update DraftsSection.commitEdit to adopt the new id**

In `frontend/src/components/DraftsSection.tsx`, the `commitEdit` mapper currently updates only `original_filename`. Change the `setDrafts` mapper to also adopt `r.video_id`:

```tsx
      const r = await renameProject(videoId, trimmed);
      setDrafts((prev) =>
        prev.map((d) =>
          d.video_id === videoId
            ? { ...d, video_id: r.video_id, original_filename: r.original_filename }
            : d,
        ),
      );
```

- [ ] **Step 2: Update LibrarySection.commitEdit the same way**

In `frontend/src/components/LibrarySection.tsx`, change its `setProjects` mapper in `commitEdit`:

```tsx
      const r = await renameProject(videoId, trimmed);
      setProjects((prev) =>
        prev.map((p) =>
          p.video_id === videoId
            ? { ...p, video_id: r.video_id, original_filename: r.original_filename }
            : p,
        ),
      );
```

- [ ] **Step 3: Checkpoint (build)**

Run: `cd /Users/chinoyoung/Code/highlights/frontend && npm run build`
Expected: zero TypeScript errors. (`Draft` and `Project` types both have `video_id: string`, so adopting it type-checks.)

---

### Task 3: Frontend — continue a draft

**Files:**
- Modify: `frontend/src/components/DraftsSection.tsx` (add `onContinue` prop + Continue button + handler)
- Modify: `frontend/src/App.tsx` (add `handleContinueDraft`, pass prop)

**Interfaces:**
- Consumes: `openProject(videoId)` → `{ video_id, duration }`; `api.resegment`, `api.startDetect`; `Draft.analyzed: boolean`.
- Produces: `DraftsSection` prop `onContinue: (videoId: string, duration: number, analyzed: boolean) => void`.

- [ ] **Step 1: Add the Continue affordance to DraftsSection**

In `frontend/src/components/DraftsSection.tsx`:
- Add `openProject` to the import from `../api`: `import { listDrafts, deleteDraft, renameProject, openProject } from "../api";`
- Change the component signature to accept the prop:

```tsx
interface DraftsSectionProps {
  onContinue: (videoId: string, duration: number, analyzed: boolean) => void;
}

export function DraftsSection({ onContinue }: DraftsSectionProps) {
```
- Add an open-error state near the other `useState`s: `const [openError, setOpenError] = useState<string | null>(null);`
- Add a handler:

```tsx
  async function handleContinue(draft: Draft) {
    setOpenError(null);
    try {
      const r = await openProject(draft.video_id);
      onContinue(r.video_id, r.duration, draft.analyzed);
    } catch (e) {
      setOpenError(e instanceof Error ? e.message : String(e));
    }
  }
```
- Render the error under the heading (after the `<h2>`):

```tsx
      {openError && <p className="text-sm text-[var(--danger)]">{openError}</p>}
```
- Add a "Continue" button as the FIRST control in the row's right-hand side. The row currently ends with the delete `<button>`; wrap both in a flex container so they sit side by side. Replace the standalone delete button at the end of each row with:

```tsx
            <div className="flex shrink-0 items-center gap-2">
              <button
                onClick={() => handleContinue(draft)}
                className="rounded bg-[var(--teal)] px-3 py-1.5 text-xs text-white
                           hover:opacity-90 transition-opacity"
              >
                Continue
              </button>
              <button
                onClick={() => handleDelete(draft.video_id)}
                aria-label={`Delete draft ${draft.original_filename}`}
                className="rounded p-1.5 text-[var(--muted)] hover:text-[var(--danger)]
                           transition-colors focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
              >
                <Trash2 size={14} />
              </button>
            </div>
```

- [ ] **Step 2: Add `handleContinueDraft` in App.tsx and pass the prop**

In `frontend/src/App.tsx`, add the handler (near `handleOpenProject`):

```tsx
  async function handleContinueDraft(vId: string, dur: number, analyzed: boolean) {
    setLibraryView(false);
    setExportJob(null);
    if (analyzed) {
      try {
        const { rallies: rs } = await api.resegment(vId, { threshold: 1 - sensitivity });
        setRallies(rs);
      } catch { setRallies([]); }
      setDuration(dur);
      setVideoId(vId);            // set last → View 4 renders with rallies already loaded
    } else {
      setRallies([]);
      setDuration(dur);
      const { job_id } = await api.startDetect(vId, { threshold: 1 - sensitivity });
      setVideoId(vId);
      setDetectJob(job_id);       // → detecting view
    }
  }
```

Then update the View 1 render of DraftsSection to pass the prop:

```tsx
            <DraftsSection onContinue={handleContinueDraft} />
```

- [ ] **Step 3: Checkpoint (build)**

Run: `cd /Users/chinoyoung/Code/highlights/frontend && npm run build`
Expected: zero TypeScript errors.

---

### Task 4: Frontend — home navigation

**Files:**
- Modify: `frontend/src/App.tsx` (add `goHome`, clickable logo, "New video" button, route library Back through `goHome`)

**Interfaces:**
- Produces: `goHome()` resets to the upload/home screen.

- [ ] **Step 1: Add `goHome`**

In `frontend/src/App.tsx`, add:

```tsx
  function goHome() {
    setSelectedFile(null);
    setVideoId(null);
    setRallies([]);
    setDetectJob(null);
    setExportJob(null);
    setAnalyzing(false);
    setLibraryView(false);
    setUploadError(null);
  }
```

- [ ] **Step 2: Make the header logo clickable + add a "New video" button**

Replace the existing `<header>...</header>` block with:

```tsx
      <header className="flex items-center justify-between border-b border-[var(--line)] px-6 py-4 sm:px-8">
        <button
          onClick={goHome}
          className="font-display text-lg font-bold tracking-tight text-[var(--ink)]
                     hover:opacity-80 transition-opacity"
          aria-label="Go to home / upload"
        >
          Pickleball<span className="text-[var(--teal)]">.</span>highlights
        </button>
        <div className="flex items-center gap-3">
          {(videoId || selectedFile) && (
            <button
              onClick={goHome}
              className="rounded border border-[var(--line)] px-3 py-1.5 text-sm
                         text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
            >
              New video
            </button>
          )}
          <ThemeToggle />
        </div>
      </header>
```

- [ ] **Step 3: Route the library-view Back button through `goHome`**

In View 4a (`libraryView && videoId`), the "← Back" button currently inlines several setters. Replace its `onClick` with `goHome`:

```tsx
              <button
                onClick={goHome}
                className="rounded border border-[var(--line)] px-3 py-1.5 text-sm text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
              >
                ← Back
              </button>
```

- [ ] **Step 4: Checkpoint (build)**

Run: `cd /Users/chinoyoung/Code/highlights/frontend && npm run build`
Expected: zero TypeScript errors.

---

## Self-Review

**Spec coverage:**
- Resume to furthest step (analyzed → review via resegment; uploaded-only → detect) → Task 3 `handleContinueDraft`. ✅
- Continue affordance on drafts → Task 3 (Continue button + `onContinue`). ✅
- Home nav: clickable logo + Home button reaching upload from any screen → Task 4 (`goHome`, header). ✅
- Library Back unified through goHome → Task 4 Step 3. ✅
- Rename moves folder, sanitized + unique, re-keys state, returns new id → Task 1. ✅
- Frontend adopts new id on rename → Task 2. ✅

**Placeholder scan:** None — every step shows complete code and exact commands.

**Type consistency:** `onContinue(videoId, duration, analyzed)` is defined in Task 3's prop and matches `handleContinueDraft`'s signature and the `<DraftsSection onContinue=...>` usage. `renameProject` returns `{video_id, original_filename}` (existing type) — adopted in Task 2 and Task 1's `_project_meta` return includes `video_id`. `unique_video_id` defined in Task 1 Step 3, used in Step 4. `Draft.analyzed` and `Draft.video_id`/`Project.video_id` exist in `types.ts` (confirmed).

**Note on ordering:** Task 1 (backend rename) before Task 2 (frontend adopts new id) so the returned id actually changes. Tasks 3 and 4 are independent of 1–2 and of each other but share `App.tsx`/`DraftsSection.tsx`; run sequentially (subagent-driven executes one task at a time, so no merge conflict).
