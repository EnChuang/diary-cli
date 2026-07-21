"""
Phase G：榜單主畫面／閱讀 CLI（不呼叫 AI）。

G1 歷史榜  G2 人物→相關事件  G3 事件→成稿＋當次分
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

from storage.characters import get_character, leaderboard, load_characters
from storage.events import get_event, list_events, load_events
from storage.ledger import list_for_character, list_for_event
from storage.paths import CHARACTERS_PATH, EVENTS_PATH, LEDGER_PATH


def _preview(text: str, n: int = 48) -> str:
    one = " ".join((text or "").split())
    if len(one) <= n:
        return one
    return one[: n - 1] + "…"


def _event_title(ev: dict[str, Any]) -> str:
    story = ev.get("story")
    if isinstance(story, dict) and story.get("title"):
        return story["title"]
    return _preview(ev.get("user_main_text") or "（無標題）", 40)


def related_events(character_id: str) -> list[dict[str, Any]]:
    """含該 character_id 的事件：confirmed 優先，同組新到舊。"""
    cid = (character_id or "").strip()
    hits = []
    for ev in load_events():
        for p in ev.get("participants") or []:
            if (p.get("character_id") or "") == cid:
                hits.append(ev)
                break
    conf = [e for e in hits if e.get("status") == "confirmed"]
    other = [e for e in hits if e.get("status") != "confirmed"]
    conf.sort(key=lambda e: e.get("updated_at") or "", reverse=True)
    other.sort(key=lambda e: e.get("updated_at") or "", reverse=True)
    return conf + other


def resolve_character(token: str) -> Optional[dict[str, Any]]:
    """id / 精確名 / 暱稱 / 榜單名次(#n 或純數字)。"""
    t = (token or "").strip()
    if not t:
        return None
    if t.startswith("#"):
        t = t[1:]
    board = leaderboard()
    if t.isdigit():
        idx = int(t)
        if 1 <= idx <= len(board):
            return board[idx - 1]
    row = get_character(t)
    if row:
        return row
    # name / nick
    for c in load_characters():
        if c.get("is_user"):
            continue
        if c.get("name") == token.strip() or c.get("display_nick") == token.strip():
            return c
    # fuzzy contains
    needle = token.strip()
    for c in load_characters():
        if c.get("is_user"):
            continue
        if needle in (c.get("name") or "") or needle in (c.get("display_nick") or ""):
            return c
    return None


def cmd_rank(*, limit: Optional[int] = None) -> int:
    rows = leaderboard()
    if limit is not None:
        rows = rows[:limit]
    print("========== 歷史榜 ==========")
    if not rows:
        print("（尚無上榜人物。完成 story_score 落盤後會出現。）")
        print(f"資料：{CHARACTERS_PATH}")
        return 0
    print(f"{'#':>3}  {'分數':>6}  {'暱稱':<8}  {'名稱':<12}  id")
    for i, r in enumerate(rows, 1):
        print(
            f"{i:>3}  {r['history_score']:>+6}  {r['display_nick']:<8}  "
            f"{r['name']:<12}  {r['id']}"
        )
    print(f"\n共 {len(leaderboard())} 人（不含使用者）")
    print("進人物：python board.py char 1")
    print("       python board.py char 小美")
    return 0


def cmd_char(token: str) -> int:
    c = resolve_character(token)
    if c is None:
        print(f"找不到人物：{token}", file=sys.stderr)
        return 1
    if c.get("is_user"):
        print("使用者本人不上歷史榜；仍可查詢相關事件。")

    print("========== 人物 ==========")
    print(f"名稱：{c['name']}（{c['display_nick']}）")
    print(f"id：  {c['id']}")
    print(f"歷史分：{c['history_score']:+d}")
    print(f"建檔：{c.get('created_at', '')}")
    print(f"更新：{c.get('updated_at', '')}")

    led = list_for_character(c["id"])
    if led:
        print(f"\n--- ledger（{len(led)} 筆）---")
        for row in sorted(led, key=lambda x: x.get("at") or "", reverse=True):
            print(
                f"  {row.get('at', '')[:19]}  "
                f"delta={row['delta']:+d}  evt={row['event_id']}"
            )
    else:
        print("\n（尚無 ledger）")

    related = related_events(c["id"])
    print(f"\n--- 相關事件（{len(related)}）---")
    if not related:
        print("（無）")
    else:
        for ev in related:
            # 當次分
            delta = None
            for p in ev.get("participants") or []:
                if p.get("character_id") == c["id"]:
                    delta = p.get("event_score")
                    break
            d_s = f"{delta:+d}" if isinstance(delta, int) else "—"
            print(
                f"  [{ev.get('status')}] 當次={d_s}  {_event_title(ev)}"
            )
            print(f"           id={ev['id']}")
    print(f"\n讀事件：python board.py event <id>")
    return 0


def cmd_event(event_id: str) -> int:
    ev = get_event(event_id.strip())
    if ev is None:
        print(f"找不到事件：{event_id}", file=sys.stderr)
        return 1

    print("========== 事件 ==========")
    print(f"id：    {ev['id']}")
    print(f"status：{ev['status']}")
    print(f"建立：  {ev.get('created_at', '')}")
    if ev.get("confirmed_at"):
        print(f"確認：  {ev['confirmed_at']}")
    if ev.get("score_mean") is not None:
        print(f"score_mean：{ev['score_mean']}")
    # D22 標題來源
    if ev.get("title_deferred"):
        print("標題：  （延後／成稿時 AI）", end="")
        if ev.get("story") and isinstance(ev["story"], dict) and ev["story"].get("title"):
            print(f" → 最終「{ev['story']['title']}」")
        else:
            print()
    elif ev.get("user_title"):
        print(f"標題：  手填「{ev['user_title']}」", end="")
        if ev.get("story") and isinstance(ev["story"], dict) and ev["story"].get("title"):
            print(f" → 成稿「{ev['story']['title']}」")
        else:
            print()

    print("\n--- 主文 ---")
    print(ev.get("user_main_text") or "（空）")

    if ev.get("ai_draft"):
        print("\n--- 初稿 ---")
        print(ev["ai_draft"])

    story = ev.get("story")
    if isinstance(story, dict):
        print("\n--- 成稿 ---")
        print(f"標題：{story.get('title', '')}")
        print(f"時間：{story.get('time') or '（未注明）'}")
        tags = story.get("tags") or []
        print(f"標籤：{', '.join(tags) if tags else '（無）'}")
        print()
        print(story.get("body") or "（空）")
    else:
        print("\n（尚未成稿）")

    print("\n--- 當次評分 ---")
    parts = ev.get("participants") or []
    if not parts:
        print("（無參與者）")
    for p in parts:
        name = p.get("temp_name") or p.get("character_id") or "?"
        if p.get("is_user"):
            print(f"  · {name}  （使用者）")
            continue
        sc = p.get("event_score")
        reason = p.get("score_reason") or ""
        sc_s = f"{sc:+d}" if isinstance(sc, int) else "—"
        print(f"  · {name}: {sc_s}  id={p.get('character_id')}")
        if reason:
            print(f"      {reason}")

    led = list_for_event(ev["id"])
    if led:
        print(f"\n--- ledger（{len(led)}）---")
        for row in led:
            print(
                f"  {row['character_id']}: {row['delta']:+d}  {row.get('at', '')[:19]}"
            )

    qa = ev.get("qa_thread") or []
    if qa:
        print(f"\n--- 問答（{len(qa)} 則，摘要）---")
        for m in qa[:8]:
            print(f"  [{m.get('role')}] {_preview(m.get('content') or '', 60)}")
        if len(qa) > 8:
            print(f"  …另有 {len(qa) - 8} 則")

    print(f"\n完整 JSON：python -m storage.events get {ev['id']}")
    return 0


def cmd_events(*, status: Optional[str] = None, limit: int = 30) -> int:
    rows = list_events(status=status)
    rows = rows[:limit]
    print("========== 事件列表 ==========")
    if not rows:
        print("（無）")
        return 0
    print(f"{'status':<18}  {'id':<20}  標題／預覽")
    for e in rows:
        print(f"{e['status']:<18}  {e['id']:<20}  {_event_title(e)}")
    print(f"\n讀取：python board.py event <id>")
    print(f"路徑：{EVENTS_PATH}")
    return 0


def cmd_status() -> int:
    def _count(path) -> int:
        if not path.is_file():
            return 0
        return sum(
            1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
        )

    n_char = len([c for c in load_characters() if not c.get("is_user")])
    n_ev = len(load_events())
    n_conf = len([e for e in load_events() if e.get("status") == "confirmed"])
    n_led = _count(LEDGER_PATH)
    print("========== 資料概況 ==========")
    print(f"上榜人物：{n_char}")
    print(f"事件：    {n_ev}（confirmed {n_conf}）")
    print(f"ledger：  {n_led}")
    print(f"chars → {CHARACTERS_PATH}")
    print(f"events→ {EVENTS_PATH}")
    print(f"ledger→ {LEDGER_PATH}")
    return 0


def cmd_interactive() -> int:
    print("=== 野史錄 · 榜單（Phase G）===")
    print("指令：rank | char <n|名|id> | event <id> | events | status | q\n")
    cmd_rank()
    while True:
        try:
            line = input("\nboard> ").strip()
        except EOFError:
            print()
            return 0
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit", "退出"):
            return 0
        parts = line.split(maxsplit=1)
        head = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        if head in ("rank", "榜", "r"):
            cmd_rank()
        elif head in ("char", "c", "人"):
            if not arg:
                print("用法：char 1  或 char 小美")
            else:
                cmd_char(arg)
        elif head in ("event", "e", "事"):
            if not arg:
                print("用法：event evt_xxx")
            else:
                cmd_event(arg)
        elif head in ("events", "list", "ls"):
            cmd_events()
        elif head in ("status", "s"):
            cmd_status()
        elif head in ("help", "?", "h"):
            print("rank | char <n|名> | event <id> | events | status | q")
        else:
            # 純數字當名次
            if head.isdigit() or head.startswith("#"):
                cmd_char(head)
            elif head.startswith("evt_"):
                cmd_event(head)
            else:
                print("未知指令。help 看說明。")


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python board.py",
        description="八卦榜單／閱讀（Phase G，無 AI）",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_rank = sub.add_parser("rank", help="歷史榜")
    p_rank.add_argument("-n", type=int, default=None, help="只顯示前 n 名")

    p_char = sub.add_parser("char", help="人物詳情＋相關事件")
    p_char.add_argument("who", help="名次 / 名 / 暱稱 / id")

    p_ev = sub.add_parser("event", help="事件成稿＋當次分")
    p_ev.add_argument("id")

    p_evs = sub.add_parser("events", help="事件列表")
    p_evs.add_argument("--status", default=None)
    p_evs.add_argument("-n", type=int, default=30)

    sub.add_parser("status", help="資料概況")
    sub.add_parser("i", help="互動瀏覽")
    sub.add_parser("interactive", help="互動瀏覽")

    args = parser.parse_args(argv)

    if args.cmd is None:
        return cmd_interactive() if sys.stdin.isatty() else cmd_rank()

    if args.cmd == "rank":
        return cmd_rank(limit=args.n)
    if args.cmd == "char":
        return cmd_char(args.who)
    if args.cmd == "event":
        return cmd_event(args.id)
    if args.cmd == "events":
        return cmd_events(status=args.status, limit=args.n)
    if args.cmd == "status":
        return cmd_status()
    if args.cmd in ("i", "interactive"):
        return cmd_interactive()

    parser.error(args.cmd)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
