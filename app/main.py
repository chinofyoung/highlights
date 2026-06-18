from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.deps import require_ffmpeg
from app.api.routes import router

app = FastAPI(title="Pickleball Highlights")


@app.on_event("startup")
def _check_ffmpeg() -> None:
    require_ffmpeg()


app.include_router(router)

WEB_DIR = Path(__file__).parent.parent / "frontend" / "dist"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
