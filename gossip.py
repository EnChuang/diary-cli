"""
野史錄 · 完整主路徑（輸入測試用）

  主文 → 初稿 → 追問 → 成稿 → 評分落盤 → 歷史榜

用法：
  python gossip.py              # 全程互動
  python gossip.py --quick      # 貼主文後，用內建示範回答自動走完（少互動）
  python gossip.py --event ID   # 從既有事件接著做（未成稿→生成，未確認→評分）
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from storage.events import append_qa, get_event, set_status
from story_followup import create_event_from_main, run_followup_loop
from story_draft import read_multiline
from story_generate import apply_generate_to_event, generate_story, print_story
from story_score import (
    apply_ai_scores_to_event,
    print_scores,
    run_score_flow,
    save_participants,
    suggest_scores,
)
from board import cmd_rank, cmd_event


# 與說明文件一致的示範主文
SAMPLE_MAIN = """今天午餐時陳美玲跟王大明在茶水間吵起來。
小美說上次提案是她做的，大明卻在會上搶功。
林主管經過只說「私下解決」，兩邊更不爽。
我在旁邊不敢插話，只覺得這週例會氣氛會很糟。"""

# --quick 用的示範問答（不呼叫追問 AI 多輪）
QUICK_QA = [
    (
        "assistant",
        "當時兩人有沒有講到具體哪一次提案？大明怎麼回應的？",
    ),
    (
        "user",
        "是上季客戶提案。大明說功勞是大家的，小美氣到拍桌子。",
    ),
    (
        "assistant",
        "林主管說完之後現場氣氛如何？有沒有其他人在場？",
    ),
    (
        "user",
        "主管走了之後兩人冷戰，茶水間只剩我和一個實習生裝忙。",
    ),
]


def print_sample() -> None:
    print("========== 建議測試主文（可整段複製） ==========")
    print(SAMPLE_MAIN)
    print("END")
    print("================================================")
    print("貼完後請單獨一行輸入 END\n")


def step_generate(event_id: str, *, yes: bool) -> int:
    event = get_event(event_id)
    if event is None:
        print(f"找不到 {event_id}", file=sys.stderr)
        return 1
    if event.get("story") and not yes:
        print("已有成稿，略過生成。")
        return 0
    if event.get("story") and yes:
        print("已有成稿，--yes 下略過重產。")
        return 0

    print("\n>>> [成稿] 呼叫 ModelArk…")
    try:
        payload = generate_story(event)
    except Exception as e:
        print("成稿失敗：", e, file=sys.stderr)
        return 1
    note = ""
    if not event.get("title_deferred") and event.get("user_title"):
        note = "（已套用你的標題）"
    elif event.get("title_deferred"):
        note = "（AI 生成標題）"
    print_story(payload, title_note=note)
    if not yes:
        try:
            ans = input("\n寫入成稿？[Y/n] ").strip().lower()
        except EOFError:
            ans = "y"
        if ans in ("n", "no"):
            print("未寫入成稿。")
            return 1
    apply_generate_to_event(event_id, payload)
    print(f"成稿已寫入 {event_id}")
    return 0


def step_score(event_id: str, *, yes: bool) -> int:
    if yes:
        return run_score_flow(event_id, skip_ai=False, yes=True, no_adjust=True)
    return run_score_flow(event_id, skip_ai=False, yes=False, no_adjust=False)


def run_quick(
    main_text: str,
    *,
    user_title: str = "",
    title_deferred: bool = True,
) -> int:
    """主文 → 初稿 → 寫入示範 Q&A → 成稿 → 評分落盤 → 榜。"""
    print("=== 快速模式（示範問答，少互動）===\n")
    try:
        event = create_event_from_main(
            main_text,
            skip_draft=False,
            user_title=user_title,
            title_deferred=title_deferred,
            prompt_title=False,
        )
    except Exception as e:
        print("初稿／建事件失敗：", e, file=sys.stderr)
        return 1
    eid = event["id"]
    print(f"\n寫入示範問答 → {eid}")
    for role, content in QUICK_QA:
        append_qa(eid, role, content)
    set_status(eid, "awaiting_generate")

    if step_generate(eid, yes=True) != 0:
        return 1
    if step_score(eid, yes=True) != 0:
        return 1

    print("\n>>> [榜單]")
    cmd_rank()
    print("\n>>> [本事件]")
    cmd_event(eid)
    print(f"\n完成。event_id = {eid}")
    print("之後可：python board.py char 小美")
    return 0


def run_full_interactive(
    *,
    user_title: str = "",
    title_deferred: Optional[bool] = None,
    prompt_title: bool = True,
) -> int:
    print("=== 野史錄 · 完整流程 ===")
    print("步驟：標題 → 主文 → 初稿 → 追問 → 成稿 → 評分 → 榜單\n")
    print_sample()

    main_text = read_multiline("請貼上主文（可直接貼示範文）。單獨一行 END 結束：\n")
    if not main_text:
        print("沒有主文。", file=sys.stderr)
        return 1

    try:
        event = create_event_from_main(
            main_text,
            skip_draft=False,
            user_title=user_title,
            title_deferred=title_deferred,
            prompt_title=prompt_title,
        )
    except Exception as e:
        print("初稿失敗：", e, file=sys.stderr)
        return 1
    eid = event["id"]

    print("\n>>> [追問] 回答問題；結束時輸入：到此為止")
    print("（也可輸入 跳過 / 補充: … / help）\n")
    rc = run_followup_loop(eid)
    if rc != 0:
        print(f"追問中斷。可恢復：python gossip.py --event {eid}")
        return rc

    event = get_event(eid)
    if event is None or event.get("status") == "confirmed":
        return 0

    if step_generate(eid, yes=False) != 0:
        print(f"可稍後：python story_generate.py --event {eid}")
        return 1

    if step_score(eid, yes=False) != 0:
        print(f"可稍後：python story_score.py --event {eid}")
        return 1

    print("\n>>> [榜單]")
    cmd_rank()
    print("\n>>> [本事件摘要]")
    cmd_event(eid)
    print(f"\n全部完成。event_id = {eid}")
    return 0


def resume_event(event_id: str, *, yes: bool) -> int:
    event = get_event(event_id)
    if event is None:
        print(f"找不到：{event_id}", file=sys.stderr)
        return 1
    if event["status"] == "confirmed":
        print("已 confirmed。查看：")
        cmd_event(event_id)
        cmd_rank()
        return 0

    if event["status"] == "draft":
        print("狀態 draft → 先繼續追問（到此為止 後會往下）")
        rc = run_followup_loop(event_id)
        if rc != 0:
            return rc
        event = get_event(event_id)

    if not event.get("story"):
        if step_generate(event_id, yes=yes) != 0:
            return 1
    else:
        print("已有成稿。")

    event = get_event(event_id)
    if event and event["status"] != "confirmed":
        if step_score(event_id, yes=yes) != 0:
            return 1

    cmd_rank()
    cmd_event(event_id)
    return 0


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python gossip.py",
        description="野史錄完整流程（輸入測試入口）",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="貼主文後用示範問答自動成稿+評分落盤",
    )
    parser.add_argument("--event", default=None, help="從既有事件恢復")
    parser.add_argument(
        "--text",
        default=None,
        help="主文（配合 --quick 可非互動）",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="只印建議測試主文",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="恢復流程時少詢問",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="事件標題（手填；成稿時優先採用）",
    )
    parser.add_argument(
        "--title-ai",
        action="store_true",
        help="標題交給 AI 於成稿時產生（預設於 --quick）",
    )
    args = parser.parse_args(argv)

    if args.sample:
        print_sample()
        return 0

    if args.event:
        return resume_event(args.event, yes=args.yes or args.quick)

    # 標題參數
    if args.title_ai:
        t_title, t_def, t_prompt = "", True, False
    elif args.title:
        t_title, t_def, t_prompt = args.title, False, False
    else:
        t_title, t_def, t_prompt = "", None, True  # 互動詢問

    if args.quick:
        if args.text:
            main = args.text.replace("\\n", "\n").strip()
        else:
            print_sample()
            main = read_multiline("貼主文，END 結束（直接 Enter 用示範文請先貼上）：\n")
            if not main:
                print("改用內建示範主文。")
                main = SAMPLE_MAIN
        # quick 未指定標題 → 預設交 AI
        if t_prompt:
            t_title, t_def = "", True
        return run_quick(main, user_title=t_title or "", title_deferred=bool(t_def))

    return run_full_interactive(
        user_title=t_title or "",
        title_deferred=t_def if not t_prompt else None,
        prompt_title=t_prompt,
    )


if __name__ == "__main__":
    raise SystemExit(_cli())
