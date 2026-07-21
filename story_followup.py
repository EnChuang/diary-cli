"""
Phase D：追問迴圈 CLI。

- 可新建：主文 → 初稿 → 存 event → 多輪追問（qa_thread）
- 可恢復：--event evt_xxx 從 jsonl 接著問
- 指令：回答 / 跳過 / 補充 / 改前答 / 到此為止
- ready_to_generate 僅建議；結束以使用者「到此為止」為準
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from llm_client import chat_json, load_skill_file
from storage.events import (
    append_qa,
    create_event,
    get_event,
    set_status,
    upsert_event,
)
from story_draft import generate_story_draft, print_draft, read_multiline
from text_zh import to_traditional

def resolve_event_title(
    *,
    title: Optional[str] = None,
    title_deferred: Optional[bool] = None,
    interactive: bool = False,
) -> tuple[str, bool]:
    """
    D22：回傳 (user_title, title_deferred)。
    interactive=True 且未從參數指定時，詢問使用者。
    """
    if title_deferred is True:
        return "", True
    if title is not None and str(title).strip():
        return to_traditional(str(title).strip()), False
    if title_deferred is False and not (title or "").strip():
        # 明確不延後但無標題 → 仍視為延後
        return "", True
    if not interactive:
        # 非互動預設：交給 AI
        return "", True

    print(
        "\n事件標題（直接 Enter 或輸入「交給AI」＝成稿時再取名；"
        "有想法就直接輸入標題）："
    )
    try:
        line = input("> ").strip()
    except EOFError:
        line = ""
    line_t = to_traditional(line)
    key = line_t.replace(" ", "").lower()
    if not line_t or key in {"交給ai", "ai", "不知道", "延後", "跳過標題", "auto", "none"}:
        print("→ 標題延後：成稿時由 AI 依完整故事產生。")
        return "", True
    print(f"→ 採用你的標題：{line_t}")
    return line_t, False

ROOT = Path(__file__).resolve().parent
SKILL_PATH = ROOT / "skill" / "story_followup.md"

STOP_WORDS = frozenset(
    {
        "到此為止",
        "到此为止",
        "停止",
        "結束",
        "结束",
        "done",
        "stop",
        ":stop",
        ":done",
    }
)
SKIP_WORDS = frozenset({"跳過", "跳过", "skip", ":skip"})
UNDO_WORDS = frozenset({"改前答", "撤銷", "撤销", "undo", ":undo"})
SHOW_WORDS = frozenset({"顯示", "显示", "show", ":show", "?"})
HELP_WORDS = frozenset({"help", "幫助", "帮助", ":help", "？"})


def validate_followup_payload(data: dict[str, Any]) -> dict[str, Any]:
    if "question" not in data or "ready_to_generate" not in data or "reason" not in data:
        raise ValueError("追問 JSON 需含 question / ready_to_generate / reason")
    if not isinstance(data["question"], str):
        raise ValueError("question 必須是字串")
    if not isinstance(data["ready_to_generate"], bool):
        raise ValueError("ready_to_generate 必須是 boolean")
    if not isinstance(data["reason"], str):
        raise ValueError("reason 必須是字串")
    return {
        "question": data["question"].strip(),
        "ready_to_generate": data["ready_to_generate"],
        "reason": data["reason"].strip(),
    }


def format_qa_thread(qa_thread: list[dict[str, Any]]) -> str:
    if not qa_thread:
        return "（尚無）"
    lines = []
    for m in qa_thread:
        role = m.get("role", "?")
        content = m.get("content", "")
        lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def build_followup_user_message(
    user_main_text: str,
    ai_draft: str,
    qa_thread: list[dict[str, Any]],
    *,
    parent_memory: str = "",
) -> str:
    mem = f"{parent_memory}\n" if parent_memory else ""
    return (
        f"{mem}"
        "## 主文\n"
        f"{user_main_text.strip()}\n\n"
        "## 初稿\n"
        f"{(ai_draft or '（尚未）').strip()}\n\n"
        "## 既有問答\n"
        f"{format_qa_thread(qa_thread)}\n\n"
        "## 指示\n"
        "請根據以上內容，輸出下一個追問 JSON（question / ready_to_generate / reason）。"
        + ("（此為後續事件，問題聚焦本次新發展，可簡要連到前情。）" if parent_memory else "")
    )


def ask_followup(
    user_main_text: str,
    ai_draft: str,
    qa_thread: list[dict[str, Any]],
    *,
    parent_memory: str = "",
) -> dict[str, Any]:
    skill = load_skill_file(SKILL_PATH)
    raw = chat_json(
        [
            {"role": "system", "content": skill},
            {
                "role": "user",
                "content": build_followup_user_message(
                    user_main_text,
                    ai_draft,
                    qa_thread,
                    parent_memory=parent_memory,
                ),
            },
        ],
        temperature=0.4,
        max_attempts=3,
    )
    return validate_followup_payload(raw)


def replace_last_user_message(
    event_id: str,
    new_content: str,
    *,
    path=None,
) -> dict[str, Any]:
    from storage.events import DEFAULT_PATH

    p = path or DEFAULT_PATH
    row = get_event(event_id, p)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    thread = list(row["qa_thread"])
    for i in range(len(thread) - 1, -1, -1):
        if thread[i].get("role") == "user":
            thread[i] = {
                **thread[i],
                "content": new_content,
            }
            row["qa_thread"] = thread
            return upsert_event(row, p)
    raise ValueError("沒有可修改的使用者回答")


def last_role(qa_thread: list[dict[str, Any]]) -> Optional[str]:
    if not qa_thread:
        return None
    return qa_thread[-1].get("role")


def print_help() -> None:
    print(
        """
