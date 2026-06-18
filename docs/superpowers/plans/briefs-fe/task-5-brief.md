# Task 5 (modern-frontend)

## Global Constraints

- **Backend Python floor:** 3.10+ (interpreter is 3.10.8). Activate `.venv` before any pytest.
- **No new backend dependencies** — background work uses stdlib `threading`.
- **Backward-compatible analyzer/exporter signatures:** new `progress_callback` params MUST default to `None` so existing callers/tests keep working.
- **Existing backend suite (24 tests) must stay green** except the two `/api/detect` & `/api/export` tests in `tests/test_api.py`, which are intentionally updated in Task 4 to the new job flow.
- **Git is disabled** (not a git repo; user policy forbids state-changing git). Wherever a step says "Commit", instead run the task's tests (and build, where relevant) and confirm green. Never run a state-changing git command.
- **Node 22 / npm 10** are installed. Frontend commands run from `frontend/`.
- **Sensitivity semantics:** higher slider = more sensitive = more rallies; the client sends `threshold = 1 - sliderValue`.
- **Job record shape (canonical, used across backend + frontend):** `{ "status": "running"|"done"|"error", "progress": float 0.0–1.0, "result": object|null, "error": string|null }`.
- **Detect job result shape:** `{ "rallies": [{start, end, confidence}] }`. **Export job result shape:** `{ "clips": [string], "stitched": string|null }`.
- **If a pinned npm version fails to resolve,** install the latest compatible version and note it in the task report.



---

## Task 5: Frontend scaffold (Vite + React + TS + Tailwind)

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/App.tsx` (placeholder), `frontend/src/test/setup.ts`

**Interfaces:**
- Produces a runnable Vite project: `npm run dev` (port 5173, proxies `/api` → 8000), `npm run build` (→ `dist/`), `npm run test` (Vitest). Tailwind 4 active with class-based dark mode.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "highlights-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "lucide-react": "^0.460.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "jsdom": "^25.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.5.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Create config files**

`frontend/vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`frontend/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "noEmit": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pickleball Highlights</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `frontend/src/index.css`** (Tailwind 4 + class-based dark variant)

```css
@import "tailwindcss";

@custom-variant dark (&:where(.dark, .dark *));

:root { color-scheme: light dark; }
body { margin: 0; }
```

- [ ] **Step 5: Create `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 6: Create placeholder `frontend/src/App.tsx`**

```tsx
export default function App() {
  return <div className="p-8 text-2xl font-bold">Pickleball Highlights</div>;
}
```

- [ ] **Step 7: Create `frontend/src/test/setup.ts`**

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 8: Install and verify build + dev**

Run (from `frontend/`):
```bash
cd frontend && npm install
npm run build
```
Expected: install succeeds; `npm run build` produces `frontend/dist/index.html` and assets with no TypeScript errors. (If a pinned version fails to resolve, install the latest compatible and note it in the report.)

Then verify dev serving + proxy (backend must be running):
```bash
# in repo root, separate shell: source .venv/bin/activate && uvicorn app.main:app
cd frontend && (npm run dev &) && sleep 4
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/   # expect 200
# stop the dev server afterwards (kill the vite process)
```

- [ ] **Step 9: Checkpoint** — `cd frontend && npm run build` succeeds and `npm run test` runs (0 tests so far is fine: it should exit 0 or report "no test files"; if Vitest errors on no tests, that's acceptable until Task 6 adds tests).

---

