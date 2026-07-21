"""
Phase E：生成成稿 CLI。

對事件（主文 + 初稿 + qa_thread）呼叫 story_generate Skill →
寫入 event.story + 更新 participants（尚不評分、不 confirm）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from llm_client import chat_json, load_skill_file
from storage.characters import default_display_nick
from storage.events import get_event, list_events, upsert_event
from story_followup import format_qa_thread

ROOT = Path(__file__).resolve().parent
SKILL_PATH = ROOT / "skill" / "story_generate.md"


def validate_generate_payload(data: dict[str, Any]) -> dict[str, Any]:
    if "story" not in data or "participants" not in data:
        raise ValueError("成稿 JSON 需含 story 與 participants")
    story = data["story"]
    if not isinstance(story, dict):
        raise ValueError("story 必須是 object")
    for key in ("title", "time", "tags", "body"):
        if key not in story:
            raise ValueError(f"story 缺少 {key}")
    if not isinstance(story["title"], str):
        raise ValueError("story.title 必須是字串")
    if not isinstance(story["time"], str):
        raise ValueError("story.time 必須是字串")
    if not isinstance(story["body"], str):
        raise ValueError("story.body 必須是字串")
    if not isinstance(story["tags"], list) or not all(
        isinstance(t, str) for t in story["tags"]
    ):
        raise ValueError("story.tags 必須是 string[]")

    parts_in = data["participants"]
    if not isinstance(parts_in, list):
        raise ValueError("participants 必須是 array")
    parts: list[dict[str, Any]] = []
    for p in parts_in:
        if not isinstance(p, dict):
            raise ValueError("participants[] 必須是 object")
        name = p.get("name", "")
        nick = p.get("display_nick", "")
        is_user = p.get("is_user", False)
        if not isinstance(name, str) or not isinstance(nick, str):
            raise ValueError("name / display_nick 必須是字串")
        if not isinstance(is_user, bool):
            raise ValueError("is_user 必須是 boolean")
        name = name.strip()
        nick = nick.strip()
        if is_user:
            nick = nick or "我"
            name = name or "我"
        else:
            if not name:
                raise ValueError("非使用者 participant 需要 name")
            nick = nick or default_display_nick(name)
        parts.append(
            {
                "name": name,
                "display_nick": nick,
                "is_user": is_user,
            }
        )

    return {
        "story": {
            "title": story["title"].strip(),
            "time": story["time"].strip(),
            "tags": [t.strip() for t in story["tags"] if str(t).strip()],
            "body": story["body"].strip(),
        },
        "participants": parts,
    }


def _title_instruction(event: dict[str, Any]) -> str:
    deferred = bool(event.get("title_deferred", True))
    user_title = (event.get("user_title") or "").strip()
    is_sequel = bool(event.get("parent_event_id"))
    sequel_note = (
        "此為後續：標題須有系列感（建議以「續・」開頭）。"
        if is_sequel
        else ""
    )
    if not deferred and user_title:
        return (
            f"使用者已定標題（必須用作 story.title，僅可微調標點）：「{user_title}」"
            f" {sequel_note}"
        )
    return (
        "標題交給 AI：請依完整故事正文與問答自訂 story.title（短標題，繁體）。"
        f" {sequel_note}"
    )


def build_generate_user_message(event: dict[str, Any]) -> str:
    parent_memory = ""
    if event.get("parent_event_id"):
        from storage.sequel import build_memory_package

        parent_memory = build_memory_package(event["parent_event_id"]) + "\n"
    return (
        f"{parent_memory}"
        "## 主文\n"
        f"{(event.get('user_main_text') or '').strip()}\n\n"
        "## 初稿\n"
        f"{(event.get('ai_draft') or '（無）').strip()}\n\n"
        "## 問答\n"
        f"{format_qa_thread(event.get('qa_thread') or [])}\n\n"
        "## 既有參與者提示（可參考，可修正）\n"
        f"{_format_existing_participants(event.get('participants') or [])}\n\n"
        "## 標題指示（D22／D23）\n"
        f"{_title_instruction(event)}\n\n"
        "## 指示\n"
        "請輸出成稿 JSON（story + participants；不要打分）。"
        "若為後續：正文僅銜接+新發展，勿重貼父篇全文。"
    )


def apply_title_policy(
    event: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    """手填標題且未延後 → 強制 story.title；後續補「續・」前綴。"""
    from storage.sequel import ensure_sequel_title

    out = {
        "story": dict(payload["story"]),
        "participants": list(payload["participants"]),
    }
    deferred = bool(event.get("title_deferred", True))
    user_title = (event.get("user_title") or "").strip()
    is_sequel = bool(event.get("parent_event_id"))
    if not deferred and user_title:
        out["story"]["title"] = user_title
    title = out["story"].get("title") or ""
    out["story"]["title"] = ensure_sequel_title(title, is_sequel=is_sequel)
    return out


def _format_existing_participants(participants: list[dict[str, Any]]) -> str:
    if not participants:
        return "（無）"
    lines = []
    for p in participants:
        name = p.get("temp_name") or p.get("character_id") or "?"
        lines.append(
            f"- {name}  is_user={p.get('is_user')}  id={p.get('character_id')}"
        )
    return "\n".join(lines)


def generate_story(event: dict[str, Any]) -> dict[str, Any]:
    skill = load_skill_file(SKILL_PATH)
    raw = chat_json(
        [
            {"role": "system", "content": skill},
            {"role": "user", "content": build_generate_user_message(event)},
        ],
        temperature=0.45,
        max_attempts=3,
    )
    payload = validate_generate_payload(raw)
    return apply_title_policy(event, payload)


def participants_to_event_rows(
    parts: list[dict[str, Any]],
    existing: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, Any]]:
    """成稿 participants → 事件 participants（尚無 event_score）。"""
    existing = existing or []
    # 用 temp_name / name 對一下既有 character_id
    by_name: dict[str, dict[str, Any]] = {}
    for e in existing:
        key = (e.get("temp_name") or e.get("character_id") or "").strip()
        if key:
            by_name[key] = e

    rows: list[dict[str, Any]] = []
    for p in parts:
        name = p["name"]
        prev = by_name.get(name) or by_name.get(p["display_nick"])
        cid = prev.get("character_id") if prev else None
        if p["is_user"]:
            cid = "self"
        row: dict[str, Any] = {
            "character_id": cid,
            "temp_name": name if not p["is_user"] else p.get("name") or "我",
            "is_user": p["is_user"],
            "event_score": None,
        }
        # 暱稱暫放 notes 式欄位不在 schema；用 score_reason 存 nick 會混淆
        # schema 無 display_nick on participant — 寫入 temp_name 用建檔名，
        # display_nick 可拼在 score_reason 前綴？較髒。
        # 契約 participants 無 display_nick；成稿 body 已用暱稱即可。
        # 可選：score_reason 留空直到 F。
        rows.append(row)
    return rows


def apply_generate_to_event(
    event_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = get_event(event_id)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    if row["status"] == "confirmed":
        raise ValueError("事件已 confirmed，不可覆寫成稿（避免與 ledger 不一致）")

    row["story"] = payload["story"]
    row["participants"] = participants_to_event_rows(
        payload["participants"], row.get("participants") or []
    )
    # 生成後維持／設為 awaiting_generate（待 F 評分確認）
    if row["status"] == "draft":
        row["status"] = "awaiting_generate"
    row["confirmed_at"] = None
    return upsert_event(row)


def print_story(
    payload: dict[str, Any],
    *,
    title_note: str = "",
) -> None:
    s = payload["story"]
    print("\n========== 成稿（尚未確認評分） ==========")
    print(f"標題：{s['title']}" + (f"  {title_note}" if title_note else ""))
    print(f"時間：{s['time'] or '（未注明）'}")
    print(f"標籤：{', '.join(s['tags']) if s['tags'] else '（無）'}")
    print("\n--- 正文 ---")
    print(s["body"])
    print("\n--- 登場 ---")
    for p in payload["participants"]:
        flag = "使用者" if p["is_user"] else "可評分"
        print(f"  · {p['name']} → {p['display_nick']}  ({flag})")
    print("\n--- JSON ---")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def pick_event_id() -> Optional[str]:
    candidates = [
        e
        for e in list_events()
        if e["status"] in ("draft", "awaiting_generate")
    ]
    if not candidates:
        print("沒有 draft / awaiting_generate 事件。", file=sys.stderr)
        return None
    print("可生成的事件：")
    for i, e in enumerate(candidates, 1):
        preview = " ".join((e.get("user_main_text") or "").split())[:40]
        has_story = "有成稿" if e.get("story") else "未成稿"
        print(f"  {i}. {e['id']}  [{e['status']}/{has_story}]  {preview}…")
    try:
        raw = input("選編號或貼 event id：").strip()
    except EOFError:
        return None
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]["id"]
        print("編號超出範圍。", file=sys.stderr)
        return None
    return raw


def run_for_event(event_id: str, *, save: bool = True, force: bool = False) -> int:
    event = get_event(event_id)
    if event is None:
        print(f"找不到：{event_id}", file=sys.stderr)
        return 1
    if event["status"] == "confirmed":
        print("已 confirmed，跳過。", file=sys.stderr)
        return 1
    if event.get("story") and not force:
        print("此事件已有成稿。要重產請加 --force")
        print_story(
            {
                "story": event["story"],
                "participants": [
                    {
                        "name": p.get("temp_name") or p.get("character_id") or "?",
                        "display_nick": p.get("temp_name") or "?",
                        "is_user": p.get("is_user", False),
                    }
                    for p in (event.get("participants") or [])
                ],
            }
        )
        return 0

    if not (event.get("user_main_text") or "").strip():
        print("主文為空，無法生成。", file=sys.stderr)
        return 1

    print(f"\n對 {event_id} 呼叫 ModelArk 生成成稿…")
    if event.get("title_deferred"):
        print("標題模式：交給 AI")
    elif event.get("user_title"):
        print(f"標題模式：手填「{event['user_title']}」（成稿優先採用）")
    try:
        payload = generate_story(event)
    except Exception as e:
        print("生成失敗：", e, file=sys.stderr)
        return 1

    note = ""
    if not event.get("title_deferred") and event.get("user_title"):
        note = "（已套用你的標題）"
    elif event.get("title_deferred"):
        note = "（AI 生成）"
    print_story(payload, title_note=note)

    if not save:
        print("\n（未寫入；預設會詢問保存）")
        return 0

    try:
        ans = input("\n確認寫入事件成稿（仍不評分／不入榜）？[y/N] ").strip().lower()
    except EOFError:
        ans = "n"
    if ans != "y":
        print("已取消，未寫入。")
        return 0

    saved = apply_generate_to_event(event_id, payload)
    print(f"已寫入 story → {saved['id']}  status={saved['status']}")
    print(f"查看：python -m storage.events show {saved['id']}")
    print("下一步 Phase F：評分與確認落盤")
    return 0


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python story_generate.py",
        description="八卦成稿（Phase E）：主文+Q&A → 故事（暱稱），不評分",
    )
    parser.add_argument("--event", default=None, help="事件 id")
    parser.add_argument(
        "--force",
        action="store_true",
        help="已有成稿也重新生成",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="生成後直接寫入，不问 y/N",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="只印 JSON、不寫入",
    )
    args = parser.parse_args(argv)

    event_id = args.event
    if not event_id:
        print("=== 八卦成稿（Phase E）===\n")
        event_id = pick_event_id()
        if not event_id:
            return 1

    if args.json_only:
        event = get_event(event_id)
        if event is None:
            print(f"找不到：{event_id}", file=sys.stderr)
            return 1
        print("呼叫 ModelArk…", file=sys.stderr)
        try:
            payload = generate_story(event)
        except Exception as e:
            print(e, file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.yes:
        event = get_event(event_id)
        if event is None:
            print(f"找不到：{event_id}", file=sys.stderr)
            return 1
        if event["status"] == "confirmed":
            print("已 confirmed。", file=sys.stderr)
            return 1
        if event.get("story") and not args.force:
            print("已有成稿，加 --force 重產。", file=sys.stderr)
            return 1
        print(f"生成並寫入 {event_id}…")
        try:
            payload = generate_story(event)
            saved = apply_generate_to_event(event_id, payload)
        except Exception as e:
            print("失敗：", e, file=sys.stderr)
            return 1
        print_story(payload)
        print(f"已寫入 → {saved['id']}")
        return 0

    return run_for_event(event_id, save=True, force=args.force)


if __name__ == "__main__":
    raise SystemExit(_cli())
