#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字界面信息服务层
负责调用 bazi_interface_generator 生成界面信息
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from core.calculators.bazi_interface_generator import BaziInterfaceGenerator


class BaziInterfaceService:
    """八字界面信息服务类"""
    
    # Redis缓存TTL（30天，身宫命宫胎元数据不随时间变化）
    CACHE_TTL = 2592000  # 30天
    
    @staticmethod
    def _generate_cache_key(solar_date: str, solar_time: str, gender: str,
                            name: str = "", location: str = "未知地",
                            latitude: float = 39.00, longitude: float = 120.00) -> str:
        """
        生成缓存键
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
            name: 姓名（可选，不影响身宫命宫胎元）
            location: 出生地点（可选，不影响身宫命宫胎元）
            latitude: 纬度（可选，不影响身宫命宫胎元）
            longitude: 经度（可选，不影响身宫命宫胎元）
            
        Returns:
            str: 缓存键
        """
        # 生成键（格式：bazi_interface:{solar_date}:{solar_time}:{gender}:{name}:{location}:{latitude}:{longitude}）
        # 注意：虽然 name, location, latitude, longitude 可能不影响身宫命宫胎元，但为了完整性，仍然包含在缓存键中
        key_parts = [
            'bazi_interface',
            solar_date,
            solar_time,
            gender,
            name or '',
            location or '未知地',
            str(latitude),
            str(longitude)
        ]
        return ':'.join(key_parts)
    
    @staticmethod
    def generate_interface_full(solar_date: str, solar_time: str, gender: str, 
                                name: str = "", location: str = "未知地",
                                latitude: float = 39.00, longitude: float = 120.00) -> dict:
        """
        完整生成八字界面信息（带Redis缓存）
        
        Args:
            solar_date: 阳历日期，格式：YYYY-MM-DD
            solar_time: 出生时间，格式：HH:MM
            gender: 性别，'male' 或 'female'
            name: 姓名，可选
            location: 出生地点，可选
            latitude: 纬度，可选
            longitude: 经度，可选
        
        Returns:
            dict: 格式化的八字界面数据
        """
        # 转换性别格式
        if gender not in ["male", "female"]:
            if gender == "男":
                gender = "male"
            elif gender == "女":
                gender = "female"
        
        # 1. 生成缓存键
        cache_key = BaziInterfaceService._generate_cache_key(
            solar_date, solar_time, gender, name, location, latitude, longitude
        )
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            import logging
            logger = logging.getLogger(__name__)
            
            cache = get_multi_cache()
            # 设置 L2 Redis TTL 为 30 天
            cache.l2.ttl = BaziInterfaceService.CACHE_TTL
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"✅ [缓存命中] BaziInterfaceService.generate_interface_full: {cache_key[:80]}...")
                return cached_result
        except Exception as e:
            # Redis不可用，降级到直接计算
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️  Redis缓存不可用，降级到直接计算: {e}")
        
        # 3. 缓存未命中，执行计算
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"⏱️ [缓存未命中] BaziInterfaceService.generate_interface_full: {cache_key[:80]}...")
        
        # 使用 BaziInterfaceGenerator 生成信息
        generator = BaziInterfaceGenerator()
        result = generator.generate_interface_info(
            name if name else "用户",
            gender,
            solar_date,
            solar_time,
            latitude,
            longitude,
            location
        )
        
        # 4. 写入缓存（仅成功时）
        if result:
            try:
                cache = get_multi_cache()
                cache.l2.ttl = BaziInterfaceService.CACHE_TTL
                cache.set(cache_key, result)
                logger.info(f"✅ [缓存写入] BaziInterfaceService.generate_interface_full: {cache_key[:80]}...")
            except Exception as e:
                # 缓存写入失败不影响业务
                logger.warning(f"⚠️  缓存写入失败（不影响业务）: {e}")
        
        return result







































