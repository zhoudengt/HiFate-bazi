#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流年大运上下文分析服务
根据用户问题和时间范围，提供相应的流年大运信息
不影响现有功能，作为可选增强模块
"""

import sys
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import calendar
import logging

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.bazi_detail_service import BaziDetailService
from server.services.daily_fortune_service import DailyFortuneService
from server.services.monthly_fortune_service import MonthlyFortuneService

# ⭐ 新增：深度分析模块
from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
from src.analyzers.wuxing_balance_analyzer import WuxingBalanceAnalyzer
from src.analyzers.fortune_relation_analyzer import FortuneRelationAnalyzer
from server.services.fortune_scoring_service import FortuneScoring

# 天干地支五行映射
TIANGAN_WUXING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

DIZHI_WUXING = {
    "子": "水", "亥": "水",
    "寅": "木", "卯": "木",
    "巳": "火", "午": "火",
    "申": "金", "酉": "金",
    "辰": "土", "戌": "土", "丑": "土", "未": "土"
}

# 十神映射（以日主为基准）
# 格式：{日主: {天干/地支: 十神}}
def get_shishen(day_stem: str, target_stem: str) -> str:
    """计算十神"""
    # 天干生克关系
    shengke_map = {
        "甲": {"甲": "比肩", "乙": "劫财", "丙": "食神", "丁": "伤官", "戊": "偏财", "己": "正财", "庚": "偏官", "辛": "正官", "壬": "偏印", "癸": "正印"},
        "乙": {"甲": "劫财", "乙": "比肩", "丙": "伤官", "丁": "食神", "戊": "正财", "己": "偏财", "庚": "正官", "辛": "偏官", "壬": "正印", "癸": "偏印"},
        "丙": {"甲": "偏印", "乙": "正印", "丙": "比肩", "丁": "劫财", "戊": "食神", "己": "伤官", "庚": "偏财", "辛": "正财", "壬": "偏官", "癸": "正官"},
        "丁": {"甲": "正印", "乙": "偏印", "丙": "劫财", "丁": "比肩", "戊": "伤官", "己": "食神", "庚": "正财", "辛": "偏财", "壬": "正官", "癸": "偏官"},
        "戊": {"甲": "偏官", "乙": "正官", "丙": "偏印", "丁": "正印", "戊": "比肩", "己": "劫财", "庚": "食神", "辛": "伤官", "壬": "偏财", "癸": "正财"},
        "己": {"甲": "正官", "乙": "偏官", "丙": "正印", "丁": "偏印", "戊": "劫财", "己": "比肩", "庚": "伤官", "辛": "食神", "壬": "正财", "癸": "偏财"},
        "庚": {"甲": "偏财", "乙": "正财", "丙": "偏官", "丁": "正官", "戊": "偏印", "己": "正印", "庚": "比肩", "辛": "劫财", "壬": "食神", "癸": "伤官"},
        "辛": {"甲": "正财", "乙": "偏财", "丙": "正官", "丁": "偏官", "戊": "正印", "己": "偏印", "庚": "劫财", "辛": "比肩", "壬": "伤官", "癸": "食神"},
        "壬": {"甲": "食神", "乙": "伤官", "丙": "偏财", "丁": "正财", "戊": "偏官", "己": "正官", "庚": "偏印", "辛": "正印", "壬": "比肩", "癸": "劫财"},
        "癸": {"甲": "伤官", "乙": "食神", "丙": "正财", "丁": "偏财", "戊": "正官", "己": "偏官", "庚": "正印", "辛": "偏印", "壬": "劫财", "癸": "比肩"}
    }
    
    return shengke_map.get(day_stem, {}).get(target_stem, "")

# 地支藏干（简化版，只取主气）
DIZHI_CANGANG = {
    "子": "癸", "丑": "己", "寅": "甲", "卯": "乙",
    "辰": "戊", "巳": "丙", "午": "丁", "未": "己",
    "申": "庚", "酉": "辛", "戌": "戊", "亥": "壬"
}


# 时间关键词映射
TIME_KEYWORDS = {
    "今天": "today",
    "今日": "today",
    "本月": "this_month",
    "这个月": "this_month",
    "前年": "year_before_last",  # 当年-2
    "去年": "last_year",          # 当年-1
    "今年": "this_year",          # 当年
    "明年": "next_year",          # 当年+1
    "后年": "year_after_next",   # 当年+2 ⭐新增
    "大后年": "two_years_after_next",  # 当年+3 ⭐新增
    "最近": "recent_years",      # 最近几年
    "近期": "recent_years",
    "未来": "future_years",       # 未来几年
    "将来": "future_years",
    "过去": "past_years",         # 过去几年
    "以前": "past_years",
    "之前": "past_years",
}


class FortuneContextService:
    """流年大运上下文服务 - 作为智能问答的增强模块"""
    
    # ⭐ 性能优化：缓存 calculate_detail_full 结果
    _detail_cache = {}
    _cache_max_size = 50  # 最多缓存50条
    
    @staticmethod
    def _get_cached_detail(solar_date: str, solar_time: str, gender: str, current_time: datetime) -> Optional[dict]:
        """获取缓存的 detail_result"""
        cache_key = f"{solar_date}_{solar_time}_{gender}_{current_time.isoformat()}"
        return FortuneContextService._detail_cache.get(cache_key)
    
    @staticmethod
    def _set_cached_detail(solar_date: str, solar_time: str, gender: str, current_time: datetime, result: dict):
        """缓存 detail_result"""
        cache_key = f"{solar_date}_{solar_time}_{gender}_{current_time.isoformat()}"
        # 简单的LRU：如果缓存满了，删除最旧的
        if len(FortuneContextService._detail_cache) >= FortuneContextService._cache_max_size:
            # 删除第一个（FIFO）
            oldest_key = next(iter(FortuneContextService._detail_cache))
            del FortuneContextService._detail_cache[oldest_key]
        FortuneContextService._detail_cache[cache_key] = result
    
    @staticmethod
    def extract_time_range_from_question(question: str) -> Dict[str, Any]:
        """
        从问题中提取时间范围
        
        Args:
            question: 用户问题
            
        Returns:
            {
                "time_type": "today" | "this_month" | "this_year" | "recent_years" | "past_years" | ...,
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
                "has_time_keyword": bool,  # 是否包含时间关键词
                "target_years": [2024, 2025],  # 目标年份列表（用于流年分析）
                "is_multi_year": bool  # 是否多年对比
            }
        """
        today = date.today()
        current_year = today.year
        
        time_info = {
            "time_type": None,
            "start_date": None,
            "end_date": None,
            "has_time_keyword": False,
            "target_years": [],
            "is_multi_year": False
        }
        
        # 1. 优先检测具体年份（如 "2025-2028"、"2025到2028"、"2025年至2028年"）
        import re
        
        # 匹配年份范围：2025-2028、2025到2028、2025年到2028年、2025至2028等
        year_range_patterns = [
            r'(\d{4})\s*[-~至到]\s*(\d{4})',  # 2025-2028、2025到2028、2025至2028
            r'(\d{4})年?\s*[-~至到]\s*(\d{4})年?',  # 2025年到2028年
        ]
        
        for pattern in year_range_patterns:
            match = re.search(pattern, question)
            if match:
                start_year = int(match.group(1))
                end_year = int(match.group(2))
                
                if start_year <= end_year and 2000 <= start_year <= 2100 and 2000 <= end_year <= 2100:
                    # 生成年份列表
                    target_years = list(range(start_year, end_year + 1))
                    
                    time_info["time_type"] = "specific_years"
                    time_info["target_years"] = target_years
                    time_info["is_multi_year"] = len(target_years) > 1
                    time_info["start_date"] = f"{start_year}-01-01"
                    time_info["end_date"] = f"{end_year}-12-31"
                    time_info["has_time_keyword"] = True
                    
                    logger.debug(f"识别到年份范围: {start_year}-{end_year}, 共{len(target_years)}年")
                    return time_info
        
        # 匹配单个年份：2025年、2025
        single_year_patterns = [
            r'(\d{4})年',  # 2025年
            r'(?<!\d)(\d{4})(?!\d)',  # 2025（前后不能有其他数字）
        ]
        
        for pattern in single_year_patterns:
            match = re.search(pattern, question)
            if match:
                year = int(match.group(1))
                
                if 2000 <= year <= 2100:
                    time_info["time_type"] = "specific_year"
                    time_info["target_years"] = [year]
                    time_info["is_multi_year"] = False
                    time_info["start_date"] = f"{year}-01-01"
                    time_info["end_date"] = f"{year}-12-31"
                    time_info["has_time_keyword"] = True
                    
                    logger.debug(f"识别到单个年份: {year}")
                    return time_info
        
        # 2. 检测时间关键词（按长度排序，优先匹配长词，避免"大后年"被"后年"误匹配）
        sorted_keywords = sorted(TIME_KEYWORDS.items(), key=lambda x: len(x[0]), reverse=True)
        for keyword, time_type in sorted_keywords:
            if keyword in question:
                time_info["time_type"] = time_type
                time_info["has_time_keyword"] = True
                break
        
        # 3. 如果没有时间关键词，默认为最近两年（去年+今年）
        if not time_info["has_time_keyword"]:
            time_info["time_type"] = "recent_years"
            time_info["target_years"] = [current_year - 1, current_year]
            time_info["is_multi_year"] = True
            time_info["start_date"] = f"{current_year - 1}-01-01"
            time_info["end_date"] = f"{current_year}-12-31"
            return time_info
        
        # 计算时间范围
        if time_info["time_type"] == "today":
            time_info["start_date"] = today.strftime("%Y-%m-%d")
            time_info["end_date"] = today.strftime("%Y-%m-%d")
        
        elif time_info["time_type"] == "this_month":
            time_info["start_date"] = today.replace(day=1).strftime("%Y-%m-%d")
            # 本月最后一天
            last_day = calendar.monthrange(today.year, today.month)[1]
            time_info["end_date"] = today.replace(day=last_day).strftime("%Y-%m-%d")
        
        elif time_info["time_type"] == "this_year":
            time_info["start_date"] = f"{current_year}-01-01"
            time_info["end_date"] = f"{current_year}-12-31"
            time_info["target_years"] = [current_year]
        
        elif time_info["time_type"] == "last_year":
            time_info["start_date"] = f"{current_year - 1}-01-01"
            time_info["end_date"] = f"{current_year - 1}-12-31"
            time_info["target_years"] = [current_year - 1]
        
        elif time_info["time_type"] == "year_before_last":
            time_info["start_date"] = f"{current_year - 2}-01-01"
            time_info["end_date"] = f"{current_year - 2}-12-31"
            time_info["target_years"] = [current_year - 2]
        
        elif time_info["time_type"] == "next_year":
            time_info["start_date"] = f"{current_year + 1}-01-01"
            time_info["end_date"] = f"{current_year + 1}-12-31"
            time_info["target_years"] = [current_year + 1]
        
        elif time_info["time_type"] == "year_after_next":
            # 后年（当年+2）
            time_info["start_date"] = f"{current_year + 2}-01-01"
            time_info["end_date"] = f"{current_year + 2}-12-31"
            time_info["target_years"] = [current_year + 2]
        
        elif time_info["time_type"] == "two_years_after_next":
            # 大后年（当年+3）
            time_info["start_date"] = f"{current_year + 3}-01-01"
            time_info["end_date"] = f"{current_year + 3}-12-31"
            time_info["target_years"] = [current_year + 3]
        
        elif time_info["time_type"] == "recent_years":
            # 最近两年（去年+今年）
            time_info["target_years"] = [current_year - 1, current_year]
            time_info["is_multi_year"] = True
            time_info["start_date"] = f"{current_year - 1}-01-01"
            time_info["end_date"] = f"{current_year}-12-31"
        
        elif time_info["time_type"] == "future_years":
            # 未来两年（今年+明年）
            time_info["target_years"] = [current_year, current_year + 1]
            time_info["is_multi_year"] = True
            time_info["start_date"] = f"{current_year}-01-01"
            time_info["end_date"] = f"{current_year + 1}-12-31"
        
        elif time_info["time_type"] == "past_years":
            # 过去两年（去年+前年），从近到远
            time_info["target_years"] = [current_year - 1, current_year - 2]
            time_info["is_multi_year"] = True
            time_info["start_date"] = f"{current_year - 2}-01-01"
            time_info["end_date"] = f"{current_year - 1}-12-31"
        
        return time_info
    
    @staticmethod
    def get_fortune_context(
        solar_date: str,
        solar_time: str,
        gender: str,
        intent_types: List[str],  # ["wealth", "health", ...]
        time_range: dict = None,  # ⚠️ 已废弃，使用 target_years 代替
        target_years: List[int] = None,  # 目标年份列表（推荐使用）
    ) -> Optional[Dict[str, Any]]:
        """
        获取流年大运上下文信息
        
        Args:
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
            intent_types: 用户关心的方面
            time_range: ⚠️ 已废弃，为了向后兼容保留
            target_years: 目标年份列表，如 [2025, 2026, 2027]（推荐使用）
            
        Returns:
            {
                "time_analysis": {
                    "type": "daily" | "monthly" | "yearly",
                    "period": "2025年" | "2025年11月" | "2025年11月24日",
                    "liunian": {...},  # 流年信息
                    "dayun": {...},    # 大运信息
                    "liuyue": {...},   # 流月信息（如果是月运）
                    "liuri": {...}     # 流日信息（如果是日运）
                },
                "fortune_summary": {
                    "wealth": "财运分析...",
                    "health": "健康分析...",
                    ...
                }
            }
        """
        try:
            result = {
                "time_analysis": {},
                "fortune_summary": {}
            }
            
            # ⭐ 新架构：优先使用 target_years（从 Intent Service 传递）
            if target_years:
                # 新架构：直接使用年份列表，默认为流年分析
                time_type = "yearly"  # 默认流年
                # 构造兼容的 time_range 结构（用于后续代码复用）
                time_range = {
                    "time_type": "yearly",
                    "target_years": target_years,
                    "start_date": f"{target_years[0]}-01-01",
                    "end_date": f"{target_years[-1]}-12-31",
                    "is_multi_year": len(target_years) > 1
                }
            elif time_range:
                # 旧架构：使用 time_range（向后兼容）
                time_type = time_range.get("time_type")
            else:
                # 都没有提供，返回 None
                logger.debug("既没有 target_years 也没有 time_range，返回None")
                return None
            
            # 根据时间类型调用不同的服务
            # time_type = time_range.get("time_type")  # 已废弃
            
            if time_type == "today":
                # 调用日运服务
                daily_fortune = DailyFortuneService.calculate_daily_fortune(
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    target_date=time_range["start_date"],
                    use_llm=False
                )
                
                if daily_fortune.get("success"):
                    result["time_analysis"] = {
                        "type": "daily",
                        "period": time_range["start_date"],
                        "data": daily_fortune.get("fortune", {})
                    }
                    
                    # 提取各方面运势
                    fortune_data = daily_fortune.get("fortune", {})
                    for intent in intent_types:
                        result["fortune_summary"][intent] = FortuneContextService._extract_fortune_by_intent(
                            fortune_data, intent, "daily"
                        )
            
            elif time_type == "this_month":
                # 调用月运服务
                target_month = time_range["start_date"][:7]  # YYYY-MM
                monthly_fortune = MonthlyFortuneService.calculate_monthly_fortune(
                    solar_date=solar_date,
                    solar_time=solar_time,
                    gender=gender,
                    target_month=target_month,
                    use_llm=False
                )
                
                if monthly_fortune.get("success"):
                    result["time_analysis"] = {
                        "type": "monthly",
                        "period": target_month,
                        "data": monthly_fortune.get("fortune", {})
                    }
                    
                    fortune_data = monthly_fortune.get("fortune", {})
                    for intent in intent_types:
                        result["fortune_summary"][intent] = FortuneContextService._extract_fortune_by_intent(
                            fortune_data, intent, "monthly"
                        )
            
            else:
                # 流年分析（支持单年或多年）
                target_years = time_range.get("target_years", [])
                logger.debug(f"target_years from time_range = {target_years}")
                
                if not target_years and time_range.get("start_date"):
                    # 兼容：如果没有target_years，从start_date提取
                    target_years = [int(time_range["start_date"][:4])]
                    logger.debug(f"从start_date提取: target_years = {target_years}")
                
                if not target_years:
                    logger.debug("target_years为空，返回None")
                    return None
                
                # ⭐ 性能优化：只调用一次 calculate_detail_full，复用结果
                # 原因：calculate_detail_full 会计算所有流年，我们只需要从结果中提取特定年份
                logger.debug(f"开始计算流年大运，目标年份: {target_years}")
                start_time = time.time()
                
                # ⭐ 性能优化：先检查缓存
                current_time = datetime(target_years[0], 1, 1)
                cached_result = FortuneContextService._get_cached_detail(
                    solar_date, solar_time, gender, current_time
                )
                
                if cached_result:
                    logger.debug(f"[FortuneContextService] 缓存命中，跳过 calculate_detail_full")
                    detail_result = cached_result
                    calc_time = 0
                else:
                    # 只调用一次，使用第一个年份（结果包含所有流年）
                    detail_result = BaziDetailService.calculate_detail_full(
                        solar_date=solar_date,
                        solar_time=solar_time,
                        gender=gender,
                        current_time=current_time
                    )
                    
                    calc_time = (time.time() - start_time) * 1000
                    logger.info(f"[FortuneContextService] calculate_detail_full 耗时: {calc_time:.0f}ms")
                    
                    # 缓存结果
                    if detail_result:
                        FortuneContextService._set_cached_detail(
                            solar_date, solar_time, gender, current_time, detail_result
                        )
                
                if not detail_result:
                    logger.warning("calculate_detail_full 返回空结果")
                    return None
                
                # 从结果中提取所有需要的流年
                liunian_list = []
                dayun_info = None
                day_stem = None  # 日主天干，用于计算十神
                
                # 获取日主天干（用于计算十神）
                bazi_pillars = detail_result.get("bazi_pillars", {})
                day_pillar = bazi_pillars.get("day", {})
                day_stem = day_pillar.get("stem", "")
                
                # 获取所有流年序列（一次计算，包含所有年份）
                liunian_sequence = detail_result.get("liunian_sequence", [])
                logger.debug(f"获取到流年序列，共 {len(liunian_sequence)} 个流年")
                
                # 从流年序列中提取目标年份
                for target_year in target_years:
                    current_liunian = None
                    for ln in liunian_sequence:
                        if ln.get("year") == target_year:
                            current_liunian = ln.copy()  # 复制，避免修改原数据
                            break
                    
                    if current_liunian:
                        # 补充计算五行和十神信息
                        stem = current_liunian.get("stem", "")
                        branch = current_liunian.get("branch", "")
                        
                        # 计算天干五行
                        if stem:
                            current_liunian["stem_element"] = TIANGAN_WUXING.get(stem, "")
                        
                        # 计算地支五行
                        if branch:
                            current_liunian["branch_element"] = DIZHI_WUXING.get(branch, "")
                        
                        # 计算十神（需要日主）
                        if day_stem:
                            if stem:
                                current_liunian["stem_shishen"] = get_shishen(day_stem, stem)
                            if branch:
                                # 地支取藏干主气计算十神
                                branch_stem = DIZHI_CANGANG.get(branch, "")
                                if branch_stem:
                                    current_liunian["branch_shishen"] = get_shishen(day_stem, branch_stem)
                        
                        liunian_list.append(current_liunian)
                    else:
                        logger.warning(f"未找到 {target_year} 年的流年信息")
                
                # 大运信息（多年共享同一个大运）
                # 从第一个年份的大运序列中查找
                dayun_sequence = detail_result.get("dayun_sequence", [])
                first_target_year = target_years[0]
                for dayun in dayun_sequence:
                    year_start = dayun.get("year_start", 0)
                    year_end = dayun.get("year_end", 0)
                    
                    # 找到包含第一个目标年份的大运
                    if year_start <= first_target_year <= year_end:
                        # 排除"小运"（stem为"小运"）
                        if dayun.get("stem") != "小运":
                            dayun_info = dayun
                            logger.debug(f"找到{first_target_year}年对应的大运: {dayun.get('stem')}{dayun.get('branch')} ({year_start}-{year_end})")
                            break
                
                # 如果没找到，fallback到current_dayun
                if not dayun_info:
                    logger.debug(f"未找到{first_target_year}年对应的大运，使用current_dayun")
                    dayun_data = detail_result.get("dayun_info", {})
                    dayun_info = dayun_data.get("current_dayun", {})
                
                if liunian_list:
                    logger.debug(f"获取到{len(liunian_list)}个流年")
                    is_multi = time_range.get("is_multi_year", False)
                    
                    # ⭐ 新增：深度分析（喜忌神、五行平衡、关系分析）
                    try:
                        logger.debug("开始深度分析...")
                        
                        # 1. 获取喜忌神分析
                        wangshuai_analyzer = WangShuaiAnalyzer()
                        wangshuai_result = wangshuai_analyzer.analyze(solar_date, solar_time, gender)
                        xi_ji = wangshuai_result.get('xi_ji', {})
                        xi_ji_elements = wangshuai_result.get('xi_ji_elements', {})
                        logger.debug(f"喜神（十神）: {xi_ji.get('xi_shen', [])}, 喜神（五行）: {xi_ji_elements.get('xi_shen', [])}")
                        
                        # 2. 获取八字五行统计（从detail_result，避免重复调用）
                        # ⭐ 性能优化：复用已计算的 detail_result，不再重复调用
                        bazi_elements = detail_result.get("element_counts", {})
                        bazi_pillars = detail_result.get("bazi_pillars", {})
                        
                        # 3. 为每个流年添加深度分析
                        shishen_stats = detail_result.get("ten_gods_stats", {})  # 获取十神统计
                        
                        for i, liunian in enumerate(liunian_list):
                            logger.debug(f"流年{i+1}/{len(liunian_list)}: {liunian.get('year')}")
                            
                            # 五行平衡分析
                            balance_result = WuxingBalanceAnalyzer.analyze(
                                bazi_elements,
                                liunian,
                                dayun_info
                            )
                            liunian['balance_analysis'] = balance_result
                            
                            # 流年大运关系分析
                            relation_result = FortuneRelationAnalyzer.analyze(
                                bazi_pillars,
                                liunian,
                                dayun_info
                            )
                            liunian['relation_analysis'] = relation_result
                            
                            # ⭐ 新增：运势评分（预判断）
                            try:
                                fortune_scores = FortuneScoring.calculate_all_scores(
                                    balance_analysis=balance_result,
                                    relation_analysis=relation_result,
                                    xi_ji=xi_ji,
                                    shishen_stats=shishen_stats,
                                    wangshuai=wangshuai_result.get('wangshuai', ''),
                                    gender=gender
                                )
                                liunian['fortune_scores'] = fortune_scores
                            except Exception as score_error:
                                logger.debug(f"评分计算失败（不影响主流程）: {score_error}")
                        
                        # 4. 添加喜忌神信息到结果
                        result["xi_ji"] = xi_ji
                        result["xi_ji_elements"] = xi_ji_elements
                        result["wangshuai"] = wangshuai_result.get('wangshuai', '')
                        logger.debug("深度分析完成，喜忌神已添加到result")
                        
                    except Exception as e:
                        logger.error(f"深度分析失败（不影响主流程）: {e}", exc_info=True)
                        import traceback
                        traceback.print_exc()
                    
                    result["time_analysis"] = {
                        "type": "yearly",
                        "is_multi_year": is_multi,
                        "period": f"{target_years[0]}年" if len(target_years) == 1 else f"{target_years[0]}-{target_years[-1]}年",
                        "liunian_list": liunian_list,  # 流年列表
                        "dayun": dayun_info
                    }
                    
                    # 为每个流年提取运势
                    for intent in intent_types:
                        # 如果是多年，生成对比分析
                        if is_multi and len(liunian_list) > 1:
                            result["fortune_summary"][intent] = FortuneContextService._extract_multi_year_fortune(
                                liunian_list, dayun_info, intent, result.get("xi_ji"), result.get("xi_ji_elements")
                            )
                        else:
                            # 单年分析
                            result["fortune_summary"][intent] = FortuneContextService._extract_yearly_fortune_by_intent(
                                liunian_list[0], dayun_info, intent, result.get("xi_ji"), result.get("xi_ji_elements")
                            )
            
            has_time_analysis = bool(result["time_analysis"])
            logger.debug(f"准备返回结果: has_time_analysis={has_time_analysis}, type={result.get('time_analysis', {}).get('type', 'N/A')}")
            
            return result if has_time_analysis else None
            
        except Exception as e:
            # 静默失败，不影响主流程
            logger.error(f"Error: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _extract_fortune_by_intent(fortune_data: dict, intent: str, time_type: str) -> str:
        """从运势数据中提取特定意图的内容"""
        
        try:
            if time_type == "daily":
                # 日运数据结构
                if intent == "wealth":
                    wealth_data = fortune_data.get("wealth", {})
                    return wealth_data.get("content", "") or wealth_data.get("summary", "暂无财运分析")
                elif intent == "health":
                    health_data = fortune_data.get("health", {})
                    return health_data.get("content", "") or health_data.get("summary", "暂无健康分析")
                elif intent == "character":
                    career_data = fortune_data.get("career", {})
                    return career_data.get("content", "") or career_data.get("summary", "暂无事业分析")
                elif intent == "marriage":
                    love_data = fortune_data.get("love", {})
                    return love_data.get("content", "") or love_data.get("summary", "暂无感情分析")
            
            elif time_type == "monthly":
                # 月运数据结构
                if intent == "wealth":
                    wealth_data = fortune_data.get("wealth", {})
                    return wealth_data.get("content", "") or wealth_data.get("summary", "暂无财运分析")
                elif intent == "health":
                    health_data = fortune_data.get("health", {})
                    return health_data.get("content", "") or health_data.get("summary", "暂无健康分析")
                elif intent == "character":
                    career_data = fortune_data.get("career", {})
                    return career_data.get("content", "") or career_data.get("summary", "暂无事业分析")
                elif intent == "marriage":
                    love_data = fortune_data.get("love", {})
                    return love_data.get("content", "") or love_data.get("summary", "暂无感情分析")
        except Exception as e:
            logger.error(f"_extract_fortune_by_intent error: {e}", exc_info=True)
        
        return "暂无相关分析"
    
    @staticmethod
    def _extract_yearly_fortune_by_intent(liunian: Optional[dict], dayun: Optional[dict], intent: str, 
                                           xi_ji: Optional[dict] = None, xi_ji_elements: Optional[dict] = None) -> str:
        """
        从流年大运中提取特定意图的内容（单年）
        
        Args:
            liunian: 流年数据
            dayun: 大运数据
            intent: 意图类型
            xi_ji: 喜忌神（十神），格式 {'xi_shen': [...], 'ji_shen': [...]}
            xi_ji_elements: 喜忌神（五行），格式 {'xi_shen': [...], 'ji_shen': [...]}
        """
        
        try:
            if not liunian:
                return "暂无流年信息"
            
            # 流年天干地支
            liunian_stem = liunian.get("stem", "")
            liunian_branch = liunian.get("branch", "")
            year = liunian.get("year", "")
            
            # 大运天干地支
            dayun_stem = dayun.get("stem", "") if dayun else ""
            dayun_branch = dayun.get("branch", "") if dayun else ""
            
            # 获取五行信息
            liunian_stem_element = liunian.get("stem_element", "")
            liunian_branch_element = liunian.get("branch_element", "")
            
            # 获取十神信息
            liunian_stem_shishen = liunian.get("stem_shishen", "")
            liunian_branch_shishen = liunian.get("branch_shishen", "")
            
            # ⭐ 新增：判断流年是否为喜神或忌神
            xi_shen_list = xi_ji.get('xi_shen', []) if xi_ji else []
            ji_shen_list = xi_ji.get('ji_shen', []) if xi_ji else []
            xi_shen_elements = xi_ji_elements.get('xi_shen', []) if xi_ji_elements else []
            ji_shen_elements = xi_ji_elements.get('ji_shen', []) if xi_ji_elements else []
            
            # 判断流年十神是否为喜/忌
            liunian_stem_is_xi = liunian_stem_shishen in xi_shen_list if liunian_stem_shishen else False
            liunian_stem_is_ji = liunian_stem_shishen in ji_shen_list if liunian_stem_shishen else False
            liunian_branch_is_xi = liunian_branch_shishen in xi_shen_list if liunian_branch_shishen else False
            liunian_branch_is_ji = liunian_branch_shishen in ji_shen_list if liunian_branch_shishen else False
            
            # 判断流年五行是否为喜/忌
            liunian_stem_element_is_xi = liunian_stem_element in xi_shen_elements if liunian_stem_element else False
            liunian_stem_element_is_ji = liunian_stem_element in ji_shen_elements if liunian_stem_element else False
            liunian_branch_element_is_xi = liunian_branch_element in xi_shen_elements if liunian_branch_element else False
            liunian_branch_element_is_ji = liunian_branch_element in ji_shen_elements if liunian_branch_element else False
            
            # 基础信息
            analysis = f"**{year}年流年{liunian_stem}{liunian_branch}**"
            if dayun_stem and dayun_branch:
                analysis += f"，大运{dayun_stem}{dayun_branch}"
            analysis += "\n"
            
            # 五行分析（带喜忌标识）
            elements_desc = []
            if liunian_stem_element:
                xi_ji_tag = ""
                if liunian_stem_element_is_xi:
                    xi_ji_tag = "✨喜"
                elif liunian_stem_element_is_ji:
                    xi_ji_tag = "⚠️忌"
                elements_desc.append(f"{liunian_stem}({liunian_stem_element}{xi_ji_tag})")
            if liunian_branch_element:
                xi_ji_tag = ""
                if liunian_branch_element_is_xi:
                    xi_ji_tag = "✨喜"
                elif liunian_branch_element_is_ji:
                    xi_ji_tag = "⚠️忌"
                elements_desc.append(f"{liunian_branch}({liunian_branch_element}{xi_ji_tag})")
            
            if elements_desc:
                analysis += f"五行组成：{'、'.join(elements_desc)}\n"
            
            # 十神分析（带喜忌标识）
            shishen_desc = []
            if liunian_stem_shishen:
                xi_ji_tag = ""
                if liunian_stem_is_xi:
                    xi_ji_tag = "✨喜神"
                elif liunian_stem_is_ji:
                    xi_ji_tag = "⚠️忌神"
                shishen_desc.append(f"天干{liunian_stem}为{liunian_stem_shishen}{xi_ji_tag}")
            if liunian_branch_shishen:
                xi_ji_tag = ""
                if liunian_branch_is_xi:
                    xi_ji_tag = "✨喜神"
                elif liunian_branch_is_ji:
                    xi_ji_tag = "⚠️忌神"
                shishen_desc.append(f"地支{liunian_branch}为{liunian_branch_shishen}{xi_ji_tag}")
            
            if shishen_desc:
                analysis += f"{'，'.join(shishen_desc)}\n"
            
            # ⭐ 新增：喜忌神综合评估
            favorable_count = sum([liunian_stem_is_xi, liunian_branch_is_xi, 
                                   liunian_stem_element_is_xi, liunian_branch_element_is_xi])
            unfavorable_count = sum([liunian_stem_is_ji, liunian_branch_is_ji,
                                      liunian_stem_element_is_ji, liunian_branch_element_is_ji])
            
            if favorable_count > unfavorable_count:
                analysis += "🎯 **吉凶评估**：流年整体利好（喜神力量强），运势较顺。\n"
            elif unfavorable_count > favorable_count:
                analysis += "🎯 **吉凶评估**：流年有挑战（忌神力量强），需谨慎应对。\n"
            else:
                analysis += "🎯 **吉凶评估**：流年吉凶参半，关键在于如何把握。\n"
            
            analysis += "\n"
            
            # 根据意图和十神关系进行具体分析
            if intent == "wealth":
                # 获取所有十神（合并天干地支）
                shishen_list = []
                if liunian_stem_shishen:
                    shishen_list.append(liunian_stem_shishen)
                if liunian_branch_shishen:
                    shishen_list.append(liunian_branch_shishen)
                
                # 财运分析 - 根据十神类型和喜忌神判断
                if "正财" in shishen_list or "偏财" in shishen_list:
                    if "正财" in shishen_list:
                        base_analysis = "流年见正财，主正当收入、工资稳定。"
                        if "正财" in xi_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}✨且正财为喜神，财运极佳！今年正财运旺盛，工资收入有望大幅增长，适合争取加薪、奖金。投资理财也会有稳定回报，建议把握机会积累财富。"
                        elif "正财" in ji_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}⚠️但正财为忌神，财运受阻。虽有收入机会，但容易因工作压力、责任增加而感到辛苦，且可能因家庭、人情开支较大。建议谨慎理财，量入为出。"
                        else:
                            analysis += f"💰 **财运分析**：{base_analysis}今年适合踏实工作，通过正规途径获取财富。"
                    else:  # 偏财
                        base_analysis = "流年见偏财，主意外之财、投资收益。"
                        if "偏财" in xi_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}✨且偏财为喜神，偏财运强！今年有望获得意外收入、投资收益、奖金提成等，适合把握投资机会，但仍需控制风险。"
                        elif "偏财" in ji_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}⚠️但偏财为忌神，投资需谨慎。今年虽有偏财机会，但风险较高，容易因投资失误、合作不当而破财。不宜冒险，建议保守理财。"
                        else:
                            analysis += f"💰 **财运分析**：{base_analysis}今年有机会获得额外收入，但需注意风险控制。"
                
                elif "比肩" in shishen_list or "劫财" in shishen_list:
                    if "劫财" in shishen_list:
                        base_analysis = "流年见劫财，主破财、争夺。"
                        if "劫财" in ji_shen_list or favorable_count < unfavorable_count:
                            analysis += f"💰 **财运分析**：{base_analysis}⚠️劫财为忌神，财运极凶！今年需高度警惕破财风险，容易因朋友借款不还、合伙纠纷、投资失利而损失。务必远离高风险投资，不要轻易为他人担保。"
                        else:
                            analysis += f"💰 **财运分析**：{base_analysis}今年财运不利，需防范破财、被骗，不宜投资冒险。容易因朋友合作而损失。"
                    else:  # 比肩
                        base_analysis = "流年见比肩，主竞争、分财。"
                        if "比肩" in ji_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}⚠️比肩为忌神，竞争压力大。今年财运平平，容易因竞争激烈、朋友分财而收入受限，建议独立决策，不宜合伙。"
                        else:
                            analysis += f"💰 **财运分析**：{base_analysis}今年财运平平，容易因朋友、合作而破财，建议独立决策，谨慎投资。"
                
                elif "食神" in shishen_list or "伤官" in shishen_list:
                    if "食神" in shishen_list:
                        base_analysis = "流年见食神生财，主才华变现。"
                        if "食神" in xi_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}✨食神为喜神，财运通畅！今年才华得以充分发挥，技能、创意可转化为可观收入。适合从事自由职业、技术开发、文化创作等工作，财运亨通。"
                        elif "食神" in ji_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}⚠️但食神为忌神，生财不顺。虽有才华，但变现困难，容易眼高手低，收入不稳定。建议脚踏实地，不要过于理想化。"
                        else:
                            analysis += f"💰 **财运分析**：{base_analysis}今年适合发挥特长赚钱，创意、技术类工作财运佳。"
                    else:  # 伤官
                        base_analysis = "流年见伤官，主技能赚钱但不稳定。"
                        if "伤官" in xi_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}✨伤官为喜神，利于突破！今年收入来源多样，适合灵活创业、自由职业。虽有波动，但总体向上，把握机会可获丰厚回报。"
                        elif "伤官" in ji_shen_list:
                            analysis += f"💰 **财运分析**：{base_analysis}⚠️且伤官为忌神，财运波动大。今年收入极不稳定，容易因冲动投资、口舌是非而破财，务必控制支出，不宜冒险。"
                        else:
                            analysis += f"💰 **财运分析**：{base_analysis}今年收入波动大，适合灵活创业，但需控制支出。"
                
                elif "正官" in shishen_list or "偏官" in shishen_list:
                    base_analysis = "流年见官杀，主压力、责任。"
                    if any(s in xi_shen_list for s in ["正官", "偏官"]):
                        analysis += f"💰 **财运分析**：{base_analysis}✨官杀为喜神，利于事业发展。今年工作压力虽大，但付出有回报，收入稳定增长。适合争取升职加薪，不宜投机取巧。"
                    else:
                        analysis += f"💰 **财运分析**：{base_analysis}财运平稳但辛苦，付出与回报成正比，不宜投机。"
                
                elif "正印" in shishen_list or "偏印" in shishen_list:
                    base_analysis = "流年见印绶，印重泄财。"
                    if any(s in ji_shen_list for s in ["正印", "偏印"]):
                        analysis += f"💰 **财运分析**：{base_analysis}⚠️印为忌神，极不利财。今年财运低迷，开支大于收入，容易因学习、健康、人情等消耗财物。建议严格控制开支，暂缓投资计划。"
                    else:
                        analysis += f"💰 **财运分析**：{base_analysis}今年不利求财，开支较大，适合学习充电而非追求物质。建议控制消费，以保守为主。"
                
                else:
                    # 默认分析，基于五行喜忌
                    if favorable_count > unfavorable_count:
                        analysis += f"💰 **财运分析**：流年{liunian_stem}{liunian_branch}，五行{liunian_stem_element}、{liunian_branch_element}。✨流年五行利于命局，财运整体向好，把握机会可有所收获。"
                    elif unfavorable_count > favorable_count:
                        analysis += f"💰 **财运分析**：流年{liunian_stem}{liunian_branch}，五行{liunian_stem_element}、{liunian_branch_element}。⚠️流年五行不利命局，财运需谨慎，不宜冒险投资。"
                    else:
                        analysis += f"💰 **财运分析**：流年{liunian_stem}{liunian_branch}，五行{liunian_stem_element}、{liunian_branch_element}。需结合八字整体判断对财运的影响。"
            
            elif intent == "health":
                # 健康分析
                if liunian_stem_element == "木" or liunian_branch_element == "木":
                    analysis += "🏥 **健康分析**：流年木旺，肝胆、筋骨、神经系统需注意。建议多休息，避免过度劳累，保持心情舒畅。"
                elif liunian_stem_element == "火" or liunian_branch_element == "火":
                    analysis += "🏥 **健康分析**：流年火旺，心血管、血压、眼睛需注意。建议清淡饮食，避免熬夜，保持情绪稳定。"
                elif liunian_stem_element == "土" or liunian_branch_element == "土":
                    analysis += "🏥 **健康分析**：流年土旺，脾胃、消化系统需注意。建议规律饮食，加强运动，保持体重健康。"
                elif liunian_stem_element == "金" or liunian_branch_element == "金":
                    analysis += "🏥 **健康分析**：流年金旺，呼吸系统、肺、大肠需注意。建议远离烟尘，多做有氧运动，预防感冒。"
                elif liunian_stem_element == "水" or liunian_branch_element == "水":
                    analysis += "🏥 **健康分析**：流年水旺，肾脏、泌尿、生殖系统需注意。建议保暖防寒，多喝水，避免过度消耗。"
                else:
                    analysis += "🏥 **健康分析**：关注流年五行对身体的影响，注意相应脏腑保养，定期体检。"
            
            elif intent == "character":
                # 事业分析
                if liunian_stem_shishen == "正官" or liunian_branch_shishen == "正官":
                    analysis += "💼 **事业分析**：流年见正官，主升职、考试、正途发展。今年工作运势佳，适合争取晋升，参加考试。"
                elif liunian_stem_shishen == "偏官" or liunian_branch_shishen == "偏官":
                    analysis += "💼 **事业分析**：流年见七杀（偏官），主压力、挑战、权力。今年工作压力大，但也是突破的机会。"
                elif liunian_stem_shishen == "正印" or liunian_branch_shishen == "正印":
                    analysis += "💼 **事业分析**：流年见正印，主学习、贵人、证书。今年适合进修学习，容易获得长辈贵人帮助。"
                elif liunian_stem_shishen == "偏印" or liunian_branch_shishen == "偏印":
                    analysis += "💼 **事业分析**：流年见偏印，主偏门技能、创新思维。今年适合从事技术、设计、另类行业。"
                else:
                    analysis += f"💼 **事业分析**：流年{liunian_stem}{liunian_branch}对事业运势有影响，把握机遇，积极进取。"
            
            elif intent == "marriage":
                # 感情分析
                if "桃花" in str(liunian_branch):
                    analysis += "💕 **感情分析**：流年带桃花，异性缘佳，单身者有望脱单，已婚者需防桃花劫。"
                elif liunian_stem_shishen == "正财" or liunian_branch_shishen == "正财":
                    analysis += "💕 **感情分析**：流年见正财（男命妻星），感情稳定，有望谈婚论嫁或感情升温。"
                elif liunian_stem_shishen == "正官" or liunian_branch_shishen == "正官":
                    analysis += "💕 **感情分析**：流年见正官（女命夫星），有望遇到正缘，适合相亲、结婚。"
                else:
                    analysis += f"💕 **感情分析**：流年{liunian_stem}{liunian_branch}，关注感情变化，把握缘分，真诚相待。"
            
            return analysis
        except Exception as e:
            logger.error(f"_extract_yearly_fortune_by_intent error: {e}", exc_info=True)
            return "流年大运分析暂时无法获取"
    
    @staticmethod
    def _extract_multi_year_fortune(liunian_list: List[dict], dayun: Optional[dict], intent: str,
                                      xi_ji: Optional[dict] = None, xi_ji_elements: Optional[dict] = None) -> str:
        """
        从多个流年中提取对比分析（多年对比）
        
        Args:
            liunian_list: 流年列表
            dayun: 大运数据
            intent: 意图类型
            xi_ji: 喜忌神（十神）
            xi_ji_elements: 喜忌神（五行）
        """
        
        try:
            if not liunian_list:
                return "暂无流年信息"
            
            # 大运信息
            dayun_stem = dayun.get("stem", "") if dayun else ""
            dayun_branch = dayun.get("branch", "") if dayun else ""
            dayun_str = f"{dayun_stem}{dayun_branch}" if dayun_stem and dayun_branch else "未知"
            
            analysis = f"当前大运：**{dayun_str}**\n\n"
            
            # 意图对应的emoji
            intent_emoji = {
                "wealth": "💰",
                "health": "🏥",
                "character": "💼",
                "marriage": "💕"
            }
            emoji = intent_emoji.get(intent, "📊")
            
            # 逐年分析（从最近的开始）
            for i, liunian in enumerate(liunian_list):
                year = liunian.get("year", "")
                stem = liunian.get("stem", "")
                branch = liunian.get("branch", "")
                
                # 五行信息
                stem_element = liunian.get("stem_element", "")
                branch_element = liunian.get("branch_element", "")
                
                # 十神信息
                stem_shishen = liunian.get("stem_shishen", "")
                branch_shishen = liunian.get("branch_shishen", "")
                
                # 年份标签（从最近的开始）
                current_year = datetime.now().year
                if i == 0:
                    # 第一个年份
                    if year == current_year:
                        year_label = "【当年】"
                    elif year == current_year - 1:
                        year_label = "【去年】"
                    elif year == current_year - 2:
                        year_label = "【前年】"
                    elif year == current_year + 1:
                        year_label = "【明年】"
                    elif year == current_year + 2:
                        year_label = "【后年】"
                    elif year == current_year + 3:
                        year_label = "【大后年】"
                    else:
                        year_label = f"【{abs(current_year - year)}年{'前' if year < current_year else '后'}】"
                else:
                    # 后续年份
                    if year == current_year:
                        year_label = "【当年】"
                    elif year == current_year - 1:
                        year_label = "【去年】"
                    elif year == current_year - 2:
                        year_label = "【前年】"
                    elif year == current_year + 1:
                        year_label = "【明年】"
                    elif year == current_year + 2:
                        year_label = "【后年】"
                    elif year == current_year + 3:
                        year_label = "【大后年】"
                    else:
                        years_diff = abs(current_year - year)
                        year_label = f"【{years_diff}年{'前' if year < current_year else '后'}】"
                
                # ⭐ 判断五行和十神是否为喜忌神
                xi_shen_list = xi_ji.get('xi_shen', []) if xi_ji else []
                ji_shen_list = xi_ji.get('ji_shen', []) if xi_ji else []
                xi_shen_elements = xi_ji_elements.get('xi_shen', []) if xi_ji_elements else []
                ji_shen_elements = xi_ji_elements.get('ji_shen', []) if xi_ji_elements else []
                
                # 五行描述（带喜忌标识）
                elements_desc = []
                if stem_element:
                    xi_ji_tag = ""
                    if stem_element in xi_shen_elements:
                        xi_ji_tag = "✨"
                    elif stem_element in ji_shen_elements:
                        xi_ji_tag = "⚠️"
                    elements_desc.append(f"{stem}({stem_element}{xi_ji_tag})")
                if branch_element:
                    xi_ji_tag = ""
                    if branch_element in xi_shen_elements:
                        xi_ji_tag = "✨"
                    elif branch_element in ji_shen_elements:
                        xi_ji_tag = "⚠️"
                    elements_desc.append(f"{branch}({branch_element}{xi_ji_tag})")
                element_str = "、".join(elements_desc) if elements_desc else "未知"
                
                # 十神描述（带喜忌标识）
                shishen_parts = []
                if stem_shishen:
                    xi_ji_tag = ""
                    if stem_shishen in xi_shen_list:
                        xi_ji_tag = "✨"
                    elif stem_shishen in ji_shen_list:
                        xi_ji_tag = "⚠️"
                    shishen_parts.append(f"{stem_shishen}{xi_ji_tag}")
                if branch_shishen:
                    xi_ji_tag = ""
                    if branch_shishen in xi_shen_list:
                        xi_ji_tag = "✨"
                    elif branch_shishen in ji_shen_list:
                        xi_ji_tag = "⚠️"
                    shishen_parts.append(f"{branch_shishen}{xi_ji_tag}")
                shishen_str = "、".join(shishen_parts) if shishen_parts else ""
                
                analysis += f"{year_label} **{year}年{stem}{branch}**\n"
                analysis += f"  五行：{element_str}"
                if shishen_str:
                    analysis += f" | 十神：{shishen_str}"
                analysis += "\n"
                
                # ⭐ 新增：深度分析（五行平衡+关系分析+刑冲合害）
                balance_analysis = liunian.get('balance_analysis', {})
                relation_analysis = liunian.get('relation_analysis', {})
                
                if balance_analysis:
                    balance_summary = balance_analysis.get('analysis', {}).get('summary', '')
                    if balance_summary:
                        analysis += f"  📊 五行平衡：{balance_summary}\n"
                
                # 关系分析（包含流年vs大运/八字的关系）
                if relation_analysis:
                    relation_summary = relation_analysis.get('summary', '')
                    if relation_summary and "无明显" not in relation_summary:
                        analysis += f"  🔗 关系分析：{relation_summary}\n"
                    
                    # ⚠️ 新增：刑冲合害详细展示
                    internal_relations = relation_analysis.get('internal_relations', {})
                    if internal_relations:
                        # 优先展示冲、刑（不利因素）
                        if internal_relations.get('chong_details'):
                            chong_str = "、".join(internal_relations['chong_details'])
                            analysis += f"  ⚠️ 冲：{chong_str}\n"
                        if internal_relations.get('xing_details'):
                            xing_str = "、".join(internal_relations['xing_details'])
                            analysis += f"  ⚠️ 刑：{xing_str}\n"
                        if internal_relations.get('hai_details'):
                            hai_str = "、".join(internal_relations['hai_details'])
                            analysis += f"  ⚠️ 害：{hai_str}\n"
                        if internal_relations.get('po_details'):
                            po_str = "、".join(internal_relations['po_details'])
                            analysis += f"  ⚠️ 破：{po_str}\n"
                        # 展示合（有利因素）
                        if internal_relations.get('he_details'):
                            he_str = "、".join(internal_relations['he_details'])
                            analysis += f"  ✅ 合：{he_str}\n"
                
                # 根据意图和十神关系进行具体分析（带喜忌神判断）
                if intent == "wealth":
                    if stem_shishen == "正财" or branch_shishen == "正财":
                        if "正财" in xi_shen_list:
                            analysis += f"  {emoji} 见正财✨（喜神），财运极佳！工资奖金有望大涨，把握机会积累财富\n"
                        elif "正财" in ji_shen_list:
                            analysis += f"  {emoji} 见正财⚠️（忌神），虽有收入但辛苦，容易因家庭人情破费，量入为出\n"
                        else:
                            analysis += f"  {emoji} 见正财，工资稳定，适合踏实工作积累财富\n"
                    
                    elif stem_shishen == "偏财" or branch_shishen == "偏财":
                        if "偏财" in xi_shen_list:
                            analysis += f"  {emoji} 见偏财✨（喜神），偏财运强！投资收益、意外之财可期，适度投资\n"
                        elif "偏财" in ji_shen_list:
                            analysis += f"  {emoji} 见偏财⚠️（忌神），投资需谨慎，易因风险决策而破财，宜保守\n"
                        else:
                            analysis += f"  {emoji} 见偏财，有意外之财机会，可适当投资但需控制风险\n"
                    
                    elif stem_shishen == "比肩" or branch_shishen == "比肩":
                        if "比肩" in ji_shen_list:
                            analysis += f"  {emoji} 见比肩⚠️（忌神），竞争压力大，易因合作分财而破财，务必独立决策\n"
                        else:
                            analysis += f"  {emoji} 见比肩，竞争激烈易破财，建议独立决策避免合作\n"
                    
                    elif stem_shishen == "劫财" or branch_shishen == "劫财":
                        if "劫财" in ji_shen_list:
                            analysis += f"  {emoji} 见劫财⚠️（忌神），破财风险极高！严防被骗、远离高风险投资和担保\n"
                        else:
                            analysis += f"  {emoji} 见劫财，破财风险高，需防范被骗，不宜冒险投资\n"
                    
                    elif stem_shishen == "食神" or branch_shishen == "食神":
                        if "食神" in xi_shen_list:
                            analysis += f"  {emoji} 见食神✨（喜神），生财有道！才华充分发挥，技能创意类工作财运亨通\n"
                        elif "食神" in ji_shen_list:
                            analysis += f"  {emoji} 见食神⚠️（忌神），虽有才华但变现困难，收入不稳，脚踏实地为宜\n"
                        else:
                            analysis += f"  {emoji} 见食神生财，才华变现，创意技术类工作财运佳\n"
                    
                    elif stem_shishen == "伤官" or branch_shishen == "伤官":
                        if "伤官" in xi_shen_list:
                            analysis += f"  {emoji} 见伤官✨（喜神），利于突破！收入来源多样，灵活创业可获丰厚回报\n"
                        elif "伤官" in ji_shen_list:
                            analysis += f"  {emoji} 见伤官⚠️（忌神），收入极不稳定，易因冲动而破财，务必控制支出\n"
                        else:
                            analysis += f"  {emoji} 见伤官，收入不稳但潜力大，适合灵活创业\n"
                    
                    elif stem_shishen in ["正印", "偏印"] or branch_shishen in ["正印", "偏印"]:
                        if any(s in ji_shen_list for s in ["正印", "偏印"]):
                            analysis += f"  {emoji} 见印绶⚠️（忌神），印重泄财，开支大于收入，严控消费暂缓投资\n"
                        else:
                            analysis += f"  {emoji} 见印绶，开支较大，适合学习充电而非求财，以保守为主\n"
                    
                    else:
                        # 基于五行喜忌的默认分析
                        favorable = (stem_element in xi_shen_elements) or (branch_element in xi_shen_elements)
                        unfavorable = (stem_element in ji_shen_elements) or (branch_element in ji_shen_elements)
                        
                        if favorable and not unfavorable:
                            analysis += f"  {emoji} 流年五行利于命局✨，财运整体向好，把握机会可有收获\n"
                        elif unfavorable and not favorable:
                            analysis += f"  {emoji} 流年五行不利命局⚠️，财运需谨慎，不宜冒险投资\n"
                        else:
                            analysis += f"  {emoji} 五行{element_str}，需结合八字分析对财运的影响\n"
                
                elif intent == "health":
                    health_tips = []
                    if stem_element == "木" or branch_element == "木":
                        health_tips.append("肝胆、筋骨需注意，保持心情舒畅")
                    if stem_element == "火" or branch_element == "火":
                        health_tips.append("心血管、血压需注意，避免熬夜")
                    if stem_element == "土" or branch_element == "土":
                        health_tips.append("脾胃、消化系统需注意，规律饮食")
                    if stem_element == "金" or branch_element == "金":
                        health_tips.append("呼吸系统需注意，预防感冒")
                    if stem_element == "水" or branch_element == "水":
                        health_tips.append("肾脏、泌尿系统需注意，保暖防寒")
                    
                    if health_tips:
                        analysis += f"  {emoji} {health_tips[0]}\n"
                    else:
                        analysis += f"  {emoji} 关注身体健康，定期体检\n"
                
                elif intent == "character":
                    if stem_shishen == "正官" or branch_shishen == "正官":
                        analysis += f"  {emoji} 见正官，升职运佳，适合争取晋升或参加考试\n"
                    elif stem_shishen == "偏官" or branch_shishen == "偏官":
                        analysis += f"  {emoji} 见七杀，压力大但也是突破机会，勇于挑战\n"
                    elif stem_shishen == "正印" or branch_shishen == "正印":
                        analysis += f"  {emoji} 见正印，学习运佳，适合进修或考证\n"
                    elif stem_shishen == "偏印" or branch_shishen == "偏印":
                        analysis += f"  {emoji} 见偏印，适合技术、设计等专业性强的工作\n"
                    else:
                        analysis += f"  {emoji} 把握机遇，积极进取，注意职场人际关系\n"
                
                elif intent == "marriage":
                    if stem_shishen == "正财" or branch_shishen == "正财":
                        analysis += f"  {emoji} 见正财（男命妻星），感情稳定，有望结婚\n"
                    elif stem_shishen == "正官" or branch_shishen == "正官":
                        analysis += f"  {emoji} 见正官（女命夫星），有望遇正缘，适合相亲\n"
                    else:
                        analysis += f"  {emoji} 关注感情变化，真诚相待，把握缘分\n"
                
                # 不是最后一年，添加换行
                if i < len(liunian_list) - 1:
                    analysis += "\n"
            
            return analysis
        except Exception as e:
            logger.error(f"_extract_multi_year_fortune error: {e}", exc_info=True)
            return "多年流年对比分析暂时无法获取"

