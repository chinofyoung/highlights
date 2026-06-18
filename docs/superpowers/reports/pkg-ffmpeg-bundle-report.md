# ffmpeg Bundle Report
Date: 2026-06-18

## SHA-256 Confirmation

| Binary  | Expected SHA-256 | Verified in packaging/bin/ |
|---------|-----------------|---------------------------|
| ffmpeg  | `6d175a4743ca50256e89a8cdd731100f9cee33bd79aeea46894d209410dc6617` | YES |
| ffprobe | `df2684842eca145bd72f4724ce9cecbf38558a4d64b2aef7846680f877702baa` | YES |

Both binaries are `Mach-O 64-bit executable arm64`, confirmed by `file -b`.

## fetch_ffmpeg.sh Run Output

```
OK: ffmpeg (Mach-O 64-bit executable arm64), sha256 verified
OK: ffprobe (Mach-O 64-bit executable arm64), sha256 verified
ffmpeg + ffprobe ready in /Users/chinoyoung/Code/highlights/packaging/bin
exit=0
```

## pytest Result

```
111 passed, 3 warnings in 8.93s
exit=0
```

No Python files changed; test suite remains fully green.

## Concerns

1. **URL mutability**: The osxexperts.net URLs (`ffmpeg71arm.zip`, `ffprobe71arm.zip`) are not content-addressed. If the upstream author rebuilds and re-uploads the zip, the SHA-256 check will intentionally fail — this is correct defensive behaviour but requires a manual pin update when the upstream binary changes.

2. **`fetch()` skips re-verification of existing binaries**: The `fetch()` function short-circuits with `return 0` if `$BIN/$tool` is already executable, but `verify()` is always called afterwards regardless, so the SHA-256 and arch check always runs. No gap here.

3. **No x86_64 fallback**: The script is arm64-only. If someone runs it on an Intel Mac, the fetch will succeed (same zip), the sha256 check will pass (same binary), but the arch check in `verify()` will fail with `ERROR: ... is not arm64`. This is correct — an arm64 binary cannot be bundled into an x86_64 build — but CI on Intel runners would need a separate pin set.

4. **No notarization/signing step here**: The binaries are bundled as-is. The `.app` packaging pipeline (`build_mac.sh` / `Highlights.spec`) is responsible for signing and notarizing; this script only gates on SHA-256 and arch.
