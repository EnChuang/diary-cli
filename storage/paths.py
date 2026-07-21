"""
本機資料路徑（野史錄）。

| 檔案 | 用途 |
|------|------|
| data/characters.jsonl | 人物 |
| data/events.jsonl | 事件 |
| data/score_ledger.jsonl | 確認後當次分流水 |
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

CHARACTERS_PATH = DATA_DIR / "characters.jsonl"
EVENTS_PATH = DATA_DIR / "events.jsonl"
LEDGER_PATH = DATA_DIR / "score_ledger.jsonl"


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
