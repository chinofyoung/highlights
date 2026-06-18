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
