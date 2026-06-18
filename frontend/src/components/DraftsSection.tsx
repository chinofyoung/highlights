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
