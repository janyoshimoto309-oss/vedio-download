from __future__ import annotations

import json
import re
from typing import Any

import httpx

from config import (
    LLM_MAX_TOKENS,
    LLM_TIMEOUT_SECONDS,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

# 官方文档（2026-09）：https://api-docs.deepseek.com/
# Chat Completions：POST {base}/chat/completions
# JSON Output：response_format={"type":"json_object"}，prompt 里必须出现 json
# Thinking 默认开启；结构化笔记关闭 thinking，避免 CoT 占满超时


def llm_configured() -> bool:
    return bool(OPENAI_API_KEY)


class LLMError(RuntimeError):
    pass


def redact_secret(text: str) -> str:
    if not text:
        return ""
    out = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._\-+=/]+", "Bearer [redacted]", text)
    out = re.sub(r"sk-[A-Za-z0-9]+", "[redacted]", out)
    out = re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)\S+", r"\1[redacted]", out)
    return out


def chat_completions_url(base: str | None = None) -> str:
    root = (base or OPENAI_BASE_URL).rstrip("/")
    if root.endswith("/chat/completions"):
        return root
    return f"{root}/chat/completions"


def build_chat_payload(system: str, user: str) -> dict[str, Any]:
    return {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "response_format": {"type": "json_object"},
        "max_tokens": LLM_MAX_TOKENS,
        "thinking": {"type": "disabled"},
    }


def chat_json(system: str, user: str) -> dict[str, Any]:
    if not OPENAI_API_KEY:
        raise LLMError(
            "未配置 DeepSeek Key。请在 backend/.env 填写 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 后重启后端。"
        )
    url = chat_completions_url()
    payload = build_chat_payload(system, user)
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(LLM_TIMEOUT_SECONDS, connect=15.0)) as client:
            resp = client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise LLMError("大模型响应超时，请稍后重试或换较短的视频。") from exc
    except Exception as exc:
        raise LLMError(f"调用大模型失败：{redact_secret(str(exc))}") from exc

    if resp.status_code >= 400:
        raise LLMError(f"大模型接口返回 {resp.status_code}")

    try:
        data = resp.json()
        message = data["choices"][0]["message"]
        content = message.get("content")
    except Exception as exc:
        raise LLMError("大模型返回格式无法解析") from exc
    if not content:
        raise LLMError("模型返回了空内容，请稍后重试。")
    return _extract_json(content)


def _extract_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise LLMError("模型没有返回可用的 JSON 总结")
