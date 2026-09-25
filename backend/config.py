import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

DOWNLOADS_DIR = BASE_DIR / "downloads"

# Netscape cookies.txt；也可通过环境变量覆盖
COOKIES_FILE = Path(os.environ.get("YTDLP_COOKIES") or (BASE_DIR / "cookies.txt"))
# 例如 chrome / edge / firefox；留空则不从浏览器读
COOKIES_FROM_BROWSER = (os.environ.get("YTDLP_COOKIES_FROM_BROWSER") or "").strip()
# chrome / chrome-110 等；需要 curl_cffi。空字符串关闭
YTDLP_IMPERSONATE = os.environ.get("YTDLP_IMPERSONATE", "chrome").strip()

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
    "douyinbrowser",
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

# DeepSeek Chat Completions（官方 base_url 为 https://api.deepseek.com，可无 /v1）
# https://api-docs.deepseek.com/  模型：deepseek-flash / deepseek-v4-pro
OPENAI_API_KEY = (
    (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
)
OPENAI_BASE_URL = (
    os.environ.get("OPENAI_BASE_URL")
    or os.environ.get("DEEPSEEK_BASE_URL")
    or "https://api.deepseek.com"
).rstrip("/")
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL") or os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash").strip()
SUMMARIZE_MAX_CHARS = int(os.environ.get("SUMMARIZE_MAX_CHARS") or "48000")
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS") or "180")
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS") or "8192")
