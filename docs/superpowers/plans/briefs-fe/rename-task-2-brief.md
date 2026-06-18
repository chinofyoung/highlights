# Task 2 Brief: Frontend — renameProject api, inline rename in both sections, App.tsx fixes, frontend test

## Objective
1. Add `renameProject` to `api.ts`
2. Add inline rename UX to both `DraftsSection.tsx` and `LibrarySection.tsx`
3. Fix two bugs in `App.tsx` (stale exportJob + swallowed errors)
4. Add api test for `renameProject`

All files are under `/Users/chinoyoung/Code/highlights/frontend/`.

---

## 1. api.ts — add renameProject

File: `/Users/chinoyoung/Code/highlights/frontend/src/api.ts`

Add this function at the end:

```typescript
export async function renameProject(
  videoId: string,
  name: string,
): Promise<{ video_id: string; original_filename: string }> {
  const r = await fetch(`/api/projects/${videoId}/name`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}
```

---

## 2. DraftsSection.tsx — inline rename

File: `/Users/chinoyoung/Code/highlights/frontend/src/components/DraftsSection.tsx`

Replace the entire file with the version below. Key changes:
- Import `Pencil`, `Check`, `X` from `lucide-react`
- Import `useRef` from react
- Import `renameProject` from `../api`
- Add state: `editingId: string | null`, `draftName: string`
- Add `inputRef: React.RefObject<HTMLInputElement>` to focus on edit start
- Each card: show `Pencil` icon button next to name; clicking enters edit mode (sets `editingId` + `draftName`)
- In edit mode: show `<input>` prefilled with name, a check button (Save), an X button (Cancel)
  - Save: trim `draftName`; if empty, cancel (no API call); else call `renameProject`, update that item's `original_filename` in state, exit edit mode
  - Cancel: just exit edit mode
  - Keyboard: Enter → Save, Esc → Cancel (onKeyDown on input)
- Update that specific item in the list state (not a full re-fetch)
- Keep existing delete button + handleDelete intact

```tsx
import { useEffect, useRef, useState } from "react";
import { Trash2, Pencil, Check, X } from "lucide-react";
import { listDrafts, deleteDraft, renameProject } from "../api";
import type { Draft } from "../types";

export function DraftsSection() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listDrafts().then(setDrafts).catch(() => {});
  }, []);

  useEffect(() => {
    if (editingId) inputRef.current?.focus();
  }, [editingId]);

  if (drafts.length === 0) return null;

  async function handleDelete(videoId: string) {
    const updated = await deleteDraft(videoId);
    setDrafts(updated);
  }

  function startEdit(draft: Draft) {
    setEditingId(draft.video_id);
    setDraftName(draft.original_filename);
  }

  function cancelEdit() {
    setEditingId(null);
    setDraftName("");
  }

  async function commitEdit(videoId: string) {
    const trimmed = draftName.trim();
    if (!trimmed) { cancelEdit(); return; }
    try {
      const r = await renameProject(videoId, trimmed);
      setDrafts((prev) =>
        prev.map((d) =>
          d.video_id === videoId ? { ...d, original_filename: r.original_filename } : d,
        ),
      );
    } finally {
      setEditingId(null);
      setDraftName("");
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-sm font-semibold tracking-wide text-[var(--muted)] uppercase">
        Unfinished drafts ({drafts.length})
      </h2>
      <div className="flex flex-col gap-2">
        {drafts.map((draft) => (
          <div
            key={draft.video_id}
            className="flex items-center justify-between gap-4 rounded-lg border border-[var(--line)]
                       bg-[var(--surface)] px-4 py-3"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              {editingId === draft.video_id ? (
                <div className="flex items-center gap-1">
                  <input
                    ref={inputRef}
                    value={draftName}
                    onChange={(e) => setDraftName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") { e.preventDefault(); commitEdit(draft.video_id); }
                      if (e.key === "Escape") cancelEdit();
                    }}
                    className="min-w-0 flex-1 rounded border border-[var(--teal)] bg-transparent
                               px-2 py-0.5 text-sm font-medium text-[var(--ink)]
                               focus:outline-none focus:ring-1 focus:ring-[var(--teal)]"
                    aria-label="Edit project name"
                  />
                  <button
                    onClick={() => commitEdit(draft.video_id)}
                    aria-label="Save name"
                    className="rounded p-1 text-[var(--teal)] hover:text-[var(--ink)] transition-colors"
                  >
                    <Check size={14} />
                  </button>
                  <button
                    onClick={cancelEdit}
                    aria-label="Cancel rename"
                    className="rounded p-1 text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
                  >
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className="font-display text-sm font-medium text-[var(--ink)] truncate">
                    {draft.original_filename}
                  </span>
                  <button
                    onClick={() => startEdit(draft)}
                    aria-label={`Rename ${draft.original_filename}`}
                    className="shrink-0 rounded p-0.5 text-[var(--muted)] hover:text-[var(--teal)] transition-colors"
                  >
                    <Pencil size={12} />
                  </button>
                </div>
              )}
              <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
                <span>{new Date(draft.uploaded_at * 1000).toLocaleString()}</span>
                <span className="font-mono">{(draft.size_bytes / 1e6).toFixed(1)} MB</span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    draft.analyzed
                      ? "bg-[var(--teal)]/10 text-[var(--teal)]"
                      : "bg-[var(--surface)] border border-[var(--line)] text-[var(--muted)]"
                  }`}
                >
                  {draft.analyzed ? "Analyzed" : "Uploaded"}
                </span>
              </div>
            </div>
            <button
              onClick={() => handleDelete(draft.video_id)}
              aria-label={`Delete draft ${draft.original_filename}`}
              className="shrink-0 rounded p-1.5 text-[var(--muted)] hover:text-[var(--danger)]
                         transition-colors focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
