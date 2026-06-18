# Highlights — Frontend

Vite + React + TypeScript + Tailwind UI for the Pickleball Highlights app.

## Development

Install dependencies (first time only):
```bash
npm install
```

Start the Vite dev server (hot reload):
```bash
npm run dev
```
Open http://localhost:5173 — Vite proxies `/api/*` to the FastAPI backend on :8000.

Or run both servers at once from the repo root:

    ./dev.sh

## Build

```bash
npm run build
```
Output lands in `dist/`, which the FastAPI server serves automatically.

## Tests

```bash
npm run test
```
