from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg
from app.api.routes import router
from app.paths import resource_dir

app = FastAPI(title="Cherry.Pickle")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


app.include_router(router)

WEB_DIR = resource_dir() / "frontend" / "dist"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
