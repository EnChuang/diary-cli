"""
清空本機資料 → 無事件／人物／流水的初始狀態。
不刪除 .env、skill、程式碼。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from storage.characters import load_characters, save_characters
from storage.events import load_events, save_events
from storage.ledger import load_ledger, save_ledger
from storage.paths import (
    CHARACTERS_PATH,
    DATA_DIR,
    EVENTS_PATH,
    LEDGER_PATH,
    ensure_data_dir,
)


def is_local_data_empty() -> bool:
    """無人物、事件、流水、pending 暫存 → 視為已清空。"""
    ensure_data_dir()
    if load_characters(CHARACTERS_PATH):
        return False
    if load_events(EVENTS_PATH):
        return False
    if load_ledger(LEDGER_PATH):
        return False
    if any(DATA_DIR.glob(".pending_generate_*.json")):
        return False
    return True


def wipe_all_local_data() -> dict[str, Any]:
    """
    寫空 characters / events / ledger，並刪除 pending 暫存檔。
    回傳摘要（僅供日誌／UI 提示）。
    """
    ensure_data_dir()
    save_characters([], CHARACTERS_PATH)
    save_events([], EVENTS_PATH)
    save_ledger([], LEDGER_PATH)

    removed_pending: list[str] = []
    for p in DATA_DIR.glob(".pending_generate_*.json"):
        try:
            p.unlink()
            removed_pending.append(p.name)
        except OSError:
            pass
    # 其他隱藏暫存
    for p in DATA_DIR.glob(".jobs*"):
        try:
            if p.is_file():
                p.unlink()
                removed_pending.append(p.name)
        except OSError:
            pass

    return {
        "characters": str(CHARACTERS_PATH),
        "events": str(EVENTS_PATH),
        "ledger": str(LEDGER_PATH),
        "removed_pending": removed_pending,
    }
