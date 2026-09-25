from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"

FILE_TTL_SECONDS = 3600
MAX_CONCURRENT_DOWNLOADS = 2
PROXY_TOKEN_TTL_SECONDS = 600

# Extractor keys 小写匹配
DIRECT_UNRELIABLE_EXTRACTORS = {
    "youtube",
    "youtubetab",
    "bilibili",
    "bilibiliie",
    "tiktok",
    "douyin",
}

FRAGMENT_PROTOCOLS = {
    "m3u8",
    "m3u8_native",
    "m3u8_frag_urls",
    "http_dash_segments",
    "dash",
}

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
