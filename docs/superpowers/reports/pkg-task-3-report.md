# pkg-task-3 Report: Desktop launcher + `desktop` optional deps

## Status
COMPLETE — all checks green.

## Files Changed

| File | Action |
|------|--------|
| `tests/test_desktop.py` | Created (3 tests: `test_free_port_is_usable`, `test_wait_until_up_false_for_closed_port`, `test_wait_until_up_true_when_listening`) |
| `app/desktop.py` | Created (desktop entry point with `_free_port`, `_wait_until_up`, `main`) |
| `pyproject.toml` | Modified — added `desktop = ["pywebview>=5", "pyinstaller>=6"]` under `[project.optional-dependencies]` |

## TDD Sequence

1. Wrote `tests/test_desktop.py` first — confirmed FAIL: `ImportError: cannot import name 'desktop' from 'app'`
2. Created `app/desktop.py` with `import webview` inside `main()` (lazy)
3. Added `desktop` extra to `pyproject.toml`
4. Ran `tests/test_desktop.py` — 3 PASSED
5. Ran full suite — 111 PASSED (baseline was 108)

## Pytest Output (full suite)

```
111 passed, 3 warnings in 8.71s
```

Warnings are pre-existing FastAPI `on_event` deprecations, not introduced by this task.

## `app.desktop` Imports Without pywebview Installed

Confirmed:
```
$ .venv/bin/python -c "from app import desktop; print('imported OK')"
imported OK
```

pywebview is NOT installed in this venv. The lazy `import webview` inside `main()` means importing the module at the top level (as tests do) does not trigger the import. Tests only call `_free_port()` and `_wait_until_up()`, which need only the stdlib (`socket`, `time`).

## Self-Review

- `_free_port()` uses bind-then-close on `127.0.0.1:0` — OS assigns an ephemeral port, we capture it, close the socket, and return the number. Small TOCTOU window exists (another process could grab the port between close and uvicorn bind), but this is standard practice for this use case and unavoidable without SO_REUSEPORT trickery.
- `_wait_until_up()` polls with `socket.create_connection` at 100ms intervals up to `timeout`. Returns `True` on first successful connection, `False` on deadline. Tested with both a closed port (returns False) and a listening socket (returns True).
- `main()` keeps `import webview` deferred: module-level imports are only stdlib + uvicorn + `app.main`, all present in dev venv.
- `pyproject.toml` change is additive — existing `dev` group unchanged, no default dependencies altered.
- Dev workflow (`uvicorn app.main:app`, `./dev.sh`) is completely unaffected: `app/desktop.py` is never imported by `app/main.py`.

## Concerns

- **TOCTOU on `_free_port`:** Between `s.close()` and `uvicorn.Server.run()` binding the port, another process could claim it. Extremely unlikely in practice on a single-user dev machine / packaged app. No mitigation needed for this use case.
- **pywebview version:** `>=5` is specified but no upper bound. If pywebview 6+ introduces breaking API changes to `create_window`/`start`, the build may break. This is acceptable for now; pin tighter when the bundle is actually built.
- **No test for `main()`:** Per spec, `main()` is not tested (would open a window). The PyInstaller smoke test (Task 5) covers end-to-end behavior.
