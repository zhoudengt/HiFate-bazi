#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存键生成器 - 统一管理所有缓存键的生成逻辑
支持7个标准参数，确保缓存键的唯一性和一致性
"""

import hashlib
import json
from typing import Optional, Dict, Any


class CacheKeyGenerator:
    """缓存键生成器"""
    
    @staticmethod
    def generate_bazi_data_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        suffix: Optional[str] = None
    ) -> str:
        """
        生成八字数据缓存键（包含7个标准参数）
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别
            calendar_type: 历法类型（solar/lunar）
            location: 出生地点
            latitude: 纬度
            longitude: 经度
            suffix: 后缀（用于区分不同的数据类型）
            
        Returns:
            str: 缓存键
        """
        # 标准化参数（确保一致性）
        calendar_type = calendar_type or "solar"
        location = location or ""
        latitude = latitude or 0.0
        longitude = longitude or 0.0
        
        # 构建键的组成部分
        key_parts = [
            "bazi_data",
            solar_date,
            solar_time,
            gender,
            calendar_type,
            location,
            f"{latitude:.6f}",  # 保留6位小数
            f"{longitude:.6f}"   # 保留6位小数
        ]
        
        if suffix:
            key_parts.append(suffix)
        
        # 生成完整键（使用冒号分隔，便于调试）
        key_str = ':'.join(key_parts)
        
        # 如果键太长，使用MD5哈希（Redis键长度限制）
        if len(key_str) > 200:
            hash_obj = hashlib.md5(key_str.encode('utf-8'))
            hash_str = hash_obj.hexdigest()
            return f"bazi_data:hash:{hash_str}"
        
        return key_str
    
    @staticmethod
    def generate_dayun_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        mode: Optional[str] = None,
        count: Optional[int] = None
    ) -> str:
        """
        生成大运数据缓存键
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别
            calendar_type: 历法类型
            location: 出生地点
            latitude: 纬度
            longitude: 经度
            mode: 查询模式
            count: 数量
            
        Returns:
            str: 缓存键
        """
        suffix_parts = ["dayun"]
        if mode:
            suffix_parts.append(mode)
        if count:
            suffix_parts.append(str(count))
        
        suffix = ':'.join(suffix_parts) if len(suffix_parts) > 1 else suffix_parts[0]
        
        return CacheKeyGenerator.generate_bazi_data_key(
            solar_date, solar_time, gender,
            calendar_type, location, latitude, longitude,
            suffix
        )
    
    @staticmethod
    def generate_liunian_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        target_years: Optional[list] = None
    ) -> str:
        """
        生成流年数据缓存键
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别
            calendar_type: 历法类型
            location: 出生地点
            latitude: 纬度
            longitude: 经度
            target_years: 目标年份列表
            
        Returns:
            str: 缓存键
        """
        suffix_parts = ["liunian"]
        if target_years:
            years_str = ','.join(str(y) for y in sorted(target_years))
            suffix_parts.append(years_str)
        
        suffix = ':'.join(suffix_parts)
        
        return CacheKeyGenerator.generate_bazi_data_key(
            solar_date, solar_time, gender,
            calendar_type, location, latitude, longitude,
            suffix
        )
    
    @staticmethod
    def generate_special_liunian_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        calendar_type: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        dayun_steps: Optional[list] = None,
        count: Optional[int] = None
    ) -> str:
        """
        生成特殊流年数据缓存键
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别
            calendar_type: 历法类型
            location: 出生地点
            latitude: 纬度
            longitude: 经度
            dayun_steps: 大运步数列表
            count: 数量
            
        Returns:
            str: 缓存键
        """
        suffix_parts = ["special_liunian"]
        if dayun_steps:
            steps_str = ','.join(str(s) for s in sorted(dayun_steps))
            suffix_parts.append(f"steps:{steps_str}")
        if count:
            suffix_parts.append(f"count:{count}")
        
        suffix = ':'.join(suffix_parts)
        
        return CacheKeyGenerator.generate_bazi_data_key(
            solar_date, solar_time, gender,
            calendar_type, location, latitude, longitude,
            suffix
        )
    
    @staticmethod
    def generate_orchestrator_key(
        solar_date: str,
        solar_time: str,
        gender: str,
        modules: Dict[str, Any],
        calendar_type: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        current_time: Optional[Any] = None,
        dayun_index: Optional[int] = None,
        dayun_year_start: Optional[int] = None,
        dayun_year_end: Optional[int] = None,
        target_year: Optional[int] = None
    ) -> str:
        """
        生成 BaziDataOrchestrator 缓存键（含 current_time 与 dayun 范围，避免切大运/换时间命中错误缓存）
        
        Args:
            solar_date: 阳历日期或农历日期
            solar_time: 出生时间
            gender: 性别
            modules: 模块配置字典
            calendar_type: 历法类型
            location: 出生地点
            latitude: 纬度
            longitude: 经度
            current_time: 当前时间（datetime 或 None）
            dayun_index: 大运索引
            dayun_year_start: 大运起始年份
            dayun_year_end: 大运结束年份
            target_year: 目标年份
            
        Returns:
            str: 缓存键
        """
        # 序列化模块配置（确保顺序一致）
        modules_str = json.dumps(modules, sort_keys=True, ensure_ascii=False)
        modules_hash = hashlib.md5(modules_str.encode('utf-8')).hexdigest()[:8]
        
        suffix = f"orchestrator:modules:{modules_hash}"
        # 大运/时间范围参与 key，避免不同 current_time 或 dayun 范围共用缓存
        scope_parts = []
        if current_time is not None:
            # 截断到小时级别，避免微秒精度导致缓存永远 miss
            if hasattr(current_time, 'strftime'):
                t_str = current_time.strftime('%Y-%m-%dT%H')
            else:
                t_str = str(current_time)
            scope_parts.append(f"t_{t_str}")
        if dayun_index is not None:
            scope_parts.append(f"di_{dayun_index}")
        if dayun_year_start is not None:
            scope_parts.append(f"ys_{dayun_year_start}")
        if dayun_year_end is not None:
            scope_parts.append(f"ye_{dayun_year_end}")
        if target_year is not None:
            scope_parts.append(f"ty_{target_year}")
        if scope_parts:
            suffix = suffix + ":" + ":".join(scope_parts)
        
        return CacheKeyGenerator.generate_bazi_data_key(
            solar_date, solar_time, gender,
            calendar_type, location, latitude, longitude,
            suffix
        )