```

---

## 3. LibrarySection.tsx — inline rename

File: `/Users/chinoyoung/Code/highlights/frontend/src/components/LibrarySection.tsx`

Replace the entire file. Key changes:
- Import `Pencil`, `Check`, `X` from `lucide-react` (already has `Trash2`)
- Import `useRef` from react
- Import `renameProject` from `../api`
- Add state: `editingId: string | null`, `editName: string`
- Add `inputRef` ref
- `handleOpen` wrapped in try/catch, surfacing error as local `openError: string | null` state with `text-[var(--danger)] text-sm` display in the section
- Each card: show `Pencil` next to the project name; editing behavior same as DraftsSection
- Keep existing View button, confirm-delete dialog, handleDelete intact

```tsx
import { useEffect, useRef, useState } from "react";
import { Trash2, Pencil, Check, X } from "lucide-react";
import { listLibrary, openProject, deleteProject, renameProject } from "../api";
import type { Project } from "../types";

interface LibrarySectionProps {
  onOpen: (videoId: string, duration: number) => void;
}

export function LibrarySection({ onOpen }: LibrarySectionProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [openError, setOpenError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listLibrary().then(setProjects).catch(() => {});
  }, []);

  useEffect(() => {
    if (editingId) inputRef.current?.focus();
  }, [editingId]);

  if (projects.length === 0) return null;

  async function handleOpen(videoId: string) {
    setOpenError(null);
    try {
      const r = await openProject(videoId);
      onOpen(r.video_id, r.duration);
    } catch (e) {
      setOpenError(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleDelete(videoId: string) {
    const updated = await deleteProject(videoId);
    setProjects(updated);
    setConfirmDeleteId(null);
  }

  function startEdit(project: Project) {
    setEditingId(project.video_id);
    setEditName(project.original_filename);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditName("");
  }

  async function commitEdit(videoId: string) {
    const trimmed = editName.trim();
    if (!trimmed) { cancelEdit(); return; }
    try {
      const r = await renameProject(videoId, trimmed);
      setProjects((prev) =>
        prev.map((p) =>
          p.video_id === videoId ? { ...p, original_filename: r.original_filename } : p,
        ),
      );
    } finally {
      setEditingId(null);
      setEditName("");
    }
  }

  const pendingProject = projects.find((p) => p.video_id === confirmDeleteId);

  return (
    <>
      <section className="flex flex-col gap-3">
        <h2 className="font-display text-sm font-semibold tracking-wide text-[var(--muted)] uppercase">
          Library ({projects.length})
        </h2>
        {openError && (
          <p className="text-sm text-[var(--danger)]">{openError}</p>
        )}
        <div className="flex flex-col gap-2">
          {projects.map((p) => (
            <div
              key={p.video_id}
              className="flex items-center justify-between gap-4 rounded-lg border border-[var(--line)]
                         bg-[var(--surface)] px-4 py-3"
            >
              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                {editingId === p.video_id ? (
                  <div className="flex items-center gap-1">
                    <input
                      ref={inputRef}
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") { e.preventDefault(); commitEdit(p.video_id); }
                        if (e.key === "Escape") cancelEdit();
                      }}
                      className="min-w-0 flex-1 rounded border border-[var(--teal)] bg-transparent
                                 px-2 py-0.5 text-sm font-medium text-[var(--ink)]
                                 focus:outline-none focus:ring-1 focus:ring-[var(--teal)]"
                      aria-label="Edit project name"
                    />
                    <button
                      onClick={() => commitEdit(p.video_id)}
                      aria-label="Save name"
                      className="rounded p-1 text-[var(--teal)] hover:text-[var(--ink)] transition-colors"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={cancelEdit}
                      aria-label="Cancel rename"
                      className="rounded p-1 text-[var(--muted)] hover:text-[var(--ink)] transition-colors"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5">
                    <span className="font-display text-sm font-medium text-[var(--ink)] truncate">
                      {p.original_filename}
                    </span>
                    <button
                      onClick={() => startEdit(p)}
                      aria-label={`Rename ${p.original_filename}`}
                      className="shrink-0 rounded p-0.5 text-[var(--muted)] hover:text-[var(--teal)] transition-colors"
                    >
                      <Pencil size={12} />
                    </button>
                  </div>
                )}
                <div className="flex items-center gap-2 text-xs text-[var(--muted)] font-mono">
                  <span>{new Date(p.uploaded_at * 1000).toLocaleDateString()}</span>
                  <span>·</span>
                  <span>{(p.size_bytes / 1e6).toFixed(1)} MB</span>
                  <span>·</span>
                  <span>{p.clip_count} clips</span>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  onClick={() => handleOpen(p.video_id)}
                  className="rounded bg-[var(--teal)] px-3 py-1.5 text-xs text-white
                             hover:opacity-90 transition-opacity"
                >
                  View
                </button>
                <button
                  onClick={() => setConfirmDeleteId(p.video_id)}
                  aria-label={`Delete project ${p.original_filename}`}
                  className="rounded p-1.5 text-[var(--muted)] hover:text-[var(--danger)]
                             transition-colors focus-visible:outline-2 focus-visible:outline-[var(--teal)]"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {confirmDeleteId !== null && pendingProject && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
          onClick={() => setConfirmDeleteId(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-xl border border-[var(--line)] bg-[var(--surface)]
                       p-6 flex flex-col gap-4 shadow-xl mx-4"
          >
            <h3
              id="delete-dialog-title"
              className="font-display text-base font-semibold text-[var(--ink)] truncate"
            >
              {pendingProject.original_filename}
            </h3>
            <p className="text-sm text-[var(--muted)]">
              Removes the video, clips, and reel. This can't be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmDeleteId(null)}
                className="rounded border border-[var(--line)] px-4 py-2 text-sm
                           text-[var(--ink)] hover:border-[var(--ink)] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(pendingProject.video_id)}
                className="rounded bg-[var(--danger)] px-4 py-2 text-sm text-white
                           hover:opacity-90 transition-opacity"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
```

---

## 4. App.tsx — two fixes

File: `/Users/chinoyoung/Code/highlights/frontend/src/App.tsx`

**Fix 1: Stale exportJob across library transitions**

In the `Back` button handler (currently):
```tsx
onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); }}
```
Change to:
```tsx
onClick={() => { setVideoId(null); setLibraryView(false); setRallies([]); setExportJob(null); }}
```

In `handleOpenProject`:
```typescript
function handleOpenProject(videoId: string, duration: number) {
  setVideoId(videoId);
  setDuration(duration);
  setLibraryView(true);
}
```
Change to:
```typescript
function handleOpenProject(videoId: string, duration: number) {
  setVideoId(videoId);
  setDuration(duration);
  setRallies([]);
  setExportJob(null);
  setLibraryView(true);
}
```

**Fix 2: LibrarySection.handleOpen swallows errors**

This was already addressed in the LibrarySection.tsx changes above (try/catch + `openError` state). The `handleOpen` in `App.tsx` itself is just:
```typescript
function handleOpenProject(videoId: string, duration: number) { ... }
```
The error surfacing happens inside `LibrarySection` — no additional change needed in App.tsx beyond Fix 1.

---

## 5. Frontend api test — renameProject

File: `/Users/chinoyoung/Code/highlights/frontend/src/test/api.test.ts`

Add these two tests inside the existing `describe("api client", ...)` block, after the last existing test:

```typescript
it("renameProject sends PATCH /api/projects/{id}/name with body", async () => {
  globalThis.fetch = mockFetch(200, { video_id: "abc", original_filename: "My Final Cut" }) as any;
  const res = await api.renameProject("abc", "My Final Cut");
  expect(res.video_id).toBe("abc");
  expect(res.original_filename).toBe("My Final Cut");
  expect(globalThis.fetch).toHaveBeenCalledWith(
    "/api/projects/abc/name",
    expect.objectContaining({
      method: "PATCH",
      headers: expect.objectContaining({ "Content-Type": "application/json" }),
      body: JSON.stringify({ name: "My Final Cut" }),
    }),
  );
});

it("renameProject throws with server detail on non-OK", async () => {
  globalThis.fetch = mockFetch(400, { detail: "Name cannot be empty" }) as any;
  await expect(api.renameProject("abc", "")).rejects.toThrow("Name cannot be empty");
});
```

---

## Run frontend build + tests

```bash
cd /Users/chinoyoung/Code/highlights/frontend && npm run build && npm run test
```

Both must pass with 0 TS errors and all tests green.

## Report

Write your report to: `/Users/chinoyoung/Code/highlights/docs/superpowers/plans/briefs-fe/rename-task-2-report.md`

Include: files changed, build output, test output.

Return: STATUS (DONE/BLOCKED/NEEDS_CONTEXT), one-line test summary.
