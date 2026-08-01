"""
AI 生成背景工作（避免長 POST 被瀏覽器／熱重載掐斷）。

狀態：running | done | error
"""
from __future__ import annotations

import threading
from typing import Any, Optional

from llm_client import format_llm_error
from storage.events import get_event

_lock = threading.Lock()
# event_id -> {status, phase, error}
_JOBS: dict[str, dict[str, Any]] = {}


def job_snapshot(event_id: str) -> dict[str, Any]:
    with _lock:
        j = dict(_JOBS.get(event_id) or {})
    return j


def is_running(event_id: str) -> bool:
    with _lock:
        return (_JOBS.get(event_id) or {}).get("status") == "running"


def _set(event_id: str, **kwargs: Any) -> None:
    with _lock:
        cur = dict(_JOBS.get(event_id) or {})
        cur.update(kwargs)
        _JOBS[event_id] = cur


def start_generate_job(event_id: str) -> dict[str, Any]:
    """啟動背景生成；已在跑則回傳現況。"""
    with _lock:
        cur = _JOBS.get(event_id) or {}
        if cur.get("status") == "running":
            return dict(cur)
        _JOBS[event_id] = {
            "status": "running",
            "phase": "generate",
            "error": None,
        }

    def worker() -> None:
        try:
            from story_generate import apply_generate_to_event, generate_story
            from story_score import (
                apply_ai_scores_to_event,
                save_participants,
                suggest_scores,
            )

            ev = get_event(event_id)
            if ev is None:
                _set(event_id, status="error", phase="error", error="找不到事件")
                return
            if ev.get("status") == "confirmed":
                _set(event_id, status="done", phase="done", error=None)
                return

            _set(event_id, phase="generate")
            payload = generate_story(ev)
            apply_generate_to_event(event_id, payload)

            _set(event_id, phase="score")
            ev2 = get_event(event_id)
            if ev2 is not None:
                try:
                    score_payload = suggest_scores(ev2)
                    merged, _w = apply_ai_scores_to_event(ev2, score_payload)
                    save_participants(
                        event_id,
                        merged["participants"],
                        merged.get("score_mean"),
                    )
                except Exception as se:
                    # 成稿已有，評分失敗仍算完成（頁面可調分／落盤）
                    _set(
                        event_id,
                        status="done",
                        phase="done",
                        error=f"成稿完成，評分失敗：{format_llm_error(se)}",
                    )
                    return

            _set(event_id, status="done", phase="done", error=None)
        except Exception as e:
            _set(
                event_id,
                status="error",
                phase="error",
                error=format_llm_error(e),
            )

    threading.Thread(target=worker, daemon=True, name=f"gen-{event_id}").start()
    return job_snapshot(event_id)


def clear_job(event_id: str) -> None:
    with _lock:
        _JOBS.pop(event_id, None)


def clear_all_jobs() -> None:
    with _lock:
        _JOBS.clear()
