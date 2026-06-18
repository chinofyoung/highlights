# Drafts Safety Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent `DELETE /api/drafts/{video_id}` from destroying completed exports, add a 409 test, and silence the React `act()` warning in App tests.

**Architecture:** Two independent fixes — (1) a one-line guard in the DELETE drafts route that checks for `output/highlights.mp4` before calling `shutil.rmtree`, and (2) a mock/waitFor adjustment in the frontend App test so async state updates from `DraftsSection` are flushed before assertions run.

**Tech Stack:** Python/FastAPI backend (pytest), React/TypeScript frontend (vitest + @testing-library/react).

## Global Constraints

- No git commands (no commit, branch, push, etc.)
- Backend venv: `source /Users/chinoyoung/Code/highlights/.venv/bin/activate`
- Frontend root: `/Users/chinoyoung/Code/highlights/frontend/`
- Report destination: append to `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/drafts-report.md`

---

### Task 1: Add 409 guard to DELETE /api/drafts/{video_id}

**Files:**
- Modify: `/Users/chinoyoung/Code/highlights/app/api/routes.py:174-184`
- Test: `/Users/chinoyoung/Code/highlights/tests/test_drafts.py`

**Interfaces:**
- Consumes: existing `delete_draft` handler in `routes.py`
- Produces: handler raises `HTTPException(409, "Not a draft (already exported)")` when `(dir / "output" / "highlights.mp4").exists()`

- [ ] **Step 1: Open routes.py and locate the delete_draft handler**

The handler is at lines 174-184 of `/Users/chinoyoung/Code/highlights/app/api/routes.py`:

```python
@router.delete("/drafts/{video_id}")
def delete_draft(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    d = workdir.WORKDIR / video_id
    if not d.exists():
        raise HTTPException(404, "Draft not found")
    if d.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    shutil.rmtree(d)
    return _list_drafts()
```

- [ ] **Step 2: Add the 409 guard — insert BEFORE `shutil.rmtree(d)`**

Replace the handler body so it becomes:

```python
@router.delete("/drafts/{video_id}")
def delete_draft(video_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_]{1,40}', video_id):
        raise HTTPException(400, "Invalid video_id")
    d = workdir.WORKDIR / video_id
    if not d.exists():
        raise HTTPException(404, "Draft not found")
    if d.resolve().parent != workdir.WORKDIR.resolve():
        raise HTTPException(400, "Invalid video_id")
    if (d / "output" / "highlights.mp4").exists():
        raise HTTPException(409, "Not a draft (already exported)")
    shutil.rmtree(d)
    return _list_drafts()
```

- [ ] **Step 3: Write the new test in test_drafts.py**

Add this test at the end of `/Users/chinoyoung/Code/highlights/tests/test_drafts.py`:

```python
def test_delete_completed_draft_returns_409(tmp_path, monkeypatch):
    from app import workdir
    monkeypatch.setattr(workdir, "WORKDIR", tmp_path)

    # Build a completed folder: has source.mp4 AND output/highlights.mp4
    completed_id = "vid_completed"
    d = _make_completed(tmp_path, completed_id)

    from app.main import app
    client = TestClient(app)
    r = client.delete(f"/api/drafts/{completed_id}")
    assert r.status_code == 409
    assert "already exported" in r.json()["detail"].lower()
    # The folder must still exist on disk — rmtree was NOT called
    assert d.exists()
```

Note: `_make_completed` already exists in the test file at line 30-36 — it creates `source.mp4` and `output/highlights.mp4`.

- [ ] **Step 4: Run just the new test to confirm it passes**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_drafts.py::test_delete_completed_draft_returns_409 -v
```

Expected output:
```
PASSED tests/test_drafts.py::test_delete_completed_draft_returns_409
```

- [ ] **Step 5: Run the full test_drafts.py suite**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest tests/test_drafts.py -v
```

Expected: all tests PASSED, no failures.

- [ ] **Step 6: Run the full pytest suite**

```bash
cd /Users/chinoyoung/Code/highlights && source .venv/bin/activate && pytest -v
```

Expected: all tests PASSED (green).

---

### Task 2: Silence act() warning in frontend App tests

**Files:**
- Modify: `/Users/chinoyoung/Code/highlights/frontend/src/test/App.test.tsx`

**Interfaces:**
- Consumes: `api.listDrafts` mock already set to `vi.fn().mockResolvedValue([])` in the mock factory at line 15
- Produces: each `render(<App />)` call is followed by `await act(async () => {})` so the async `listDrafts()` state update is flushed before assertions