指令（單獨一行）：
  直接輸入文字     → 回答目前問題
  跳過 / skip      → 跳過此題
  補充: …          → 自由補充（不綁上一題）
  改前答 / undo    → 修改上一則使用者回答（會再提示輸入新內容）
  到此為止 / done  → 結束追問，status=awaiting_generate
  顯示 / show      → 印出目前問答
  help             → 本說明
""".strip()
    )


def print_thread(event: dict[str, Any]) -> None:
    print(f"\n--- qa_thread（{event['id']} / {event['status']}）---")
    print(format_qa_thread(event.get("qa_thread") or []))


def create_event_from_main(
    main_text: str,
    *,
    skip_draft: bool = False,
    user_title: str = "",
    title_deferred: Optional[bool] = None,
    prompt_title: bool = False,
    parent_event_id: Optional[str] = None,
) -> dict[str, Any]:
    """主文 →（可選 AI 初稿）→ 寫入 draft 事件（D22 標題；可選 D23 後續）。"""
    from storage.sequel import build_memory_package, ensure_sequel_title

    is_sequel = bool(parent_event_id)
    ut, deferred = resolve_event_title(
        title=user_title if user_title else None,
        title_deferred=title_deferred,
        interactive=prompt_title,
    )
    if is_sequel and not deferred and ut:
        ut = ensure_sequel_title(ut, is_sequel=True)

    parent_memory = ""
    if is_sequel:
        parent_memory = build_memory_package(parent_event_id)  # type: ignore[arg-type]

    draft_meta = {
        "title": "",
        "time": "",
        "tags": [],
        "ai_draft": "",
        "suggested_participants": [],
    }
    if not skip_draft:
        print("\n呼叫 ModelArk 產初稿中…")
        draft_meta = generate_story_draft(
            main_text, parent_memory=parent_memory
        )
        print_draft(draft_meta)
        if not deferred and ut:
            print(f"（你的事件標題「{ut}」將在成稿時優先採用；初稿標題僅供參考）")

    participants = []
    for p in draft_meta.get("suggested_participants") or []:
        participants.append(
            {
                "character_id": None,
                "temp_name": p.get("name") or "",
                "is_user": bool(p.get("is_user")),
                "event_score": None,
            }
        )

    notes_parts = []
    if is_sequel:
        notes_parts.append(f"parent={parent_event_id}")
    if not deferred and ut:
        notes_parts.append(f"user_title={ut}")
    elif deferred:
        notes_parts.append("title_deferred=true")
    if draft_meta.get("title"):
        notes_parts.append(f"draft_title={draft_meta['title']}")
    if draft_meta.get("time"):
        notes_parts.append(f"time={draft_meta['time']}")
    if draft_meta.get("tags"):
        notes_parts.append("tags=" + ",".join(draft_meta["tags"]))

    event = create_event(
        main_text,
        ai_draft=draft_meta.get("ai_draft") or "",
        status="draft",
        participants=participants,
        notes="; ".join(notes_parts)[:500] if notes_parts else None,
        user_title=ut,
        title_deferred=deferred,
        parent_event_id=parent_event_id,
    )
    print(f"\n已存事件 draft：{event['id']}")
    if is_sequel:
        print(f"後續 · 父篇：{parent_event_id}")
    if deferred:
        print("標題模式：交給 AI（成稿時）")
    else:
        print(f"標題模式：手填「{ut}」")
    return event


def _looks_complete_question(text: str) -> bool:
    """最後一則像「夠料／已完整」類提示，而非一般追問。"""
    t = (text or "").strip()
    if not t:
        return True
    markers = (
        "已大致夠料",
        "故事已大致完整",
        "故事已完整",
        "已可生成",
        "到此為止",
        "無需再問",
        "沒有更多問題",
    )
    return any(m in t for m in markers)


def ensure_pending_question(event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    若最後一則不是 assistant 問題，則呼叫 AI 並 append。
    回傳 (event, followup_payload)。
    """
    COMPLETE_Q = "故事已大致完整。還有需要補充的嗎？沒有的話可按「到此為止」。"

    qa = event.get("qa_thread") or []
    if last_role(qa) == "assistant":
        # 重用最後一題；推斷是否「已完整」
        last_q = (qa[-1].get("content") or "").strip()
        ready = _looks_complete_question(last_q)
        return event, {
            "question": last_q or COMPLETE_Q,
            "ready_to_generate": ready,
            "reason": "",
        }

    parent_memory = ""
    if event.get("parent_event_id"):
        from storage.sequel import build_memory_package

        parent_memory = build_memory_package(event["parent_event_id"])

    print("\n呼叫 ModelArk 產生下一問…")
    fu = ask_followup(
        event["user_main_text"],
        event.get("ai_draft") or "",
        qa,
        parent_memory=parent_memory,
    )
    # 沒問題／已可生成 → 統一完整提示；並把實際寫入的字回填 fu.question
    if fu.get("ready_to_generate") or not (fu.get("question") or "").strip():
        q = COMPLETE_Q
        fu = {
            **fu,
            "question": q,
            "ready_to_generate": True,
        }
    else:
        q = fu["question"].strip()
        fu = {**fu, "question": q}
    event = append_qa(event["id"], "assistant", q)
    return event, fu


