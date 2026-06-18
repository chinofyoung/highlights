export const MIN_GAP = 0.2;

export function pxToTime(px: number, trackWidthPx: number, duration: number): number {
  if (trackWidthPx <= 0) return 0;
  return (px / trackWidthPx) * duration;
}

export function clampStart(
  newStart: number,
  rally: { start: number; end: number },
  prevEnd: number,
  minGap: number,
): number {
  return Math.min(Math.max(newStart, prevEnd), rally.end - minGap);
}

export function clampEnd(
  newEnd: number,
  rally: { start: number; end: number },
  nextStart: number,
  minGap: number,
): number {
  return Math.max(Math.min(newEnd, nextStart), rally.start + minGap);
}

export function moveBody(
  deltaT: number,
  rally: { start: number; end: number },
  prevEnd: number,
  nextStart: number,
): { start: number; end: number } {
  const len = rally.end - rally.start;
  let start = rally.start + deltaT;
  start = Math.max(prevEnd, Math.min(start, nextStart - len));
  return { start, end: start + len };
}
