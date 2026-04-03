# -*- coding: utf-8 -*-
"""V2 任务模块 Service：聚合查询、领奖、活跃值累计。"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from server.services.v2 import quest_dao, points_service

logger = logging.getLogger(__name__)

DAILY_BOX_TASKTYPE = 99
WEEKLY_BOX_TASKTYPE = 100

TASKTYPE_LABELS = {
    1: "升级",
    3: "学堂学习",
    5: "摇卦",
    6: "祈福",
    7: "查看运势",
}


def _today_key() -> str:
    return date.today().isoformat()


def _week_key() -> str:
    d = date.today()
    return f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"


def get_quest_overview(user_id: int) -> Dict[str, Any]:
    """一次性返回日常/每日宝箱/每周宝箱/主线/活跃值。"""
    today = _today_key()
    week = _week_key()

    daily_configs = quest_dao.get_daily_quest_configs()
    daily_progress = {
        r["quest_config_id"]: r
        for r in quest_dao.get_user_daily_progress(user_id, today)
    }
    daily_list = []
    for c in daily_configs:
        cid = int(c["id"])
        prog = daily_progress.get(cid, {})
        daily_list.append({
            "id": cid,
            "name": c["name"],
            "tasktype": int(c["tasktype"]),
            "target": int(c["condition_count"]),
            "progress": int(prog.get("progress", 0)),
            "completed": bool(prog.get("completed", 0)),
            "claimed": bool(prog.get("claimed", 0)),
            "reward_item_id": int(c["reward_item_id"]),
            "reward_num": int(c["reward_num"]),
            "activity_point": int(c["activity_point"]),
        })

    def _build_boxes(tasktype: int, period_key: str) -> List[Dict[str, Any]]:
        configs = quest_dao.get_box_configs(tasktype)
        prog_map = {
            r["quest_config_id"]: r
            for r in quest_dao.get_user_daily_progress(user_id, period_key)
        }
        out = []
        for c in configs:
            cid = int(c["id"])
            prog = prog_map.get(cid, {})
            out.append({
                "id": cid,
                "name": c["name"],
                "threshold": int(c["condition_count"]),
                "reward_item_id": int(c["reward_item_id"]),
                "reward_num": int(c["reward_num"]),
                "claimed": bool(prog.get("claimed", 0)),
            })
        return out

    daily_boxes = _build_boxes(DAILY_BOX_TASKTYPE, today)
    weekly_boxes = _build_boxes(WEEKLY_BOX_TASKTYPE, week)

    daily_activity = quest_dao.get_activity_points(user_id, "daily", today)
    weekly_activity = quest_dao.get_activity_points(user_id, "weekly", week)

    main_quests = quest_dao.get_current_main_quests(user_id)
    main_list = []
    for q in main_quests:
        main_list.append({
            "id": int(q["id"]),
            "tasktype": int(q["tasktype"]),
            "tasktype_label": TASKTYPE_LABELS.get(int(q["tasktype"]), ""),
            "taskname": q.get("taskname") or "",
            "condition_value": int(q["condition_value"]),
            "award_item_id": int(q["award_item_id"]),
            "award_num": int(q["award_num"]),
            "completed": bool(q.get("completed", 0)),
            "claimed": bool(q.get("claimed", 0)),
        })

    return {
        "daily": daily_list,
        "daily_boxes": daily_boxes,
        "weekly_boxes": weekly_boxes,
        "daily_activity": daily_activity,
        "weekly_activity": weekly_activity,
        "main": main_list,
    }


def claim_daily_reward(user_id: int, quest_config_id: int) -> Dict[str, Any]:
    """领取每日任务奖励：发命运点 + 活跃值。"""
    today = _today_key()
    week = _week_key()

    configs = quest_dao.get_daily_quest_configs()
    cfg = next((c for c in configs if int(c["id"]) == quest_config_id), None)
    if not cfg:
        return {"ok": False, "error": "config_not_found"}

    ok = quest_dao.claim_daily_quest(user_id, quest_config_id, today)
    if not ok:
        return {"ok": False, "error": "not_claimable"}

    reward_num = int(cfg["reward_num"])
    activity = int(cfg["activity_point"])

    pts_result = points_service.add_points(user_id, reward_num, "quest_daily", f"daily_{quest_config_id}")

    if activity > 0:
        quest_dao.add_activity_points(user_id, "daily", today, activity)
        quest_dao.add_activity_points(user_id, "weekly", week, activity)

    return {
        "ok": True,
        "reward_item_id": int(cfg["reward_item_id"]),
        "reward_num": reward_num,
        "activity_added": activity,
        "destiny_points": pts_result.get("destiny_points"),
    }


def claim_main_reward(user_id: int, quest_id: int) -> Dict[str, Any]:
    """领取主线任务奖励。"""
    cfg = quest_dao.get_main_quest_by_id(quest_id)
    if not cfg:
        return {"ok": False, "error": "quest_not_found"}

    ok = quest_dao.claim_main_quest(user_id, quest_id)
    if not ok:
        return {"ok": False, "error": "not_claimable"}

    reward_num = int(cfg["award_num"])
    pts_result = points_service.add_points(user_id, reward_num, "quest_main", f"main_{quest_id}")

    return {
        "ok": True,
        "reward_item_id": int(cfg["award_item_id"]),
        "reward_num": reward_num,
        "destiny_points": pts_result.get("destiny_points"),
    }


def claim_box_reward(user_id: int, box_config_id: int) -> Dict[str, Any]:
    """领取宝箱奖励（需活跃值达到阈值）。"""
    configs_daily = quest_dao.get_box_configs(DAILY_BOX_TASKTYPE)
    configs_weekly = quest_dao.get_box_configs(WEEKLY_BOX_TASKTYPE)
    all_cfgs = configs_daily + configs_weekly

    cfg = next((c for c in all_cfgs if int(c["id"]) == box_config_id), None)
    if not cfg:
        return {"ok": False, "error": "box_not_found"}

    tt = int(cfg["tasktype"])
    threshold = int(cfg["condition_count"])

    if tt == DAILY_BOX_TASKTYPE:
        period_key = _today_key()
        period_type = "daily"
    else:
        period_key = _week_key()
        period_type = "weekly"

    current_pts = quest_dao.get_activity_points(user_id, period_type, period_key)
    if current_pts < threshold:
        return {"ok": False, "error": "activity_not_enough", "current": current_pts, "need": threshold}

    ok = quest_dao.claim_box(user_id, box_config_id, period_key)
    if not ok:
        return {"ok": False, "error": "already_claimed"}

    reward_num = int(cfg["reward_num"])
    pts_result = points_service.add_points(user_id, reward_num, "quest_box", f"box_{box_config_id}")

    return {
        "ok": True,
        "reward_item_id": int(cfg["reward_item_id"]),
        "reward_num": reward_num,
        "destiny_points": pts_result.get("destiny_points"),
    }


def record_daily_action(user_id: int, tasktype: int) -> Optional[Dict[str, Any]]:
    """
    外部事件触发（如完成祈福 → tasktype=6）。
    匹配每日任务配置 → 进度+1。
    """
    today = _today_key()
    configs = quest_dao.get_daily_quest_configs()
    cfg = next((c for c in configs if int(c["tasktype"]) == tasktype), None)
    if not cfg:
        return None

    target = int(cfg["condition_count"])
    new_prog, newly_completed = quest_dao.increment_daily_progress(
        user_id, int(cfg["id"]), today, target,
    )
    return {
        "quest_config_id": int(cfg["id"]),
        "progress": new_prog,
        "target": target,
        "newly_completed": newly_completed,
    }
