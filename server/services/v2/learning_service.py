# -*- coding: utf-8 -*-
"""V2 学堂：解锁链、测验、奖励（命运点、经验、随机掉落）。"""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from server.services.v2 import economy_dao, learning_dao, points_service, xp_service
from server.services.v2 import juqing_service

logger = logging.getLogger(__name__)

# 与 Excel 关卡表无测验字段时的默认题库（与旧前端一致）
DEFAULT_QUIZ_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "q1",
        "text": "五行中「金」所克的元素是？",
        "options": ["木", "水", "火", "土"],
        "correct": 0,
    },
    {
        "id": "q2",
        "text": "四柱八字中的「日主」指的是？",
        "options": ["年干", "月干", "日干", "时干"],
        "correct": 2,
    },
    {
        "id": "q3",
        "text": "地支「子」的阴阳属性为？",
        "options": ["阳", "阴", "中性", "随月而变"],
        "correct": 1,
    },
]

EXPERIENCE_VARIANT_LABELS = ("寻道", "问道", "悟道", "践道")


def _quiz_for_level(row: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if row and row.get("quiz_json"):
        raw = row["quiz_json"]
        if isinstance(raw, list) and len(raw) > 0:
            return raw
    return DEFAULT_QUIZ_QUESTIONS


def _normalize_quiz_public(qlist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for q in qlist:
        out.append(
            {
                "id": str(q.get("id", "")),
                "text": str(q.get("text", "")),
                "options": list(q.get("options") or []),
                "type": str(q.get("type", "single")),
            }
        )
    return out


def _playable(level: Dict[str, Any], completed: set) -> bool:
    ul = level.get("unlock_sn")
    if ul is None:
        return True
    return int(ul) in completed


def get_chapters_payload(user_id: int) -> Dict[str, Any]:
    chapters = learning_dao.fetch_all_chapters()
    completed = learning_dao.get_user_completed_level_sns(user_id)
    items: List[Dict[str, Any]] = []
    for ch in chapters:
        cid = int(ch["id"])
        levels = learning_dao.fetch_levels_by_chapter(cid)
        total = len(levels)
        done = sum(1 for lv in levels if int(lv["sn"]) in completed)
        if cid == 1:
            unlocked = True
        else:
            prev_levels = learning_dao.fetch_levels_by_chapter(cid - 1)
            if prev_levels:
                last_sn = int(prev_levels[-1]["sn"])
                unlocked = last_sn in completed
            else:
                unlocked = False
        pct = int(round(100 * done / total)) if total else 0
        items.append(
            {
                "id": cid,
                "code": str(cid),
                "name": ch["name"],
                "description": ch.get("description") or "",
                "cover": ch.get("cover_scene") or "",
                "sections_count": total,
                "completed_stages": done,
                "completed_pct": pct,
                "unlocked": unlocked,
            }
        )
    return {"chapters": items}


def get_stages_payload(user_id: int, chapter_id: int) -> Dict[str, Any]:
    ch_rows = learning_dao.fetch_all_chapters()
    ch = next((c for c in ch_rows if int(c["id"]) == chapter_id), None)
    if not ch:
        return {"error": "chapter_not_found"}
    completed = learning_dao.get_user_completed_level_sns(user_id)
    levels = learning_dao.fetch_levels_by_chapter(chapter_id)
    stages = []
    for lv in levels:
        sn = int(lv["sn"])
        playable = _playable(lv, completed)
        is_done = sn in completed
        locked = not playable and not is_done
        stages.append(
            {
                "sn": sn,
                "code": str(sn),
                "chapter_id": chapter_id,
                "stage_index": int(lv["stage_index"]),
                "name": lv["name"],
                "battlefield": int(lv["battlefield"]),
                "locked": locked,
                "completed": is_done,
                "playable": playable or is_done,
                "reward_preview": {
                    "destiny_points": int(lv["reward_coin_num"]) if int(lv["reward_coin_id"]) == 1001 else 0,
                    "xp": int(lv["reward_xp_num"]) if int(lv["reward_xp_id"]) == 1002 else 0,
                },
            }
        )
    return {
        "chapter": {
            "id": chapter_id,
            "name": ch["name"],
            "description": ch.get("description") or "",
            "cover": str(ch.get("cover_scene") or "201"),
        },
        "stages": stages,
    }


def get_stage_detail(user_id: int, stage_sn: int) -> Dict[str, Any]:
    row = learning_dao.fetch_level_by_sn(stage_sn)
    if not row:
        return {"error": "level_not_found"}
    completed = learning_dao.get_user_completed_level_sns(user_id)
    playable = _playable(row, completed)
    is_done = stage_sn in completed
    if not playable and not is_done:
        return {"error": "level_locked"}
    variant = random.randrange(0, 4)
    start_lines = []
    end_lines = []
    if row.get("start_drama_id"):
        start_lines = juqing_service.get_dialogue(int(row["start_drama_id"])) or []
    if row.get("end_drama_id"):
        end_lines = juqing_service.get_dialogue(int(row["end_drama_id"])) or []
    body = row.get("lesson_body") or (
        f"本关「{row['name']}」：结合六爻与命理基础，循序渐进。完成下方测验即可领取通关奖励。"
    )
    return {
        "stage": {
            "sn": stage_sn,
            "chapter_id": int(row["chapter_id"]),
            "stage_index": int(row["stage_index"]),
            "name": row["name"],
            "battlefield": int(row["battlefield"]),
            "completed": is_done,
        },
        "lesson_body": body,
        "experience_variant": variant,
        "experience_variant_label": EXPERIENCE_VARIANT_LABELS[variant],
        "start_dialogue": start_lines,
        "end_dialogue": end_lines,
    }


def get_quiz_payload(user_id: int, stage_sn: int) -> Dict[str, Any]:
    row = learning_dao.fetch_level_by_sn(stage_sn)
    if not row:
        return {"error": "level_not_found"}
    completed = learning_dao.get_user_completed_level_sns(user_id)
    if not _playable(row, completed) and stage_sn not in completed:
        return {"error": "level_locked"}
    qlist = _quiz_for_level(row)
    return {
        "quiz_id": stage_sn,
        "battlefield": int(row["battlefield"]),
        "questions": _normalize_quiz_public(qlist),
    }


def _score_answers(qlist: List[Dict[str, Any]], answers: List[int]) -> int:
    if len(answers) < len(qlist):
        return -1
    score = 0
    for i, q in enumerate(qlist):
        correct = q.get("correct")
        if correct is None:
            continue
        if int(answers[i]) == int(correct):
            score += 1
    return score


def _roll_drop(drop_id: int) -> Optional[Tuple[int, int]]:
    d = learning_dao.fetch_drop_by_sn(drop_id)
    if not d:
        return None
    ids = d.get("item_ids") or []
    rates = d.get("rates") or []
    qtys = d.get("quantities") or []
    if len(ids) != len(rates) or len(ids) != len(qtys) or not ids:
        return None
    total = sum(int(x) for x in rates)
    if total <= 0:
        return None
    r = random.randint(1, total)
    acc = 0
    for i, w in enumerate(rates):
        acc += int(w)
        if r <= acc:
            return int(ids[i]), int(qtys[i])
    return int(ids[-1]), int(qtys[-1])


def complete_stage(
    user_id: int,
    stage_sn: int,
    answers: Optional[List[int]] = None,
) -> Dict[str, Any]:
    row = learning_dao.fetch_level_by_sn(stage_sn)
    if not row:
        return {"ok": False, "error": "level_not_found"}
    completed = learning_dao.get_user_completed_level_sns(user_id)
    if stage_sn in completed:
        return {
            "ok": True,
            "already_completed": True,
            "rewards": None,
        }
    if not _playable(row, completed):
        return {"ok": False, "error": "level_locked"}
    qlist = _quiz_for_level(row)
    if answers is None:
        answers = []
    sc = _score_answers(qlist, answers)
    if sc < 0:
        return {"ok": False, "error": "invalid_answers"}

    reward_coin_id = int(row["reward_coin_id"])
    reward_coin_num = int(row["reward_coin_num"])
    reward_xp_num = int(row["reward_xp_num"])
    drop_id = int(row["drop_id"])

    drops_granted: List[Dict[str, Any]] = []

    if reward_coin_id == economy_dao.DESTINY_CURRENCY_ITEM_ID and reward_coin_num > 0:
        pr = points_service.add_points(user_id, reward_coin_num, "academy", f"level_{stage_sn}")
        if not pr.get("ok"):
            logger.warning("add_points failed for user %s: %s", user_id, pr)

    if reward_xp_num > 0:
        xr = xp_service.add_xp(user_id, reward_xp_num, "academy", f"level_{stage_sn}")
        if not xr.get("ok"):
            logger.warning("add_xp failed for user %s: %s", user_id, xr)

    rolled = _roll_drop(drop_id)
    if rolled:
        item_id, qty = rolled
        if economy_dao.add_to_inventory(user_id, item_id, qty):
            drops_granted.append({"item_id": item_id, "quantity": qty})

    learning_dao.insert_level_completion(user_id, stage_sn, sc)

    return {
        "ok": True,
        "already_completed": False,
        "score": sc,
        "total_questions": len(qlist),
        "rewards": {
            "destiny_points": reward_coin_num if reward_coin_id == economy_dao.DESTINY_CURRENCY_ITEM_ID else 0,
            "xp": reward_xp_num,
            "drops": drops_granted,
        },
    }