def run_followup_loop(event_id: str, *, max_rounds: int = 20) -> int:
    event = get_event(event_id)
    if event is None:
        print(f"找不到事件：{event_id}", file=sys.stderr)
        return 1
    if event["status"] == "confirmed":
        print("事件已 confirmed，無法再追問。", file=sys.stderr)
        return 1

    print(f"\n=== 追問迴圈（{event_id}）===")
    print("輸入 help 看指令。結束請輸入：到此為止\n")
    print("--- 主文摘要 ---")
    preview = " ".join(event["user_main_text"].split())
    print(preview[:120] + ("…" if len(preview) > 120 else ""))
    if event.get("ai_draft"):
        print("\n--- 初稿摘要 ---")
        dprev = " ".join(event["ai_draft"].split())
        print(dprev[:160] + ("…" if len(dprev) > 160 else ""))

    rounds = 0
    while rounds < max_rounds:
        event = get_event(event_id)
        assert event is not None

        try:
            event, fu = ensure_pending_question(event)
        except Exception as e:
            print("追問失敗：", e, file=sys.stderr)
            print(f"進度已保存在 {event_id}，可稍後：python story_followup.py --event {event_id}")
            return 1

        print("\n----------")
        print(f"AI：{fu['question'] or event['qa_thread'][-1]['content']}")
        if fu.get("reason"):
            print(f"（{fu['reason']}）")
        if fu.get("ready_to_generate"):
            print("【建議】AI 認為已可生成；仍可繼續答，或輸入「到此為止」。")

        try:
            line = to_traditional(input("\n你：").strip())
        except EOFError:
            print(f"\n中斷。已存檔，恢復：python story_followup.py --event {event_id}")
            return 0

        if not line:
            continue

        low = line.lower()
        cmd = line if line in STOP_WORDS | SKIP_WORDS | UNDO_WORDS | SHOW_WORDS | HELP_WORDS else low

        if line in HELP_WORDS or low in HELP_WORDS or line == "?":
            print_help()
            continue

        if line in SHOW_WORDS or low in SHOW_WORDS:
            print_thread(event)
            continue

        if line in STOP_WORDS or low in STOP_WORDS:
            set_status(event_id, "awaiting_generate")
            print(f"\n已結束追問。status=awaiting_generate")
            print(f"查看：python -m storage.events show {event_id}")
            print("（Phase E 才會做「生成」成稿）")
            return 0

        if line in SKIP_WORDS or low in SKIP_WORDS:
            event = append_qa(event_id, "user", "（跳過）")
            rounds += 1
            continue

        if line in UNDO_WORDS or low in UNDO_WORDS:
            try:
                new_ans = to_traditional(input("新的上一則回答：").strip())
            except EOFError:
                continue
            if not new_ans:
                print("未修改。")
                continue
            try:
                replace_last_user_message(event_id, new_ans)
                # 刪掉最後一則 assistant（若在 user 之後還有就不刪；改前答後應重問）
                # 簡化：改完上一 user 後，若 thread 結尾是 user，下一輪 ensure 會再問
                # 若結尾是 assistant（改的是更早的？我們只改最後 user）
                # 若結構是 … user, assistant（未答），改前答改的是更早的 user — OK
                # 若結構是 … assistant, user 剛答完，下一輪會再 AI 問 — 改前答在「剛答完」時：
                # last is user, ensure will call AI — good
                # 若 last is assistant (waiting answer), 改前答改上一個 user，問題仍顯示 — good
                print("已更新上一則回答。")
            except ValueError as e:
                print(e)
            continue

        # 補充: xxx / 補充：xxx
        if line.startswith("補充:") or line.startswith("補充：") or low.startswith(":sup "):
            if low.startswith(":sup "):
                content = line[5:].strip()
            else:
                content = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            if not content:
                print("補充內容為空。")
                continue
            event = append_qa(event_id, "user", f"【補充】{content}")
            rounds += 1
            continue

        # 一般回答
        event = append_qa(event_id, "user", line)
        rounds += 1

    print(f"已達本回合追問上限（{max_rounds}）。可 --event 繼續或「到此為止」。")
    print(f"目前：python story_followup.py --event {event_id}")
    return 0


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python story_followup.py",
        description="八卦追問迴圈（Phase D）",
    )
    parser.add_argument(
        "--event",
        default=None,
        help="從既有 event id 恢復追問",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="主文（新建；非互動）",
    )
    parser.add_argument(
        "--skip-draft",
        action="store_true",
        help="新建時跳過 AI 初稿（只存主文再追問）",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=20,
        help="單次行程最多使用者回答輪數",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="事件標題（手填；與 --title-ai 二選一）",
    )
    parser.add_argument(
        "--title-ai",
        action="store_true",
        help="標題交給 AI 於成稿時產生（D22）",
    )
    args = parser.parse_args(argv)

    if args.event:
        return run_followup_loop(args.event.strip(), max_rounds=args.max_rounds)

    print("=== 八卦追問（Phase D）===")
    print("流程：標題(D22) → 主文 → 初稿 → 多輪追問 →「到此為止」\n")

    if args.text is not None:
        main_text = to_traditional(args.text.replace("\\n", "\n").strip())
        prompt_title = False
        title_kw: dict = {}
        if args.title_ai:
            title_kw = {"title_deferred": True, "user_title": ""}
        elif args.title:
            title_kw = {"user_title": args.title, "title_deferred": False}
        else:
            title_kw = {"title_deferred": True, "user_title": ""}
    else:
        main_text = read_multiline()
        prompt_title = not args.title_ai and not args.title
        title_kw = {}
        if args.title_ai:
            title_kw = {"title_deferred": True, "user_title": "", "prompt_title": False}
        elif args.title:
            title_kw = {
                "user_title": args.title,
                "title_deferred": False,
                "prompt_title": False,
            }
        else:
            title_kw = {"prompt_title": True}

    if not main_text:
        print("沒有主文。", file=sys.stderr)
        return 1

    try:
        event = create_event_from_main(
            main_text, skip_draft=args.skip_draft, **title_kw
        )
    except Exception as e:
        print("建立事件失敗：", e, file=sys.stderr)
        return 1

    return run_followup_loop(event["id"], max_rounds=args.max_rounds)


if __name__ == "__main__":
    raise SystemExit(_cli())
