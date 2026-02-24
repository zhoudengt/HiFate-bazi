#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户画像服务 - 年运报告用户分层
基于年龄/性别/命盘/用户自选标签，构建用户关注优先级和状态标记
供 AnnualReportService 调用，完全独立，失败时降级为空字典不影响主流程
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.utils.dayun_liunian_helper import calculate_user_age

logger = logging.getLogger(__name__)

# 年龄性别分层表（默认关注优先级）
# 来源：命理框架 standards/命理框架.md 第1层基础分层
_AGE_GENDER_FOCUS_TABLE = {
    ("18-22", "male"):   ["学业", "财运", "桃花", "健康"],
    ("18-22", "female"): ["学业", "桃花", "财运", "健康"],
    ("23-27", "male"):   ["事业", "财运", "桃花", "健康"],
    ("23-27", "female"): ["桃花", "事业", "财运", "健康"],
    ("28-35", "male"):   ["事业", "财运", "桃花", "健康"],
    ("28-35", "female"): ["桃花", "事业", "财运", "健康"],
    ("36-45", "male"):   ["财运", "事业", "健康", "人际"],
    ("36-45", "female"): ["健康", "人际", "财运", "事业"],
    ("46-55", "male"):   ["健康", "财运", "人际", "事业"],
    ("46-55", "female"): ["健康", "人际", "财运", "事业"],
    ("55+", "male"):     ["健康", "人际", "财运", "精神生活"],
    ("55+", "female"):   ["健康", "人际", "财运", "精神生活"],
}

# 五行 → 对应脏腑
_ELEMENT_ORGAN_MAP = {
    "金": ["肺系", "大肠"],
    "木": ["肝系", "胆"],
    "水": ["肾系", "膀胱"],
    "火": ["心系", "小肠"],
    "土": ["脾系", "胃"],
}

# 情绪联动：主线压力源 → 对应健康影响
_EMOTION_LINK_MAP = {
    "事业压力": "肝气郁结",
    "感情困扰": "心火上炎",
    "财务焦虑": "脾气虚弱",
    "人际消耗": "肺气不宣",
}


def _get_age_group(age: int) -> str:
    if age <= 22:
        return "18-22"
    elif age <= 27:
        return "23-27"
    elif age <= 35:
        return "28-35"
    elif age <= 45:
        return "36-45"
    elif age <= 55:
        return "46-55"
    else:
        return "55+"


