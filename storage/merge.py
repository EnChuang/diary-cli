"""
角色 merge／改掛（Phase H）。

H1 事件內改掛 character_id  
H2 兩角色合併（ledger + 事件 participants 遷移）  
H3 以 ledger 重算 history_score  
H4 預設僅資料合併；可選簡單暱稱字串替換（不呼叫 AI 再生成）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

from storage import characters as char_mod
from storage import events as evt_mod
from storage import ledger as led_mod
from storage.confirm import recompute_history_scores
from storage.paths import CHARACTERS_PATH, EVENTS_PATH, LEDGER_PATH
from text_zh import name_key, to_traditional


def delete_character(
    character_id: str,
    *,
    characters_path: Path = CHARACTERS_PATH,
) -> None:
    cid = character_id.strip()
    if cid == char_mod.USER_ID:
        raise ValueError("不可刪除使用者 self")
    rows = char_mod.load_characters(characters_path)
    new_rows = [r for r in rows if r["id"] != cid]
    if len(new_rows) == len(rows):
        raise KeyError(f"找不到人物：{cid}")
    char_mod.save_characters(new_rows, characters_path)


def relink_participant(
    event_id: str,
    *,
    to_character_id: str,
    from_character_id: Optional[str] = None,
    from_temp_name: Optional[str] = None,
    participant_index: Optional[int] = None,
    events_path: Path = EVENTS_PATH,
    characters_path: Path = CHARACTERS_PATH,
    ledger_path: Path = LEDGER_PATH,
    recompute: bool = True,
) -> dict[str, Any]:
    """
    將事件中某一參與者改掛到 to_character_id。
    若事件已 confirmed 且有 ledger，同步改 ledger 的 character_id。
    """
    to_id = to_character_id.strip()
    target = char_mod.get_character(to_id, characters_path)
    if target is None:
        raise KeyError(f"目標人物不存在：{to_id}")
    if target.get("is_user"):
        raise ValueError("不可改掛到使用者 self（用 is_user 標記）")

    ev = evt_mod.get_event(event_id, events_path)
    if ev is None:
        raise KeyError(f"找不到事件：{event_id}")

    parts = [dict(p) for p in (ev.get("participants") or [])]
    idx: Optional[int] = participant_index
    if idx is None:
        for i, p in enumerate(parts):
            if p.get("is_user"):
                continue
            if from_character_id and p.get("character_id") == from_character_id:
                idx = i
                break
            if from_temp_name and (p.get("temp_name") or "") == from_temp_name:
                idx = i
                break
    if idx is None or idx < 0 or idx >= len(parts):
        raise ValueError("找不到要改掛的參與者（請指定 from id／temp_name／index）")

    old = parts[idx]
    if old.get("is_user"):
        raise ValueError("不可改掛使用者參與者")
    old_cid = old.get("character_id")
    parts[idx]["character_id"] = to_id
    if not parts[idx].get("temp_name"):
        parts[idx]["temp_name"] = target["name"]

    # 若同事件已有同一 to_id，合併列（保留有分數的）
    parts = _collapse_duplicate_participants(parts, keep_id=to_id)

    ev["participants"] = parts
    saved = evt_mod.upsert_event(ev, events_path)

    # ledger：該 event 下 old_cid → to_id
    if old_cid and old_cid != to_id:
        _remap_ledger_character(
            from_id=old_cid,
            to_id=to_id,
            only_event_id=event_id,
            ledger_path=ledger_path,
        )

    if recompute:
        recompute_history_scores(
            characters_path=characters_path, ledger_path=ledger_path
        )

    return {
        "event": evt_mod.get_event(event_id, events_path),
        "old_character_id": old_cid,
        "to_character_id": to_id,
    }


def _collapse_duplicate_participants(
    parts: list[dict[str, Any]],
    *,
    keep_id: str,
) -> list[dict[str, Any]]:
    """同一 character_id 多列時合併：優先保留有 event_score 的，理由併接。"""
    by_key: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    extras: list[dict[str, Any]] = []

    for p in parts:
        if p.get("is_user"):
            key = f"user:{(p.get('character_id') or 'self')}"
        else:
            cid = p.get("character_id")
            if not cid:
                extras.append(p)
                continue
            key = f"char:{cid}"
        if key not in by_key:
            by_key[key] = dict(p)
            order.append(key)
            continue
        cur = by_key[key]
        # merge scores: keep non-null; if both, keep first non-null then prefer keep_id row already there
        if cur.get("event_score") is None and p.get("event_score") is not None:
            cur["event_score"] = p["event_score"]
        if p.get("score_reason"):
            if cur.get("score_reason"):
                if p["score_reason"] not in cur["score_reason"]:
                    cur["score_reason"] = cur["score_reason"] + "；" + p["score_reason"]
            else:
                cur["score_reason"] = p["score_reason"]
        if p.get("temp_name") and not cur.get("temp_name"):
            cur["temp_name"] = p["temp_name"]
        by_key[key] = cur

    out = [by_key[k] for k in order]
    out.extend(extras)
    return out


def _remap_ledger_character(
    *,
    from_id: str,
    to_id: str,
    only_event_id: Optional[str] = None,
    ledger_path: Path = LEDGER_PATH,
) -> int:
    """
    改 ledger 的 character_id（from → to）。
    同 event 可有多筆（分屬原兩人）；加總仍等於歷史分，不強行併列以免截斷。
    """
    rows = led_mod.load_ledger(ledger_path)
    changed = 0
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        if row["character_id"] == from_id:
            if only_event_id is None or row["event_id"] == only_event_id:
                row["character_id"] = to_id
                changed += 1
        out.append(row)
    if changed:
        led_mod.save_ledger(out, ledger_path)
    return changed


def rewrite_story_nicks(
    story: Optional[dict[str, Any]],
    *,
    from_names: list[str],
    to_nick: str,
) -> Optional[dict[str, Any]]:
    """H4 輕量：成稿正文／標題內字串替換（非 AI 再生成）。"""
    if not story or not isinstance(story, dict):
        return story
    out = dict(story)
    body = out.get("body") or ""
    title = out.get("title") or ""
    # 長字串先替換，減少部分匹配問題
    names = sorted({n for n in from_names if n}, key=len, reverse=True)
    for n in names:
        if n == to_nick:
            continue
        body = body.replace(n, to_nick)
        title = title.replace(n, to_nick)
    out["body"] = body
    out["title"] = title
    return out


def merge_characters(
    source_id: str,
    target_id: str,
    *,
    rewrite_nicks: bool = False,
    delete_source: bool = True,
    characters_path: Path = CHARACTERS_PATH,
    events_path: Path = EVENTS_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> dict[str, Any]:
    """
    將 source 併入 target（保留 target 檔案）。
    - 所有事件 participants：source → target，並折叠重複
    - ledger：source → target（同事件合併 delta）
    - 重算 history_score
    - 可選刪除 source 人物列
    - rewrite_nicks：把 source 的 name/nick 字串換成 target.display_nick
    """
    src = source_id.strip()
    tgt = target_id.strip()
    if src == tgt:
        raise ValueError("source 與 target 不可相同")
    if src == char_mod.USER_ID or tgt == char_mod.USER_ID:
        raise ValueError("不可 merge 使用者 self")

    source = char_mod.get_character(src, characters_path)
    target = char_mod.get_character(tgt, characters_path)
    if source is None:
        raise KeyError(f"找不到 source：{src}")
    if target is None:
        raise KeyError(f"找不到 target：{tgt}")
    if source.get("is_user") or target.get("is_user"):
        raise ValueError("不可 merge is_user 角色")

    events_touched = 0
    for ev in evt_mod.load_events(events_path):
        parts = [dict(p) for p in (ev.get("participants") or [])]
        changed = False
        for p in parts:
            if p.get("character_id") == src:
                p["character_id"] = tgt
                if not p.get("temp_name"):
                    p["temp_name"] = target["name"]
                changed = True
        if changed:
            parts = _collapse_duplicate_participants(parts, keep_id=tgt)
            ev["participants"] = parts
            if rewrite_nicks and ev.get("story"):
                from_names = [
                    source.get("name") or "",
                    source.get("display_nick") or "",
                ]
                ev["story"] = rewrite_story_nicks(
                    ev["story"],
                    from_names=from_names,
                    to_nick=target.get("display_nick") or target["name"],
                )
            evt_mod.upsert_event(ev, events_path)
            events_touched += 1
        elif rewrite_nicks and ev.get("story"):
            # 即使無 participants 命中，也可依名字掃正文（謹慎：可能誤傷）
            pass

    led_changed = _remap_ledger_character(
        from_id=src, to_id=tgt, only_event_id=None, ledger_path=ledger_path
    )

    if delete_source:
        # 刪前再確認無殘留 ledger
        still = led_mod.list_for_character(src, ledger_path)
        if still:
            _remap_ledger_character(
                from_id=src, to_id=tgt, ledger_path=ledger_path
            )
        delete_character(src, characters_path=characters_path)

    recompute_history_scores(
        characters_path=characters_path, ledger_path=ledger_path
    )
    target_after = char_mod.get_character(tgt, characters_path)

    return {
        "source_id": src,
        "target_id": tgt,
        "events_touched": events_touched,
        "ledger_rows_remapped": led_changed,
        "source_deleted": delete_source,
        "rewrite_nicks": rewrite_nicks,
        "target": target_after,
        "leaderboard": char_mod.leaderboard(characters_path),
    }


def _resolve_char(token: str) -> Optional[dict[str, Any]]:
    t = to_traditional((token or "").strip())
    if not t:
        return None
    row = char_mod.get_character(t)
    if row:
        return row
    by_name = char_mod.find_character_by_name(t)
    if by_name:
        return by_name
    for c in char_mod.load_characters():
        if name_key(c.get("name") or "") == name_key(t):
            return c
        if name_key(c.get("display_nick") or "") == name_key(t):
            return c
    for c in char_mod.load_characters():
        if t in to_traditional(c.get("name") or "") or t in to_traditional(
            c.get("display_nick") or ""
        ):
            return c
    return None


def _pick_canonical(group: list[dict[str, Any]]) -> dict[str, Any]:
    """同名多筆時保留誰：char_demo_* 優先，否則建立時間最早。"""
    def sort_key(c: dict[str, Any]) -> tuple:
        demo = 0 if str(c.get("id", "")).startswith("char_demo_") else 1
        return (demo, c.get("created_at") or "", c.get("id") or "")

    return sorted(group, key=sort_key)[0]


def dedupe_by_name(
    *,
    rewrite_nicks: bool = True,
    characters_path: Path = CHARACTERS_PATH,
    events_path: Path = EVENTS_PATH,
    ledger_path: Path = LEDGER_PATH,
) -> list[dict[str, Any]]:
    """
    依繁體 name 合併重複角色；並把 name/nick 全部改為繁體。
    回傳合併報告列表。
    """
    # 先把現有角色名轉繁體寫回
    rows = char_mod.load_characters(characters_path)
    for r in rows:
        r["name"] = to_traditional(r.get("name") or "")
        r["display_nick"] = to_traditional(r.get("display_nick") or "")
    char_mod.save_characters(rows, characters_path)

    # 事件文字轉繁（讀時 validate 已轉；強制重存）
    events = evt_mod.load_events(events_path)
    for ev in events:
        evt_mod.upsert_event(ev, events_path)

    by_key: dict[str, list[dict[str, Any]]] = {}
    for c in char_mod.load_characters(characters_path):
        if c.get("is_user"):
            continue
        k = name_key(c.get("name") or "")
        if not k:
            continue
        by_key.setdefault(k, []).append(c)

    reports: list[dict[str, Any]] = []
    for k, group in by_key.items():
        if len(group) < 2:
            continue
        keep = _pick_canonical(group)
        for other in group:
            if other["id"] == keep["id"]:
                continue
            result = merge_characters(
                other["id"],
                keep["id"],
                rewrite_nicks=rewrite_nicks,
                delete_source=True,
                characters_path=characters_path,
                events_path=events_path,
                ledger_path=ledger_path,
            )
            reports.append(
                {
                    "merged": other["id"],
                    "into": keep["id"],
                    "name": keep["name"],
                    "history_score": result["target"]["history_score"]
                    if result.get("target")
                    else None,
                }
            )
    recompute_history_scores(
        characters_path=characters_path, ledger_path=ledger_path
    )
    return reports


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m storage.merge",
        description="角色 merge／改掛（Phase H）",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_m = sub.add_parser("chars", help="合併兩角色：source → target（保留 target）")
    p_m.add_argument("source", help="被合併（將消失）")
    p_m.add_argument("target", help="保留的主檔")
    p_m.add_argument(
        "--rewrite-nicks",
        action="store_true",
        help="成稿內把 source 名／暱稱字串換成 target 暱稱（非 AI）",
    )
    p_m.add_argument(
        "--keep-source",
        action="store_true",
        help="不刪 source 人物列（仍會改掛與 ledger）",
    )
    p_m.add_argument("-y", "--yes", action="store_true", help="不詢問")

    p_r = sub.add_parser("relink", help="事件內改掛參與者")
    p_r.add_argument("event_id")
    p_r.add_argument("--to", required=True, help="目標 character id／名")
    p_r.add_argument("--from-id", default=None, help="原 character_id")
    p_r.add_argument("--from-name", default=None, help="原 temp_name")
    p_r.add_argument("--index", type=int, default=None, help="participants 索引 0-based")

    sub.add_parser("recompute", help="依 ledger 重算全部 history_score")
    sub.add_parser("dupes", help="列出可能重複的名稱（同 name）")
    p_dd = sub.add_parser(
        "dedupe",
        help="自動合併同名（繁體鍵）重複角色，並全庫名稱轉繁體",
    )
    p_dd.add_argument("-y", "--yes", action="store_true")
    p_dd.add_argument(
        "--no-rewrite-nicks",
        action="store_true",
        help="合併時不改成稿字串",
    )

    args = parser.parse_args(argv)

    if args.cmd == "recompute":
        rows = recompute_history_scores()
        print(f"已重算 {len(rows)} 人")
        for r in char_mod.leaderboard():
            print(f"  {r['history_score']:>+5}  {r['name']}  {r['id']}")
        return 0

    if args.cmd == "dupes":
        by_name: dict[str, list[dict[str, Any]]] = {}
        for c in char_mod.load_characters():
            if c.get("is_user"):
                continue
            by_name.setdefault(name_key(c["name"]), []).append(c)
        found = False
        for key, group in sorted(by_name.items()):
            if len(group) < 2:
                continue
            found = True
            print(f"【{group[0]['name']}】×{len(group)}  key={key}")
            for g in group:
                print(
                    f"  {g['history_score']:>+5}  {g['display_nick']:<8}  {g['id']}"
                )
            keep = _pick_canonical(group)
            print(f"  建議保留：{keep['id']}；或執行 python -m storage.merge dedupe -y")
        if not found:
            print("（未發現同名重複）")
        return 0

    if args.cmd == "dedupe":
        # 預覽
        by_name: dict[str, list] = {}
        for c in char_mod.load_characters():
            if c.get("is_user"):
                continue
            by_name.setdefault(name_key(c["name"]), []).append(c)
        pending = {k: g for k, g in by_name.items() if len(g) >= 2}
        if not pending:
            print("無需合併；仍會執行名稱轉繁體。")
        else:
            print(f"將合併 {len(pending)} 組同名：")
            for g in pending.values():
                keep = _pick_canonical(g)
                others = [x["id"] for x in g if x["id"] != keep["id"]]
                print(f"  {keep['name']}: 保留 {keep['id']} ← {others}")
        if not args.yes:
            try:
                ans = input("確認 dedupe？[y/N] ").strip().lower()
            except EOFError:
                ans = "n"
            if ans != "y":
                print("已取消")
                return 0
        reports = dedupe_by_name(rewrite_nicks=not args.no_rewrite_nicks)
        print(f"完成合併 {len(reports)} 筆")
        for r in reports:
            print(f"  {r['merged']} → {r['into']}  ({r['name']}) score={r['history_score']}")
        print("--- 榜 ---")
        for i, row in enumerate(char_mod.leaderboard(), 1):
            print(f"  {i}. {row['name']} {row['history_score']:+d}  {row['id']}")
        return 0

    if args.cmd == "relink":
        to = _resolve_char(args.to)
        if to is None:
            print(f"找不到目標：{args.to}", file=sys.stderr)
            return 1
        try:
            result = relink_participant(
                args.event_id,
                to_character_id=to["id"],
                from_character_id=args.from_id,
                from_temp_name=args.from_name,
                participant_index=args.index,
            )
        except (KeyError, ValueError) as e:
            print(e, file=sys.stderr)
            return 1
        print(
            f"已改掛：{result['old_character_id']} → {result['to_character_id']} "
            f"@ {args.event_id}"
        )
        return 0

    if args.cmd == "chars":
        src = _resolve_char(args.source)
        tgt = _resolve_char(args.target)
        if src is None:
            print(f"找不到 source：{args.source}", file=sys.stderr)
            return 1
        if tgt is None:
            print(f"找不到 target：{args.target}", file=sys.stderr)
            return 1
        print(
            f"將合併：{src['name']}({src['id']}, {src['history_score']:+d}) "
            f"→ {tgt['name']}({tgt['id']}, {tgt['history_score']:+d})"
        )
        print(f"rewrite_nicks={args.rewrite_nicks}  delete_source={not args.keep_source}")
        if not args.yes:
            try:
                ans = input("確認合併？[y/N] ").strip().lower()
            except EOFError:
                ans = "n"
            if ans != "y":
                print("已取消")
                return 0
        try:
            result = merge_characters(
                src["id"],
                tgt["id"],
                rewrite_nicks=args.rewrite_nicks,
                delete_source=not args.keep_source,
            )
        except (KeyError, ValueError) as e:
            print(e, file=sys.stderr)
            return 1
        print(
            f"完成：events={result['events_touched']} "
            f"ledger_remap≈{result['ledger_rows_remapped']} "
            f"deleted={result['source_deleted']}"
        )
        t = result["target"]
        print(f"target 歷史分現為：{t['history_score']:+d}  ({t['name']})")
        print("--- 榜 ---")
        for i, r in enumerate(result["leaderboard"][:10], 1):
            print(f"  {i}. {r['name']} {r['history_score']:+d}  {r['id']}")
        return 0

    parser.error(args.cmd)
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
