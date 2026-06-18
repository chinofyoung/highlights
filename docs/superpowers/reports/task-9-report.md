# Task 9 Report: Eval Harness (Metrics + CLI)

## Files Changed

Created:
- `app/eval/__init__.py` — empty package init
- `app/eval/metrics.py` — `iou(a, b)` and `score(detected, labels, cutoff=0.5)`
- `scripts/eval.py` — CLI runner
- `eval/labels/.gitkeep` — placeholder for label files directory
- `tests/test_eval.py` — 3 TDD tests

## TDD Steps Followed

### Step 1 — Failing test written
`tests/test_eval.py` created with `test_iou_basic`, `test_score_perfect`, `test_score_with_fp_and_fn`.

### Step 2 — Confirmed fail
```
pytest tests/test_eval.py -v
ERROR: ModuleNotFoundError: No module named 'app.eval'
```

### Step 3 — Implementation written
`app/eval/__init__.py` (empty), `app/eval/metrics.py` with `iou` and `score`.

### Step 4 — Confirmed pass
```
pytest tests/test_eval.py -v
tests/test_eval.py::test_iou_basic PASSED
tests/test_eval.py::test_score_perfect PASSED
tests/test_eval.py::test_score_with_fp_and_fn PASSED
3 passed in 0.01s
```

### Step 5 — CLI and labels dir created
`scripts/eval.py` and `eval/labels/.gitkeep` created.

### Step 6 — CLI smoke test
```
.venv/bin/python scripts/eval.py --labels eval/labels
No label files in eval/labels
Exit code: 1
```
Prints correct message and exits non-zero as specified.

### Step 7 — Full suite checkpoint
```
.venv/bin/python -m pytest -q
93 passed, 3 warnings in 8.24s
```
All 93 tests pass (90 pre-existing + 3 new).

## Self-Review

- `iou`: correctly computes intersection / union; returns 0.0 for non-overlapping intervals and when union is zero.
- `score`: greedy matching (best IoU per detected segment, no double-matching labels via `matched` set). Returns all required keys: `tp, fp, fn, precision, recall, f1, mean_iou`.
- `mean_iou` is the average IoU over matched (TP) pairs; 0.0 when no matches.
- CLI `sys.path.insert` allows running from repo root without package install.
- `_find_video` guards against non-video extensions.
- No new Python dependencies introduced (pure stdlib + existing app modules).

## Concerns

None. Implementation is straightforward and matches spec verbatim. The `score` function uses a greedy matching strategy which is standard for segmentation evaluation; a more exhaustive Hungarian-algorithm match would only differ on edge cases not covered by the spec tests.
