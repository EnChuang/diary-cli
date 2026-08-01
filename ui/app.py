"""
野史錄 · 極簡本機 Web 殼（Phase I 起步）

啟動（專案根目錄）：
  pip install -r requirements.txt
  uvicorn ui.app:app --reload --host 127.0.0.1 --port 8765 --reload-dir ui --reload-dir storage --reload-dir skill

瀏覽：http://127.0.0.1:8765

注意：PowerShell 勿用 data/*（會展開成檔名）。reload 只監看程式目錄，避免寫入 data/*.jsonl 中斷 AI 回應。

樣式暫為中性預設；正式視覺對照 design/ 內參考後再調 static/style.css。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage.characters import leaderboard  # noqa: E402
from storage.events import (  # noqa: E402
    LIKELY_ROLE_LABELS,
    append_qa,
    delete_draft_event,
    delete_event_tree,
    get_event,
    get_sole_draft,
    is_readable_event,
    list_events,
    list_subtree_ids,
    mark_cast_confirmed,
    needs_cast_confirm,
    resume_step_for_event,
    set_status,
)
from storage.paths import ensure_data_dir  # noqa: E402
from storage.sequel import (  # noqa: E402
    can_add_sequel,
    children_summary,
    parent_title_for_display,
)
from story_followup import (  # noqa: E402
    _looks_complete_question,
    create_event_from_main,
    ensure_pending_question,
)
from llm_client import format_llm_error  # noqa: E402
from text_zh import to_traditional  # noqa: E402
from storage.reset import is_local_data_empty, wipe_all_local_data  # noqa: E402
from ui.gen_jobs import (  # noqa: E402
    clear_all_jobs,
    clear_job,
    is_running,
    job_snapshot,
    start_generate_job,
)

UI_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(UI_DIR / "templates"))

app = FastAPI(title="野史錄 · Yes Log", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")


def _event_title(ev: dict[str, Any]) -> str:
    story = ev.get("story")
    if isinstance(story, dict) and story.get("title"):
        return story["title"]
    ut = (ev.get("user_title") or "").strip()
    if ut and not ev.get("title_deferred"):
        return ut
    preview = " ".join((ev.get("user_main_text") or "").split())
    return (preview[:36] + "…") if len(preview) > 36 else (preview or ev["id"])


def _scored_parts(ev: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for p in ev.get("participants") or []:
        if p.get("is_user"):
            continue
        out.append(
            {
                "name": p.get("temp_name") or p.get("character_id") or "?",
                "score": p.get("event_score"),
                "reason": p.get("score_reason") or "",
            }
        )
    return out


@app.on_event("startup")
def _startup() -> None:
    ensure_data_dir()


def _resume_url(ev: dict[str, Any]) -> str:
    step = resume_step_for_event(ev)
    eid = ev["id"]
    if step == "score":
        return f"/events/{eid}/score"
    if step == "generate":
        return f"/events/{eid}/generate"
    if step == "detail":
        return f"/events/{eid}"
    if step == "cast":
        return f"/events/{eid}/cast"
    return f"/events/{eid}/followup"


def _draft_dialog(
    request: Request,
    *,
    intent: str,
    parent_id: str = "",
) -> HTMLResponse:
    """D24：有唯一草稿時詢問繼續／放棄。"""
    draft = get_sole_draft()
    assert draft is not None
    return templates.TemplateResponse(
        "draft_dialog.html",
        {
            "request": request,
            "page": "draft",
            "draft": draft,
            "draft_title": _event_title(draft),
            "resume_url": _resume_url(draft),
            "intent": intent,
            "parent_id": parent_id,
        },
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    board = leaderboard()
    events = list_events()
    rows = [
        {
            "id": e["id"],
            "status": e["status"],
            "title": _event_title(e),
            "confirmed": e.get("status") == "confirmed",
            "is_draft": e.get("status") != "confirmed",
            "is_sequel": bool(e.get("parent_event_id")),
        }
        for e in events
    ]
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "board": board,
            "events": rows,
            "page": "home",
        },
    )


@app.get("/events/{event_id}", response_class=HTMLResponse)
def event_detail(request: Request, event_id: str) -> HTMLResponse:
    """D21 + D23 導覽。"""
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")

    story = ev.get("story") if isinstance(ev.get("story"), dict) else None
    is_reading = bool(story) or ev.get("status") == "confirmed"
    parent = None
    parent_title = None
    if ev.get("parent_event_id"):
        parent = get_event(ev["parent_event_id"])
        if parent:
            parent_title = parent_title_for_display(parent)
    children = children_summary(event_id)
    can_sequel = can_add_sequel(event_id)
    child_count = max(0, len(list_subtree_ids(event_id)) - 1)

    return templates.TemplateResponse(
        "event_detail.html",
        {
            "request": request,
            "ev": ev,
            "story": story,
            "qa": ev.get("qa_thread") or [],
            "scores": _scored_parts(ev),
            "score_mean": ev.get("score_mean"),
            "is_reading": is_reading,
            "page": "event",
            "list_title": _event_title(ev),
            "parent": parent,
            "parent_title": parent_title,
            "children": children,
            "can_sequel": can_sequel,
            "child_count": child_count,
        },
    )


@app.get("/new", response_class=HTMLResponse)
def new_form(request: Request, force: str = "") -> HTMLResponse:
    # D24：有草稿則詢問（冷啟動不彈；僅進新增時）
    if force not in ("1", "true", "yes") and get_sole_draft() is not None:
        return _draft_dialog(request, intent="new")
    return templates.TemplateResponse(
        "new_event.html",
        {
            "request": request,
            "page": "new",
            "error": None,
            "is_sequel": False,
            "parent_id": "",
            "parent_title": "",
        },
    )


@app.post("/draft/resolve")
def draft_resolve(
    action: str = Form(...),
    intent: str = Form("new"),
    parent_id: str = Form(""),
) -> RedirectResponse:
    """繼續或放棄唯一草稿。"""
    draft = get_sole_draft()
    action = (action or "").strip().lower()
    if action == "continue":
        if draft is None:
            return RedirectResponse(url="/", status_code=303)
        return RedirectResponse(url=_resume_url(draft), status_code=303)
    if action == "abandon":
        if draft is not None:
            try:
                delete_draft_event(draft["id"])
            except ValueError:
                pass
        if intent == "sequel" and parent_id:
            return RedirectResponse(
                url=f"/events/{parent_id}/sequel?force=1", status_code=303
            )
        return RedirectResponse(url="/new?force=1", status_code=303)
    return RedirectResponse(url="/", status_code=303)


@app.post("/new", response_class=HTMLResponse)
def new_submit(
    request: Request,
    main_text: str = Form(...),
    user_title: str = Form(""),
    title_mode: str = Form("ai"),
    parent_id: str = Form(""),
) -> HTMLResponse:
    main_text = to_traditional((main_text or "").strip())
    parent_id = (parent_id or "").strip()
    is_sequel = bool(parent_id)

    form_ctx = {
        "request": request,
        "page": "new",
        "is_sequel": is_sequel,
        "parent_id": parent_id,
        "parent_title": "",
    }
    if is_sequel:
        parent = get_event(parent_id)
        if parent is None or not is_readable_event(parent):
            form_ctx["error"] = "父事件不可用或不存在"
            return templates.TemplateResponse(
                "new_event.html", form_ctx, status_code=400
            )
        form_ctx["parent_title"] = parent_title_for_display(parent)

    if not main_text:
        form_ctx["error"] = "請填寫主文"
        return templates.TemplateResponse(
            "new_event.html", form_ctx, status_code=400
        )

    if get_sole_draft() is not None:
        return _draft_dialog(
            request,
            intent="sequel" if is_sequel else "new",
            parent_id=parent_id,
        )

    deferred = title_mode != "manual"
    title = to_traditional((user_title or "").strip())
    if not deferred and not title:
        deferred = True
    if is_sequel and not deferred and title:
        from storage.sequel import ensure_sequel_title

        title = ensure_sequel_title(title, is_sequel=True)

    try:
        event = create_event_from_main(
            main_text,
            skip_draft=False,
            user_title="" if deferred else title,
            title_deferred=deferred,
            prompt_title=False,
            parent_event_id=parent_id or None,
        )
    except Exception as e:
        form_ctx["error"] = f"建立失敗：{format_llm_error(e)}"
        return templates.TemplateResponse(
            "new_event.html", form_ctx, status_code=500
        )

    return RedirectResponse(
        url=f"/events/{event['id']}/cast", status_code=303
    )


@app.get("/events/{event_id}/cast", response_class=HTMLResponse)
def cast_page(request: Request, event_id: str) -> HTMLResponse:
    """出場人物確認（追問前）。"""
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)
    # 已確認過且在後段流程 → 導向正確步驟
    if not needs_cast_confirm(ev) and not (
        request.query_params.get("edit") in ("1", "true", "yes")
    ):
        return RedirectResponse(url=_resume_url(ev), status_code=303)

    rows = []
    for p in ev.get("participants") or []:
        name = (p.get("temp_name") or "").strip()
        rows.append(
            {
                "temp_name": name,
                "is_user": bool(p.get("is_user")),
                "likely_role": name in LIKELY_ROLE_LABELS,
            }
        )

    return templates.TemplateResponse(
        "cast.html",
        {
            "request": request,
            "ev": ev,
            "cast_rows": rows,
            "error": None,
            "page": "cast",
            "list_title": _event_title(ev),
            "parent_title": _parent_title_line(ev),
        },
    )


@app.post("/events/{event_id}/cast", response_class=HTMLResponse)
async def cast_save(request: Request, event_id: str) -> HTMLResponse:
    """儲存確認後的出場表，進入追問。"""
    from story_score import save_participants

    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    form = await request.form()
    try:
        count = int(form.get("count") or "0")
    except ValueError:
        count = 0

    participants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i in range(max(0, count)):
        name = to_traditional((form.get(f"name_{i}") or "").strip())
        if not name:
            continue
        # 勾選刪除
        if form.get(f"drop_{i}") in ("1", "on", "true", "yes"):
            continue
        is_user = form.get(f"user_{i}") in ("1", "on", "true", "yes")
        key = name
        if key in seen and not is_user:
            continue
        seen.add(key)
        participants.append(
            {
                "character_id": "self" if is_user else None,
                "temp_name": name,
                "is_user": is_user,
                "event_score": None,
            }
        )

    # 至少保留結構（允許零個非本人，但通常至少有人）
    error = None
    non_user = [p for p in participants if not p["is_user"]]
    if not participants:
        error = "請至少保留一位出場者（或新增人名）。若主文只有你自己，請新增並勾選「是我本人」。"
    elif not non_user and not any(p["is_user"] for p in participants):
        error = "請確認出場名單。"

    if error:
        rows = []
        for p in participants or ev.get("participants") or []:
            name = (p.get("temp_name") or "").strip()
            rows.append(
                {
                    "temp_name": name,
                    "is_user": bool(p.get("is_user")),
                    "likely_role": name in LIKELY_ROLE_LABELS,
                }
            )
        # 若全刪了，用表單 raw 重建空表給 UI
        if not rows:
            for i in range(max(1, count)):
                name = to_traditional((form.get(f"name_{i}") or "").strip())
                rows.append(
                    {
                        "temp_name": name,
                        "is_user": form.get(f"user_{i}")
                        in ("1", "on", "true", "yes"),
                        "likely_role": name in LIKELY_ROLE_LABELS,
                    }
                )
        return templates.TemplateResponse(
            "cast.html",
            {
                "request": request,
                "ev": ev,
                "cast_rows": rows,
                "error": error,
                "page": "cast",
                "list_title": _event_title(ev),
                "parent_title": _parent_title_line(ev),
            },
            status_code=400,
        )

    save_participants(event_id, participants, None)
    mark_cast_confirmed(event_id)
    return RedirectResponse(
        url=f"/events/{event_id}/followup", status_code=303
    )


@app.get("/events/{parent_id}/sequel", response_class=HTMLResponse)
def sequel_form(
    request: Request, parent_id: str, force: str = ""
) -> HTMLResponse:
    parent = get_event(parent_id)
    if parent is None:
        raise HTTPException(404, "找不到父事件")
    if not is_readable_event(parent):
        raise HTTPException(400, "僅已落成事件可加後續")
    if force not in ("1", "true", "yes") and get_sole_draft() is not None:
        return _draft_dialog(
            request, intent="sequel", parent_id=parent_id
        )
    return templates.TemplateResponse(
        "new_event.html",
        {
            "request": request,
            "page": "new",
            "error": None,
            "is_sequel": True,
            "parent_id": parent_id,
            "parent_title": parent_title_for_display(parent),
        },
    )


def _parent_title_line(ev: dict[str, Any]) -> str:
    pid = (ev.get("parent_event_id") or "").strip()
    if not pid:
        return ""
    parent = get_event(pid)
    if not parent:
        return ""
    return parent_title_for_display(parent)


def _last_assistant_question(ev: dict[str, Any]) -> str:
    """永遠以 qa_thread 最後一則 AI 為準（避免頂框空白）。"""
    for m in reversed(ev.get("qa_thread") or []):
        if m.get("role") == "assistant":
            return (m.get("content") or "").strip()
    return ""


@app.get("/events/{event_id}/followup", response_class=HTMLResponse)
def followup_page(
    request: Request, event_id: str, after_skip: str = ""
) -> HTMLResponse:
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)
    if needs_cast_confirm(ev):
        return RedirectResponse(
            url=f"/events/{event_id}/cast", status_code=303
        )

    error = None
    fu: Optional[dict[str, Any]] = None
    try:
        qa = ev.get("qa_thread") or []
        if qa and qa[-1].get("role") == "assistant":
            last_q = (qa[-1].get("content") or "").strip()
            fu = {
                "question": last_q,
                "ready_to_generate": _looks_complete_question(last_q),
                "reason": "",
            }
        else:
            ev, fu = ensure_pending_question(ev)
            ev = get_event(event_id) or ev
    except Exception as e:
        error = format_llm_error(e)
        fu = {
            "question": "",
            "ready_to_generate": False,
            "reason": "",
        }

    # 顯示文案：永遠以 qa_thread 最後 AI 為準
    display_q = _last_assistant_question(ev)
    if not display_q and fu:
        display_q = (fu.get("question") or "").strip()
    ready_complete = bool(fu and fu.get("ready_to_generate")) or (
        bool(display_q) and _looks_complete_question(display_q)
    )
    if error and not display_q:
        # 有錯誤時頂框給明確提示，避免只顯示「尚無問題」
        display_q = "目前無法取得 AI 追問，請查看上方錯誤訊息後再試。"
        ready_complete = False
    elif ready_complete:
        display_q = "故事已大致完整。還有需要補充的嗎？沒有的話可按「到此為止」。"
    elif not display_q:
        display_q = "（尚無問題）"

    skip_wrap_hint = after_skip in ("1", "true", "yes") and ready_complete

    return templates.TemplateResponse(
        "followup.html",
        {
            "request": request,
            "ev": ev,
            "fu": fu,
            "display_question": display_q,
            "ready_complete": ready_complete,
            "skip_wrap_hint": skip_wrap_hint,
            "error": error,
            "page": "followup",
            "list_title": _event_title(ev),
            "parent_title": _parent_title_line(ev),
        },
    )


@app.post("/events/{event_id}/followup")
def followup_action(
    event_id: str,
    action: str = Form("answer"),  # answer | skip | done（缺省視為回答）
    answer: str = Form(""),
) -> RedirectResponse:
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)
    if needs_cast_confirm(ev):
        return RedirectResponse(
            url=f"/events/{event_id}/cast", status_code=303
        )

    action = (action or "answer").strip().lower()
    if action == "done":
        set_status(event_id, "awaiting_generate")
        return RedirectResponse(url=f"/events/{event_id}/generate", status_code=303)
    if action == "skip":
        # 跳過本題 → 立刻產下一問；若已無問題則進入「可到此為止」狀態（勿靜默無反應）
        append_qa(event_id, "user", "（跳過）")
        wrap = False
        try:
            ev2 = get_event(event_id) or ev
            _ev_u, fu = ensure_pending_question(ev2)
            wrap = bool(fu and fu.get("ready_to_generate"))
        except Exception:
            # GET 頁會再試／顯示錯誤
            pass
        if wrap:
            return RedirectResponse(
                url=f"/events/{event_id}/followup?after_skip=1",
                status_code=303,
            )
        return RedirectResponse(
            url=f"/events/{event_id}/followup", status_code=303
        )
    # answer（含未知 action：保守當回答）
    text = to_traditional((answer or "").strip())
    if text:
        append_qa(event_id, "user", text)
    return RedirectResponse(url=f"/events/{event_id}/followup", status_code=303)


def _generate_ctx(
    request: Request,
    ev: dict[str, Any],
    *,
    error: Optional[str] = None,
    ready: bool = False,
) -> dict[str, Any]:
    story = ev.get("story") if isinstance(ev.get("story"), dict) else None
    has_story = bool(story and (story.get("body") or "").strip())
    return {
        "request": request,
        "ev": ev,
        "page": "generate",
        "list_title": _event_title(ev),
        "error": error,
        "ready": bool(ready and has_story),
        "story": story or {},
        "scores": _scored_parts(ev) if has_story else [],
        "parent_title": _parent_title_line(ev),
    }


def _has_story(ev: dict[str, Any]) -> bool:
    story = ev.get("story") if isinstance(ev.get("story"), dict) else None
    return bool(story and (story.get("body") or "").strip())


def _has_scores(ev: dict[str, Any]) -> bool:
    return any(
        not p.get("is_user") and p.get("event_score") is not None
        for p in (ev.get("participants") or [])
    )


def _auto_score_event(event_id: str) -> Optional[str]:
    """成稿後補評分；失敗回傳警告字串。"""
    from story_score import apply_ai_scores_to_event, save_participants, suggest_scores

    ev = get_event(event_id)
    if ev is None or not _has_story(ev):
        return "找不到成稿，無法評分。"
    if _has_scores(ev):
        return None
    try:
        score_payload = suggest_scores(ev)
        merged, _warnings = apply_ai_scores_to_event(ev, score_payload)
        save_participants(
            event_id, merged["participants"], merged.get("score_mean")
        )
        return None
    except Exception as e:
        return format_llm_error(e)


@app.get("/events/{event_id}/generate", response_class=HTMLResponse)
def generate_page(
    request: Request, event_id: str, fresh: str = "", warn: str = ""
) -> HTMLResponse:
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    force_fresh = fresh in ("1", "true", "yes")
    error = None
    if warn == "score":
        error = (
            "成稿已寫入，但 AI 自動評分失敗（可能無回應或額度不足）。"
            "可重新生成，或直接確認落盤（無分角色會略過）。"
        )

    if force_fresh:
        clear_job(event_id)

    job = job_snapshot(event_id)
    if job.get("status") == "error" and job.get("error"):
        error = str(job["error"])
    elif job.get("status") == "done" and job.get("error"):
        error = str(job["error"])

    # 背景還在跑：顯示等待 UI
    if is_running(event_id) and not force_fresh:
        return templates.TemplateResponse(
            "generate.html",
            {
                **_generate_ctx(request, ev, error=error, ready=False),
                "job_running": True,
                "job_phase": job.get("phase") or "generate",
            },
        )

    # 已有成稿：直接進調分（不再在 GET 阻塞呼叫 AI 評分）
    if _has_story(ev) and not force_fresh:
        return templates.TemplateResponse(
            "generate.html",
            {
                **_generate_ctx(request, ev, error=error, ready=True),
                "job_running": False,
                "job_phase": "",
            },
        )

    return templates.TemplateResponse(
        "generate.html",
        {
            **_generate_ctx(request, ev, error=error, ready=False),
            "job_running": False,
            "job_phase": "",
        },
    )


@app.get("/events/{event_id}/generate/status")
def generate_status(event_id: str) -> JSONResponse:
    """輪詢背景生成狀態。"""
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    job = job_snapshot(event_id)
    return JSONResponse(
        {
            "status": job.get("status") or ("done" if _has_story(ev) else "idle"),
            "phase": job.get("phase") or "",
            "error": job.get("error"),
            "has_story": _has_story(ev),
            "has_scores": _has_scores(ev),
            "running": is_running(event_id),
        }
    )


@app.post("/events/{event_id}/generate/start")
async def generate_start(
    event_id: str, force: str = ""
) -> JSONResponse:
    """立刻回傳，在背景執行成稿＋評分。"""
    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return JSONResponse({"ok": True, "status": "done", "has_story": True})

    force_run = force in ("1", "true", "yes")

    # 已有成稿且未要求重跑 → 直接完成
    if _has_story(ev) and not is_running(event_id) and not force_run:
        return JSONResponse(
            {
                "ok": True,
                "status": "done",
                "has_story": True,
                "has_scores": _has_scores(ev),
            }
        )

    if force_run:
        clear_job(event_id)

    job = start_generate_job(event_id)
    return JSONResponse(
        {
            "ok": True,
            "status": job.get("status") or "running",
            "phase": job.get("phase") or "generate",
        }
    )


@app.post("/events/{event_id}/generate", response_class=HTMLResponse)
async def generate_run(request: Request, event_id: str) -> HTMLResponse:
    from storage.confirm import confirm_event
    from storage.scoring import mean_of_scores
    from story_score import save_participants

    ev = get_event(event_id)
    if ev is None:
        raise HTTPException(404, "找不到事件")
    if ev.get("status") == "confirmed":
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    form = await request.form()
    action = (form.get("action") or "run").strip().lower()

    # —— 確認落盤（可調分後） ——
    if action == "confirm":
        try:
            count = int(form.get("score_count") or "0")
        except ValueError:
            count = 0
        parts = [dict(p) for p in (ev.get("participants") or [])]
        non_user = [p for p in parts if not p.get("is_user")]
        for i in range(count):
            raw = form.get(f"score_{i}")
            name = (form.get(f"name_{i}") or "").strip()
            reason = to_traditional((form.get(f"reason_{i}") or "").strip())
            try:
                sc = int(str(raw).strip())
            except (TypeError, ValueError):
                continue
            target = None
            if i < len(non_user):
                target = non_user[i]
            if name:
                for p in non_user:
                    if (p.get("temp_name") or "") == name:
                        target = p
                        break
            if target is not None:
                target["event_score"] = sc
                # 使用者可改 AI 評語，落盤寫入 score_reason
                target["score_reason"] = reason
        scores_list = [
            int(p["event_score"])
            for p in parts
            if not p.get("is_user") and p.get("event_score") is not None
        ]
        mean = mean_of_scores(scores_list) if scores_list else None
        save_participants(event_id, parts, mean)
        clear_job(event_id)
        confirm_event(event_id, clamp_scores=True)
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    # 舊表單 POST run：改導向背景任務（相容）
    if action in ("run", "generate", ""):
        if _has_story(ev) and not is_running(event_id):
            return RedirectResponse(
                url=f"/events/{event_id}/generate", status_code=303
            )
        start_generate_job(event_id)
        return RedirectResponse(
            url=f"/events/{event_id}/generate", status_code=303
        )

    return RedirectResponse(url=f"/events/{event_id}/generate", status_code=303)


@app.get("/events/{event_id}/score", response_class=HTMLResponse)
def score_page(event_id: str) -> RedirectResponse:
    """舊評分入口改併入 AI 生成頁。"""
    return RedirectResponse(url=f"/events/{event_id}/generate", status_code=303)


@app.post("/events/{event_id}/score", response_class=HTMLResponse)
async def score_run(event_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/events/{event_id}/generate", status_code=303)


# —— 放棄未落盤事件（流程各步共用） ——


@app.post("/events/{event_id}/abandon")
def abandon_event(event_id: str) -> RedirectResponse:
    """刪除未 confirmed 草稿／進行中事件，回首頁。"""
    ev = get_event(event_id)
    if ev is None:
        return RedirectResponse(url="/", status_code=303)
    if ev.get("status") == "confirmed":
        raise HTTPException(status_code=400, detail="已落成事件請用「刪除」")
    try:
        ids = list_subtree_ids(event_id)
        for i in ids:
            clear_job(i)
        delete_draft_event(event_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url="/?abandoned=1", status_code=303)


@app.post("/events/{event_id}/delete")
def delete_event_route(event_id: str) -> RedirectResponse:
    """
    刪除本篇；若有後續則連刪全部子孫。
    清除 ledger 後重算歷史榜。刪子不刪父。
    成功／失敗皆回首頁（計分榜），避免停在已刪事件或錯誤頁。
    """
    try:
        if get_event(event_id) is not None:
            for i in list_subtree_ids(event_id):
                try:
                    clear_job(i)
                except Exception:
                    pass
            delete_event_tree(event_id, recompute_scores=True)
    except Exception:
        pass
    return RedirectResponse(url="/", status_code=303)


# —— 一鍵銷毀（低調入口：頁腳；確認框後才執行） ——


@app.get("/settings/wipe", response_class=HTMLResponse)
def wipe_page(request: Request) -> HTMLResponse:
    empty = is_local_data_empty()
    return templates.TemplateResponse(
        "wipe.html",
        {
            "request": request,
            "page": "wipe",
            "error": None,
            "already_empty": empty,
        },
    )


@app.post("/settings/wipe", response_class=HTMLResponse)
def wipe_run(
    request: Request,
    confirm: str = Form(""),
) -> HTMLResponse:
    if is_local_data_empty():
        return templates.TemplateResponse(
            "wipe.html",
            {
                "request": request,
                "page": "wipe",
                "error": None,
                "already_empty": True,
                "show_empty_hint": True,
            },
        )
    # 須經確認框送出 confirm=1
    if confirm not in ("1", "yes", "true", "on"):
        return templates.TemplateResponse(
            "wipe.html",
            {
                "request": request,
                "page": "wipe",
                "error": "未確認，未執行銷毀。請再次點「一鍵銷毀」並在確認框選擇確認。",
                "already_empty": False,
            },
            status_code=400,
        )
    wipe_all_local_data()
    clear_all_jobs()
    return RedirectResponse(url="/?wiped=1", status_code=303)


def main() -> None:
    import uvicorn

    # 只監看程式目錄，避免 data/*.jsonl 寫入觸發 reload 掐斷 AI 回應
    uvicorn.run(
        "ui.app:app",
        host="127.0.0.1",
        port=8765,
        reload=True,
        reload_dirs=[
            str(ROOT / "ui"),
            str(ROOT / "storage"),
            str(ROOT / "skill"),
            str(ROOT),  # 根目錄 .py（llm_client、story_*）
        ],
        reload_includes=["*.py"],
        reload_excludes=["data", "dev-local", ".venv"],
        app_dir=str(ROOT),
    )


if __name__ == "__main__":
    main()