**Background:** `DraftsSection` calls `listDrafts()` on mount and calls `setState` when it resolves. In tests, this promise resolves after the first render but outside `act()`, causing React to warn. The mock already returns a resolved value; we just need to flush the microtask queue after render.

- [ ] **Step 1: Add `act` to the imports from @testing-library/react**

At line 2 of `/Users/chinoyoung/Code/highlights/frontend/src/test/App.test.tsx`, the import is:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
```

Change it to:

```typescript
import { render, screen, waitFor, act } from "@testing-library/react";
```

- [ ] **Step 2: Wrap each `render(<App />)` with an async act flush**

Each test currently calls `render(<App />)` synchronously. Wrap each with an async act so the post-render state update from `listDrafts()` is flushed.

The pattern for every test that calls `render(<App />)` is:

```typescript
// Before (example from test 1):
render(<App />);
expect(screen.getByText(/find the rallies/i)).toBeInTheDocument();

// After:
render(<App />);
await act(async () => {});
expect(screen.getByText(/find the rallies/i)).toBeInTheDocument();
```

Apply this to ALL four `render(<App />)` calls in the file (lines 28, 33, 51, 61, 77). In tests that already `await` something before the assertion (e.g. `waitFor`), adding `await act(async () => {})` immediately after `render` is still correct — it flushes before the event sequence begins.

The four test bodies become:

**Test "shows UploadView initially" (line 27-30):** Make the test async and add the flush:
```typescript
it("shows UploadView initially", async () => {
  render(<App />);
  await act(async () => {});
  expect(screen.getByText(/find the rallies/i)).toBeInTheDocument();
});
```

**Test "selecting a file..." (line 32-48):** Already async. Add flush after render:
```typescript
render(<App />);
await act(async () => {});
// rest unchanged
```

**Test "clicking Analyze video..." (line 50-74):** Already async. Add flush after render:
```typescript
render(<App />);
await act(async () => {});
// rest unchanged
```

**Test "Reset button returns to UploadView" (line 76-92):** Already async. Add flush after render:
```typescript
render(<App />);
await act(async () => {});
// rest unchanged
```

- [ ] **Step 3: Ensure listDrafts mock re-resolves after vi.clearAllMocks()**

The `beforeEach` at line 22 calls `vi.clearAllMocks()`, which resets `mockResolvedValue([])` set in the factory. After clearing, `listDrafts` returns `undefined` by default, which causes the state update to resolve with `undefined` and can still cause warnings.

Add a `beforeEach` that re-applies the mock after clearing:

```typescript
beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listDrafts).mockResolvedValue([]);
  vi.mocked(api.deleteDraft).mockResolvedValue([]);
});
```

This replaces the existing `beforeEach` at line 22-24.

- [ ] **Step 4: Run the frontend build (TypeScript check)**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run build
```

Expected: exits 0, no TypeScript errors.

- [ ] **Step 5: Run frontend tests**

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run test
```

Expected: all tests pass. Verify the `act()` warning is absent (search stdout/stderr for "act" warning text: `Warning: An update to ... inside a test was not wrapped in act`).

---

### Task 3: Append results to drafts-report.md

**Files:**
- Modify: `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/drafts-report.md`

- [ ] **Step 1: Append the report section**

Append the following to the end of `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/drafts-report.md`:

```markdown

---

## Safety Fix + Test Hygiene — 2026-06-17

### Fix 1: DELETE /api/drafts/{video_id} — 409 guard for completed folders

**Change:** Added a check in `delete_draft` (routes.py) before `shutil.rmtree`:
if `(dir / "output" / "highlights.mp4").exists()` → raise `HTTPException(409, "Not a draft (already exported)")`.

**Location:** `/Users/chinoyoung/Code/highlights/app/api/routes.py` — `delete_draft` handler.

**New test:** `test_delete_completed_draft_returns_409` in `tests/test_drafts.py`.
- Constructs a completed folder (source.mp4 + output/highlights.mp4) via `_make_completed`.
- DELETE → expect 409.
- Asserts folder still exists on disk.

**Backend test output:**
[paste pytest -v output here]

### Fix 2: React act() warning in App.test.tsx

**Change:** Added `await act(async () => {})` after each `render(<App />)` call to flush the async `listDrafts()` state update from `DraftsSection`. Also added `vi.mocked(api.listDrafts).mockResolvedValue([])` in `beforeEach` to re-apply the mock after `vi.clearAllMocks()`.

**Location:** `/Users/chinoyoung/Code/highlights/frontend/src/test/App.test.tsx`

**Frontend test output:**
[paste npm run test output here]
```
