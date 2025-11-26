# -*- coding: utf-8 -*-
"""
八字服务客户端
调用八字核心服务获取用户的喜神、忌神等信息
"""

import sys
import os
import logging
from typing import Dict, Optional

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

logger = logging.getLogger(__name__)


class BaziClient:
    """八字服务客户端"""
    
    def __init__(self):
        """初始化八字客户端"""
        try:
            from src.clients.bazi_analyzer_client import BaziAnalyzerClient
            from src.clients.wangshuai_analyzer_client import WangShuaiAnalyzerClient
            
            self.analyzer_client = BaziAnalyzerClient()
            self.wangshuai_client = WangShuaiAnalyzerClient()
            
            logger.info("✅ 八字客户端初始化成功")
        except Exception as e:
            logger.error(f"❌ 八字客户端初始化失败: {e}")
            self.analyzer_client = None
            self.wangshuai_client = None
    
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
        try:
            # 1. 调用旺衰分析服务获取喜神忌神
            if self.wangshuai_client:
                try:
                    result = self.wangshuai_client.calculate_wangshuai(
                        solar_date, solar_time, gender
                    )
                    
                    if result.get('success'):
                        data = result.get('data', {})
                        xishen_list = data.get('xishen', [])
                        jishen_list = data.get('jishen', [])
                        
                        # 提取主要喜神忌神
                        xishen = xishen_list[0] if xishen_list else None
                        jishen = jishen_list[0] if jishen_list else None
                        
                        logger.info(f"获取喜神忌神成功: 喜神={xishen}, 忌神={jishen}")
                        
                        return {
                            'success': True,
                            'xishen': xishen,
                            'xishen_list': xishen_list,
                            'jishen': jishen,
                            'jishen_list': jishen_list,
                            'wangshuai_level': data.get('level', ''),
                            'day_stem': data.get('bazi', {}).get('day_pillar', {}).get('stem', '')
                        }
                except Exception as e:
                    logger.warning(f"旺衰服务调用失败，尝试本地计算: {e}")
            
            # 2. 备用方案：使用本地八字计算
            return self._calculate_local(solar_date, solar_time, gender)
            
        except Exception as e:
            logger.error(f"获取喜神忌神失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'xishen': None,
                'jishen': None
            }
    
    def _calculate_local(self, solar_date: str, solar_time: str, gender: str) -> Dict:
        """本地计算喜神忌神（备用方案）"""
        try:
            from src.bazi_calculator import WenZhenBazi
            from src.analyzers.wangshuai_analyzer import WangShuaiAnalyzer
            
            # 1. 计算八字
            bazi_calc = WenZhenBazi(solar_date, solar_time, gender)
            bazi_result = bazi_calc.calculate()
            
            # 2. 计算旺衰和喜神忌神
            analyzer = WangShuaiAnalyzer()
            wangshuai_result = analyzer.analyze(bazi_result)
            
            xishen_list = wangshuai_result.get('xishen', [])
            jishen_list = wangshuai_result.get('jishen', [])
            
            xishen = xishen_list[0] if xishen_list else None
            jishen = jishen_list[0] if jishen_list else None
            
            logger.info(f"本地计算喜神忌神成功: 喜神={xishen}, 忌神={jishen}")
            
            return {
                'success': True,
                'xishen': xishen,
                'xishen_list': xishen_list,
                'jishen': jishen,
                'jishen_list': jishen_list,
                'wangshuai_level': wangshuai_result.get('level', ''),
                'day_stem': bazi_result.get('bazi_pillars', {}).get('day_pillar', {}).get('stem', ''),
                'source': 'local'
            }
            
        except Exception as e:
            logger.error(f"本地计算失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'xishen': None,
                'jishen': None
            }
    
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
            from src.bazi_calculator import WenZhenBazi
            
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
    print(f"结果: {result}")

