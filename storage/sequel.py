"""
D23 事件後續：回憶包、標題前綴、可讀性檢查。
"""
from __future__ import annotations

from typing import Any, Optional

from storage.events import get_event, is_readable_event, list_children
from text_zh import to_traditional

SEQUEL_PREFIX = "續・"


def ensure_sequel_title(title: str, *, is_sequel: bool) -> str:
    """保證後續標題帶系列前綴。"""
    t = to_traditional((title or "").strip())
    if not is_sequel:
        return t
    if not t:
        return f"{SEQUEL_PREFIX}後續"
    # 已有「續」開頭則不重複加
    if t.startswith("續"):
        return t
    return f"{SEQUEL_PREFIX}{t}"


def format_parent_scores(parent: dict[str, Any]) -> str:
    lines = []
    for p in parent.get("participants") or []:
        if p.get("is_user"):
            continue
        name = p.get("temp_name") or p.get("character_id") or "?"
        sc = p.get("event_score")
        reason = p.get("score_reason") or ""
        sc_s = f"{sc:+d}" if isinstance(sc, int) else "—"
        line = f"- {name}: {sc_s}"
        if reason:
            line += f"（{reason}）"
        lines.append(line)
    if parent.get("score_mean") is not None:
        lines.append(f"本場平均 score_mean={parent['score_mean']}")
    return "\n".join(lines) if lines else "（無評分）"


def format_parent_qa(parent: dict[str, Any]) -> str:
    qa = parent.get("qa_thread") or []
    if not qa:
        return "（無問答）"
    lines = []
    for m in qa:
        role = "AI" if m.get("role") == "assistant" else "使用者"
        lines.append(f"[{role}] {m.get('content') or ''}")
    return "\n".join(lines)


def build_memory_package(parent_event_id: str) -> str:
    """組回憶包字串供 Skill user message。"""
    parent = get_event(parent_event_id)
    if parent is None:
        return "（找不到父事件）"
    story = parent.get("story") if isinstance(parent.get("story"), dict) else {}
    title = story.get("title") or parent.get("user_title") or parent_event_id
    body = story.get("body") or ""
    time_s = story.get("time") or ""
    tags = ", ".join(story.get("tags") or [])
    return (
        f"## 父篇回憶（事件後續 D23，勿整篇重印進新成稿）\n"
        f"父篇 id：{parent['id']}\n"
        f"父篇標題：{title}\n"
        f"父篇時間：{time_s}\n"
        f"父篇標籤：{tags or '（無）'}\n\n"
        f"### 父篇成稿正文\n{body or '（無）'}\n\n"
        f"### 父篇問答\n{format_parent_qa(parent)}\n\n"
        f"### 父篇當次評分\n{format_parent_scores(parent)}\n\n"
        f"### 撰寫要求\n"
        f"- 本則是「後續」：開頭用心銜接前情，讀起來像同一故事軸的下一段。\n"
        f"- 正文只寫**銜接 + 本次新發展**，不要重貼父篇全文。\n"
        f"- 評分時只評本則出場／有語氣者；可反映劇情反轉力道。\n"
        f"- 標題若由你取，請帶系列感（程式也會補「續・」前綴）。\n"
    )


def parent_title_for_display(parent: dict[str, Any]) -> str:
    story = parent.get("story")
    if isinstance(story, dict) and story.get("title"):
        return story["title"]
    return (parent.get("user_title") or parent.get("id") or "").strip()


def can_add_sequel(event_id: str) -> bool:
    ev = get_event(event_id)
    return ev is not None and is_readable_event(ev)


def children_summary(parent_id: str) -> list[dict[str, Any]]:
    """給 UI 的子篇列表。"""
    out = []
    for e in list_children(parent_id):
        story = e.get("story") if isinstance(e.get("story"), dict) else None
        title = (
            (story or {}).get("title")
            or e.get("user_title")
            or e["id"]
        )
        out.append(
            {
                "id": e["id"],
                "title": title,
                "status": e.get("status"),
                "is_draft": e.get("status") != "confirmed",
                "confirmed": e.get("status") == "confirmed",
            }
        )
    return out
