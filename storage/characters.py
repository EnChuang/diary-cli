"""
人物讀寫（Phase B1）。

契約：dev-local/DATA_CONTRACT.md §2 + schema/character.schema.json
- data/characters.jsonl：一行一人
- 榜單：is_user == false，依 history_score 降序
- 不呼叫 AI
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from storage.paths import CHARACTERS_PATH
from text_zh import name_key, to_traditional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = CHARACTERS_PATH
USER_ID = "self"

REQUIRED_FIELDS = (
    "id",
    "name",
    "display_nick",
    "history_score",
    "is_user",
    "created_at",
    "updated_at",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_display_nick(name: str) -> str:
    """暫定暱稱：已是「小…」則沿用；否則「小」+ 名末 1～2 字。Skill 細節後定。"""
    name = to_traditional((name or "").strip())
    if not name:
        return "小?"
    if name.startswith("小") and len(name) >= 2:
        return name
    tail = name[-2:] if len(name) >= 2 else name
    return f"小{tail}"


def new_character_id() -> str:
    return f"char_{uuid.uuid4().hex[:12]}"


def validate_character(row: dict[str, Any]) -> dict[str, Any]:
    """輕量欄位檢查（對齊 schema 必填與型別語意）。"""
    if not isinstance(row, dict):
        raise ValueError("character 必須是 object")
    missing = [k for k in REQUIRED_FIELDS if k not in row]
    if missing:
        raise ValueError(f"缺少欄位：{', '.join(missing)}")

    for key in ("id", "name", "display_nick", "created_at", "updated_at"):
        if not isinstance(row[key], str) or not row[key].strip():
            raise ValueError(f"{key} 必須為非空字串")

    if not isinstance(row["history_score"], int) or isinstance(row["history_score"], bool):
        raise ValueError("history_score 必須為 integer")
    if not isinstance(row["is_user"], bool):
        raise ValueError("is_user 必須為 boolean")

    # 回傳正規化副本（不允許 extra 欄位污染寫盤）；名稱一律繁體
    return {
        "id": row["id"].strip(),
        "name": to_traditional(row["name"].strip()),
        "display_nick": to_traditional(row["display_nick"].strip()),
        "history_score": int(row["history_score"]),
        "is_user": bool(row["is_user"]),
        "created_at": row["created_at"].strip(),
        "updated_at": row["updated_at"].strip(),
    }


def load_characters(path: Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
                rows.append(validate_character(obj))
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    return rows


def save_characters(rows: Iterable[dict[str, Any]], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = [validate_character(r) for r in rows]
    # 以 id 去重：後寫覆蓋先寫（防 seed 重複）
    by_id: dict[str, dict[str, Any]] = {}
    for r in validated:
        by_id[r["id"]] = r
    ordered = list(by_id.values())
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def list_characters(
    *,
    include_user: bool = True,
    path: Path = DEFAULT_PATH,
) -> list[dict[str, Any]]:
    rows = load_characters(path)
    if not include_user:
        rows = [r for r in rows if not r["is_user"]]
    return rows


def get_character(character_id: str, path: Path = DEFAULT_PATH) -> Optional[dict[str, Any]]:
    cid = (character_id or "").strip()
    for row in load_characters(path):
        if row["id"] == cid:
            return row
    return None


def find_character_by_name(
    name: str,
    path: Path = DEFAULT_PATH,
    *,
    include_user: bool = False,
) -> Optional[dict[str, Any]]:
    """依繁體正規化名稱找既有角色（避免簡繁／重複建檔）。"""
    key = name_key(name)
    if not key:
        return None
    for row in load_characters(path):
        if row.get("is_user") and not include_user:
            continue
        if name_key(row.get("name") or "") == key:
            return row
        if name_key(row.get("display_nick") or "") == key:
            return row
    # 末兩字
    if len(key) >= 2:
        tail = key[-2:]
        hits = []
        for row in load_characters(path):
            if row.get("is_user") and not include_user:
                continue
            nk = name_key(row.get("name") or "")
            if len(nk) >= 2 and nk[-2:] == tail:
                hits.append(row)
        if len(hits) == 1:
            return hits[0]
    return None


def upsert_character(row: dict[str, Any], path: Path = DEFAULT_PATH) -> dict[str, Any]:
    clean = validate_character(row)
    rows = load_characters(path)
    found = False
    for i, existing in enumerate(rows):
        if existing["id"] == clean["id"]:
            # 保留 created_at，更新其餘
            clean["created_at"] = existing["created_at"]
            clean["updated_at"] = _now_iso()
            rows[i] = clean
            found = True
            break
    if not found:
        rows.append(clean)
    save_characters(rows, path)
    return clean


def create_character(
    name: str,
    *,
    display_nick: Optional[str] = None,
    history_score: int = 0,
    is_user: bool = False,
    character_id: Optional[str] = None,
    path: Path = DEFAULT_PATH,
    reuse_by_name: bool = True,
) -> dict[str, Any]:
    name = to_traditional((name or "").strip())
    if not name:
        raise ValueError("name 不可為空")
    if is_user:
        cid = USER_ID
        if display_nick is None:
            display_nick = "我"
    else:
        # 同名繁體已存在 → 重用，避免榜上重複
        if reuse_by_name and not character_id:
            by_name = find_character_by_name(name, path)
            if by_name is not None:
                return by_name
        cid = (character_id or new_character_id()).strip()
        if not cid:
            raise ValueError("character_id 不可為空")

    existing = get_character(cid, path)
    if existing and not is_user:
        raise ValueError(f"id 已存在：{cid}")

    now = _now_iso()
    nick = to_traditional((display_nick or default_display_nick(name)).strip())
    row = {
        "id": cid,
        "name": name,
        "display_nick": nick,
        "history_score": int(history_score),
        "is_user": bool(is_user),
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }
    return upsert_character(row, path)


def update_character(
    character_id: str,
    *,
    name: Optional[str] = None,
    display_nick: Optional[str] = None,
    history_score: Optional[int] = None,
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    row = get_character(character_id, path)
    if row is None:
        raise KeyError(f"找不到人物：{character_id}")
    if name is not None:
        row["name"] = name.strip()
    if display_nick is not None:
        row["display_nick"] = display_nick.strip()
    if history_score is not None:
        if not isinstance(history_score, int) or isinstance(history_score, bool):
            raise ValueError("history_score 必須為 integer")
        row["history_score"] = history_score
    row["updated_at"] = _now_iso()
    return upsert_character(row, path)


def ensure_user(name: str = "我", path: Path = DEFAULT_PATH) -> dict[str, Any]:
    """固定使用者本體 id=self；永不進榜。"""
    existing = get_character(USER_ID, path)
    if existing:
        return existing
    name = to_traditional((name or "我").strip()) or "我"
    return create_character(
        name,
        display_nick="我",
        is_user=True,
        character_id=USER_ID,
        path=path,
        reuse_by_name=False,
    )


def leaderboard(path: Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    """歷史榜：非使用者，history_score 降序。"""
    rows = [r for r in load_characters(path) if not r["is_user"]]
    return sorted(rows, key=lambda r: (-r["history_score"], r["name"], r["id"]))


def seed_demo_characters(path: Path = DEFAULT_PATH, *, force: bool = False) -> list[dict[str, Any]]:
    """
    寫入假資料供 B1 驗證。
    force=False 且檔案已有內容時：只 ensure_user，不覆蓋既有角色。
    force=True：覆寫為 demo 集合（含 self + 三人）。
    """
    if force or not path.is_file() or path.stat().st_size == 0:
        now = _now_iso()
        demo = [
            {
                "id": USER_ID,
                "name": "我",
                "display_nick": "我",
                "history_score": 0,
                "is_user": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "char_demo_mei",
                "name": "陳美玲",
                "display_nick": "小美",
                "history_score": 42,
                "is_user": False,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "char_demo_wang",
                "name": "王大明",
                "display_nick": "小明",
                "history_score": -15,
                "is_user": False,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "char_demo_lin",
                "name": "林主管",
                "display_nick": "小主",
                "history_score": 8,
                "is_user": False,
                "created_at": now,
                "updated_at": now,
            },
        ]
        save_characters(demo, path)
        return load_characters(path)

    ensure_user(path=path)
    return load_characters(path)


def _print_table(rows: list[dict[str, Any]], *, rank: bool = False) -> None:
    if not rows:
        print("（無資料）")
        return
    if rank:
        print(f"{'#':>3}  {'name':<12}  {'nick':<8}  {'score':>6}  id")
        for i, r in enumerate(rows, start=1):
            print(
                f"{i:>3}  {r['name']:<12}  {r['display_nick']:<8}  "
                f"{r['history_score']:>6}  {r['id']}"
            )
    else:
        print(f"{'name':<12}  {'nick':<8}  {'score':>6}  {'user':<5}  id")
        for r in rows:
            print(
                f"{r['name']:<12}  {r['display_nick']:<8}  "
                f"{r['history_score']:>6}  {str(r['is_user']):<5}  {r['id']}"
            )


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m storage.characters",
        description="人物讀寫 CLI（Phase B1，不呼叫 AI）",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PATH,
        help=f"jsonl 路徑（預設 {DEFAULT_PATH}）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="寫入假資料")
    p_seed.add_argument(
        "--force",
        action="store_true",
        help="覆寫為 demo 集合",
    )

    sub.add_parser("list", help="列出全部人物")
    sub.add_parser("rank", help="歷史榜（排除使用者）")

    p_get = sub.add_parser("get", help="依 id 查詢")
    p_get.add_argument("id")

    p_add = sub.add_parser("add", help="新增人物")
    p_add.add_argument("name")
    p_add.add_argument("--nick", default=None, help="display_nick")
    p_add.add_argument("--score", type=int, default=0)

    args = parser.parse_args(argv)
    path: Path = args.path

    if args.cmd == "seed":
        rows = seed_demo_characters(path, force=args.force)
        print(f"已寫入／讀取 {len(rows)} 人 → {path}")
        _print_table(rows)
        return 0

    if args.cmd == "list":
        _print_table(list_characters(path=path))
        return 0

    if args.cmd == "rank":
        _print_table(leaderboard(path=path), rank=True)
        return 0

    if args.cmd == "get":
        row = get_character(args.id, path=path)
        if row is None:
            print(f"找不到：{args.id}", file=sys.stderr)
            return 1
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "add":
        row = create_character(
            args.name,
            display_nick=args.nick,
            history_score=args.score,
            path=path,
        )
        print(json.dumps(row, ensure_ascii=False, indent=2))
        print(f"已寫入 → {path}")
        return 0

    parser.error(f"未知命令：{args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
