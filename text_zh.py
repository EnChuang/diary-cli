"""
全文繁體：使用者輸入與模型輸出一律轉成繁體再入系統／顯示。
依賴：zhconv
"""
from __future__ import annotations

from typing import Any

import zhconv


def to_traditional(text: Any) -> str:
    """任意字串 → 繁體；非字串轉 str。None → ''。"""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return text
    return zhconv.convert(text, "zh-hant")


def traditionalize_obj(obj: Any) -> Any:
    """遞迴把 JSON 結構內所有字串轉繁體（保留 int/bool/null）。"""
    if isinstance(obj, str):
        return to_traditional(obj)
    if isinstance(obj, list):
        return [traditionalize_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: traditionalize_obj(v) for k, v in obj.items()}
    return obj


def name_key(name: str) -> str:
    """比對用人名鍵：繁體 + 去空白。"""
    return "".join(to_traditional(name).split())
