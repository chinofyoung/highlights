import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useJob } from "../useJob";
import * as api from "../api";

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe("useJob", () => {
  it("polls until done and exposes result", async () => {
    let callCount = 0;
    vi.spyOn(api, "getJob").mockImplementation(async () => {
      callCount += 1;
      if (callCount === 1) {
        return { status: "running", progress: 0.5, result: null, error: null } as any;
      }
      return { status: "done", progress: 1, result: { rallies: [] }, error: null } as any;
    });

    const { result } = renderHook(() => useJob("j1"));

    // Flush the immediate tick (microtask queue + state update)
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    await waitFor(() => expect(result.current.status).toBe("running"));

    // Advance 500ms to fire the interval tick (2nd call → done)
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.result).toEqual({ rallies: [] });
  });

  it("does nothing when jobId is null", async () => {
    const spy = vi.spyOn(api, "getJob");
    renderHook(() => useJob(null));
    await vi.advanceTimersByTimeAsync(1000);
    expect(spy).not.toHaveBeenCalled();
  });
});
