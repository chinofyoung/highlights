import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import * as api from "../api";

// Mock the entire api module so no real fetch happens
vi.mock("../api", () => ({
  uploadVideo: vi.fn(),
  startDetect: vi.fn(),
  startExport: vi.fn(),
  getJob: vi.fn(),
  resegment: vi.fn(),
  videoUrl: vi.fn((id: string) => `/api/video/${id}`),
  listDrafts: vi.fn().mockResolvedValue([]),
  deleteDraft: vi.fn().mockResolvedValue([]),
  listLibrary: vi.fn().mockResolvedValue([]),
  deleteProject: vi.fn().mockResolvedValue([]),
  openProject: vi.fn(),
}));

globalThis.URL.createObjectURL = vi.fn(() => "blob:mock");
globalThis.URL.revokeObjectURL = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.listDrafts).mockResolvedValue([]);
  vi.mocked(api.deleteDraft).mockResolvedValue([]);
  vi.mocked(api.listLibrary).mockResolvedValue([]);
});

describe("App — no-auto-analyze contract", () => {
  it("shows UploadView initially", async () => {
    render(<App />);
    await act(async () => {});
    expect(screen.getByText(/find the rallies/i)).toBeInTheDocument();
  });

  it("selecting a file shows SelectedVideo and does NOT call startDetect", async () => {
    render(<App />);
    await act(async () => {});

    const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
    const file = new File(["video"], "match.mp4", { type: "video/mp4" });

    await userEvent.upload(input, file);

    // SelectedVideo should now be visible
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /analyze video/i })).toBeInTheDocument()
    );

    // startDetect must NOT have been called yet
    expect(api.startDetect).not.toHaveBeenCalled();
    expect(api.uploadVideo).not.toHaveBeenCalled();
  });

  it("clicking Analyze video calls uploadVideo then startDetect", async () => {
    vi.mocked(api.uploadVideo).mockResolvedValue({ video_id: "v1", duration: 120 });
    vi.mocked(api.startDetect).mockResolvedValue({ job_id: "j1" });
    vi.mocked(api.getJob).mockResolvedValue({
      status: "running",
      progress: 0,
      result: null,
      error: null,
    });

    render(<App />);
    await act(async () => {});

    const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
    const file = new File(["video"], "match.mp4", { type: "video/mp4" });
    await userEvent.upload(input, file);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /analyze video/i })).toBeInTheDocument()
    );

    await userEvent.click(screen.getByRole("button", { name: /analyze video/i }));

    await waitFor(() => expect(api.uploadVideo).toHaveBeenCalledWith(file));
    await waitFor(() => expect(api.startDetect).toHaveBeenCalledWith("v1", { threshold: 0.5 }));
  });

  it("Reset button returns to UploadView", async () => {
    render(<App />);
    await act(async () => {});

    const input = document.querySelector<HTMLInputElement>("input[type=file]")!;
    const file = new File(["video"], "match.mp4", { type: "video/mp4" });
    await userEvent.upload(input, file);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /choose a different video/i })).toBeInTheDocument()
    );

    await userEvent.click(screen.getByRole("button", { name: /choose a different video/i }));

    await waitFor(() =>
      expect(screen.getByText(/find the rallies/i)).toBeInTheDocument()
    );
  });
});
