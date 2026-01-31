#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存预热模块

在冷启动或定时任务中主动填充 L1/L2 缓存，降低首次请求延迟。
- 每日运势：每天 0 点可调用 warmup_daily_fortune(date)
- 热门八字组合：启动时或定时调用 warmup_hot_bazi_combinations()
- 启动时一次性预热：warmup_on_startup()
"""

import logging
from datetime import datetime, timedelta
from typing import List, Tuple

logger = logging.getLogger(__name__)

# 热门八字组合（基于常见查询）：(solar_date, solar_time, gender)
DEFAULT_HOT_BAZI_COMBINATIONS: List[Tuple[str, str, str]] = [
    ("1990-01-01", "12:00", "male"),
    ("1990-01-01", "12:00", "female"),
    ("1995-05-15", "08:30", "male"),
    ("1995-05-15", "08:30", "female"),
    ("1988-08-08", "06:00", "male"),
    ("1992-12-25", "14:00", "female"),
    ("1985-03-20", "10:00", "male"),
    ("1998-07-01", "00:00", "female"),
]


def warmup_daily_fortune(date: str) -> int:
    """
    预热指定日期的每日运势缓存。

    对若干代表生辰调用大运流年接口，使当日运势结果进入缓存（由服务内部写入 L1/L2），
    适合每天 0 点由定时任务调用。

    Args:
        date: 日期，格式 YYYY-MM-DD（作为 current_time 的日期部分）

    Returns:
        成功预热的条目数量
    """
    count = 0
    try:
        current_dt = datetime.strptime(f"{date} 12:00", "%Y-%m-%d %H:%M")
    except ValueError:
        logger.warning("预热每日运势: 日期格式错误 date=%s", date)
        return 0
    for solar_date, solar_time, gender in DEFAULT_HOT_BAZI_COMBINATIONS[:4]:
        try:
            from server.services.bazi_display_service import BaziDisplayService
            result = BaziDisplayService.get_fortune_display(
                solar_date, solar_time, gender,
                current_time=current_dt,
                dayun_index=None,
                dayun_year_start=None,
                dayun_year_end=None,
                target_year=None,
                quick_mode=True,
                async_warmup=False,
            )
            if result and result.get("success"):
                count += 1
                logger.debug("缓存预热: fortune %s %s %s @ %s", solar_date, solar_time, gender, date)
        except Exception as e:
            logger.warning("预热每日运势失败 %s %s %s @ %s: %s", solar_date, solar_time, gender, date, e)
    if count > 0:
        logger.info("每日运势预热完成: date=%s, 预热 %d 条", date, count)
    return count


def warmup_hot_bazi_combinations(
    combinations: List[Tuple[str, str, str]] | None = None,
) -> int:
    """
    预热热门八字组合的排盘与展示缓存。

    使用 DEFAULT_HOT_BAZI_COMBINATIONS 或传入的 (solar_date, solar_time, gender)
    调用 get_pan_display，将结果写入多级缓存。

    Args:
        combinations: 可选，指定 (solar_date, solar_time, gender) 列表；为 None 时使用默认列表。

    Returns:
        成功预热的条目数量
    """
    combos = combinations or DEFAULT_HOT_BAZI_COMBINATIONS
    count = 0
    for solar_date, solar_time, gender in combos:
        try:
            from server.services.bazi_display_service import BaziDisplayService
            from server.utils.api_cache_helper import generate_cache_key, set_cached_result, L2_TTL
            result = BaziDisplayService.get_pan_display(solar_date, solar_time, gender)
            if result and result.get("success"):
                cache_key = generate_cache_key("pan", solar_date, solar_time, gender)
                set_cached_result(cache_key, result, ttl=L2_TTL)
                count += 1
                logger.debug("缓存预热: pan %s %s %s", solar_date, solar_time, gender)
        except Exception as e:
            logger.warning("预热排盘缓存失败 %s %s %s: %s", solar_date, solar_time, gender, e)
    if count > 0:
        logger.info("热门八字组合预热完成: 共 %d 条", count)
    return count


def warmup_on_startup() -> None:
    """
    应用启动时执行的一次性预热。

    - 预热当日每日运势（warmup_daily_fortune(今日)）
    - 预热热门八字组合（warmup_hot_bazi_combinations()）

    建议在 FastAPI lifespan 或 uvicorn 启动后、在后台线程中调用，避免阻塞主线程。
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        warmup_daily_fortune(today)
        warmup_hot_bazi_combinations()
        logger.info("缓存启动预热执行完成")
    except Exception as e:
        logger.warning("缓存启动预热失败（不影响服务）: %s", e, exc_info=True)
