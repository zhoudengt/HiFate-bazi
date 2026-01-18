#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旺衰服务层 - 业务逻辑封装
"""

import logging
import os
import sys
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from core.analyzers.wangshuai_analyzer import WangShuaiAnalyzer

logger = logging.getLogger(__name__)


class WangShuaiService:
    """旺衰服务层"""
    
    # Redis缓存TTL（30天，旺衰数据不随时间变化）
    CACHE_TTL = 2592000  # 30天
    
    @staticmethod
    def _generate_cache_key(solar_date: str, solar_time: str, gender: str) -> str:
        """
        生成缓存键
        
        Args:
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
            
        Returns:
            str: 缓存键
        """
        # 生成键（格式：wangshuai:{solar_date}:{solar_time}:{gender}）
        key_parts = [
            'wangshuai',
            solar_date,
            solar_time,
            gender
        ]
        return ':'.join(key_parts)
    
    @staticmethod
    def calculate_wangshuai(solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """
        计算命局旺衰（带Redis缓存）
        
        Args:
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
        
        Returns:
            旺衰分析结果
        """
        # 1. 生成缓存键
        cache_key = WangShuaiService._generate_cache_key(solar_date, solar_time, gender)
        
        # 2. 先查缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            # 设置 L2 Redis TTL 为 30 天
            cache.l2.ttl = WangShuaiService.CACHE_TTL
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"✅ [缓存命中] WangShuaiService.calculate_wangshuai: {cache_key[:50]}...")
                return cached_result
        except Exception as e:
            # Redis不可用，降级到直接计算
            logger.warning(f"⚠️  Redis缓存不可用，降级到直接计算: {e}")
        
        # 3. 缓存未命中，执行计算
        logger.info(f"⏱️ [缓存未命中] WangShuaiService.calculate_wangshuai: {cache_key[:50]}...")
        logger.info(f"🔍 旺衰服务: 开始计算 - 日期: {solar_date}, 时间: {solar_time}, 性别: {gender}")
        
        try:
            analyzer = WangShuaiAnalyzer()
            result = analyzer.analyze(solar_date, solar_time, gender)
            
            # 获取月支并计算调候
            bazi_info = result.get('bazi_info', {})
            month_branch = bazi_info.get('month_branch', '')
            
            # 计算调候信息
            if month_branch:
                tiaohou_info = WangShuaiAnalyzer.calculate_tiaohou(month_branch)
                result['tiaohou'] = tiaohou_info
                logger.info(f"🌡️ 调候计算: 月支={month_branch}, 调候五行={tiaohou_info.get('tiaohou_element')}")
            else:
                result['tiaohou'] = None
                logger.warning("⚠️ 调候计算: 未找到月支信息")
            
            logger.info(f"✅ 旺衰服务: 计算成功 - 旺衰: {result.get('wangshuai')}, 总分: {result.get('total_score')}")
            
            response = {
                'success': True,
                'data': result
            }
            
            # 4. 写入缓存（仅成功时）
            if response.get('success'):
                try:
                    cache = get_multi_cache()
                    cache.l2.ttl = WangShuaiService.CACHE_TTL
                    cache.set(cache_key, response)
                    logger.info(f"✅ [缓存写入] WangShuaiService.calculate_wangshuai: {cache_key[:50]}...")
                except Exception as e:
                    # 缓存写入失败不影响业务
                    logger.warning(f"⚠️  缓存写入失败（不影响业务）: {e}")
            
            return response
        except Exception as e:
            logger.error(f"❌ 旺衰服务: 计算失败 - {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

