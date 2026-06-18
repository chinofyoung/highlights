import { describe, it, expect, vi, beforeEach } from "vitest";
import * as api from "../api";

beforeEach(() => { vi.restoreAllMocks(); });

function mockFetch(status: number, body: any) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

describe("api client", () => {
  it("startDetect posts and returns job_id", async () => {
    globalThis.fetch = mockFetch(200, { job_id: "abc" }) as any;
    const res = await api.startDetect("v1", { threshold: 0.3 });
    expect(res.job_id).toBe("abc");
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/detect",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws with server detail on non-OK", async () => {
    globalThis.fetch = mockFetch(400, { detail: "bad video" }) as any;
    await expect(api.uploadVideo(new File([""], "x.txt"))).rejects.toThrow("bad video");
  });

  it("getJob returns the record", async () => {
    globalThis.fetch = mockFetch(200, { status: "done", progress: 1, result: { rallies: [] }, error: null }) as any;
    const rec = await api.getJob("j1");
    expect(rec.status).toBe("done");
  });

  it("videoUrl builds the right path", () => {
    expect(api.videoUrl("v9")).toBe("/api/video/v9");
  });

  it("listOutput hits GET /api/output/{id}", async () => {
    globalThis.fetch = mockFetch(200, { clips: ["clip_001.mp4"], stitched: "highlights.mp4" }) as any;
    const res = await api.listOutput("v1");
    expect(res.clips).toEqual(["clip_001.mp4"]);
    expect(res.stitched).toBe("highlights.mp4");
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/output/v1");
  });

  it("outputUrl builds the right path", () => {
    expect(api.outputUrl("v9", "clip_001.mp4")).toBe("/api/output/v9/clip_001.mp4");
  });

  it("deleteClip sends DELETE and returns updated listing", async () => {
    globalThis.fetch = mockFetch(200, { clips: ["clip_002.mp4"], stitched: "highlights.mp4" }) as any;
    const res = await api.deleteClip("v1", "clip_001.mp4");
    expect(res.clips).toEqual(["clip_002.mp4"]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/output/v1/clip_001.mp4",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("clearOutput sends DELETE to /api/output/{id}", async () => {
    globalThis.fetch = mockFetch(200, { clips: [], stitched: null }) as any;
    const res = await api.clearOutput("v1");
    expect(res.clips).toEqual([]);
    expect(res.stitched).toBeNull();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/output/v1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("listDrafts hits GET /api/drafts", async () => {
    const mockDrafts = [
      { video_id: "abc", original_filename: "match.mp4", uploaded_at: 123.0, analyzed: true, size_bytes: 1000 },
    ];
    globalThis.fetch = mockFetch(200, mockDrafts) as any;
    const res = await api.listDrafts();
    expect(res).toEqual(mockDrafts);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/drafts");
  });

  it("deleteDraft sends DELETE and returns updated list", async () => {
    globalThis.fetch = mockFetch(200, []) as any;
    const res = await api.deleteDraft("abc");
    expect(res).toEqual([]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/drafts/abc",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("listLibrary hits GET /api/library", async () => {
    const mockProjects = [
      { video_id: "abc", original_filename: "game.mp4", uploaded_at: 200.0, size_bytes: 5000000, clip_count: 2 },
    ];
    globalThis.fetch = mockFetch(200, mockProjects) as any;
    const res = await api.listLibrary();
    expect(res).toEqual(mockProjects);
    expect(globalThis.fetch).toHaveBeenCalledWith("/api/library");
  });

  it("openProject sends POST /api/library/{id}/open", async () => {
    globalThis.fetch = mockFetch(200, { video_id: "abc", duration: 120.5 }) as any;
    const res = await api.openProject("abc");
    expect(res.video_id).toBe("abc");
    expect(res.duration).toBe(120.5);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/library/abc/open",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("deleteProject sends DELETE /api/library/{id} and returns updated list", async () => {
    globalThis.fetch = mockFetch(200, []) as any;
    const res = await api.deleteProject("abc");
    expect(res).toEqual([]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/library/abc",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

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
});
