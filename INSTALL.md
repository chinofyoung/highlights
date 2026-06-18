# Installing Cherry.Pickle (macOS, Apple Silicon)

1. Unzip `CherryPickle-mac-arm64.zip`.
2. Drag **CherryPickle.app** into your **Applications** folder.
3. First launch only: **right-click** the app → **Open** → **Open**.
   (It's unsigned, so a normal double-click shows an "unidentified developer"
   warning the first time. Right-click → Open bypasses it once.)
   Alternatively, in Terminal:
   `xattr -dr com.apple.quarantine /Applications/CherryPickle.app`
4. The app opens in its own window. Your videos and exported clips are saved in
   **~/Documents/Highlights**.

Requires an Apple Silicon (M-series) Mac.
