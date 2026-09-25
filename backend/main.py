from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.video import router as video_router
from config import CORS_ORIGINS, DOWNLOADS_DIR
from services.downloader import ffmpeg_available
from services.task_store import cleanup_expired


@asynccontextmanager
async def lifespan(_app: FastAPI):
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_expired()
    yield
    cleanup_expired()


app = FastAPI(title="万能视频下载", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(video_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "ffmpeg": ffmpeg_available()}
