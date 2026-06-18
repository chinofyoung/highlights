import type { JobRecord, Rally, DetectParams, Draft, Project } from "./types";

export function toRally(r: any): Rally {
  return {
    start: r.start,
    end: r.end,
    confidence: r.confidence,
    serveStart: r.serve_start ?? r.serveStart ?? r.start,
    serveEnd: r.serve_end ?? r.serveEnd ?? r.end,
    serveResolved: r.serve_resolved ?? r.serveResolved ?? false,
    included: true,
  };
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function uploadVideo(file: File): Promise<{ video_id: string; duration: number }> {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export function startDetect(videoId: string, params: DetectParams) {
  return postJSON<{ job_id: string }>("/api/detect", { video_id: videoId, params });
}

export function startExport(videoId: string, ranges: { start: number; end: number }[]) {
  return postJSON<{ job_id: string }>("/api/export", { video_id: videoId, ranges });
}

export async function getJob(jobId: string): Promise<JobRecord> {
  const r = await fetch(`/api/jobs/${jobId}`);
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  await postJSON<unknown>(`/api/jobs/${jobId}/cancel`, {});
}

export async function resegment(videoId: string, params: DetectParams): Promise<{ rallies: Rally[] }> {
  const data = await postJSON<{ rallies: any[] }>("/api/resegment", { video_id: videoId, params });
  return { rallies: data.rallies.map(toRally) };
}

export function videoUrl(videoId: string): string {
  return `/api/video/${videoId}`;
}

export async function listOutput(videoId: string): Promise<{ clips: string[]; stitched: string | null }> {
  const r = await fetch(`/api/output/${videoId}`);
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export function outputUrl(videoId: string, filename: string): string {
  return `/api/output/${videoId}/${filename}`;
}

export async function deleteClip(videoId: string, filename: string): Promise<{ clips: string[]; stitched: string | null }> {
  const r = await fetch(`/api/output/${videoId}/${filename}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function clearOutput(videoId: string): Promise<{ clips: string[]; stitched: string | null }> {
  const r = await fetch(`/api/output/${videoId}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function listDrafts(): Promise<Draft[]> {
  const r = await fetch("/api/drafts");
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function deleteDraft(videoId: string): Promise<Draft[]> {
  const r = await fetch(`/api/drafts/${videoId}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function listLibrary(): Promise<Project[]> {
  const r = await fetch("/api/library");
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function openProject(videoId: string): Promise<{ video_id: string; duration: number }> {
  const r = await fetch(`/api/library/${videoId}/open`, { method: "POST" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

export async function deleteProject(videoId: string): Promise<Project[]> {
  const r = await fetch(`/api/library/${videoId}`, { method: "DELETE" });
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new Error(detail || r.statusText);
  }
  return r.json();
}

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
