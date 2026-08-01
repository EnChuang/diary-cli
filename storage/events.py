"""
事件草稿讀寫（Phase B2）。

契約：dev-local/DATA_CONTRACT.md §3 + schema/event.schema.json
- data/events.jsonl：一行一事件
- 不呼叫 AI（ai_draft / qa 可手填或 seed）
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from storage.paths import EVENTS_PATH
from text_zh import to_traditional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = EVENTS_PATH

STATUSES = frozenset({"draft", "awaiting_generate", "confirmed"})
QA_ROLES = frozenset({"user", "assistant"})

REQUIRED_FIELDS = (
    "id",
    "status",
    "created_at",
    "updated_at",
    "confirmed_at",
    "user_main_text",
    "ai_draft",
    "qa_thread",
    "story",
    "participants",
    "score_mean",
)

# 示例八卦主文（給 seed／教學用）
DEMO_MAIN_TEXT = """今天午餐時陳美玲跟王大明在茶水間吵起來。
小美說上次提案是她做的，大明卻在會上搶功。
林主管經過只說「私下解決」，兩邊更不爽。
我在旁邊不敢插話，只覺得這週例會氣氛會很糟。"""

DEMO_AI_DRAFT = """【茶水間搶功風波】
午餐時段，陳美玲與王大明在茶水間爆發爭執：小美主張提案出自她手，大明卻在會上居功。
林主管路過僅以「私下解決」帶過，火上加油。旁觀的「我」選擇沉默，预感例會氣氛不妙。"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_event_id() -> str:
    return f"evt_{uuid.uuid4().hex[:12]}"


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def validate_qa_message(msg: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(msg, dict):
        raise ValueError("qa_thread 項目必須是 object")
    for key in ("role", "content", "at"):
        if key not in msg:
            raise ValueError(f"qa 缺少欄位：{key}")
    if msg["role"] not in QA_ROLES:
        raise ValueError("qa.role 必須是 user 或 assistant")
    if not isinstance(msg["content"], str):
        raise ValueError("qa.content 必須是字串")
    if not isinstance(msg["at"], str) or not msg["at"].strip():
        raise ValueError("qa.at 必須為非空字串")
    return {
        "role": msg["role"],
        "content": to_traditional(msg["content"]),
        "at": msg["at"].strip(),
    }


def validate_story(story: Any) -> Optional[dict[str, Any]]:
    if story is None:
        return None
    if not isinstance(story, dict):
        raise ValueError("story 必須是 object 或 null")
    for key in ("title", "time", "tags", "body"):
        if key not in story:
            raise ValueError(f"story 缺少欄位：{key}")
    if not isinstance(story["title"], str):
        raise ValueError("story.title 必須是字串")
    if not isinstance(story["time"], str):
        raise ValueError("story.time 必須是字串")
    if not isinstance(story["body"], str):
        raise ValueError("story.body 必須是字串")
    if not isinstance(story["tags"], list) or not all(isinstance(t, str) for t in story["tags"]):
        raise ValueError("story.tags 必須是 string[]")
    return {
        "title": to_traditional(story["title"]),
        "time": to_traditional(story["time"]),
        "tags": [to_traditional(t) for t in story["tags"]],
        "body": to_traditional(story["body"]),
    }


def validate_participant(p: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(p, dict):
        raise ValueError("participant 必須是 object")
    if "is_user" not in p or "event_score" not in p:
        raise ValueError("participant 需要 is_user 與 event_score")
    if not isinstance(p["is_user"], bool):
        raise ValueError("participant.is_user 必須是 boolean")

    score = p["event_score"]
    if score is not None:
        if not _is_int(score):
            raise ValueError("event_score 必須是 integer 或 null")
        if score < -100 or score > 100:
            raise ValueError("event_score 須在 -100～100")
        if p["is_user"] and score is not None:
            raise ValueError("使用者 participant 的 event_score 必須是 null")

    out: dict[str, Any] = {
        "is_user": p["is_user"],
        "event_score": score,
    }
    if "character_id" in p:
        cid = p["character_id"]
        if cid is not None and (not isinstance(cid, str) or not cid.strip()):
            raise ValueError("character_id 必須是非空字串或 null")
        out["character_id"] = cid.strip() if isinstance(cid, str) else None
    if "temp_name" in p:
        if not isinstance(p["temp_name"], str):
            raise ValueError("temp_name 必須是字串")
        out["temp_name"] = to_traditional(p["temp_name"])
    if "score_reason" in p:
        if not isinstance(p["score_reason"], str):
            raise ValueError("score_reason 必須是字串")
        out["score_reason"] = to_traditional(p["score_reason"])
    return out


def validate_event(row: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise ValueError("event 必須是 object")
    missing = [k for k in REQUIRED_FIELDS if k not in row]
    if missing:
        raise ValueError(f"缺少欄位：{', '.join(missing)}")

    for key in ("id", "created_at", "updated_at"):
        if not isinstance(row[key], str) or not row[key].strip():
            raise ValueError(f"{key} 必須為非空字串")
    if row["status"] not in STATUSES:
        raise ValueError("status 必須是 draft | awaiting_generate | confirmed")
    if row["confirmed_at"] is not None:
        if not isinstance(row["confirmed_at"], str) or not row["confirmed_at"].strip():
            raise ValueError("confirmed_at 必須是字串或 null")
    if not isinstance(row["user_main_text"], str):
        raise ValueError("user_main_text 必須是字串")
    if not isinstance(row["ai_draft"], str):
        raise ValueError("ai_draft 必須是字串")
    if not isinstance(row["qa_thread"], list):
        raise ValueError("qa_thread 必須是 array")
    if not isinstance(row["participants"], list):
        raise ValueError("participants 必須是 array")
    if row["score_mean"] is not None and not isinstance(row["score_mean"], (int, float)):
        raise ValueError("score_mean 必須是 number 或 null")
    if isinstance(row["score_mean"], bool):
        raise ValueError("score_mean 必須是 number 或 null")

    out: dict[str, Any] = {
        "id": row["id"].strip(),
        "status": row["status"],
        "created_at": row["created_at"].strip(),
        "updated_at": row["updated_at"].strip(),
        "confirmed_at": (
            row["confirmed_at"].strip()
            if isinstance(row["confirmed_at"], str)
            else None
        ),
        "user_main_text": to_traditional(row["user_main_text"]),
        "ai_draft": to_traditional(row["ai_draft"]),
        "qa_thread": [validate_qa_message(m) for m in row["qa_thread"]],
        "story": validate_story(row["story"]),
        "participants": [validate_participant(p) for p in row["participants"]],
        "score_mean": None if row["score_mean"] is None else float(row["score_mean"]),
    }
    if "notes" in row and row["notes"] is not None:
        if not isinstance(row["notes"], str):
            raise ValueError("notes 必須是字串")
        out["notes"] = to_traditional(row["notes"])

    # D22 標題
    user_title = to_traditional((row.get("user_title") or "").strip())
    if "title_deferred" in row:
        if not isinstance(row["title_deferred"], bool):
            raise ValueError("title_deferred 必須是 boolean")
        title_deferred = row["title_deferred"]
    else:
        # 舊資料：無手填標題則視為延後
        title_deferred = not bool(user_title)
    if title_deferred:
        user_title = user_title  # 仍可保留暫定字，但語意以 deferred 為準
    out["user_title"] = user_title
    out["title_deferred"] = title_deferred

    # D23 後續
    if "parent_event_id" in row and row["parent_event_id"] is not None:
        pid = row["parent_event_id"]
        if not isinstance(pid, str) or not pid.strip():
            raise ValueError("parent_event_id 必須是非空字串或 null")
        out["parent_event_id"] = pid.strip()
    else:
        out["parent_event_id"] = None
    return out


def load_events(path: Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(validate_event(json.loads(text)))
            except (json.JSONDecodeError, ValueError) as e:
                raise ValueError(f"{path}:{lineno}: {e}") from e
    return rows


def save_events(rows: Iterable[dict[str, Any]], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validated = [validate_event(r) for r in rows]
    by_id: dict[str, dict[str, Any]] = {}
    for r in validated:
        by_id[r["id"]] = r
    ordered = list(by_id.values())
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def get_event(event_id: str, path: Path = DEFAULT_PATH) -> Optional[dict[str, Any]]:
    eid = (event_id or "").strip()
    for row in load_events(path):
        if row["id"] == eid:
            return row
    return None


def list_events(
    *,
    status: Optional[str] = None,
    path: Path = DEFAULT_PATH,
) -> list[dict[str, Any]]:
    rows = load_events(path)
    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"未知 status：{status}")
        rows = [r for r in rows if r["status"] == status]
    # 新到舊
    return sorted(rows, key=lambda r: r["updated_at"], reverse=True)


def upsert_event(row: dict[str, Any], path: Path = DEFAULT_PATH) -> dict[str, Any]:
    clean = validate_event(row)
    rows = load_events(path)
    found = False
    for i, existing in enumerate(rows):
        if existing["id"] == clean["id"]:
            clean["created_at"] = existing["created_at"]
            clean["updated_at"] = _now_iso()
            rows[i] = clean
            found = True
            break
    if not found:
        rows.append(clean)
    save_events(rows, path)
    return clean


def create_event(
    user_main_text: str,
    *,
    ai_draft: str = "",
    status: str = "draft",
    event_id: Optional[str] = None,
    qa_thread: Optional[list[dict[str, Any]]] = None,
    participants: Optional[list[dict[str, Any]]] = None,
    story: Any = None,
    score_mean: Any = None,
    notes: Optional[str] = None,
    user_title: str = "",
    title_deferred: Optional[bool] = None,
    parent_event_id: Optional[str] = None,
    path: Path = DEFAULT_PATH,
    allow_second_draft: bool = False,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"未知 status：{status}")
    if status == "confirmed":
        pass
    # D24：未 confirmed 新建前，全庫只能有 0 份草稿
    if status != "confirmed" and not allow_second_draft:
        existing_draft = get_sole_draft(path)
        if existing_draft is not None:
            raise ValueError(
                f"已有進行中草稿（{existing_draft['id']}），請先繼續或放棄"
            )

    now = _now_iso()
    eid = (event_id or new_event_id()).strip()
    if get_event(eid, path) is not None:
        raise ValueError(f"id 已存在：{eid}")

    ut = to_traditional((user_title or "").strip())
    if title_deferred is None:
        title_deferred = not bool(ut)
    if title_deferred and not ut:
        ut = ""

    parent_id = None
    if parent_event_id:
        parent_id = parent_event_id.strip()
        parent = get_event(parent_id, path)
        if parent is None:
            raise ValueError(f"找不到父事件：{parent_id}")
        if not is_readable_event(parent):
            raise ValueError("僅已可閱讀（confirmed+成稿）的事件可加後續")

    row: dict[str, Any] = {
        "id": eid,
        "status": status,
        "created_at": now,
        "updated_at": now,
        "confirmed_at": now if status == "confirmed" else None,
        "user_main_text": to_traditional(
            user_main_text if user_main_text is not None else ""
        ),
        "ai_draft": to_traditional(ai_draft if ai_draft is not None else ""),
        "qa_thread": qa_thread or [],
        "story": story,
        "participants": participants or [],
        "score_mean": score_mean,
        "user_title": ut,
        "title_deferred": bool(title_deferred),
        "parent_event_id": parent_id,
    }
    if notes is not None:
        row["notes"] = to_traditional(notes)
    return upsert_event(row, path)


def is_readable_event(ev: dict[str, Any]) -> bool:
    """已可閱讀：confirmed 且有成稿 body。"""
    if ev.get("status") != "confirmed":
        return False
    story = ev.get("story")
    return isinstance(story, dict) and bool((story.get("body") or "").strip())


def is_draft_event(ev: dict[str, Any]) -> bool:
    return ev.get("status") != "confirmed"


def get_sole_draft(path: Path = DEFAULT_PATH) -> Optional[dict[str, Any]]:
    """D24：全庫應只有 0～1 份草稿；若異常多份取 updated_at 最新。"""
    drafts = [e for e in load_events(path) if is_draft_event(e)]
    if not drafts:
        return None
    drafts.sort(key=lambda e: e.get("updated_at") or "", reverse=True)
    return drafts[0]


def list_children(
    parent_event_id: str, path: Path = DEFAULT_PATH
) -> list[dict[str, Any]]:
    pid = parent_event_id.strip()
    kids = [e for e in load_events(path) if e.get("parent_event_id") == pid]
    kids.sort(key=lambda e: e.get("updated_at") or "", reverse=True)
    return kids


def count_children(parent_event_id: str, path: Path = DEFAULT_PATH) -> int:
    return len(list_children(parent_event_id, path))


def list_subtree_ids(event_id: str, path: Path = DEFAULT_PATH) -> list[str]:
    """
    本篇 id + 所有子孫後續（任意深度）。
    刪子篇時不會包含父；刪父時包含全部子／孫。
    """
    eid = event_id.strip()
    rows = load_events(path)
    by_parent: dict[str, list[str]] = {}
    ids_present: set[str] = set()
    for r in rows:
        rid = r["id"]
        ids_present.add(rid)
        pid = r.get("parent_event_id")
        if pid:
            by_parent.setdefault(str(pid).strip(), []).append(rid)
    if eid not in ids_present:
        return []
    out: list[str] = []
    stack = [eid]
    seen: set[str] = set()
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        out.append(cur)
        for child in by_parent.get(cur, []):
            stack.append(child)
    return out


def delete_event_tree(
    event_id: str,
    *,
    path: Path = DEFAULT_PATH,
    recompute_scores: bool = True,
) -> dict[str, Any]:
    """
    刪除本篇及全部子孫後續；清除對應 ledger；可選重算人物歷史分。
    不刪父篇。回傳摘要。
    """
    from storage.confirm import recompute_history_scores
    from storage.ledger import load_ledger, save_ledger
    from storage.paths import LEDGER_PATH

    eid = event_id.strip()
    ev = get_event(eid, path)
    if ev is None:
        raise KeyError(f"找不到事件：{eid}")

    to_delete = set(list_subtree_ids(eid, path))
    if not to_delete:
        raise KeyError(f"找不到事件：{eid}")

    rows = [r for r in load_events(path) if r["id"] not in to_delete]
    save_events(rows, path)

    led_path = LEDGER_PATH
    led_before = load_ledger(led_path)
    led_after = [r for r in led_before if r["event_id"] not in to_delete]
    removed_led = len(led_before) - len(led_after)
    if removed_led or len(led_after) != len(led_before):
        save_ledger(led_after, led_path)

    if recompute_scores:
        try:
            recompute_history_scores()
        except Exception:
            # 事件與 ledger 已刪；重算失敗不阻擋刪除結果
            pass

    return {
        "root_id": eid,
        "deleted_ids": sorted(to_delete),
        "deleted_count": len(to_delete),
        "ledger_rows_removed": removed_led,
        "had_children": len(to_delete) > 1,
    }


def delete_draft_event(event_id: str, path: Path = DEFAULT_PATH) -> None:
    """刪除未 confirmed 草稿（含其子孫草稿／篇章）；已 confirmed 根則拒絕。"""
    ev = get_event(event_id, path)
    if ev is None:
        raise KeyError(f"找不到事件：{event_id}")
    if ev.get("status") == "confirmed":
        raise ValueError("不可刪除已落成事件（請用事件刪除）")
    delete_event_tree(event_id, path=path, recompute_scores=True)


CAST_OK_MARK = "cast_ok=1"

# 常見職稱／泛稱：初稿常誤當人名（UI 確認出場時可提示）
LIKELY_ROLE_LABELS = frozenset(
    {
        "主管",
        "老板",
        "老闆",
        "上司",
        "經理",
        "總監",
        "同事",
        "朋友",
        "同學",
        "某人",
        "大家",
        "眾人",
        "路人",
        "客戶",
        "老闆娘",
    }
)


def is_cast_confirmed(ev: dict[str, Any]) -> bool:
    notes = ev.get("notes") or ""
    return CAST_OK_MARK in notes


def needs_cast_confirm(ev: dict[str, Any]) -> bool:
    """
    建立後、追問前須確認出場人名。
    已有問答／成稿／awaiting_generate 的舊草稿不強制回退。
    """
    if ev.get("status") == "confirmed":
        return False
    if is_cast_confirmed(ev):
        return False
    if ev.get("qa_thread"):
        return False
    if ev.get("status") == "awaiting_generate":
        return False
    story = ev.get("story")
    if isinstance(story, dict) and (story.get("body") or "").strip():
        return False
    return True


def mark_cast_confirmed(
    event_id: str, *, path: Path = DEFAULT_PATH
) -> dict[str, Any]:
    row = get_event(event_id, path)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    notes = (row.get("notes") or "").strip()
    if CAST_OK_MARK not in notes:
        row["notes"] = f"{notes}; {CAST_OK_MARK}".strip("; ").strip()
        row["updated_at"] = _now_iso()
        return upsert_event(row, path)
    return row


def resume_step_for_event(ev: dict[str, Any]) -> str:
    """回傳建議繼續的步驟：cast | followup | generate | score | detail。"""
    if ev.get("status") == "confirmed":
        return "detail"
    story = ev.get("story")
    if isinstance(story, dict) and (story.get("body") or "").strip():
        return "score"
    if ev.get("status") == "awaiting_generate":
        return "generate"
    if needs_cast_confirm(ev):
        return "cast"
    return "followup"


def set_ai_draft(
    event_id: str,
    ai_draft: str,
    *,
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    row = get_event(event_id, path)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    row["ai_draft"] = to_traditional(ai_draft)
    row["updated_at"] = _now_iso()
    return upsert_event(row, path)


def append_qa(
    event_id: str,
    role: str,
    content: str,
    *,
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    if role not in QA_ROLES:
        raise ValueError("role 必須是 user 或 assistant")
    row = get_event(event_id, path)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    row["qa_thread"].append(
        {
            "role": role,
            "content": to_traditional(content),
            "at": _now_iso(),
        }
    )
    row["updated_at"] = _now_iso()
    return upsert_event(row, path)


def set_status(
    event_id: str,
    status: str,
    *,
    path: Path = DEFAULT_PATH,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"未知 status：{status}")
    row = get_event(event_id, path)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    row["status"] = status
    if status == "confirmed" and row["confirmed_at"] is None:
        row["confirmed_at"] = _now_iso()
    if status != "confirmed":
        row["confirmed_at"] = None
    row["updated_at"] = _now_iso()
    return upsert_event(row, path)


def seed_demo_events(path: Path = DEFAULT_PATH, *, force: bool = False) -> list[dict[str, Any]]:
    """
    寫入一則示例八卦草稿（含主文、假 AI 初稿、簡短 Q&A）。
    force=True 時覆寫整個 events 檔為 demo 一則。
    """
    if not force and path.is_file() and path.stat().st_size > 0:
        return load_events(path)

    now = _now_iso()
    demo = {
        "id": "evt_demo_tea",
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "confirmed_at": None,
        "user_main_text": DEMO_MAIN_TEXT,
        "ai_draft": DEMO_AI_DRAFT,
        "qa_thread": [
            {
                "role": "assistant",
                "content": "兩人之前有沒有公開合作過類似提案？主管平常偏袒哪邊？",
                "at": now,
            },
            {
                "role": "user",
                "content": "上次季度提案是小美主導；主管通常和稀泥，沒明顯偏誰。",
                "at": now,
            },
        ],
        "story": None,
        "participants": [
            {
                "character_id": "self",
                "is_user": True,
                "event_score": None,
            },
            {
                "character_id": "char_demo_mei",
                "temp_name": "陳美玲",
                "is_user": False,
                "event_score": None,
            },
            {
                "character_id": "char_demo_wang",
                "temp_name": "王大明",
                "is_user": False,
                "event_score": None,
            },
            {
                "character_id": "char_demo_lin",
                "temp_name": "林主管",
                "is_user": False,
                "event_score": None,
            },
        ],
        "score_mean": None,
        "notes": "B2 seed：尚未生成成稿／評分",
    }
    save_events([demo], path)
    return load_events(path)


def read_multiline(prompt: str = "貼上八卦主文。單獨一行只輸入 END 結束：\n") -> str:
    print(prompt)
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _preview(text: str, n: int = 40) -> str:
    one = " ".join(text.split())
    if len(one) <= n:
        return one
    return one[: n - 1] + "…"


def _print_list(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("（無事件）")
        return
    print(f"{'status':<18}  {'qa':>3}  {'id':<20}  preview")
    for r in rows:
        print(
            f"{r['status']:<18}  {len(r['qa_thread']):>3}  {r['id']:<20}  "
            f"{_preview(r['user_main_text'])}"
        )


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m storage.events",
        description="事件草稿讀寫 CLI（Phase B2，不呼叫 AI）",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_PATH,
        help=f"jsonl 路徑（預設 {DEFAULT_PATH}）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="寫入示例八卦草稿")
    p_seed.add_argument("--force", action="store_true", help="覆寫 events 檔")

    p_list = sub.add_parser("list", help="列出事件")
    p_list.add_argument("--status", choices=sorted(STATUSES), default=None)

    p_get = sub.add_parser("get", help="依 id 查看完整 JSON")
    p_get.add_argument("id")

    p_show = sub.add_parser("show", help="可讀摘要（主文／初稿／問答）")
    p_show.add_argument("id")

    sub.add_parser(
        "new",
        help="互動輸入主文（多行，END 結束）→ 存 draft",
    )

    p_add = sub.add_parser("add", help="用參數新增 draft（非互動）")
    p_add.add_argument("--text", required=True, help="主文（可用 \\n）")
    p_add.add_argument("--draft", default="", help="可選 ai_draft")

    p_qa = sub.add_parser("qa", help="追加一則 Q&A")
    p_qa.add_argument("id")
    p_qa.add_argument("role", choices=sorted(QA_ROLES))
    p_qa.add_argument("content")

    p_draft = sub.add_parser("set-draft", help="寫入／覆寫 ai_draft（手動，無 AI）")
    p_draft.add_argument("id")
    p_draft.add_argument("text")

    p_st = sub.add_parser("set-status", help="改 status")
    p_st.add_argument("id")
    p_st.add_argument("status", choices=sorted(STATUSES))

    p_cf = sub.add_parser(
        "confirm",
        help="確認落盤（寫 ledger + 更新歷史分；見 storage.confirm）",
    )
    p_cf.add_argument("id")
    p_cf.add_argument("--no-clamp", action="store_true")

    args = parser.parse_args(argv)
    path: Path = args.path

    if args.cmd == "seed":
        rows = seed_demo_events(path, force=args.force)
        print(f"已寫入／讀取 {len(rows)} 則 → {path}")
        _print_list(rows)
        return 0

    if args.cmd == "list":
        _print_list(list_events(status=args.status, path=path))
        return 0

    if args.cmd == "get":
        row = get_event(args.id, path=path)
        if row is None:
            print(f"找不到：{args.id}", file=sys.stderr)
            return 1
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "show":
        row = get_event(args.id, path=path)
        if row is None:
            print(f"找不到：{args.id}", file=sys.stderr)
            return 1
        print(f"id:     {row['id']}")
        print(f"status: {row['status']}")
        print("\n--- 主文 ---")
        print(row["user_main_text"] or "（空）")
        print("\n--- AI 初稿（可空）---")
        print(row["ai_draft"] or "（尚未）")
        print("\n--- Q&A ---")
        if not row["qa_thread"]:
            print("（無）")
        else:
            for m in row["qa_thread"]:
                print(f"[{m['role']}] {m['content']}")
        print("\n--- participants ---")
        if not row["participants"]:
            print("（無）")
        else:
            for p in row["participants"]:
                name = p.get("temp_name") or p.get("character_id") or "?"
                print(
                    f"  {name}: score={p['event_score']} "
                    f"user={p['is_user']} id={p.get('character_id')}"
                )
        return 0

    if args.cmd == "new":
        text = read_multiline()
        if not text:
            print("沒有內容，未寫入。", file=sys.stderr)
            return 1
        row = create_event(text, path=path)
        print(f"\n已存 draft：{row['id']}")
        print(f"路徑：{path}")
        print("查看：python -m storage.events show " + row["id"])
        return 0

    if args.cmd == "add":
        text = args.text.replace("\\n", "\n")
        row = create_event(text, ai_draft=args.draft, path=path)
        print(json.dumps(row, ensure_ascii=False, indent=2))
        print(f"已寫入 → {path}")
        return 0

    if args.cmd == "qa":
        try:
            row = append_qa(args.id, args.role, args.content, path=path)
        except KeyError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"qa 共 {len(row['qa_thread'])} 則 → {row['id']}")
        return 0

    if args.cmd == "set-draft":
        try:
            row = set_ai_draft(args.id, args.text, path=path)
        except KeyError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"已更新 ai_draft → {row['id']}")
        return 0

    if args.cmd == "set-status":
        try:
            row = set_status(args.id, args.status, path=path)
        except KeyError as e:
            print(e, file=sys.stderr)
            return 1
        print(f"status={row['status']} confirmed_at={row['confirmed_at']} → {row['id']}")
        return 0

    if args.cmd == "confirm":
        from storage.confirm import confirm_event

        try:
            result = confirm_event(args.id, clamp_scores=not args.no_clamp)
        except (KeyError, ValueError) as e:
            print(e, file=sys.stderr)
            return 1
        ev = result["event"]
        print(f"confirmed: {ev['id']}  score_mean={ev['score_mean']}")
        print(f"ledger: {len(result['ledger_rows'])} 筆")
        for i, r in enumerate(result["leaderboard"], 1):
            print(f"  {i}. {r['name']} {r['history_score']}")
        return 0

    parser.error(f"未知命令：{args.cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
