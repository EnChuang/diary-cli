"""
Phase F：評分建議 + 調分 + 確認落盤。

AI 建議當次分 → 平均±10 clamp → 使用者可改 → confirm（ledger + 歷史榜）。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from llm_client import chat_json, load_skill_file
from storage.confirm import confirm_event
from storage.events import get_event, list_events, upsert_event
from storage.scoring import apply_scores_to_participants, legal_bounds, mean_of_scores
from story_followup import format_qa_thread
from text_zh import name_key, to_traditional

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL_PATH = ROOT / "skill" / "story_score.md"


def validate_score_payload(data: dict[str, Any]) -> dict[str, Any]:
    if "scores" not in data:
        raise ValueError("評分 JSON 需含 scores")
    scores = data["scores"]
    if not isinstance(scores, list):
        raise ValueError("scores 必須是 array")
    clean = []
    for item in scores:
        if not isinstance(item, dict):
            raise ValueError("scores[] 必須是 object")
        name = item.get("name", "")
        sc = item.get("event_score")
        reason = item.get("score_reason", "")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("score.name 必須為非空字串")
        if not isinstance(sc, int) or isinstance(sc, bool):
            # 模型有時給 float
            if isinstance(sc, float) and sc == int(sc):
                sc = int(sc)
            else:
                try:
                    sc = int(sc)
                except (TypeError, ValueError) as e:
                    raise ValueError(f"event_score 必須是整數：{name}") from e
        if sc < -100 or sc > 100:
            raise ValueError(f"event_score 超出範圍：{name}={sc}")
        if not isinstance(reason, str):
            reason = str(reason)
        clean.append(
            {
                "name": name.strip(),
                "event_score": sc,
                "score_reason": reason.strip(),
            }
        )
    summary = data.get("summary", "")
    if not isinstance(summary, str):
        summary = str(summary)
    return {"scores": clean, "summary": summary.strip()}


def build_score_user_message(event: dict[str, Any]) -> str:
    story = event.get("story") or {}
    body = ""
    if isinstance(story, dict):
        body = (
            f"標題：{story.get('title', '')}\n"
            f"時間：{story.get('time', '')}\n"
            f"標籤：{', '.join(story.get('tags') or [])}\n"
            f"正文：\n{story.get('body', '')}"
        )
    lines = ["## 待評分人物（勿評 is_user=true）"]
    for p in event.get("participants") or []:
        if p.get("is_user"):
            lines.append(
                f"- [使用者略過] {p.get('temp_name') or p.get('character_id') or '我'}"
            )
        else:
            lines.append(
                f"- {p.get('temp_name') or p.get('character_id') or '?'}"
            )
    parent_memory = ""
    if event.get("parent_event_id"):
        from storage.sequel import build_memory_package

        parent_memory = (
            build_memory_package(event["parent_event_id"])
            + "\n（評分時可參考父篇分數與是否反轉；只評**本則後續**有出場者。）\n\n"
        )
    return (
        f"{parent_memory}"
        "## 主文\n"
        f"{(event.get('user_main_text') or '').strip()}\n\n"
        "## 成稿\n"
        f"{body or '（尚無成稿，請依主文與問答）'}\n\n"
        "## 問答\n"
        f"{format_qa_thread(event.get('qa_thread') or [])}\n\n"
        + "\n".join(lines)
        + "\n\n## 指示\n"
        "請輸出評分 JSON（只評非使用者）。\n"
        "核心：分數＝**使用者對此人的主觀觀感**（喜歡／反感／對「我」好不好），"
        "不是道德分、不是誰可憐誰該贏。\n"
        "禁止：僅因受害者／被罵／哭泣就給高分；"
        "壞人被罵哭若使用者仍反感 → 負分或中性。\n"
        "若相對父篇有劇情反轉，請在分數與理由中反映使用者觀感的力道變化。"
    )


def suggest_scores(event: dict[str, Any]) -> dict[str, Any]:
    skill = load_skill_file(SKILL_PATH)
    raw = chat_json(
        [
            {"role": "system", "content": skill},
            {"role": "user", "content": build_score_user_message(event)},
        ],
        temperature=0.35,
        max_attempts=3,
    )
    return validate_score_payload(raw)


def _names_compatible(a: str, b: str) -> bool:
    na, nb = name_key(a), name_key(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    if len(na) >= 2 and len(nb) >= 2 and na[-2:] == nb[-2:]:
        return True
    return False


def match_participant_index(
    participants: list[dict[str, Any]],
    name: str,
) -> Optional[int]:
    """用 name 對 temp_name / character_id 做寬鬆匹配（繁體鍵）。"""
    target = to_traditional((name or "").strip())
    if not target:
        return None
    for i, p in enumerate(participants):
        if p.get("is_user"):
            continue
        keys = [p.get("temp_name") or "", p.get("character_id") or ""]
        for k in keys:
            if k and _names_compatible(k, target):
                return i
    return None


def apply_ai_scores_to_event(
    event: dict[str, Any],
    score_payload: dict[str, Any],
    *,
    clamp: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    """
    把 AI scores 合併進 participants，並 clamp。
    回傳 (更新後 event 副本欄位 participants+score_mean 預覽, warnings)
    """
    participants = [dict(p) for p in (event.get("participants") or [])]
    warnings: list[str] = []

    # 確保至少有可評列：若 participants 空，從 scores 建
    if not any(not p.get("is_user") for p in participants):
        for s in score_payload["scores"]:
            participants.append(
                {
                    "character_id": None,
                    "temp_name": s["name"],
                    "is_user": False,
                    "event_score": None,
                }
            )

    matched: set[int] = set()
    for s in score_payload["scores"]:
        idx = match_participant_index(participants, s["name"])
        if idx is None:
            # 盡量不新建：再掃一次僅比對末兩字
            for i, p in enumerate(participants):
                if p.get("is_user"):
                    continue
                tn = p.get("temp_name") or ""
                if tn and _names_compatible(tn, s["name"]):
                    idx = i
                    break
        if idx is None:
            participants.append(
                {
                    "character_id": None,
                    "temp_name": s["name"],
                    "is_user": False,
                    "event_score": s["event_score"],
                    "score_reason": s.get("score_reason") or "",
                }
            )
            matched.add(len(participants) - 1)
            warnings.append(f"新增人物列：{s['name']}")
            continue
        if participants[idx].get("is_user"):
            warnings.append(f"略過使用者：{s['name']}")
            continue
        participants[idx]["event_score"] = s["event_score"]
        if s.get("score_reason"):
            participants[idx]["score_reason"] = s["score_reason"]
        matched.add(idx)

    for i, p in enumerate(participants):
        if p.get("is_user"):
            p["event_score"] = None
            continue
        if i not in matched and p.get("event_score") is None:
            warnings.append(
                f"未獲 AI 分數：{p.get('temp_name') or p.get('character_id')}"
            )

    participants, mu, mean_i = apply_scores_to_participants(
        participants, clamp=clamp
    )
    out = dict(event)
    out["participants"] = participants
    out["score_mean"] = float(mean_i) if mean_i is not None else None
    if mu is not None:
        lo, hi = legal_bounds(mu)
        warnings.append(f"μ={mu:.2f} 合法區間≈[{lo},{hi}] score_mean={mean_i}")
    return out, warnings


def save_participants(event_id: str, participants: list[dict[str, Any]], score_mean) -> dict[str, Any]:
    row = get_event(event_id)
    if row is None:
        raise KeyError(event_id)
    if row["status"] == "confirmed":
        raise ValueError("已 confirmed，不可改分")
    row["participants"] = participants
    row["score_mean"] = score_mean
    return upsert_event(row)


def print_scores(event: dict[str, Any], *, header: str = "當次評分") -> None:
    print(f"\n========== {header} ==========")
    if event.get("story") and isinstance(event["story"], dict):
        print(f"故事：{event['story'].get('title', '')}")
    parts = event.get("participants") or []
    scored = []
    for p in parts:
        name = p.get("temp_name") or p.get("character_id") or "?"
        if p.get("is_user"):
            print(f"  · {name}  （使用者，不評分）")
            continue
        sc = p.get("event_score")
        reason = p.get("score_reason") or ""
        print(f"  · {name}: {sc:+d}" if isinstance(sc, int) else f"  · {name}: （未評）")
        if reason:
            print(f"      理由：{reason}")
        if isinstance(sc, int):
            scored.append(sc)
    if scored:
        mu = mean_of_scores(scored)
        lo, hi = legal_bounds(mu)
        print(f"\n平均 μ={mu:.2f}  合法≈[{lo},{hi}]  score_mean={event.get('score_mean')}")
    else:
        print("（尚無分數）")


def interactive_adjust(participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    調分迴圈。指令：
      列表編號 分數   例：1 20
      名 分數         例：陳美玲 -5
      ok / 確認 / done
      list
    """
    parts = [dict(p) for p in participants]
    print(
        "\n可調分：輸入「編號 分數」或「名字 分數」；完成輸入 ok；list 重看。"
    )
    while True:
        # 編號表
        indexable = []
        for p in parts:
            if p.get("is_user"):
                continue
            indexable.append(p)
        for i, p in enumerate(indexable, 1):
            name = p.get("temp_name") or p.get("character_id") or "?"
            sc = p.get("event_score")
            sc_s = f"{sc:+d}" if isinstance(sc, int) else "—"
            print(f"  [{i}] {name}: {sc_s}")

        try:
            line = input("調分> ").strip()
        except EOFError:
            break
        if not line:
            continue
        low = line.lower()
        if low in ("ok", "done", "確認", "确认", "y", "yes"):
            break
        if low in ("list", "ls", "顯示"):
            continue
        if low in ("help", "?", "幫助"):
            print("格式：1 15   或   小美 -10   ；完成：ok")
            continue

        tokens = line.replace("：", " ").replace(":", " ").split()
        if len(tokens) < 2:
            print("格式：編號 分數")
            continue
        score_tok = tokens[-1]
        name_tok = " ".join(tokens[:-1])
        try:
            new_score = int(score_tok)
        except ValueError:
            print("分數須為整數")
            continue
        if new_score < -100 or new_score > 100:
            print("分數須在 -100～100")
            continue

        target = None
        if name_tok.isdigit():
            idx = int(name_tok)
            if 1 <= idx <= len(indexable):
                target = indexable[idx - 1]
        if target is None:
            mi = match_participant_index(parts, name_tok)
            if mi is not None:
                target = parts[mi]
        if target is None:
            print(f"找不到：{name_tok}")
            continue
        if target.get("is_user"):
            print("不可評使用者")
            continue
        target["event_score"] = new_score
        print(f"  → {target.get('temp_name')} = {new_score:+d}")

    parts, mu, mean_i = apply_scores_to_participants(parts, clamp=True)
    if mu is not None:
        print(f"已套用 ±10 約束後 μ={mu:.2f} mean={mean_i}")
    return parts


