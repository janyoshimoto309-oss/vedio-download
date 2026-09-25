from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from config import PROXY_TOKEN_TTL_SECONDS

_SECRET = os.environ.get("VIDEO_DL_SECRET", "dev-only-change-me").encode("utf-8")


def issue(url: str, headers: dict[str, str] | None, filename: str, ttl: int = PROXY_TOKEN_TTL_SECONDS) -> str:
    payload = {
        "u": url,
        "h": headers or {},
        "n": filename,
        "exp": int(time.time()) + ttl,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sig = hmac.new(_SECRET, raw, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")
    return token


def verify(token: str) -> dict[str, Any]:
    try:
        blob = base64.urlsafe_b64decode(token.encode("ascii"))
        raw, sig = blob.rsplit(b".", 1)
    except Exception as exc:
        raise ValueError("token 无效") from exc
    expected = hmac.new(_SECRET, raw, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("token 签名错误")
    payload = json.loads(raw.decode("utf-8"))
    if int(payload.get("exp") or 0) < time.time():
        raise ValueError("token 已过期")
    return payload
