# -*- coding: utf-8 -*-
"""
办公桌风水主分析器
整合物品检测、方位计算、规则匹配、八字融合
"""

import logging
import time
from typing import Dict, Optional

from item_detector import DeskItemDetector
from position_calculator import PositionCalculator
from rule_engine import DeskFengshuiEngine
from bazi_client import BaziClient

logger = logging.getLogger(__name__)


class DeskFengshuiAnalyzer:
    """办公桌风水分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.detector = DeskItemDetector()
        self.engine = DeskFengshuiEngine()
        self.bazi_client = BaziClient()
        
        logger.info("✅ 办公桌风水分析器初始化成功")
    
    def analyze(self, image_bytes: bytes, solar_date: Optional[str] = None,
                solar_time: Optional[str] = None, gender: Optional[str] = None,
                use_bazi: bool = True) -> Dict:
        """
        分析办公桌风水
        
        Args:
            image_bytes: 办公桌照片
            solar_date: 用户出生日期（可选）
            solar_time: 用户出生时间（可选）
            gender: 性别（可选）
            use_bazi: 是否使用八字分析
        
        Returns:
            分析结果
        """
        start_time = time.time()
        
        try:
            # 1. 检测物品
            logger.info("开始物品检测...")
            detection_result = self.detector.detect(image_bytes)
            
            if not detection_result.get('success'):
                return {
                    'success': False,
                    'error': detection_result.get('error', '物品检测失败')
                }
            
            items = detection_result.get('items', [])
            img_shape = detection_result.get('image_shape')
            
            logger.info(f"检测到 {len(items)} 个物品")
            
            # 2. 计算位置
            logger.info("计算物品位置...")
            enriched_items = PositionCalculator.calculate_all_positions(items, img_shape)
            
            # 3. 获取八字信息（如果需要）
            bazi_info = None
            if use_bazi and solar_date and solar_time and gender:
                logger.info("获取八字信息...")
                bazi_result = self.bazi_client.get_xishen_jishen(solar_date, solar_time, gender)
                
                if bazi_result.get('success'):
                    bazi_info = bazi_result
                else:
                    logger.warning(f"获取八字信息失败: {bazi_result.get('error')}")
            
            # 4. 匹配规则
            logger.info("匹配风水规则...")
            rule_result = self.engine.match_rules(enriched_items, bazi_info)
            
            if not rule_result.get('success'):
                return {
                    'success': False,
                    'error': rule_result.get('error', '规则匹配失败')
                }
            
            # 5. 构建响应
            duration = int((time.time() - start_time) * 1000)
            
            response = {
                'success': True,
                'items': enriched_items,
                'adjustments': rule_result.get('adjustments', []),
                'additions': rule_result.get('additions', []),
                'removals': rule_result.get('removals', []),
                'score': rule_result.get('score', 0),
                'summary': rule_result.get('summary', ''),
                'duration': duration
            }
            
            # 添加八字信息（如果有）
            if bazi_info:
                response['xishen'] = bazi_info.get('xishen', '')
                response['jishen'] = bazi_info.get('jishen', '')
            
            logger.info(f"分析完成，耗时 {duration}ms，评分 {response['score']}分")
            
            return response
            
        except Exception as e:
            logger.error(f"分析失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    analyzer = DeskFengshuiAnalyzer()
    
    # 加载测试图像
    with open("test_desk.jpg", "rb") as f:
        image_bytes = f.read()
    
    result = analyzer.analyze(
        image_bytes=image_bytes,
        solar_date="1990-01-01",
        solar_time="12:00",
        gender="male",
        use_bazi=True
    )
    
    print(f"分析结果: {result}")

