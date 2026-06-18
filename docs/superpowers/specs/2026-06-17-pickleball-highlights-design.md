# Pickleball Highlight Extractor — Design

**Date:** 2026-06-17
**Status:** Approved design, pending implementation plan

## Summary

A local web app that takes a fixed-camera pickleball match video, automatically
detects rallies (removing dead time between points), lets the user review and
trim the detected rallies in a browser UI, then exports both individual clips
(one per rally) and a single stitched highlight video.

Runs entirely on the user's machine. No hosting, no cloud, no accounts.

## Goals (v1)

- Extract **all rallies**, removing dead time (walking, ball retrieval, chatting).
- Work on **fixed-camera, full-court** footage.
- Provide a **review-then-export** workflow: detection is a starting point the
  user corrects, not the final word.
- Produce **both** individual per-rally clips and one stitched highlight video.

## Non-goals (deferred)

- Ranking/scoring rallies by "excitement" (planned as a later feature).
- Handheld / moving-camera footage.
- Multi-user / hosted deployment (designed so it *could* grow there, not built for it).
- Ball tracking via custom-trained YOLO (explicitly avoided for v1 — see Rationale).

## Rationale: why audio + motion, not ball tracking

A pickleball is small, fast, and motion-blurs to near-invisibility. Stock object
detectors do not reliably detect it; a custom-trained model would require
collecting and labeling footage — a project unto itself. For a **fixed camera**,
two cheap signals are strong and require no ML training:

- **Motion energy** — players move during rallies, the court is still between points.
- **Audio energy** — paddle "pops" and rally noise punctuate active play.

This is simpler and often more reliable than ball tracking. Ball detection can be
added later as an enhancement if needed.

## Architecture

Two halves communicating over `localhost`:

```
Browser (review UI)  ◄── HTTP ──►  Python backend (FastAPI)
                                        │
                            ┌───────────┼───────────┐
                         analyzer    exporter    workdir/
                      (motion+audio) (ffmpeg)   (files, cache)
```

The user runs one command, opens `localhost:8000`, uploads a video, reviews
detected rallies, and exports.

### Tech stack

- **Backend:** Python 3.11+, FastAPI, uvicorn.
- **Processing:** system `ffmpeg`/`ffprobe`; OpenCV (`opencv-python`) for motion;
  NumPy for signal math. Audio RMS computed from an ffmpeg-extracted WAV with
  NumPy (avoids a heavy `librosa` dependency).
- **Frontend:** static `index.html` + vanilla JS (no build step).
- **System prerequisite:** `ffmpeg` and `ffprobe` installed and on `PATH`.

## Detection pipeline

For each uploaded video:

1. **Extract** — use ffmpeg to produce (a) a downsampled frame stream at ~5–10 fps
   for motion analysis and (b) a mono WAV of the audio track.
2. **Motion energy** — for consecutive sampled frames, compute a frame-difference
   magnitude (e.g. mean absolute difference of grayscale frames, optionally over
   the court region). Produces a per-timestamp motion time series.
3. **Audio energy** — compute a short-window RMS / transient envelope over the
   WAV. Produces a per-timestamp audio time series.
4. **Segment** — normalize and combine the two signals, smooth, and threshold to
   find contiguous "active" spans.
5. **Merge & filter** — merge spans separated by gaps shorter than
   `merge_gap_seconds` (mid-rally lulls); drop spans shorter than
   `min_rally_seconds` (noise/false positives).
6. **Pad** — extend each span by `pad_seconds` before and after so serves and
   final shots are not clipped.
7. **Output** — a list of rallies `{ start, end, confidence }`.

### Caching

The raw motion and audio time series are cached to the video's workdir after
step 3. Steps 4–6 (segmentation) are cheap and run against the cached signals, so
the UI sensitivity slider re-segments **instantly** without reprocessing video.

### Tunable parameters (with sensible defaults)

- `sample_fps` — frame sampling rate for motion (default ~8).
- `threshold` — activity threshold (exposed to the UI as the sensitivity slider).
- `merge_gap_seconds` — max gap to bridge within one rally (default ~2s).
- `min_rally_seconds` — minimum length to count as a rally (default ~2–3s).
- `pad_seconds` — padding added to each clip start/end (default ~1s).

## Review UI

- HTML5 `<video>` player loading the uploaded file from the backend.
- A **timeline** below the player with one colored block per detected rally.
- Per rally: **include/exclude** toggle, **drag handles** to adjust start/end,
  click-to-preview (seek + play that span).
- A global **sensitivity slider** that calls the backend to re-segment cached
  signals and redraws blocks instantly.
- An **Export** button that sends the approved/edited rally list to the backend.

## Export

On export, the backend receives the final list of approved `[start, end]` ranges:

- ffmpeg cuts each range into an **individual clip**, re-encoded for
  frame-accurate cuts (not stream-copy, which only cuts on keyframes).
- The clips are concatenated into **one stitched highlight video**.
- Both individual clips and the stitched video are written to the video's output
  folder; the UI reports the output paths.

## Module boundaries

Kept small and single-purpose so each is independently understandable and testable.

- `analyzer/`
  - `motion.py` — extract motion energy time series from frames.
  - `audio.py` — extract audio energy time series from WAV.
  - `segment.py` — pure functions: combine/threshold/merge/filter/pad signals →
    rally list. No I/O; testable with synthetic arrays.
- `exporter/`
  - `ffmpeg.py` — cut a range to a clip; concat clips to a stitched video.
- `api/`
  - FastAPI routes: `upload`, `detect`, `resegment` (slider), `export`. Tracks
    per-video job state.
- `web/`
  - `index.html` + timeline/player JS. No build step.
- `workdir/`
  - Per-video folder holding the original upload, extracted WAV, cached signal
    arrays, and the output clips/stitched video.

## Data flow

```
upload video
  → save to workdir
  → analyzer: extract frames + audio, compute signals, cache them
  → segment → return rally JSON
  → user edits in UI (toggle / trim / slider → resegment)
  → POST approved ranges
  → exporter: cut clips + concat stitched
  → return output paths
```

## Error handling

- On startup, verify `ffmpeg`/`ffprobe` are available; fail with a clear message if not.
- Validate uploads are decodable video (probe with ffprobe); reject otherwise.
- Handle "no rallies found" gracefully (empty timeline + message, suggest lowering
  threshold).
- Provide progress feedback for long videos during the extract/analyze step.

## Testing

- **analyzer/segment.py** — unit tests with synthetic motion/audio arrays
  covering: basic spans, gap merging, short-span filtering, padding, empty input.
- **analyzer/motion.py & audio.py** — tested against one short bundled sample clip
  (assert signal shape/length and that an active region scores higher than a still one).
- **exporter/ffmpeg.py** — cut a known clip and assert output duration and that
  the stitched file's duration ≈ sum of clip durations.
- **api** — smoke test the upload → detect → export flow against the sample clip.

## Future enhancements (out of scope for v1)

- Rally ranking / "best rallies only" scoring.
- Optional ball detection to refine boundaries.
- Handheld-footage support (camera-motion compensation, audio-weighted detection).
- Packaging for non-technical users / optional hosting.