class UserProfileService:
    """用户画像服务（年运报告分层）"""

    @staticmethod
    def build_user_profile(
        solar_date: str,
        gender: str,
        bazi_data: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        target_year: int,
        focus_tags: Optional[List[str]] = None,
        relationship_status: Optional[str] = None,
        career_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        三层漏斗构建用户画像

        第1层：age + gender → 默认 focus_priority
        第2层：命盘状态检测 → 覆盖排序
        第3层：用户自选 focus_tags → 最高优先级覆盖

        Args:
            solar_date: 出生阳历日期 YYYY-MM-DD
            gender: male / female
            bazi_data: 八字基础数据（含 ten_gods_stats / element_counts）
            wangshuai_data: 旺衰数据（含 xi_shen / ji_shen）
            target_year: 目标年份
            focus_tags: 用户自选标签，如 ["事业","桃花"]
            relationship_status: single / dating / married
            career_status: employed / unemployed / freelance / student

        Returns:
            dict: {
                age, gender, age_group, focus_priority,
                focus_source, bazi_states, user_tags
            }
        """
        try:
            # 计算年龄
            age = calculate_user_age(solar_date)
            age_group = _get_age_group(age)

            # 第1层：年龄性别默认排序
            gender_key = gender if gender in ("male", "female") else "male"
            default_priority = _AGE_GENDER_FOCUS_TABLE.get(
                (age_group, gender_key),
                ["事业", "财运", "健康", "人际"]
            )
            focus_priority = list(default_priority)
            focus_source = "age_default"

            # 第2层：命盘智能判断
            bazi_states = UserProfileService._detect_bazi_states(
                bazi_data, wangshuai_data, target_year
            )
            if bazi_states:
                # 根据命盘检测到的强信号调整优先级
                bazi_priority = UserProfileService._bazi_states_to_priority(bazi_states)
                if bazi_priority:
                    # 将命盘检测到的高优先级事项移到前面，保留完整列表
                    reordered = list(bazi_priority)
                    for item in focus_priority:
                        if item not in reordered:
                            reordered.append(item)
                    focus_priority = reordered
                    focus_source = "bazi_detect"

            # 第3层：用户主动选择（最高优先级）
            if focus_tags:
                valid_tags = [t for t in focus_tags if t in ["事业", "桃花", "财运", "健康", "学业", "人际"]]
                if valid_tags:
                    reordered = list(valid_tags)
                    for item in focus_priority:
                        if item not in reordered:
                            reordered.append(item)
                    focus_priority = reordered
                    focus_source = "user_choice"

            # 确保财运始终在列表中（万金油）
            if "财运" not in focus_priority:
                focus_priority.append("财运")

            # 用户自报状态标签
            user_tags = {}
            if relationship_status:
                user_tags["感情状态"] = {
                    "single": "单身",
                    "dating": "恋爱中",
                    "married": "已婚",
                }.get(relationship_status, relationship_status)
            if career_status:
                user_tags["职业状态"] = {
                    "employed": "在职",
                    "unemployed": "待业",
                    "freelance": "自由职业",
                    "student": "学生",
                }.get(career_status, career_status)

            return {
                "age": age,
                "gender": gender,
                "age_group": age_group,
                "focus_priority": focus_priority,
                "focus_source": focus_source,
                "bazi_states": bazi_states,
                "user_tags": user_tags,
            }

        except Exception as e:
            logger.warning(f"[UserProfileService] build_user_profile 失败，降级为空: {e}", exc_info=True)
            return {}

    @staticmethod
    def _detect_bazi_states(
        bazi_data: Dict[str, Any],
        wangshuai_data: Dict[str, Any],
        target_year: int,
    ) -> Dict[str, Any]:
        """
        从命盘提取当前状态标记（对应命理框架第2层）

        Returns:
            dict: {
                career: str,       # 事业状态标记
                romance: str,      # 桃花状态标记
                wealth: str,       # 财运状态标记
                health: str,       # 健康状态标记
                health_focus: list, # 需关注的脏腑
                emotion_link: str, # 跨模块情绪联动线索
            }
        """
        try:
            states = {}

            ten_gods = bazi_data.get("ten_gods_stats", {})
            element_counts = bazi_data.get("element_counts", {})
            xi_shen = wangshuai_data.get("xi_shen", "")
            ji_shen = wangshuai_data.get("ji_shen", "")

            # ---------- 事业状态检测 ----------
            career_state = UserProfileService._detect_career_state(ten_gods, xi_shen, ji_shen)
            if career_state:
                states["career"] = career_state

            # ---------- 桃花/感情状态检测 ----------
            romance_state = UserProfileService._detect_romance_state(bazi_data, ten_gods)
            if romance_state:
                states["romance"] = romance_state

            # ---------- 财运状态检测 ----------
            wealth_state = UserProfileService._detect_wealth_state(ten_gods, xi_shen, ji_shen)
            if wealth_state:
                states["wealth"] = wealth_state

            # ---------- 健康状态检测 ----------
            health_state, health_focus = UserProfileService._detect_health_state(element_counts)
            if health_state:
                states["health"] = health_state
            if health_focus:
                states["health_focus"] = health_focus

            # ---------- 跨模块情绪联动 ----------
            emotion_link = UserProfileService._build_emotion_link(states)
            if emotion_link:
                states["emotion_link"] = emotion_link

            return states

        except Exception as e:
            logger.warning(f"[UserProfileService] _detect_bazi_states 失败: {e}", exc_info=True)
            return {}

    @staticmethod
    def _detect_career_state(
        ten_gods: Dict[str, Any],
        xi_shen: str,
        ji_shen: str,
    ) -> str:
        """
        根据十神统计判断事业状态
        官杀混杂 → 被动变动型
        食伤生财 → 主动拓展型
        比劫夺财 → 竞争压力型
        印星过旺 → 方向迷茫型
        """
        if not ten_gods:
            return ""

        # 将十神统计转为数量字典（兼容多种格式）
        god_counts = {}
        for k, v in ten_gods.items():
            try:
                god_counts[k] = int(v) if not isinstance(v, int) else v
            except (ValueError, TypeError):
                god_counts[k] = 0

        zhengguang = god_counts.get("正官", 0)
        pianguang = god_counts.get("偏官", 0)  # 七杀
        shishen = god_counts.get("食神", 0)
        shangguan = god_counts.get("伤官", 0)
        bijian = god_counts.get("比肩", 0)
        jiancai = god_counts.get("劫财", 0)
        zhengyin = god_counts.get("正印", 0)
        pianyin = god_counts.get("偏印", 0)  # 枭神

        # 官杀混杂：正官和七杀同时存在且各>=1
        if zhengguang >= 1 and pianguang >= 1:
            return "被动变动型"

        # 食伤生财：食神/伤官多
        if (shishen + shangguan) >= 2:
            return "主动拓展型"

        # 比劫夺财：比肩/劫财多
        if (bijian + jiancai) >= 3:
            return "竞争压力型"

        # 印星过旺
        if (zhengyin + pianyin) >= 3:
            return "方向迷茫型"

        return ""

    @staticmethod
    def _detect_romance_state(
        bazi_data: Dict[str, Any],
        ten_gods: Dict[str, Any],
    ) -> str:
        """
        根据日支特征和十神判断桃花/感情状态
        日支被冲 → 关系压力型
        正财/正官明显（对应性别的伴侣星）→ 有缘分活跃
        缺少配偶星 → 沉淀型
        """
        if not bazi_data:
            return ""

        god_counts = {}
        for k, v in (ten_gods or {}).items():
            try:
                god_counts[k] = int(v) if not isinstance(v, int) else v
            except (ValueError, TypeError):
                god_counts[k] = 0

        # 日支关系检测
        relationships = bazi_data.get("relationships", {})
        if isinstance(relationships, dict):
            chong = relationships.get("chong", [])
            if isinstance(chong, list):
                for pair in chong:
                    if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                        positions = [str(p).lower() for p in pair]
                        if any("day" in p or "日" in p for p in positions):
                            return "关系压力型"

        # 配偶星检测（正财/正官为配偶星之一，简化处理）
        zhengcai = god_counts.get("正财", 0)
        piancai = god_counts.get("偏财", 0)
        zhengguang = god_counts.get("正官", 0)
        pianguang = god_counts.get("偏官", 0)

        spouse_count = zhengcai + piancai + zhengguang + pianguang
        if spouse_count >= 2:
            return "变动型"
        elif spouse_count == 0:
            return "沉淀型"

        return ""

    @staticmethod
    def _detect_wealth_state(
        ten_gods: Dict[str, Any],
        xi_shen: str,
        ji_shen: str,
    ) -> str:
        """
        根据财星状态判断财运
        正财多 + 财在喜神 → 正财上升型
        偏财多 → 偏财机会型
        比劫旺 + 财在忌神 → 守财型
        """
        if not ten_gods:
            return ""

        god_counts = {}
        for k, v in ten_gods.items():
            try:
                god_counts[k] = int(v) if not isinstance(v, int) else v
            except (ValueError, TypeError):
                god_counts[k] = 0

        zhengcai = god_counts.get("正财", 0)
        piancai = god_counts.get("偏财", 0)
        bijian = god_counts.get("比肩", 0)
        jiancai = god_counts.get("劫财", 0)

        xi_shen_str = xi_shen or ""
        ji_shen_str = ji_shen or ""

        # 偏财明显
        if piancai >= 2:
            return "偏财机会型"

        # 正财稳固且财在喜神
        if zhengcai >= 1 and ("财" in xi_shen_str or "水" in xi_shen_str or "木" in xi_shen_str):
            return "正财上升型"

        # 比劫夺财
        if (bijian + jiancai) >= 3 and ("财" in ji_shen_str or zhengcai <= 1):
            return "守财型"

        return "稳定型"

    @staticmethod
    def _detect_health_state(
        element_counts: Dict[str, Any],
    ):
        """
        根据五行偏枯判断健康状态和需关注脏腑

        Returns:
            (health_state: str, health_focus: list)
        """
        if not element_counts:
            return "", []

        # 标准化五行数量（支持中文键和英文键）
        key_map = {
            "金": ["金", "metal", "Metal"],
            "木": ["木", "wood", "Wood"],
            "水": ["水", "water", "Water"],
            "火": ["火", "fire", "Fire"],
            "土": ["土", "earth", "Earth"],
        }

        counts = {}
        for zh_key, aliases in key_map.items():
            for alias in aliases:
                if alias in element_counts:
                    try:
                        counts[zh_key] = int(element_counts[alias])
                    except (ValueError, TypeError):
                        counts[zh_key] = 0
                    break
            if zh_key not in counts:
                counts[zh_key] = 0

        # 找出缺失（0）和过旺（>=4）的五行
        missing = [e for e, c in counts.items() if c == 0]
        excess = [e for e, c in counts.items() if c >= 4]

        health_focus = []
        for e in missing:
            # 缺某行 → 对应脏腑需关注
            health_focus.extend(_ELEMENT_ORGAN_MAP.get(e, []))
        for e in excess:
            # 某行过旺 → 对应脏腑易失衡
            organs = _ELEMENT_ORGAN_MAP.get(e, [])
            for o in organs:
                if o not in health_focus:
                    health_focus.append(o)

        if missing or excess:
            return "脏腑调养型", health_focus[:4]  # 最多返回4个

        return "元气养护型", []

    @staticmethod
    def _bazi_states_to_priority(bazi_states: Dict[str, Any]) -> List[str]:
        """根据命盘状态标记推导关注优先级"""
        priority = []

        career = bazi_states.get("career", "")
        romance = bazi_states.get("romance", "")
        wealth = bazi_states.get("wealth", "")
        health = bazi_states.get("health", "")

        # 有明确事业信号
        if career in ("被动变动型", "竞争压力型", "方向迷茫型"):
            priority.append("事业")
        elif career == "主动拓展型":
            priority.append("事业")

        # 感情有变动信号
        if romance in ("变动型", "关系压力型"):
            priority.append("桃花")

        # 财运有强信号
        if wealth in ("偏财机会型", "守财型"):
            priority.append("财运")

        # 健康有明确需求
        if health == "脏腑调养型":
            priority.append("健康")

        return priority

    @staticmethod
    def _build_emotion_link(states: Dict[str, Any]) -> str:
        """根据主线状态构建跨模块情绪联动线索"""
        career = states.get("career", "")
        romance = states.get("romance", "")
        wealth = states.get("wealth", "")

        if career in ("被动变动型", "竞争压力型"):
            return "事业压力→肝气郁结"
        if romance in ("关系压力型",):
            return "感情困扰→心火上炎"
        if wealth in ("守财型",):
            return "财务焦虑→脾气虚弱"

        return ""
