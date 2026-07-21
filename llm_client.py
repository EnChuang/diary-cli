"""
ModelArk（OpenAI 相容）共用客戶端 — M1。

- 讀 .env 的 ARK_*
- strip code fence
- chat → 解析 JSON（失敗可重試）
- 空回覆／額度用盡／連線失敗 → 使用者可讀錯誤（LLMError）
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI

from text_zh import to_traditional, traditionalize_obj

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"

# 系統側提醒：模型請用繁體（仍以後處理 traditionalize 為準）
_TRAD_HINT = "（重要：所有中文輸出請使用繁體中文，不要使用簡體字。）"

DEFAULT_ARK_BASE_URL = "https://ark.ap-southeast.bytepluses.com/api/v3"
DEFAULT_ARK_MODEL = "deepseek-v4-pro-260425"


class LLMError(RuntimeError):
    """可直接顯示給使用者的 AI／ModelArk 錯誤。"""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None):
        super().__init__(message)
        self.user_message = message
        self.cause = cause


def load_env() -> None:
    load_dotenv(ENV_PATH)


def get_model() -> str:
    load_env()
    return os.getenv("ARK_MODEL", DEFAULT_ARK_MODEL)


def make_client() -> OpenAI:
    load_env()
    key = os.getenv("ARK_API_KEY", "").strip()
    if not key or key.startswith("ark-你的") or key.startswith("sk-你的"):
        raise LLMError(
            "尚未設定 API 金鑰。請在專案根目錄的 .env 填入 ARK_API_KEY 後重試。"
        )
    return OpenAI(
        api_key=key,
        base_url=os.getenv("ARK_BASE_URL", DEFAULT_ARK_BASE_URL).rstrip("/"),
    )


def strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_json_object(text: str) -> str:
    """從可能含雜訊的回覆中抽出第一個 JSON object 字串。"""
    text = strip_code_fence(text)
    if not text:
        raise json.JSONDecodeError("空回覆", text, 0)
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        json.loads(candidate)  # may raise
        return candidate
    raise json.JSONDecodeError("找不到 JSON object", text, 0)


def _prepare_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """使用者／系統內容轉繁體；system 附加繁體提醒。"""
    out: list[dict[str, str]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = to_traditional(msg.get("content") or "")
        if role == "system" and _TRAD_HINT not in content:
            content = content.rstrip() + "\n\n" + _TRAD_HINT
        out.append({"role": role, "content": content})
    return out


def _error_blob(exc: BaseException) -> str:
    parts = [str(exc), type(exc).__name__]
    body = getattr(exc, "body", None)
    if body is not None:
        parts.append(str(body))
    resp = getattr(exc, "response", None)
    if resp is not None:
        try:
            parts.append(str(getattr(resp, "text", "") or ""))
        except Exception:
            pass
    code = getattr(exc, "code", None)
    if code is not None:
        parts.append(str(code))
    status = getattr(exc, "status_code", None)
    if status is not None:
        parts.append(str(status))
    return " ".join(parts).lower()


def format_llm_error(exc: BaseException) -> str:
    """把任意例外轉成介面上可讀的繁中說明。"""
    if isinstance(exc, LLMError):
        return exc.user_message

    blob = _error_blob(exc)
    name = type(exc).__name__.lower()

    # —— 額度／Token／帳務 ——
    quota_markers = (
        "insufficient_quota",
        "insufficient quota",
        "quota exceeded",
        "quota_exceeded",
        "billing",
        "balance",
        "out of credit",
        "credit",
        "token.*exhaust",
        "tokens? (limit|exceed|exceeded|用尽|用盡|不足)",
        "rate_limit",
        "ratelimit",
        "too many requests",
        "429",
        "额度",
        "額度",
        "余额",
        "餘額",
        "欠费",
        "欠費",
        "资源包",
        "資源包",
        "overloaded",
    )
    if any(re.search(m, blob) for m in quota_markers) or "ratelimit" in name:
        return (
            "AI 服務額度不足或呼叫過於頻繁（可能 Token／配額已用盡）。"
            "請檢查 ModelArk 帳號餘額與用量後再試。"
        )

    # —— 金鑰／權限 ——
    if any(
        x in blob
        for x in (
            "invalid_api_key",
            "authentication",
            "unauthorized",
            "401",
            "403",
            "permission",
            "api key",
        )
    ) or "auth" in name:
        return "API 金鑰無效或無權限。請檢查 .env 的 ARK_API_KEY 是否正確。"

    # —— 連線／逾時 ——
    if any(
        x in blob
        for x in (
            "timeout",
            "timed out",
            "connection",
            "connect",
            "network",
            "dns",
            "unreachable",
        )
    ) or "timeout" in name or "connection" in name:
        return "無法連線到 AI 服務或等待逾時。請確認網路後再試。"

    # —— 模型不存在 ——
    if any(x in blob for x in ("model", "not found", "404", "does not exist")):
        if "model" in blob:
            return (
                "指定的 AI 模型無法使用。請檢查 .env 的 ARK_MODEL 是否正確、"
                "帳號是否有權限。"
            )

    # —— 空回覆（JSON 路徑也會走到） ——
    if "空回覆" in str(exc) or "empty" in blob and "json" in blob:
        return "AI 沒有回傳內容（空回應）。請稍後再試；若持續發生，可能是模型異常或額度問題。"

    # —— 無法解析 ——
    if "無法解析" in str(exc) or "json" in blob:
        raw = str(exc)
        if len(raw) > 280:
            raw = raw[:280] + "…"
        return f"AI 有回應但格式無法解析。{raw}"

    # —— 其他 API ——
    msg = str(exc).strip() or name
    if len(msg) > 240:
        msg = msg[:240] + "…"
    return f"AI 呼叫失敗：{msg}"


def _raise_api_error(exc: BaseException) -> None:
    raise LLMError(format_llm_error(exc), cause=exc) from exc


def chat_text(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.4,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
) -> str:
    c = client or make_client()
    m = model or get_model()
    prepared = _prepare_messages(messages)
    try:
        resp = c.chat.completions.create(
            model=m,
            messages=prepared,
            temperature=temperature,
        )
    except LLMError:
        raise
    except Exception as e:
        _raise_api_error(e)

    if resp is None:
        raise LLMError("AI 完全沒有回應，請稍後再試。")

    choices = getattr(resp, "choices", None) or []
    if not choices:
        raise LLMError(
            "AI 沒有回傳任何結果（可能服務異常或額度已用盡）。請稍後再試或檢查 ModelArk 用量。"
        )

    message = choices[0].message
    content = getattr(message, "content", None)
    if content is None or not str(content).strip():
        finish = getattr(choices[0], "finish_reason", None) or ""
        if str(finish).lower() in ("length", "max_tokens"):
            raise LLMError(
                "AI 回應在長度上限被截斷且沒有可用內容。請縮短輸入後再試。"
            )
        raise LLMError(
            "AI 沒有回傳內容（空回應）。可能是模型未輸出、服務異常，或 Token／額度已用盡。"
            "請稍後再試或至 ModelArk 確認用量。"
        )

    return to_traditional(str(content).strip())


def chat_json(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.4,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
    max_attempts: int = 3,
) -> dict[str, Any]:
    """
    呼叫模型並解析為 dict。
    解析失敗時追加一輪「只輸出合法 JSON」重試（C3）。
    回傳物件內所有字串已轉繁體。
    API／空回覆錯誤以 LLMError 拋出（可直接顯示給使用者）。
    """
    c = client or make_client()
    m = model or get_model()
    working = _prepare_messages(messages)
    last_err: Optional[Exception] = None
    last_raw = ""

    for attempt in range(max_attempts):
        try:
            last_raw = chat_text(
                working, temperature=temperature, model=m, client=c
            )
        except LLMError:
            raise

        if not (last_raw or "").strip():
            raise LLMError(
                "AI 沒有回傳內容（空回應）。請稍後再試；若持續發生，請檢查額度與模型狀態。"
            )

        try:
            payload = extract_json_object(last_raw)
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise ValueError("JSON 根節點必須是 object")
            return traditionalize_obj(data)
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            if attempt + 1 >= max_attempts:
                break
            working = working + [
                {"role": "assistant", "content": last_raw},
                {
                    "role": "user",
                    "content": to_traditional(
                        "上一段回覆不是可解析的單一 JSON object。"
                        "請只輸出合法 JSON（不要代碼圍欄、不要說明），"
                        "欄位結構與 system 要求一致。全部中文用繁體。"
                    ),
                },
            ]

    raise LLMError(
        "AI 有回應，但多次嘗試後仍無法解析為有效內容。"
        f"（{last_err}）請稍後再試。"
    )


def load_skill_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"找不到 Skill：{path}")
    return path.read_text(encoding="utf-8")
