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

from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer

logger = logging.getLogger(__name__)


class WangShuaiService:
    """旺衰服务层"""
    
    @staticmethod
    def calculate_wangshuai(solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """
        计算命局旺衰
        
        Args:
            solar_date: 出生日期
            solar_time: 出生时间
            gender: 性别
        
        Returns:
            旺衰分析结果
        """
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
            
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            logger.error(f"❌ 旺衰服务: 计算失败 - {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

