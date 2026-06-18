# Task 8: (brief)

## Global Constraints

- **Python version floor:** 3.10+ (3.10.8 is the available interpreter; code is 3.10-compatible).
- **System dependency:** `ffmpeg` and `ffprobe` must be on `PATH`.
- **No heavy audio libs:** audio energy is computed from an ffmpeg-extracted WAV using NumPy only — do NOT add `librosa` or similar.
- **No build step for frontend:** plain `index.html` + JS served as static files.
- **Git is disabled for this project** (user global instruction + not a git repo). Wherever a task would normally `git commit`, instead run the task's full test suite and confirm green as the checkpoint. Do not run any state-changing git command.
- **Frame-accurate cuts:** export must re-encode cut ranges, not stream-copy (stream-copy only cuts on keyframes).
- **Detection defaults:** `sample_fps=8`, `merge_gap_seconds=2.0`, `min_rally_seconds=2.5`, `pad_seconds=1.0`, `threshold=0.5` (normalized 0–1).



---

## Task 8: Review UI (frontend)

**Files:**
- Create: `app/web/index.html`, `app/web/app.js`, `app/web/style.css`

**Interfaces:**
- Consumes the REST API from Task 7. No backend changes.
- Produces: a single-page UI: upload form → video player → timeline of rally blocks → include/exclude toggles + drag-to-trim → sensitivity slider (calls `/api/resegment`) → Export button (calls `/api/export`) → shows output paths.

This task is UI; it is verified manually (Step 5) rather than by unit tests.

- [ ] **Step 1: Create `app/web/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Pickleball Highlights</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>
  <h1>Pickleball Highlights</h1>

  <section id="upload-section">
    <input type="file" id="file" accept="video/*" />
    <button id="upload-btn">Upload &amp; Detect</button>
    <span id="status"></span>
  </section>

  <section id="review-section" hidden>
    <video id="player" controls width="640"></video>

    <div class="controls">
      <label>Sensitivity
        <input type="range" id="sensitivity" min="0" max="1" step="0.05" value="0.5" />
      </label>
      <button id="export-btn">Export</button>
    </div>

    <div id="timeline"></div>
    <ul id="rally-list"></ul>
    <pre id="result"></pre>
  </section>

  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `app/web/style.css`**

```css
body { font-family: system-ui, sans-serif; margin: 2rem; }
.controls { margin: 1rem 0; display: flex; gap: 1rem; align-items: center; }
#timeline {
  position: relative; height: 40px; background: #eee;
  border-radius: 4px; margin: 1rem 0;
}
.rally-block {
  position: absolute; top: 0; height: 100%;
  background: #4caf50; opacity: 0.8; border-radius: 4px; cursor: pointer;
}
.rally-block.excluded { background: #bbb; opacity: 0.5; }
#rally-list { list-style: none; padding: 0; }
#rally-list li { padding: 0.25rem 0; }
```

- [ ] **Step 3: Create `app/web/app.js`**

```javascript
let videoId = null;
let duration = 0;
let rallies = [];

const $ = (id) => document.getElementById(id);

async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}

$("upload-btn").onclick = async () => {
  const file = $("file").files[0];
  if (!file) return;
  $("status").textContent = "Uploading…";
  const fd = new FormData();
  fd.append("file", file);
  const up = await (await fetch("/api/upload", { method: "POST", body: fd })).json();
  videoId = up.video_id;
  duration = up.duration;
  $("player").src = `/api/video/${videoId}`;
  $("status").textContent = "Detecting rallies…";
  const det = await postJSON("/api/detect", {
    video_id: videoId,
    params: { threshold: parseFloat($("sensitivity").value) },
  });
  rallies = det.rallies.map((r) => ({ ...r, included: true }));
  $("review-section").hidden = false;
  $("status").textContent = `${rallies.length} rallies found`;
  render();
};

$("sensitivity").oninput = debounce(async () => {
  if (!videoId) return;
  const det = await postJSON("/api/resegment", {
    video_id: videoId,
    params: { threshold: parseFloat($("sensitivity").value) },
  });
  rallies = det.rallies.map((r) => ({ ...r, included: true }));
  render();
}, 250);

$("export-btn").onclick = async () => {
  const ranges = rallies.filter((r) => r.included)
    .map((r) => ({ start: r.start, end: r.end }));
  $("result").textContent = "Exporting…";
  const res = await postJSON("/api/export", { video_id: videoId, ranges });
  $("result").textContent =
    `Stitched: ${res.stitched}\nClips:\n${res.clips.join("\n")}`;
};

function render() {
  const tl = $("timeline");
  tl.innerHTML = "";
  rallies.forEach((r, i) => {
    const block = document.createElement("div");
    block.className = "rally-block" + (r.included ? "" : " excluded");
    block.style.left = (100 * r.start / duration) + "%";
    block.style.width = (100 * (r.end - r.start) / duration) + "%";
    block.title = `Rally ${i + 1}`;
    block.onclick = () => { $("player").currentTime = r.start; $("player").play(); };
    tl.appendChild(block);
  });

  const list = $("rally-list");
  list.innerHTML = "";
  rallies.forEach((r, i) => {
    const li = document.createElement("li");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = r.included;
    cb.onchange = () => { r.included = cb.checked; render(); };
    li.appendChild(cb);
    li.appendChild(document.createTextNode(
      ` Rally ${i + 1}: ${r.start.toFixed(1)}s – ${r.end.toFixed(1)}s ` +
      `(conf ${(r.confidence ?? 0).toFixed(2)})`));
    list.appendChild(li);
  });
}

function debounce(fn, ms) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
```

- [ ] **Step 4: Start the server**

Run: `uvicorn app.main:app --reload`
Expected: starts without error; if ffmpeg missing, fails fast with the Task 1 message.

- [ ] **Step 5: Manual verification**

Open `http://localhost:8000`. Upload a real fixed-camera pickleball clip. Confirm: rallies appear as green blocks; clicking a block seeks/plays; the sensitivity slider changes the block set; unchecking excludes a rally; Export writes `highlights.mp4` + `clip_*.mp4` under `workdir/<id>/output/` and the paths show in the result box. Note any issues for follow-up.

- [ ] **Step 6: Checkpoint** — Run `pytest -v` (ensure nothing regressed). Confirm green.

---

