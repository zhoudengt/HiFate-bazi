# -*- coding: utf-8 -*-
"""
八字服务客户端
直接使用本地服务获取用户的喜神、忌神等信息
修复：移除不存在的 gRPC 客户端引用，直接使用本地 WangShuaiService
"""

import sys
import os
import logging
import time
from typing import Dict, Optional

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger(__name__)


class BaziClient:
    """八字服务客户端（使用本地服务）"""
    
    def __init__(self):
        """初始化八字客户端"""
        try:
            # 直接使用本地旺衰服务，不需要 gRPC 客户端
            from server.services.wangshuai_service import WangShuaiService
            self.wangshuai_service = WangShuaiService
            logger.info("✅ 八字客户端初始化成功（本地服务模式）")
        except Exception as e:
            logger.error(f"❌ 八字客户端初始化失败: {e}", exc_info=True)
            self.wangshuai_service = None
    
    def get_xishen_jishen(self, solar_date: str, solar_time: str, gender: str) -> Dict:
        """
        获取用户的喜神和忌神
        
        Args:
            solar_date: 阳历日期 YYYY-MM-DD
            solar_time: 出生时间 HH:MM
            gender: 性别 male/female
        
        Returns:
            喜神忌神信息
        """
        start_time = time.time()
        
        try:
            # 使用本地旺衰服务计算喜神忌神
            if not self.wangshuai_service:
                logger.warning("旺衰服务未初始化，尝试直接使用分析器")
                return self._calculate_with_analyzer(solar_date, solar_time, gender)
            
            # 调用旺衰服务
            result = self.wangshuai_service.calculate_wangshuai(
                solar_date, solar_time, gender
            )
            
            if not result or not result.get('success'):
                error_msg = result.get('error', '未知错误') if result else '返回空结果'
                logger.error(f"旺衰服务计算失败: {error_msg}")
                # 尝试使用分析器直接计算
                return self._calculate_with_analyzer(solar_date, solar_time, gender)
            
            # 提取数据
            data = result.get('data', {})
            xishen_list = data.get('xishen', [])
            jishen_list = data.get('jishen', [])
            
            # 提取主要喜神忌神
            xishen = xishen_list[0] if xishen_list else None
            jishen = jishen_list[0] if jishen_list else None
            
            # 获取日干
            bazi_info = data.get('bazi_info', {})
            day_stem = self._safe_get_day_stem(bazi_info)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ 获取喜神忌神成功（耗时: {elapsed:.2f}秒）: 喜神={xishen}, 忌神={jishen}")
            
            return {
                'success': True,
                'xishen': xishen,
                'xishen_list': xishen_list,
                'jishen': jishen,
                'jishen_list': jishen_list,
                'wangshuai_level': data.get('level', ''),
                'day_stem': day_stem,
                'source': 'service'
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 获取喜神忌神失败（耗时: {elapsed:.2f}秒）: {e}", exc_info=True)
            # 尝试使用分析器直接计算作为最后手段
            try:
                return self._calculate_with_analyzer(solar_date, solar_time, gender)
            except Exception as e2:
                logger.error(f"❌ 所有计算方法都失败: {e2}")
                return {
                    'success': False,
                    'error': str(e),
                    'xishen': None,
                    'jishen': None
                }
    
    def _calculate_with_analyzer(self, solar_date: str, solar_time: str, gender: str) -> Dict:
        """直接使用分析器计算喜神忌神（备用方案）"""
        try:
            from core.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
            
            # 直接使用分析器，它内部会计算八字
            analyzer = WangShuaiAnalyzer()
            wangshuai_result = analyzer.analyze(solar_date, solar_time, gender)
            
            if not wangshuai_result or not wangshuai_result.get('success'):
                error_msg = wangshuai_result.get('error', '未知错误') if wangshuai_result else '返回空结果'
                raise Exception(f"旺衰分析失败: {error_msg}")
            
            xishen_list = wangshuai_result.get('xishen', [])
            jishen_list = wangshuai_result.get('jishen', [])
            
            xishen = xishen_list[0] if xishen_list else None
            jishen = jishen_list[0] if jishen_list else None
            
            # 获取日干
            bazi_info = wangshuai_result.get('bazi_info', {})
            day_stem = self._safe_get_day_stem(bazi_info)
            
            logger.info(f"✅ 直接计算喜神忌神成功: 喜神={xishen}, 忌神={jishen}")
            
            return {
                'success': True,
                'xishen': xishen,
                'xishen_list': xishen_list,
                'jishen': jishen,
                'jishen_list': jishen_list,
                'wangshuai_level': wangshuai_result.get('level', ''),
                'day_stem': day_stem,
                'source': 'analyzer'
            }
            
        except Exception as e:
            logger.error(f"直接计算失败: {e}", exc_info=True)
            raise
    
    def _safe_get_day_stem(self, bazi_info: Optional[Dict]) -> str:
        """安全获取日干"""
        try:
            if not bazi_info or not isinstance(bazi_info, dict):
                return ''
            day_stem = bazi_info.get('day_stem', '')
            return day_stem if isinstance(day_stem, str) else ''
        except Exception:
            return ''
    
    def get_basic_info(self, solar_date: str, solar_time: str, gender: str) -> Dict:
        """
        获取八字基本信息
        
        Args:
            solar_date: 阳历日期
            solar_time: 出生时间
            gender: 性别
        
        Returns:
            八字基本信息
        """
        try:
            from core.calculators.bazi_calculator import WenZhenBazi
            
            bazi_calc = WenZhenBazi(solar_date, solar_time, gender)
            bazi_result = bazi_calc.calculate()
            
            return {
                'success': True,
                'bazi_pillars': bazi_result.get('bazi_pillars', {}),
                'elements': bazi_result.get('elements', {}),
                'element_counts': bazi_result.get('element_counts', {})
            }
            
        except Exception as e:
            logger.error(f"获取八字基本信息失败: {e}")
            return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    client = BaziClient()
    
    result = client.get_xishen_jishen('1990-01-01', '12:00', 'male')
    logger.info(f"结果: {result}")

