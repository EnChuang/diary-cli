"""
評分流水帳（Phase B3）。

契約：DATA_CONTRACT §4 + schema/score_ledger.schema.json
- data/score_ledger.jsonl：一行一筆 delta
- history_score 應可由此重算
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from storage.paths import LEDGER_PATH

DEFAULT_PATH = LEDGER_PATH
REQUIRED = ("id", "event_id", "character_id", "delta", "at")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_ledger_id() -> str:
    return f"led_{uuid.uuid4().hex[:12]}"


def validate_ledger(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("ledger 必須是 object")
    missing = [k for k in REQUIRED if k not in row]
    if missing:
        raise ValueError(f"缺少欄位：{', '.join(missing)}")
    for key in ("id", "event_id", "character_id", "at"):
        if not isinstance(row[key], str) or not row[key].strip():
            raise ValueError(f"{key} 必須為非空字串")
    delta = row["delta"]
    if not isinstance(delta, int) or isinstance(delta, bool):
        raise ValueError("delta 必須為 integer")
    if delta < -100 or delta > 100:
        raise ValueError("delta 須在 -100～100")
    return {
        "id": row["id"].strip(),
        "event_id": row["event_id"].strip(),
        "character_id": row["character_id"].strip(),
        "delta": int(delta),
        "at": row["at"].strip(),
    }


def load_ledger(path: Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(validate_ledger(json.loads(text)))
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    return rows


def save_ledger(rows: Iterable[dict[str, Any]], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = [validate_ledger(r) for r in rows]
    by_id: dict[str, dict[str, Any]] = {r["id"]: r for r in validated}
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in by_id.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_ledger_rows(
    new_rows: list[dict[str, Any]],
    path: Path = DEFAULT_PATH,
) -> list[dict[str, Any]]:
    rows = load_ledger(path)
    clean = [validate_ledger(r) for r in new_rows]
    rows.extend(clean)
    save_ledger(rows, path)
    return clean


def list_for_event(event_id: str, path: Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    eid = event_id.strip()
    return [r for r in load_ledger(path) if r["event_id"] == eid]


def list_for_character(character_id: str, path: Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    cid = character_id.strip()
    return [r for r in load_ledger(path) if r["character_id"] == cid]


def sum_deltas_by_character(path: Path = DEFAULT_PATH) -> dict[str, int]:
    totals: dict[str, int] = {}
    for r in load_ledger(path):
        totals[r["character_id"]] = totals.get(r["character_id"], 0) + r["delta"]
    return totals


def make_ledger_row(
    *,
    event_id: str,
    character_id: str,
    delta: int,
    at: Optional[str] = None,
    ledger_id: Optional[str] = None,
) -> dict[str, Any]:
    return validate_ledger(
        {
            "id": ledger_id or new_ledger_id(),
            "event_id": event_id,
            "character_id": character_id,
            "delta": delta,
            "at": at or _now_iso(),
        }
    )


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m storage.ledger",
        description="評分流水 CLI（Phase B3）",
    )
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="列出全部 ledger")
    p_e = sub.add_parser("event", help="依 event_id 篩選")
    p_e.add_argument("event_id")
    p_c = sub.add_parser("char", help="依 character_id 篩選")
    p_c.add_argument("character_id")
    sub.add_parser("sums", help="各角色 delta 加總")

    args = parser.parse_args(argv)
    path = args.path

    if args.cmd == "list":
        rows = load_ledger(path)
    elif args.cmd == "event":
        rows = list_for_event(args.event_id, path)
    elif args.cmd == "char":
        rows = list_for_character(args.character_id, path)
    elif args.cmd == "sums":
        for cid, total in sorted(sum_deltas_by_character(path).items(), key=lambda x: -x[1]):
            print(f"{total:>6}  {cid}")
        return 0
    else:
        parser.error(args.cmd)
        return 2

    if not rows:
        print("（無）")
        return 0
    for r in rows:
        print(
            f"{r['at']}  evt={r['event_id']}  char={r['character_id']}  "
            f"delta={r['delta']:+d}  {r['id']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