def pick_event_id() -> Optional[str]:
    candidates = [
        e
        for e in list_events()
        if e["status"] in ("draft", "awaiting_generate") and e.get("story")
    ]
    # 也允許無成稿但有主文
    if not candidates:
        candidates = [
            e for e in list_events() if e["status"] in ("draft", "awaiting_generate")
        ]
    if not candidates:
        print("沒有可評分事件。", file=sys.stderr)
        return None
    print("可評分／確認的事件：")
    for i, e in enumerate(candidates, 1):
        title = ""
        if e.get("story") and isinstance(e["story"], dict):
            title = e["story"].get("title") or ""
        preview = title or " ".join((e.get("user_main_text") or "").split())[:36]
        print(f"  {i}. {e['id']}  [{e['status']}]  {preview}")
    try:
        raw = input("選編號或 event id：").strip()
    except EOFError:
        return None
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]["id"]
        return None
    return raw


def run_score_flow(
    event_id: str,
    *,
    skip_ai: bool = False,
    yes: bool = False,
    no_adjust: bool = False,
) -> int:
    event = get_event(event_id)
    if event is None:
        print(f"找不到：{event_id}", file=sys.stderr)
        return 1
    if event["status"] == "confirmed":
        print("已 confirmed。", file=sys.stderr)
        return 1

    if not event.get("story"):
        print("警告：尚無成稿，將依主文／問答評分（建議先 story_generate）。")

    score_payload: Optional[dict[str, Any]] = None
    if not skip_ai:
        # 若已有分數且 yes，可跳過 AI
        has_scores = any(
            (not p.get("is_user") and p.get("event_score") is not None)
            for p in (event.get("participants") or [])
        )
        if has_scores and yes:
            print("沿用事件上既有分數（--yes 且已有分）。")
        else:
            print(f"\n呼叫 ModelArk 建議評分…（{event_id}）")
            try:
                score_payload = suggest_scores(event)
            except Exception as e:
                print("評分建議失敗：", e, file=sys.stderr)
                return 1
            print(f"AI 立場：{score_payload.get('summary') or '（無）'}")
            event, warnings = apply_ai_scores_to_event(event, score_payload)
            for w in warnings:
                print(f"  · {w}")
            print_scores(event, header="AI 建議分（已 clamp ±10）")
            # 先寫入建議分，方便中斷恢復
            save_participants(
                event_id, event["participants"], event.get("score_mean")
            )
            print("（建議分已暫存至事件）")
    else:
        event = get_event(event_id)
        print_scores(event, header="目前分數")

    # F5：是否修改 AI 分數
    if not no_adjust and not yes:
        try:
            ans = input("\n是否修改分數？[y/N] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans == "y":
            event = get_event(event_id)
            new_parts = interactive_adjust(event.get("participants") or [])
            event = save_participants(
                event_id,
                new_parts,
                apply_scores_to_participants(new_parts, clamp=True)[2],
            )
            # save_participants 沒算 mean 完整 — 再算一次
            parts, mu, mean_i = apply_scores_to_participants(
                get_event(event_id)["participants"], clamp=True
            )
            event = save_participants(
                event_id, parts, float(mean_i) if mean_i is not None else None
            )
            print_scores(event, header="調分後")

    event = get_event(event_id)
    print_scores(event, header="確認前最終分")

    if not yes:
        try:
            ans = input("\n確認落盤（寫 ledger + 更新歷史榜）？[y/N] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans != "y":
            print("已取消落盤；分數仍保留在事件上。")
            return 0

    try:
        result = confirm_event(event_id, clamp_scores=True)
    except Exception as e:
        print("落盤失敗：", e, file=sys.stderr)
        return 1

    ev = result["event"]
    print(f"\n已 confirmed：{ev['id']}  score_mean={ev['score_mean']}")
    print(f"ledger {len(result['ledger_rows'])} 筆")
    print("--- 歷史榜 ---")
    for i, r in enumerate(result["leaderboard"], 1):
        print(f"  {i}. {r['name']} ({r['display_nick']}) {r['history_score']:+d}")
    print("\n查看：")
    print(f"  python -m storage.events show {ev['id']}")
    print("  python -m storage.characters rank")
    print("  python -m storage.ledger list")
    return 0


def _cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python story_score.py",
        description="八卦評分與確認（Phase F）",
    )
    parser.add_argument("--event", default=None)
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="不呼叫 AI，用事件上既有分數",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="不詢問調分／確認，直接 AI（若需要）+ 落盤",
    )
    parser.add_argument(
        "--no-adjust",
        action="store_true",
        help="跳過調分步驟，仍會問是否落盤（除非 --yes）",
    )
    parser.add_argument(
        "--suggest-only",
        action="store_true",
        help="只產 AI 建議分並暫存，不落盤",
    )
    args = parser.parse_args(argv)

    event_id = args.event
    if not event_id:
        print("=== 八卦評分／確認（Phase F）===\n")
        event_id = pick_event_id()
        if not event_id:
            return 1

    if args.suggest_only:
        event = get_event(event_id)
        if event is None:
            print(f"找不到：{event_id}", file=sys.stderr)
            return 1
        print("呼叫 ModelArk…")
        try:
            payload = suggest_scores(event)
            event, warnings = apply_ai_scores_to_event(event, payload)
            save_participants(
                event_id, event["participants"], event.get("score_mean")
            )
        except Exception as e:
            print(e, file=sys.stderr)
            return 1
        print(payload.get("summary", ""))
        for w in warnings:
            print(w)
        print_scores(get_event(event_id))
        print("已暫存建議分，未 confirm。")
        return 0

    return run_score_flow(
        event_id,
        skip_ai=args.skip_ai,
        yes=args.yes,
        no_adjust=args.no_adjust,
    )


if __name__ == "__main__":
    raise SystemExit(_cli())
