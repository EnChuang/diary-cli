"""
事件確認落盤（Phase B3）。

流程：
1. 檢查事件存在且尚未 confirmed（或允許 idempotent 拒絕重入）
2. 參與者分數通過平均±10（可 clamp）
3. 缺 character_id 時用 temp_name 建檔
4. 寫 ledger（非使用者）
5. 事件 status=confirmed + score_mean + story（若有）
6. 依 ledger 重算各角 history_score
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

from storage import characters as char_mod
from storage import events as evt_mod
from storage import ledger as led_mod
from storage.paths import CHARACTERS_PATH, EVENTS_PATH, LEDGER_PATH
from storage.scoring import apply_scores_to_participants, scored_participants
from text_zh import to_traditional


def recompute_history_scores(
    *,
    characters_path: Path = CHARACTERS_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> list[dict[str, Any]]:
    """以 ledger 加總覆寫每位非使用者 history_score；使用者維持 0（或不寫 ledger）。"""
    totals = led_mod.sum_deltas_by_character(ledger_path)
    rows = char_mod.load_characters(characters_path)
    now_touched = False
    for row in rows:
        if row["is_user"]:
            if row["history_score"] != 0:
                row["history_score"] = 0
                now_touched = True
            continue
        new_score = int(totals.get(row["id"], 0))
        if row["history_score"] != new_score:
            row["history_score"] = new_score
            now_touched = True
    if rows:
        char_mod.save_characters(rows, characters_path)
    return char_mod.load_characters(characters_path)


def _ensure_participant_character(
    p: dict[str, Any],
    *,
    characters_path: Path,
) -> dict[str, Any]:
    """回傳更新後的 participant（必有 character_id）。"""
    out = dict(p)
    if out.get("is_user"):
        out["character_id"] = char_mod.USER_ID
        char_mod.ensure_user(path=characters_path)
        out["event_score"] = None
        return out

    cid = out.get("character_id")
    temp = to_traditional((out.get("temp_name") or "").strip())
    if temp:
        out["temp_name"] = temp
    if cid:
        existing = char_mod.get_character(cid, characters_path)
        if existing is None:
            # id 不存在：先試同名，再建立
            name = temp or cid
            by_name = char_mod.find_character_by_name(name, characters_path)
            if by_name is not None:
                out["character_id"] = by_name["id"]
                return out
            char_mod.create_character(
                name,
                character_id=cid,
                history_score=0,
                path=characters_path,
                reuse_by_name=False,
            )
        return out

    if not temp:
        raise ValueError("非使用者 participant 需要 character_id 或 temp_name")
    # 優先重用同名角色，避免榜上重複
    existing_name = char_mod.find_character_by_name(temp, characters_path)
    if existing_name is not None:
        out["character_id"] = existing_name["id"]
        return out
    created = char_mod.create_character(
        temp, history_score=0, path=characters_path, reuse_by_name=True
    )
    out["character_id"] = created["id"]
    return out


def confirm_event(
    event_id: str,
    *,
    clamp_scores: bool = True,
    require_scores: bool = True,
    story: Optional[dict[str, Any]] = None,
    events_path: Path = EVENTS_PATH,
    characters_path: Path = CHARACTERS_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> dict[str, Any]:
    """
    確認事件並落盤。回傳 {event, ledger_rows, leaderboard}。
    """
    row = evt_mod.get_event(event_id, events_path)
    if row is None:
        raise KeyError(f"找不到事件：{event_id}")
    if row["status"] == "confirmed":
        existing = led_mod.list_for_event(event_id, ledger_path)
        if existing:
            raise ValueError(f"事件已 confirmed 且已有 ledger：{event_id}")
        # status 已 confirmed 但無 ledger：允許補寫

    # 解析並建檔角色
    participants: list[dict[str, Any]] = []
    for p in row["participants"]:
        participants.append(
            _ensure_participant_character(p, characters_path=characters_path)
        )

    participants, mu, mean_i = apply_scores_to_participants(
        participants, clamp=clamp_scores
    )
    scored = scored_participants(participants)
    if require_scores and not scored:
        raise ValueError("確認前至少一位非使用者需有 event_score")

    for p in scored:
        if not p.get("character_id"):
            raise ValueError("被評分角色缺少 character_id")

    now = evt_mod._now_iso()
    if story is not None:
        row["story"] = story
    elif row.get("story") is None:
        # 允許無成稿（B 階段假資料可補最小 story）
        row["story"] = {
            "title": "（未生成標題）",
            "time": "",
            "tags": [],
            "body": row.get("ai_draft") or row.get("user_main_text") or "",
        }

    row["participants"] = participants
    row["score_mean"] = float(mean_i) if mean_i is not None else None
    row["status"] = "confirmed"
    row["confirmed_at"] = now
    row["updated_at"] = now
    saved = evt_mod.upsert_event(row, events_path)

    ledger_rows: list[dict[str, Any]] = []
    for p in scored:
        ledger_rows.append(
            led_mod.make_ledger_row(
                event_id=saved["id"],
                character_id=p["character_id"],
                delta=int(p["event_score"]),
                at=now,
            )
        )
    if ledger_rows:
        led_mod.append_ledger_rows(ledger_rows, ledger_path)

    recompute_history_scores(
        characters_path=characters_path, ledger_path=ledger_path
    )

    return {
        "event": evt_mod.get_event(saved["id"], events_path),
        "ledger_rows": ledger_rows,
        "leaderboard": char_mod.leaderboard(characters_path),
    }


def seed_phase_b(
    *,
    force: bool = True,
    characters_path: Path = CHARACTERS_PATH,
    events_path: Path = EVENTS_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> dict[str, Any]:
    """
    端到端假資料：人物（歷史分由 ledger 決定）→ 待確認事件（含分）→ confirm → 榜。
    force=True 時覆寫 characters/events/ledger。
    """
    if force:
        characters_path.parent.mkdir(parents=True, exist_ok=True)
        # 人物初始 history 全 0，確認後由 ledger 寫入
        now = char_mod._now_iso()
        demo_chars = [
            {
                "id": char_mod.USER_ID,
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
                "history_score": 0,
                "is_user": False,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "char_demo_wang",
                "name": "王大明",
                "display_nick": "小明",
                "history_score": 0,
                "is_user": False,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "char_demo_lin",
                "name": "林主管",
                "display_nick": "小主",
                "history_score": 0,
                "is_user": False,
                "created_at": now,
                "updated_at": now,
            },
        ]
        char_mod.save_characters(demo_chars, characters_path)
        if ledger_path.is_file():
            ledger_path.unlink()
        # 寫待確認事件（含合法分數）
        now_e = evt_mod._now_iso()
        event = {
            "id": "evt_demo_tea",
            "status": "awaiting_generate",
            "created_at": now_e,
            "updated_at": now_e,
            "confirmed_at": None,
            "user_main_text": evt_mod.DEMO_MAIN_TEXT,
            "ai_draft": evt_mod.DEMO_AI_DRAFT,
            "qa_thread": [
                {
                    "role": "assistant",
                    "content": "兩人之前有沒有公開合作過類似提案？主管平常偏袒哪邊？",
                    "at": now_e,
                },
                {
                    "role": "user",
                    "content": "上次季度提案是小美主導；主管通常和稀泥，沒明顯偏誰。",
                    "at": now_e,
                },
            ],
            "story": {
                "title": "茶水間搶功風波",
                "time": "某日午餐",
                "tags": ["職場", "搶功", "茶水間"],
                "body": (
                    "午餐時段，小美與小明在茶水間爭執：提案功勞歸誰。"
                    "小主路過只丟下一句「私下解決」。一旁的我沒插話。"
                ),
            },
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
                    "event_score": 15,
                    "score_reason": "被搶功，敘述偏同情",
                },
                {
                    "character_id": "char_demo_wang",
                    "temp_name": "王大明",
                    "is_user": False,
                    # 與 15、5 同場：μ=5，合法約 [-5,15]，-5 恰在下界
                    "event_score": -5,
                    "score_reason": "會上居功",
                },
                {
                    "character_id": "char_demo_lin",
                    "temp_name": "林主管",
                    "is_user": False,
                    "event_score": 5,
                    "score_reason": "和稀泥但未公開幫兇",
                },
            ],
            "score_mean": None,
            "notes": "Phase B seed：可 confirm",
        }
        evt_mod.save_events([event], events_path)
    else:
        char_mod.seed_demo_characters(characters_path, force=False)
        evt_mod.seed_demo_events(events_path, force=False)

    result = confirm_event(
        "evt_demo_tea",
        events_path=events_path,
        characters_path=characters_path,
        ledger_path=ledger_path,
    )
    return result


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m storage.confirm",
        description="確認落盤 / Phase B 端到端 seed（不呼叫 AI）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_c = sub.add_parser("event", help="確認指定事件")
    p_c.add_argument("event_id")
    p_c.add_argument("--no-clamp", action="store_true", help="不合法則直接失敗")

    p_s = sub.add_parser(
        "seed-b",
        help="覆寫人物/事件/ledger 假資料並 confirm",
    )
    p_s.add_argument(
        "--no-force",
        action="store_true",
        help="不覆寫既有（僅當 evt_demo_tea 可確認時）",
    )

    sub.add_parser("recompute", help="依 ledger 重算 history_score")
    sub.add_parser("rank", help="印歷史榜")
    sub.add_parser("status", help="各資料檔列數（B4 並存檢查）")

    args = parser.parse_args(argv)

    if args.cmd == "event":
        try:
            result = confirm_event(args.event_id, clamp_scores=not args.no_clamp)
        except (KeyError, ValueError) as e:
            print(e, file=sys.stderr)
            return 1
        ev = result["event"]
        print(f"confirmed: {ev['id']}  score_mean={ev['score_mean']}")
        print(f"ledger: {len(result['ledger_rows'])} 筆")
        print("--- 歷史榜 ---")
        for i, r in enumerate(result["leaderboard"], 1):
            print(f"{i}. {r['name']} ({r['display_nick']}) {r['history_score']}")
        return 0

    if args.cmd == "seed-b":
        result = seed_phase_b(force=not args.no_force)
        ev = result["event"]
        print("Phase B seed 完成")
        print(f"event: {ev['id']} status={ev['status']} mean={ev['score_mean']}")
        print(f"ledger: {len(result['ledger_rows'])} 筆 → {LEDGER_PATH}")
        print("--- 歷史榜 ---")
        for i, r in enumerate(result["leaderboard"], 1):
            print(
                f"{i}. {r['name']:<8} {r['display_nick']:<6} "
                f"{r['history_score']:>4}  {r['id']}"
            )
        print("\n查看：")
        print("  python -m storage.events show evt_demo_tea")
        print("  python -m storage.ledger list")
        print("  python -m storage.characters rank")
        return 0

    if args.cmd == "recompute":
        rows = recompute_history_scores()
        print(f"已重算 {len(rows)} 人")
        for r in char_mod.leaderboard():
            print(f"  {r['name']}: {r['history_score']}")
        return 0

    if args.cmd == "rank":
        for i, r in enumerate(char_mod.leaderboard(), 1):
            print(f"{i}. {r['name']} {r['history_score']}")
        return 0

    if args.cmd == "status":
        from storage.paths import EVENTS_PATH as EP, CHARACTERS_PATH as CP

        def _count(p: Path) -> int:
            if not p.is_file():
                return 0
            return sum(1 for line in p.read_text(encoding="utf-8").splitlines() if line.strip())

        print(f"characters.jsonl   {_count(CP):>4} 行  {CP}")
        print(f"events.jsonl       {_count(EP):>4} 行  {EP}")
        print(f"score_ledger.jsonl {_count(LEDGER_PATH):>3} 行  {LEDGER_PATH}")
        return 0

    parser.error(args.cmd)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
