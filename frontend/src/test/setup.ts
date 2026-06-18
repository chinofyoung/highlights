import "@testing-library/jest-dom";

// @testing-library/dom's waitFor detects fake timers by checking `typeof jest`.
// Vitest does not expose `jest` globally, so we alias it to `vi` so that
// waitFor uses the fake-timer code path instead of real setInterval.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).jest = (globalThis as any).vi;

// ThemeToggle calls window.matchMedia; provide a stub for jsdom
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
