"""
評分約束（DATA_CONTRACT §5）。

- 只評 is_user == false
- event_score ∈ [-100, 100] 整數
- 同場平均 ±10：L=floor(μ-10), R=ceil(μ+10)，再 ∩ [-100,100]
- 不合法時 clamp 進 [L,R]，最多 5 輪；仍失敗則報錯
- score_mean 展示用 round(μ)
"""
from __future__ import annotations

import math
from typing import Any, Optional


def scored_participants(participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """非使用者且已有 event_score 的參與者。"""
    out = []
    for p in participants:
        if p.get("is_user"):
            continue
        if p.get("event_score") is None:
            continue
        out.append(p)
    return out


def mean_of_scores(scores: list[int]) -> float:
    if not scores:
        raise ValueError("至少需要一個被評分分數才能算平均")
    return sum(scores) / len(scores)


def legal_bounds(mu: float) -> tuple[int, int]:
    lo = max(-100, math.floor(mu - 10))
    hi = min(100, math.ceil(mu + 10))
    if lo > hi:
        # 理論上 μ∈[-100,100] 時不該發生；保守處理
        lo, hi = -100, 100
    return lo, hi


def scores_in_bounds(scores: list[int], lo: int, hi: int) -> bool:
    return all(lo <= s <= hi for s in scores)


def clamp_scores(scores: list[int], lo: int, hi: int) -> list[int]:
    return [min(hi, max(lo, s)) for s in scores]


def validate_or_clamp_scores(
    scores: list[int],
    *,
    max_rounds: int = 5,
    clamp: bool = True,
) -> tuple[list[int], float, int]:
    """
    回傳 (合法分數列表, μ, score_mean=round(μ))。
    clamp=False 時不合法直接 ValueError。
    """
    if not scores:
        raise ValueError("被評分角色至少一人且須有 event_score")
    for s in scores:
        if not isinstance(s, int) or isinstance(s, bool):
            raise ValueError("event_score 必須為整數")
        if s < -100 or s > 100:
            raise ValueError(f"event_score 超出 ±100：{s}")

    current = list(scores)
    for _ in range(max_rounds):
        mu = mean_of_scores(current)
        lo, hi = legal_bounds(mu)
        if scores_in_bounds(current, lo, hi):
            return current, mu, int(round(mu))
        if not clamp:
            raise ValueError(
                f"分數不在平均±10 內：scores={current} μ={mu:.4f} 合法[{lo},{hi}]"
            )
        current = clamp_scores(current, lo, hi)

    mu = mean_of_scores(current)
    lo, hi = legal_bounds(mu)
    if not scores_in_bounds(current, lo, hi):
        raise ValueError(
            f"clamp {max_rounds} 次後仍不合法：scores={current} μ={mu:.4f} [{lo},{hi}]；請手調"
        )
    return current, mu, int(round(mu))


def apply_scores_to_participants(
    participants: list[dict[str, Any]],
    *,
    clamp: bool = True,
) -> tuple[list[dict[str, Any]], Optional[float], Optional[int]]:
    """
    就地驗證／clamp 非使用者分數；使用者必須 event_score is None。
    回傳 (新 participants, μ 或 None, score_mean 或 None)。
    若無人被評分：允許（score_mean=None），例如尚未生成。
    """
    out: list[dict[str, Any]] = [dict(p) for p in participants]
    for p in out:
        if p.get("is_user") and p.get("event_score") is not None:
            raise ValueError("使用者 participant 的 event_score 必須是 null")

    idxs = []
    scores: list[int] = []
    for i, p in enumerate(out):
        if p.get("is_user"):
            continue
        sc = p.get("event_score")
        if sc is None:
            continue
        idxs.append(i)
        scores.append(int(sc))

    if not scores:
        return out, None, None

    fixed, mu, mean_i = validate_or_clamp_scores(scores, clamp=clamp)
    for i, sc in zip(idxs, fixed):
        out[i]["event_score"] = sc
    return out, mu, mean_i
