# PyInstaller spec — build from repo root: `.venv/bin/pyinstaller packaging/CherryPickle.spec`
import os

ROOT = os.path.abspath(os.getcwd())

a = Analysis(
    [os.path.join(ROOT, 'app', 'desktop.py')],
    pathex=[ROOT],
    binaries=[
        (os.path.join(ROOT, 'packaging', 'bin', 'ffmpeg'), 'bin'),
        (os.path.join(ROOT, 'packaging', 'bin', 'ffprobe'), 'bin'),
    ],
    datas=[
        (os.path.join(ROOT, 'frontend', 'dist'), 'frontend/dist'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='CherryPickle', console=False, target_arch='arm64',
)
coll = COLLECT(exe, a.binaries, a.datas, name='CherryPickle')

VERSION = os.environ.get('VERSION', '0.1.0')
app = BUNDLE(
    coll,
    name='CherryPickle.app',
    icon=None,
    bundle_identifier='com.local.cherrypickle',
    info_plist={
        'CFBundleName': 'Cherry.Pickle',
        'CFBundleDisplayName': 'Cherry.Pickle',
        'CFBundleShortVersionString': VERSION,
        'CFBundleVersion': VERSION,
    },
)
