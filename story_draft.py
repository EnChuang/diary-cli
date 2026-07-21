"""
Phase C：單輪故事／八卦初稿 CLI。

主文 → ModelArk + skill/story_draft.md → 顯示 JSON 初稿（預設不落盤）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from llm_client import chat_json, load_skill_file
from storage.events import create_event, set_ai_draft
from text_zh import to_traditional

ROOT = Path(__file__).resolve().parent
SKILL_PATH = ROOT / "skill" / "story_draft.md"

REQUIRED_KEYS = ("title", "time", "tags", "ai_draft", "suggested_participants")


def validate_draft_payload(data: dict[str, Any]) -> dict[str, Any]:
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"初稿 JSON 缺欄位：{', '.join(missing)}")
    if not isinstance(data["title"], str):
        raise ValueError("title 必須是字串")
    if not isinstance(data["time"], str):
        raise ValueError("time 必須是字串")
    if not isinstance(data["ai_draft"], str):
        raise ValueError("ai_draft 必須是字串")
    if not isinstance(data["tags"], list) or not all(
        isinstance(t, str) for t in data["tags"]
    ):
        raise ValueError("tags 必須是 string[]")
    parts = data["suggested_participants"]
    if not isinstance(parts, list):
        raise ValueError("suggested_participants 必須是 array")
    clean_parts = []
    for p in parts:
        if not isinstance(p, dict):
            raise ValueError("suggested_participants[] 必須是 object")
        name = p.get("name", "")
        if not isinstance(name, str):
            raise ValueError("participant.name 必須是字串")
        is_user = p.get("is_user", False)
        if not isinstance(is_user, bool):
            raise ValueError("participant.is_user 必須是 boolean")
        clean_parts.append({"name": name.strip(), "is_user": is_user})
    return {
        "title": data["title"].strip(),
        "time": data["time"].strip(),
        "tags": [t.strip() for t in data["tags"] if str(t).strip()],
        "ai_draft": data["ai_draft"].strip(),
        "suggested_participants": clean_parts,
    }


def generate_story_draft(
    user_main_text: str,
    *,
    parent_memory: str = "",
) -> dict[str, Any]:
    skill = load_skill_file(SKILL_PATH)
    user_content = user_main_text
    if parent_memory:
        user_content = (
            f"{parent_memory}\n"
            f"## 本次後續主文（使用者新輸入）\n{user_main_text}\n\n"
            f"請依回憶包與本次主文產出初稿 JSON；正文勿重貼父篇全文。"
        )
    raw = chat_json(
        [
            {"role": "system", "content": skill},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,
        max_attempts=3,
    )
    return validate_draft_payload(raw)


def read_multiline(prompt: str = "貼上八卦／事件主文。單獨一行只輸入 END 結束：\n") -> str:
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
    return to_traditional("\n".join(lines).strip())


def print_draft(draft: dict[str, Any]) -> None:
    print("\n========== 初稿（尚未寫入） ==========")
    print(f"標題：{draft['title']}")
    print(f"時間：{draft['time'] or '（未注明）'}")
    print(f"標籤：{', '.join(draft['tags']) if draft['tags'] else '（無）'}")
    print("\n--- 正文 ---")
    print(draft["ai_draft"])
    print("\n--- 建議登場 ---")
    if not draft["suggested_participants"]:
        print("（無）")
    else:
        for p in draft["suggested_participants"]:
            flag = "使用者" if p["is_user"] else "可評分"
            print(f"  · {p['name']}  ({flag})")
    print("\n--- 原始 JSON ---")
    print(json.dumps(draft, ensure_ascii=False, indent=2))


def run_interactive(*, save: bool = False) -> int:
    print("=== 八卦初稿 CLI（Phase C）===")
    print("Skill: story_draft.md + ModelArk；預設只顯示、不落盤\n")

    main_text = read_multiline()
    if not main_text:
        print("沒有內容，結束。", file=sys.stderr)
        return 1

    print("\n呼叫 ModelArk 產初稿中…")
    try:
        draft = generate_story_draft(main_text)
    except Exception as e:
        print("初稿失敗：", e, file=sys.stderr)
        print("未寫入任何事件。", file=sys.stderr)
        return 1

    print_draft(draft)

    if not save:
        print("\n（Phase C 預設不落盤。若要存成事件 draft，加參數 --save）")
        return 0

    ans = input("\n確認寫入 events.jsonl 為 draft？[y/N] ").strip().lower()
    if ans != "y":
        print("已取消，未寫入。")
        return 0

    notes = f"title={draft['title']}; time={draft['time']}; tags={','.join(draft['tags'])}"
    event = create_event(
        main_text,
        ai_draft=draft["ai_draft"],
        status="draft",
        notes=notes[:500],
    )
    # create_event 已帶 ai_draft；再 set 一次無妨
    set_ai_draft(event["id"], draft["ai_draft"])
    print(f"已寫入事件 draft：{event['id']}")
    print(f"查看：python -m storage.events show {event['id']}")
    return 0


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python story_draft.py",
        description="八卦初稿（Phase C）：主文 → AI 草稿，預設不落盤",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="主文（非互動）；也可用 stdin / 互動 END",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="顯示後可確認寫入 data/events.jsonl（可選，非 C 必做）",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="只印 JSON（方便管線）",
    )
    args = parser.parse_args(argv)

    if args.text is not None:
        main_text = args.text.replace("\\n", "\n").strip()
    elif not sys.stdin.isatty():
        main_text = sys.stdin.read().strip()
        # 允許檔尾 END
        if main_text.endswith("\nEND"):
            main_text = main_text[: -len("\nEND")].strip()
        elif main_text.endswith("END"):
            main_text = main_text[: -len("END")].rstrip()
    else:
        return run_interactive(save=args.save)

    if not main_text:
        print("沒有內容。", file=sys.stderr)
        return 1

    print("呼叫 ModelArk 產初稿中…", file=sys.stderr)
    try:
        draft = generate_story_draft(main_text)
    except Exception as e:
        print("初稿失敗：", e, file=sys.stderr)
        return 1

    if args.json_only:
        print(json.dumps(draft, ensure_ascii=False, indent=2))
    else:
        print_draft(draft)

    if args.save:
        ans = input("\n確認寫入 events.jsonl 為 draft？[y/N] ").strip().lower()
        if ans == "y":
            notes = f"title={draft['title']}; time={draft['time']}"
            event = create_event(
                main_text,
                ai_draft=draft["ai_draft"],
                status="draft",
                notes=notes[:500],
            )
            print(f"已寫入：{event['id']}", file=sys.stderr)
        else:
            print("未寫入。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
