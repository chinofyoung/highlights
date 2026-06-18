import { describe, it, expect } from "vitest";
import { pxToTime, clampStart, clampEnd, moveBody, MIN_GAP } from "../timeline-math";

describe("timeline math", () => {
  it("pxToTime maps proportionally", () => {
    expect(pxToTime(50, 100, 10)).toBe(5);
    expect(pxToTime(0, 100, 10)).toBe(0);
  });

  it("clampStart respects prevEnd floor", () => {
    expect(clampStart(1, { start: 5, end: 8 }, 3, MIN_GAP)).toBe(3);
  });

  it("clampStart respects min gap ceiling", () => {
    expect(clampStart(7.9, { start: 5, end: 8 }, 0, MIN_GAP)).toBe(8 - MIN_GAP);
  });

  it("clampEnd respects nextStart ceiling", () => {
    expect(clampEnd(12, { start: 5, end: 8 }, 10, MIN_GAP)).toBe(10);
  });

  it("clampEnd respects min gap floor", () => {
    expect(clampEnd(5.1, { start: 5, end: 8 }, 99, MIN_GAP)).toBe(5 + MIN_GAP);
  });

  it("moveBody preserves length and clamps to prevEnd", () => {
    const r = moveBody(-10, { start: 5, end: 8 }, 2, 99);
    expect(r.end - r.start).toBeCloseTo(3);
    expect(r.start).toBe(2);
  });

  it("moveBody clamps to nextStart", () => {
    const r = moveBody(10, { start: 5, end: 8 }, 0, 12);
    expect(r.end).toBe(12);
    expect(r.end - r.start).toBeCloseTo(3);
  });
});
