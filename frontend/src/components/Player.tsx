import { forwardRef, useImperativeHandle, useRef } from "react";

export interface PlayerHandle {
  seekTo(t: number): void;
  play(): void;
  playSegment(start: number, end: number): void;
}

export const Player = forwardRef<PlayerHandle, { src: string }>(({ src }, ref) => {
  const v = useRef<HTMLVideoElement>(null);
  const segListenerRef = useRef<((e: Event) => void) | null>(null);
  useImperativeHandle(ref, () => ({
    seekTo(t) { if (v.current) v.current.currentTime = t; },
    play() { v.current?.play(); },
    playSegment(start, end) {
      if (!v.current) return;
      // Clear any previous segment listener to prevent overlapping plays
      if (segListenerRef.current) {
        v.current.removeEventListener("timeupdate", segListenerRef.current);
        segListenerRef.current = null;
      }
      v.current.currentTime = start;
      const listener = () => {
        if (v.current && v.current.currentTime >= end) {
          v.current.pause();
          v.current.removeEventListener("timeupdate", listener);
          segListenerRef.current = null;
        }
      };
      segListenerRef.current = listener;
      v.current.addEventListener("timeupdate", listener);
      v.current.play();
    },
  }));
  return (
    <video ref={v} src={src} controls
           className="w-full rounded-lg bg-black shadow-lg" />
  );
});
