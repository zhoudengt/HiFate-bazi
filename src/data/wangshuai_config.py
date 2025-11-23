#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旺衰配置加载器 - 从Excel读取配置表
"""

import os
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas未安装，将使用硬编码配置")


class WangShuaiConfigLoader:
    """旺衰配置加载器 - 从Excel读取配置表"""
    
    def __init__(self, excel_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            excel_path: Excel文件路径，默认：docs/命局旺衰.xlsx
        """
        if excel_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            excel_path = os.path.join(project_root, 'docs', '命局旺衰.xlsx')
        
        self.excel_path = excel_path
        self.config = {}
        self._load_config()
        logger.info(f"✅ 旺衰配置加载完成，配置文件: {excel_path}")
    
    def _load_config(self):
        """从Excel加载所有配置表"""
        if PANDAS_AVAILABLE and os.path.exists(self.excel_path):
            try:
                logger.info(f"📖 开始从Excel加载配置: {self.excel_path}")
                
                # 读取各Sheet（根据实际Excel结构调整）
                excel_file = pd.ExcelFile(self.excel_path)
                sheet_names = excel_file.sheet_names
                logger.info(f"📋 Excel包含的Sheet: {sheet_names}")
                
                # 尝试读取各个Sheet
                configs = {}
                
                # Sheet1: 月支得令表
                if '月支得令' in sheet_names or 'Sheet1' in sheet_names:
                    sheet_name = '月支得令' if '月支得令' in sheet_names else 'Sheet1'
                    df_month = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    configs['month_branch'] = self._df_to_dict(df_month)
                    logger.info(f"✅ 加载月支得令表: {len(configs['month_branch'])} 行")
                
                # Sheet2: 得地五行表
                if '得地五行' in sheet_names or 'Sheet2' in sheet_names:
                    sheet_name = '得地五行' if '得地五行' in sheet_names else 'Sheet2'
                    df_de_di = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    configs['de_di'] = self._df_to_dict(df_de_di)
                    logger.info(f"✅ 加载得地五行表: {len(configs['de_di'])} 行")
                
                # Sheet3: 藏干计分表
                if '藏干计分' in sheet_names or 'Sheet3' in sheet_names:
                    sheet_name = '藏干计分' if '藏干计分' in sheet_names else 'Sheet3'
                    df_hidden = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    configs['hidden_scores'] = self._df_to_dict(df_hidden)
                    logger.info(f"✅ 加载藏干计分表: {len(configs['hidden_scores'])} 行")
                
                # Sheet4: 旺衰阈值表
                if '旺衰阈值' in sheet_names or 'Sheet4' in sheet_names:
                    sheet_name = '旺衰阈值' if '旺衰阈值' in sheet_names else 'Sheet4'
                    df_threshold = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    configs['thresholds'] = self._df_to_dict(df_threshold)
                    logger.info(f"✅ 加载旺衰阈值表: {len(configs['thresholds'])} 行")
                
                # Sheet5: 喜忌判定表
                if '喜忌判定' in sheet_names or 'Sheet5' in sheet_names:
                    sheet_name = '喜忌判定' if '喜忌判定' in sheet_names else 'Sheet5'
                    df_xi_ji = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    configs['xi_ji'] = self._df_to_dict(df_xi_ji)
                    logger.info(f"✅ 加载喜忌判定表: {len(configs['xi_ji'])} 行")
                
                # Sheet6: 十神五行映射表
                if '十神五行' in sheet_names or 'Sheet6' in sheet_names:
                    sheet_name = '十神五行' if '十神五行' in sheet_names else 'Sheet6'
                    df_ten_god = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                    configs['ten_god_elements'] = self._df_to_dict(df_ten_god)
                    logger.info(f"✅ 加载十神五行表: {len(configs['ten_god_elements'])} 行")
                
                self.config = configs
                logger.info(f"✅ 配置加载完成，共 {len(configs)} 个配置表")
                
            except Exception as e:
                logger.error(f"❌ 从Excel加载配置失败: {e}", exc_info=True)
                logger.info("⚠️ 使用硬编码配置作为备选")
                self.config = self._get_default_config()
        else:
            logger.warning("⚠️ Excel文件不存在或pandas未安装，使用硬编码配置")
            self.config = self._get_default_config()
    
    def _df_to_dict(self, df) -> List[Dict]:
        """将DataFrame转换为字典列表"""
        try:
            # 清理NaN值
            df = df.fillna('')
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"转换DataFrame失败: {e}")
            return []
    
    def _get_default_config(self) -> Dict:
        """获取默认硬编码配置（当Excel不可用时）"""
        logger.info("📝 使用硬编码默认配置")
        
        return {
            'month_branch': [
                {'日干': '甲', '月支1': '寅', '月支2': '卯', '月支3': '亥', '月支4': '子'},
                {'日干': '乙', '月支1': '寅', '月支2': '卯', '月支3': '亥', '月支4': '子'},
                {'日干': '丙', '月支1': '巳', '月支2': '午', '月支3': '寅', '月支4': '卯'},
                {'日干': '丁', '月支1': '巳', '月支2': '午', '月支3': '寅', '月支4': '卯'},
                {'日干': '戊', '月支1': '巳', '月支2': '午', '月支3': '辰', '月支4': '戌'},
                {'日干': '己', '月支1': '巳', '月支2': '午', '月支3': '辰', '月支4': '戌'},
                {'日干': '庚', '月支1': '申', '月支2': '酉', '月支3': '辰', '月支4': '戌'},
                {'日干': '辛', '月支1': '申', '月支2': '酉', '月支3': '辰', '月支4': '戌'},
                {'日干': '壬', '月支1': '亥', '月支2': '子', '月支3': '申', '月支4': '酉'},
                {'日干': '癸', '月支1': '亥', '月支2': '子', '月支3': '申', '月支4': '酉'},
            ],
            'de_di': [
                {'日干': '甲', '生得地五行': '水', '同得地五行': '木'},
                {'日干': '乙', '生得地五行': '水', '同得地五行': '木'},
                {'日干': '丙', '生得地五行': '木', '同得地五行': '火'},
                {'日干': '丁', '生得地五行': '木', '同得地五行': '火'},
                {'日干': '戊', '生得地五行': '火', '同得地五行': '土'},
                {'日干': '己', '生得地五行': '火', '同得地五行': '土'},
                {'日干': '庚', '生得地五行': '土', '同得地五行': '金'},
                {'日干': '辛', '生得地五行': '土', '同得地五行': '金'},
                {'日干': '壬', '生得地五行': '金', '同得地五行': '水'},
                {'日干': '癸', '生得地五行': '金', '同得地五行': '水'},
            ],
            'hidden_scores': [
                # 1个藏干：对应分值1 = 15
                {'藏干数量': 1, '第1个匹配': 15, '第1个不匹配': -15},
                # 2个藏干：对应分值1 = 10, 对应分值2 = 5
                {'藏干数量': 2, '第1个匹配': 10, '第1个不匹配': -10, '第2个匹配': 5, '第2个不匹配': -5},
                # 3个藏干：对应分值1 = 8, 对应分值2 = 4, 对应分值3 = 3
                {'藏干数量': 3, '第1个匹配': 8, '第1个不匹配': -8, '第2个匹配': 4, '第2个不匹配': -4, '第3个匹配': 3, '第3个不匹配': -3},
            ],
            'thresholds': [
                {'旺衰状态': '极旺', '最小分数': 80, '最大分数': 100},
                {'旺衰状态': '身旺', '最小分数': 50, '最大分数': 79},
                {'旺衰状态': '平衡', '最小分数': 40, '最大分数': 49},
                {'旺衰状态': '身弱', '最小分数': 20, '最大分数': 39},
                {'旺衰状态': '极弱', '最小分数': 0, '最大分数': 19},
            ],
            'xi_ji': [
                {'旺衰状态': '极旺', '喜神': '食神,伤官,偏财,正财,七杀,正官', '忌神': '比肩,劫财,偏印,正印'},
                {'旺衰状态': '身旺', '喜神': '食神,伤官,偏财,正财,七杀,正官', '忌神': '比肩,劫财,偏印,正印'},
                {'旺衰状态': '平衡', '喜神': '比肩,劫财,食神,伤官', '忌神': '偏财,正财,七杀,正官'},
                {'旺衰状态': '身弱', '喜神': '比肩,劫财,偏印,正印', '忌神': '食神,伤官,偏财,正财,七杀,正官'},
                {'旺衰状态': '极弱', '喜神': '比肩,劫财,偏印,正印', '忌神': '食神,伤官,偏财,正财,七杀,正官'},
            ],
            'ten_god_elements': [
                {'十神': '比肩', '五行': '木'},  # 根据实际天干确定
                {'十神': '劫财', '五行': '木'},
                {'十神': '食神', '五行': '火'},
                {'十神': '伤官', '五行': '火'},
                {'十神': '偏财', '五行': '土'},
                {'十神': '正财', '五行': '土'},
                {'十神': '七杀', '五行': '金'},
                {'十神': '正官', '五行': '金'},
                {'十神': '偏印', '五行': '水'},
                {'十神': '正印', '五行': '水'},
            ]
        }

