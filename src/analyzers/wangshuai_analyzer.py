#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命局旺衰分析器 - 核心计算逻辑
"""

import logging
from typing import Dict, List, Any, Optional
from src.data.wangshuai_config import WangShuaiConfigLoader
from src.tool.BaziCalculator import BaziCalculator
from src.data.constants import HIDDEN_STEMS, STEM_ELEMENTS

logger = logging.getLogger(__name__)


class WangShuaiAnalyzer:
    """命局旺衰分析器"""
    
    # 五行生克关系
    ELEMENT_RELATIONS = {
        '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
        '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
        '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
        '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
        '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
    }
    
    def __init__(self, config_loader: Optional[WangShuaiConfigLoader] = None):
        """
        初始化分析器
        
        Args:
            config_loader: 配置加载器，默认自动创建
        """
        if config_loader is None:
            config_loader = WangShuaiConfigLoader()
        self.config = config_loader.config
        logger.info("✅ 旺衰分析器初始化完成")
    
    def analyze(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        """
        分析命局旺衰
        
        Args:
            solar_date: 出生日期 '1987-01-07'
            solar_time: 出生时间 '09:55'
            gender: 性别 'male'/'female'
        
        Returns:
            旺衰分析结果
        """
        logger.info(f"🔍 开始分析旺衰 - 日期: {solar_date}, 时间: {solar_time}, 性别: {gender}")
        
        # 1. 计算八字
        logger.info("📊 步骤1: 计算八字基础信息")
        bazi = self._calculate_bazi(solar_date, solar_time, gender)
        logger.info(f"   日干: {bazi['day_stem']}, 月支: {bazi['month_branch']}")
        logger.info(f"   年柱: {bazi['year_stem']}{bazi['year_branch']}, "
                   f"月柱: {bazi['month_stem']}{bazi['month_branch']}, "
                   f"日柱: {bazi['day_stem']}{bazi['day_branch']}, "
                   f"时柱: {bazi['hour_stem']}{bazi['hour_branch']}")
        
        # 2. 计算得令分（45分或-45分）
        logger.info("📊 步骤2: 计算得令分（月支权重）")
        de_ling_score = self._calculate_de_ling(bazi)
        logger.info(f"   得令分: {de_ling_score} 分")
        
        # 3. 计算得地分（年日时三柱）
        logger.info("📊 步骤3: 计算得地分（年日时支）")
        de_di_score = self._calculate_de_di(bazi)
        logger.info(f"   得地分: {de_di_score} 分")
        
        # 4. 计算得势分（10分或0分）✅ 修正为10分
        logger.info("📊 步骤4: 计算得势分（天干生扶）")
        de_shi_score = self._calculate_de_shi(bazi)
        logger.info(f"   得势分: {de_shi_score} 分")
        
        # 5. 计算总分并判定旺衰
        logger.info("📊 步骤5: 计算总分并判定旺衰")
        total_score = de_ling_score + de_di_score + de_shi_score
        logger.info(f"   总分: {total_score} = {de_ling_score} + {de_di_score} + {de_shi_score}")
        wangshuai = self._determine_wangshuai(total_score)
        logger.info(f"   旺衰判定: {wangshuai}")
        
        # 6. 判定喜忌
        logger.info("📊 步骤6: 判定喜忌")
        xi_ji = self._determine_xi_ji(wangshuai)
        logger.info(f"   喜神: {xi_ji['xi_shen']}")
        logger.info(f"   忌神: {xi_ji['ji_shen']}")
        
        # 7. 计算喜忌五行
        logger.info("📊 步骤7: 计算喜忌五行")
        xi_ji_elements = self._calculate_xi_ji_elements(xi_ji, bazi)
        logger.info(f"   喜神五行: {xi_ji_elements['xi_shen']}")
        logger.info(f"   忌神五行: {xi_ji_elements['ji_shen']}")
        
        result = {
            'wangshuai': wangshuai,
            'total_score': total_score,
            'scores': {
                'de_ling': de_ling_score,
                'de_di': de_di_score,
                'de_shi': de_shi_score
            },
            'xi_shen': xi_ji['xi_shen'],
            'ji_shen': xi_ji['ji_shen'],
            'xi_shen_elements': xi_ji_elements['xi_shen'],
            'ji_shen_elements': xi_ji_elements['ji_shen'],
            'bazi_info': {
                'day_stem': bazi['day_stem'],
                'month_branch': bazi['month_branch']
            }
        }
        
        logger.info("✅ 旺衰分析完成")
        return result
    
    def _calculate_bazi(self, solar_date: str, solar_time: str, gender: str) -> Dict:
        """计算八字基础信息"""
        try:
            calculator = BaziCalculator(solar_date, solar_time, gender)
            result = calculator.calculate()
            
            if not result or 'bazi_pillars' not in result:
                raise ValueError("八字计算结果为空")
            
            pillars = result['bazi_pillars']
            return {
                'year_stem': pillars['year']['stem'],
                'year_branch': pillars['year']['branch'],
                'month_stem': pillars['month']['stem'],
                'month_branch': pillars['month']['branch'],
                'day_stem': pillars['day']['stem'],
                'day_branch': pillars['day']['branch'],
                'hour_stem': pillars['hour']['stem'],
                'hour_branch': pillars['hour']['branch']
            }
        except Exception as e:
            logger.error(f"计算八字失败: {e}", exc_info=True)
            raise
    
    def _calculate_de_ling(self, bazi: Dict) -> int:
        """
        计算得令分（45分或-45分）
        
        根据日干查询对应的月支：
        - 若满足条件（得令）：+45分
        - 若不满足条件（失令）：-45分
        """
        day_stem = bazi['day_stem']  # 日干：丙
        month_branch = bazi['month_branch']  # 月支
        
        logger.info(f"   检查得令: 日干={day_stem}, 月支={month_branch}")
        
        # 从配置表查询日干对应的得令月支列表
        month_config = self.config.get('month_branch', [])
        de_ling_branches = []
        
        for row in month_config:
            if row.get('日干') == day_stem:
                # 获取该日干对应的得令月支列表
                de_ling_branches = [
                    row.get('月支1'),
                    row.get('月支2'),
                    row.get('月支3'),
                    row.get('月支4')
                ]
                de_ling_branches = [b for b in de_ling_branches if b]  # 去除空值
                logger.info(f"   日干{day_stem}的得令月支: {de_ling_branches}")
                break
        
        if not de_ling_branches:
            logger.warning(f"   未找到日干{day_stem}的得令配置，默认失令=-45分")
            return -45
        
        if month_branch in de_ling_branches:
            logger.info(f"   ✅ 月支{month_branch}在得令列表中，得令=+45分")
            return 45
        else:
            logger.info(f"   ❌ 月支{month_branch}不在得令列表中，失令=-45分")
            return -45
    
    def _calculate_de_di(self, bazi: Dict) -> int:
        """
        计算得地分（年日时三柱）
        
        根据日干确定生得地五行和同得地五行
        检查年日时三柱的藏干，按顺序匹配计分
        """
        day_stem = bazi['day_stem']
        day_element = STEM_ELEMENTS.get(day_stem)
        
        logger.info(f"   检查得地: 日干={day_stem}, 日干五行={day_element}")
        
        # 从配置表获取生得地和同得地五行
        de_di_config = self.config.get('de_di', [])
        sheng_de_di = None
        tong_de_di = None
        
        for row in de_di_config:
            if row.get('日干') == day_stem:
                sheng_de_di = row.get('生得地五行')  # 木
                tong_de_di = row.get('同得地五行')   # 火
                break
        
        if not sheng_de_di or not tong_de_di:
            logger.warning(f"   未找到日干{day_stem}的得地配置")
            return 0
        
        logger.info(f"   生得地五行: {sheng_de_di}, 同得地五行: {tong_de_di}")
        target_elements = [sheng_de_di, tong_de_di]
        
        total_score = 0
        
        # 检查年、日、时三柱
        for pillar_name in ['year', 'day', 'hour']:
            branch = bazi[f'{pillar_name}_branch']
            hidden_stems = HIDDEN_STEMS.get(branch, [])
            
            logger.info(f"   {pillar_name}柱: {branch}, 藏干: {hidden_stems}")
            
            # 根据藏干数量匹配计分规则
            hidden_count = len(hidden_stems)
            score_rule = self._get_hidden_score_rule(hidden_count)
            
            if not score_rule:
                logger.warning(f"   未找到{hidden_count}个藏干的计分规则")
                continue
            
            # 按顺序匹配藏干
            pillar_score = 0
            for idx, hidden_stem_info in enumerate(hidden_stems):
                # 提取天干和五行
                stem_char = hidden_stem_info[0]  # 天干字符
                stem_element = STEM_ELEMENTS.get(stem_char)
                
                if not stem_element:
                    logger.warning(f"   未找到天干{stem_char}的五行")
                    continue
                
                position = idx + 1
                if stem_element in target_elements:
                    # 匹配到生得地或同得地
                    key = f'第{position}个匹配'
                    score = score_rule.get(key, 0)
                    pillar_score += score
                    logger.info(f"     第{position}个藏干{stem_char}({stem_element})匹配，得分: {score}")
                else:
                    # 未匹配
                    key = f'第{position}个不匹配'
                    score = score_rule.get(key, 0)
                    pillar_score += score
                    logger.info(f"     第{position}个藏干{stem_char}({stem_element})不匹配，得分: {score}")
            
            logger.info(f"   {pillar_name}柱得分: {pillar_score}")
            total_score += pillar_score
        
        logger.info(f"   得地总分: {total_score}")
        return total_score
    
    def _get_hidden_score_rule(self, hidden_count: int) -> Dict:
        """根据藏干数量获取计分规则"""
        hidden_config = self.config.get('hidden_scores', [])
        
        for row in hidden_config:
            if row.get('藏干数量') == hidden_count:
                # 返回该行的计分规则
                rule = {}
                for key, value in row.items():
                    if key != '藏干数量' and value:
                        rule[key] = value
                logger.info(f"   找到{hidden_count}个藏干的计分规则: {rule}")
                return rule
        
        return {}
    
    def _calculate_de_shi(self, bazi: Dict) -> int:
        """
        计算得势分（10分或0分）✅ 修正为10分
        
        检查年干、月干、时干
        若存在生扶日干的天干，记10分
        """
        day_stem = bazi['day_stem']
        day_element = STEM_ELEMENTS.get(day_stem)
        
        logger.info(f"   检查得势: 日干={day_stem}, 日干五行={day_element}")
        
        # 检查年干、月干、时干
        for stem_name in ['year_stem', 'month_stem', 'hour_stem']:
            stem = bazi[stem_name]
            stem_element = STEM_ELEMENTS.get(stem)
            
            if not stem_element:
                continue
            
            logger.info(f"   检查{stem_name}: {stem}({stem_element})")
            
            # 判断是否生扶日干
            # 1. 同五行（如日干丙，出现丙或丁）
            if stem_element == day_element:
                logger.info(f"   ✅ {stem_name}{stem}与日干{day_stem}同五行，得势=10分")
                return 10  # ✅ 修正为10分
            
            # 2. 生我者（如日干丙属火，出现甲或乙属木）
            if self._is_sheng_wo(day_element, stem_element):
                logger.info(f"   ✅ {stem_name}{stem}({stem_element})生日干{day_stem}({day_element})，得势=10分")
                return 10  # ✅ 修正为10分
        
        logger.info(f"   ❌ 未找到生扶日干的天干，得势=0分")
        return 0
    
    def _is_sheng_wo(self, day_element: str, stem_element: str) -> bool:
        """判断是否生我者"""
        relations = self.ELEMENT_RELATIONS.get(day_element, {})
        return relations.get('produced_by') == stem_element
    
    def _determine_wangshuai(self, total_score: int) -> str:
        """
        判定旺衰（使用固定阈值，数学比较）
        
        阈值规则（更新后）：
        - 总分 > +40分      → 极旺
        - 10 <= 总分 <= 40  → 身旺
        - -10 < 总分 < 10   → 平衡
        - -40 <= 总分 <= -10 → 身弱
        - 总分 < -40分      → 极弱
        """
        logger.info(f"   根据总分{total_score}判定旺衰（数学比较）")
        
        # 按优先级判定（数学比较，不是绝对值）
        if total_score > 40:
            wangshuai = '极旺'
            logger.info(f"   ✅ 总分{total_score} > 40，判定为: {wangshuai}")
        elif 10 <= total_score <= 40:
            wangshuai = '身旺'
            logger.info(f"   ✅ 10 <= 总分{total_score} <= 40，判定为: {wangshuai}")
        elif -10 < total_score < 10:
            wangshuai = '平衡'
            logger.info(f"   ✅ -10 < 总分{total_score} < 10，判定为: {wangshuai}")
        elif -40 <= total_score <= -10:
            wangshuai = '身弱'
            logger.info(f"   ✅ -40 <= 总分{total_score} <= -10，判定为: {wangshuai}")
        else:  # total_score < -40
            wangshuai = '极弱'
            logger.info(f"   ✅ 总分{total_score} < -40，判定为: {wangshuai}")
        
        return wangshuai
    
    def _determine_xi_ji(self, wangshuai: str) -> Dict[str, List[str]]:
        """判定喜忌"""
        xi_ji_config = self.config.get('xi_ji', [])
        
        for row in xi_ji_config:
            if row.get('旺衰状态') == wangshuai:
                xi_shen_str = row.get('喜神', '')
                ji_shen_str = row.get('忌神', '')
                
                xi_shen = xi_shen_str.split(',') if isinstance(xi_shen_str, str) else (xi_shen_str or [])
                ji_shen = ji_shen_str.split(',') if isinstance(ji_shen_str, str) else (ji_shen_str or [])
                
                # 去除空值
                xi_shen = [x.strip() for x in xi_shen if x.strip()]
                ji_shen = [j.strip() for j in ji_shen if j.strip()]
                
                return {
                    'xi_shen': xi_shen,
                    'ji_shen': ji_shen
                }
        
        return {'xi_shen': [], 'ji_shen': []}
    
    def _calculate_xi_ji_elements(self, xi_ji: Dict, bazi: Dict) -> Dict[str, List[str]]:
        """
        计算喜忌五行（根据表格规则）
        
        规则：
        - 扶（比肩、劫财）→ 日干五行（同我）
        - 泄（食神、伤官）→ 日干所生的五行（我生）
        - 耗（偏财、正财）→ 日干所克的五行（我克）
        - 克（七杀、正官）→ 克日干的五行（克我）
        - 生（偏印、正印）→ 生日干的五行（生我）
        """
        day_stem = bazi['day_stem']  # 日干：丙
        day_element = STEM_ELEMENTS.get(day_stem)  # 日干五行：火
        
        if not day_element:
            logger.warning(f"未找到日干{day_stem}的五行")
            return {'xi_shen': [], 'ji_shen': []}
        
        # 获取五行生克关系
        relations = self.ELEMENT_RELATIONS.get(day_element, {})
        
        # 十神到五行映射规则（根据表格）
        ten_god_element_map = {
            # 扶（同我）
            '比肩': day_element,  # 日干五行
            '劫财': day_element,  # 日干五行
            
            # 泄（我生）
            '食神': relations.get('produces'),  # 日干所生的五行
            '伤官': relations.get('produces'),  # 日干所生的五行
            
            # 耗（我克）
            '偏财': relations.get('controls'),  # 日干所克的五行
            '正财': relations.get('controls'),  # 日干所克的五行
            
            # 克（克我）
            '七杀': relations.get('controlled_by'),  # 克日干的五行
            '正官': relations.get('controlled_by'),  # 克日干的五行
            
            # 生（生我）
            '偏印': relations.get('produced_by'),  # 生日干的五行
            '正印': relations.get('produced_by')   # 生日干的五行
        }
        
        xi_elements = []
        ji_elements = []
        
        # 计算喜神五行
        for ten_god in xi_ji['xi_shen']:
            element = ten_god_element_map.get(ten_god)
            if element and element not in xi_elements:
                xi_elements.append(element)
        
        # 计算忌神五行
        for ten_god in xi_ji['ji_shen']:
            element = ten_god_element_map.get(ten_god)
            if element and element not in ji_elements:
                ji_elements.append(element)
        
        logger.info(f"   日干{day_stem}({day_element})的喜忌五行计算完成")
        logger.info(f"   喜神五行: {xi_elements}, 忌神五行: {ji_elements}")
        
        return {
            'xi_shen': xi_elements,
            'ji_shen': ji_elements
        }
    
    @staticmethod
    def calculate_tiaohou(month_branch: str) -> Dict[str, Any]:
        """
        计算调候五行
        
        调候：调节气候平衡
        - 夏季炎热（巳午未月），需要水来调节降温
        - 冬季寒冷（亥子丑月），需要火来调节取暖
        - 春秋季节气候适中，不需要特别调候
        
        Args:
            month_branch: 月支（如 '午'、'子'）
        
        Returns:
            {
                'tiaohou_element': '水' or '火' or None,
                'season': '夏季' or '冬季' or '春秋',
                'description': 说明文字
            }
        """
        # 夏季三月：巳午未 → 需要水来调候
        if month_branch in ['巳', '午', '未']:
            return {
                'tiaohou_element': '水',
                'season': '夏季',
                'month_branch': month_branch,
                'description': '夏月炎热，需水调候'
            }
        
        # 冬季三月：亥子丑 → 需要火来调候
        elif month_branch in ['亥', '子', '丑']:
            return {
                'tiaohou_element': '火',
                'season': '冬季',
                'month_branch': month_branch,
                'description': '冬月寒冷，需火调候'
            }
        
        # 春秋季节：寅卯辰、申酉戌 → 气候适中
        else:
            return {
                'tiaohou_element': None,
                'season': '春秋',
                'month_branch': month_branch,
                'description': '春秋气候适中，无需特别调候'
            }

