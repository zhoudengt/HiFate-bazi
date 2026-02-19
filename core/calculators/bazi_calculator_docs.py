#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging

# 添加项目根目录到模块路径，确保与原脚本行为一致
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import math
import contextlib
import io
from typing import Dict, Any, Optional
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

from core.data.constants import *  # noqa: F401,F403
from core.data.stems_branches import *  # noqa: F401,F403
from core.config.deities_config import DeitiesCalculator
from core.config.star_fortune_config import StarFortuneCalculator
from core.config.shishen_short_config import SHISHEN_SHORT_MAP, BRANCH_MAIN_QI, TIANGAN_SHISHEN_MAP, DIZHI_SHISHEN_MAP
from core.calculators.LunarConverter import LunarConverter


class BaziCalculator:
    """八字计算工具类 - 使用统一的农历转换方法"""

    def __init__(self, solar_date, solar_time, gender='male'):
        self.solar_date = solar_date
        self.solar_time = solar_time
        self.gender = gender
        self.lunar_date = None
        self.bazi_pillars = {}
        self.details = {}
        self.adjusted_solar_date = solar_date  # 记录调整后的日期
        self.adjusted_solar_time = solar_time  # 记录调整后的时间
        self.is_zi_shi_adjusted = False  # 标记是否进行了子时调整
        self.last_result = None
        self.last_matched_rules = []

        # 五行生克关系
        self.element_relations = {
            '木': {'produces': '火', 'controls': '土', 'produced_by': '水', 'controlled_by': '金'},
            '火': {'produces': '土', 'controls': '金', 'produced_by': '木', 'controlled_by': '水'},
            '土': {'produces': '金', 'controls': '水', 'produced_by': '火', 'controlled_by': '木'},
            '金': {'produces': '水', 'controls': '木', 'produced_by': '土', 'controlled_by': '火'},
            '水': {'produces': '木', 'controls': '火', 'produced_by': '金', 'controlled_by': '土'}
        }

    def get_main_star(self, day_stem, target_stem, pillar_type):
        """
        计算主星（十神）- 修正版本
        与HiFate逻辑一致
        """
        if pillar_type == 'day':
            return '元男' if self.gender == 'male' else '元女'

        day_element = STEM_ELEMENTS[day_stem]
        target_element = STEM_ELEMENTS[target_stem]
        day_yinyang = STEM_YINYANG[day_stem]
        target_yinyang = STEM_YINYANG[target_stem]

        relation_type = self._get_element_relation(day_element, target_element)
        is_same_yinyang = (day_yinyang == target_yinyang)

        if relation_type == 'same':
            return '比肩' if is_same_yinyang else '劫财'
        elif relation_type == 'me_producing':
            return '食神' if is_same_yinyang else '伤官'
        elif relation_type == 'me_controlling':
            return '偏财' if is_same_yinyang else '正财'
        elif relation_type == 'controlling_me':
            return '七杀' if is_same_yinyang else '正官'
        elif relation_type == 'producing_me':
            return '偏印' if is_same_yinyang else '正印'

        return '未知'

    def _get_element_relation(self, day_element, target_element):
        """判断五行生克关系"""
        if day_element == target_element:
            return 'same'

        relations = self.element_relations[day_element]

        if target_element == relations['produces']:
            return 'me_producing'
        elif target_element == relations['controls']:
            return 'me_controlling'
        elif target_element == relations['produced_by']:
            return 'producing_me'
        elif target_element == relations['controlled_by']:
            return 'controlling_me'

        return 'unknown'

    def get_branch_ten_gods(self, day_stem, branch):
        """
        计算地支藏干的十神（副星）- 修正版本
        与HiFate逻辑一致
        """
        hidden_stems = HIDDEN_STEMS.get(branch, [])
        branch_gods = []

        for hidden_stem in hidden_stems:
            stem_char = hidden_stem[0] if len(hidden_stem) > 0 else hidden_stem
            ten_god = self.get_main_star(day_stem, stem_char, 'hidden')
            branch_gods.append(ten_god)

        return branch_gods

    def calculate(self):
        """执行八字排盘计算 - 使用统一的农历转换方法"""
        try:
            # 1. 使用统一的农历转换方法计算四柱和农历
            self._calculate_with_lunar_converter()

            # 2. 计算十神
            self._calculate_ten_gods()

            # 3. 计算藏干
            self._calculate_hidden_stems()

            # 4. 计算星运和自坐
            self._calculate_star_fortune()

            # 5. 计算空亡
            self._calculate_kongwang()

            # 6. 计算纳音
            self._calculate_nayin()

            # 7. 计算神煞
            self._calculate_deities()

            result = self._format_result()
            self.last_result = result
            return result
        except Exception as e:
            logger.error(f"计算错误: {e}", exc_info=True)
            return None

    def _calculate_with_lunar_converter(self):
        """使用统一的农历转换方法计算四柱八字和农历日期"""
        # 使用 LunarConverter 获取农历信息
        lunar_result = LunarConverter.solar_to_lunar(self.solar_date, self.solar_time)

        # 保存结果
        self.lunar_date = lunar_result['lunar_date']
        self.bazi_pillars = lunar_result['bazi_pillars']
        self.adjusted_solar_date = lunar_result['adjusted_solar_date']
        self.adjusted_solar_time = lunar_result['adjusted_solar_time']
        self.is_zi_shi_adjusted = lunar_result['is_zi_shi_adjusted']

        # 子时调整日志（仅debug级别）
        if self.is_zi_shi_adjusted:
            logger.debug(f"子时调整: {self.adjusted_solar_date} {self.adjusted_solar_time}")

    def _calculate_ten_gods(self):
        """计算十神"""
        day_stem = self.bazi_pillars['day']['stem']

        for pillar_type, pillar in self.bazi_pillars.items():
            # 计算主星
            main_star = self.get_main_star(day_stem, pillar['stem'], pillar_type)

            # 计算副星
            branch_gods = self.get_branch_ten_gods(day_stem, pillar['branch'])

            # 修正时柱亥的副星顺序
            if pillar_type == 'hour' and pillar['branch'] == '亥':
                if branch_gods == ['正印', '劫财']:
                    branch_gods = ['劫财', '正印']  # 修正顺序

            if pillar_type not in self.details:
                self.details[pillar_type] = {}

            self.details[pillar_type].update({
                'main_star': main_star,
                # 为兼容旧逻辑保留 hidden_stars 字段，同时新增 sub_stars
                'hidden_stars': list(branch_gods),
                'sub_stars': list(branch_gods)
            })

    def _calculate_hidden_stems(self):
        """计算藏干"""
        for pillar_type, pillar in self.bazi_pillars.items():
            branch = pillar['branch']
            hidden_stems = HIDDEN_STEMS.get(branch, [])
            self.details[pillar_type]['hidden_stems'] = hidden_stems

    def _calculate_star_fortune(self):
        """计算星运和自坐"""
        calculator = StarFortuneCalculator()

        # 获取日干
        day_stem = self.bazi_pillars['day']['stem']

        for pillar_type, pillar in self.bazi_pillars.items():
            # 星运：日干在各地支的十二长生状态
            star_fortune = calculator.get_stem_fortune(day_stem, pillar['branch'])

            # 自坐：各柱天干在各自地支的十二长生状态
            self_sitting = calculator.get_stem_fortune(pillar['stem'], pillar['branch'])

            self.details[pillar_type].update({
                'star_fortune': star_fortune,
                'self_sitting': self_sitting
            })

    def _calculate_kongwang(self):
        """计算空亡 - 修正为每柱单独计算空亡"""
        calculator = StarFortuneCalculator()

        for pillar_type, pillar in self.bazi_pillars.items():
            # 每柱单独计算空亡
            pillar_ganzhi = f"{pillar['stem']}{pillar['branch']}"
            kongwang = calculator.get_kongwang(pillar_ganzhi)

            if pillar_type not in self.details:
                self.details[pillar_type] = {}

            self.details[pillar_type]['kongwang'] = kongwang

    def _calculate_nayin(self):
        """计算纳音"""
        for pillar_type, pillar in self.bazi_pillars.items():
            nayin = NAYIN_MAP.get((pillar['stem'], pillar['branch']), '')
            self.details[pillar_type]['nayin'] = nayin

    def _calculate_deities(self):
        """计算神煞 - 基于已计算好的四柱数据"""
        calculator = DeitiesCalculator()

        # 直接使用已经计算好的四柱数据
        year_stem = self.bazi_pillars['year']['stem']
        year_branch = self.bazi_pillars['year']['branch']
        month_stem = self.bazi_pillars['month']['stem']
        month_branch = self.bazi_pillars['month']['branch']
        day_stem = self.bazi_pillars['day']['stem']
        day_branch = self.bazi_pillars['day']['branch']
        hour_stem = self.bazi_pillars['hour']['stem']
        hour_branch = self.bazi_pillars['hour']['branch']

        # 计算各柱神煞
        year_deities = calculator.calculate_year_deities(year_stem, year_branch, self.bazi_pillars)
        month_deities = calculator.calculate_month_deities(month_stem, month_branch, self.bazi_pillars)
        day_deities = calculator.calculate_day_deities(day_stem, day_branch, self.bazi_pillars)
        hour_deities = calculator.calculate_hour_deities(hour_stem, hour_branch, self.bazi_pillars)

        # 赋值到details中
        self.details['year']['deities'] = year_deities
        self.details['month']['deities'] = month_deities
        self.details['day']['deities'] = day_deities
        self.details['hour']['deities'] = hour_deities

    def _build_ten_gods_stats(self):
        """
        构建十神统计信息：
        - main: 各柱主星出现次数
        - sub: 各柱副星（由地支推演出的十神）出现次数
        - totals: 主星+副星总和
        """
        stats = {
            'main': {},
            'sub': {},
            'totals': {}
        }

        def _record(group_key: str, star_name: str, pillar: str):
            if not star_name:
                return
            group = stats[group_key]
            entry = group.setdefault(star_name, {'count': 0, 'pillars': {}})
            entry['count'] += 1
            entry['pillars'][pillar] = entry['pillars'].get(pillar, 0) + 1

            total_entry = stats['totals'].setdefault(star_name, {'count': 0, 'pillars': {}})
            total_entry['count'] += 1
            total_entry['pillars'][pillar] = total_entry['pillars'].get(pillar, 0) + 1

        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_detail = self.details.get(pillar_type, {})
            _record('main', pillar_detail.get('main_star'), pillar_type)

            sub_stars = pillar_detail.get('sub_stars')
            if sub_stars is None:
                sub_stars = pillar_detail.get('hidden_stars', [])
            for star in sub_stars:
                _record('sub', star, pillar_type)

        # 为兼容外部调用，提供别名
        stats['ten_gods_main'] = stats['main']
        stats['ten_gods_sub'] = stats['sub']
        stats['ten_gods_total'] = stats['totals']

        return stats

    def _build_elements_info(self):
        """
        构建四柱的天干、地支及其对应五行信息
        """
        elements = {}
        for pillar in ['year', 'month', 'day', 'hour']:
            pillar_data = self.bazi_pillars.get(pillar, {})
            stem = pillar_data.get('stem')
            branch = pillar_data.get('branch')
            elements[pillar] = {
                'stem': stem,
                'stem_element': STEM_ELEMENTS.get(stem),
                'branch': branch,
                'branch_element': BRANCH_ELEMENTS.get(branch)
            }
        return elements

    def _build_element_counts(self, elements):
        """
        统计八字中各五行出现次数（天干+地支）
        """
        counts = {}
        for pillar_info in elements.values():
            stem_element = pillar_info.get('stem_element')
            branch_element = pillar_info.get('branch_element')
            if stem_element:
                counts[stem_element] = counts.get(stem_element, 0) + 1
            if branch_element:
                counts[branch_element] = counts.get(branch_element, 0) + 1
        return counts

    def _describe_element_relation(self, source_element, target_element):
        """
        描述两个五行之间的关系
        返回：same / generate / generated_by / control / controlled_by / unknown
        """
        if not source_element or not target_element:
            return 'unknown'
        if source_element == target_element:
            return 'same'

        relations = self.element_relations.get(source_element, {})
        if target_element == relations.get('produces'):
            return 'generate'
        if target_element == relations.get('controls'):
            return 'control'
        if target_element == relations.get('produced_by'):
            return 'generated_by'
        if target_element == relations.get('controlled_by'):
            return 'controlled_by'
        return 'unknown'

    def _build_element_relationships(self, elements):
        """
        构建常用的五行关系描述
        """
        relationships = {
            'element_relations': {}
        }
        day_stem_element = elements.get('day', {}).get('stem_element')
        day_branch_element = elements.get('day', {}).get('branch_element')

        relationships['element_relations']['day_stem->day_branch'] = \
            self._describe_element_relation(day_stem_element, day_branch_element)
        relationships['element_relations']['day_branch->day_stem'] = \
            self._describe_element_relation(day_branch_element, day_stem_element)

        # 其他常用关系可按需扩展
        return relationships

    def _format_result(self):
        """格式化输出结果"""
        elements = self._build_elements_info()
        element_counts = self._build_element_counts(elements)
        element_relationships = self._build_element_relationships(elements)

        result = {
            'basic_info': {
                'solar_date': self.solar_date,
                'solar_time': self.solar_time,
                'adjusted_solar_date': self.adjusted_solar_date,
                'adjusted_solar_time': self.adjusted_solar_time,
                'lunar_date': self.lunar_date,
                'gender': self.gender,
                'is_zi_shi_adjusted': self.is_zi_shi_adjusted
            },
            'bazi_pillars': self.bazi_pillars,
            'details': self.details,
            'ten_gods_stats': self._build_ten_gods_stats(),
            'elements': elements,
            'element_counts': element_counts,
            'relationships': element_relationships
        }
        return result

    def _ensure_result(self):
        """确保已经计算过排盘"""
        if self.last_result is None:
            self.last_result = self.calculate()
        return self.last_result

    def build_rule_input(self) -> dict:
        """
        构造规则引擎需要的八字数据结构
        """
        result = self._ensure_result()
        if not result:
            raise ValueError("八字计算失败，无法构造规则匹配数据")

        return {
            'basic_info': result.get('basic_info', {}),
            'bazi_pillars': result.get('bazi_pillars', {}),
            'details': result.get('details', {}),
            'ten_gods_stats': result.get('ten_gods_stats', {}),
            'elements': result.get('elements', {}),
            'element_counts': result.get('element_counts', {}),
            'relationships': result.get('relationships', {})
        }

    def match_rules(self, rule_types=None, use_cache=True):
        """
        匹配规则，返回命中的规则列表
        """
        from server.services.rule_service import RuleService  # 延迟导入避免循环依赖

        bazi_data = self.build_rule_input()
        matched_rules = RuleService.match_rules(
            bazi_data,
            rule_types=rule_types,
            use_cache=use_cache
        )
        self.last_matched_rules = matched_rules
        return matched_rules

    def print_matched_rules(self, rule_types=None, include_content=True):
        """
        打印规则匹配结果（仅用于调试）
        """
        try:
            matched = self.match_rules(rule_types=rule_types)
        except Exception as exc:
            logger.error(f"规则匹配失败: {exc}")
            return []

        if not matched:
            logger.debug("未匹配到任何规则")
            return matched

        logger.debug(f"匹配到 {len(matched)} 条规则")
        return matched

    def get_calculation_result(self):
        """获取计算结果 - 供其他模块调用"""
        return self.calculate()

    def calculate_dayun_liunian(self, current_time=None, dayun_index=None, target_year=None, 
                                 skip_liunian_sequence=False):
        """
        计算大运和流年信息 - 使用统一的农历转换方法
        Args:
            current_time: 当前时间，用于计算流年，默认为系统当前时间
            dayun_index: 大运索引（可选），指定要计算的大运，只计算该大运范围内的流年（性能优化）
            target_year: 目标年份（可选），指定要计算流月的年份，默认为大运起始年份
            skip_liunian_sequence: 是否跳过流年序列计算（默认False）。
                                   当只需要获取大运列表时设为True可大幅提升性能（约2秒）
        """
        if not hasattr(self, 'details') or not self.details:
            self.calculate()

        if current_time is None:
            from datetime import datetime
            current_time = datetime.now()

        self.current_time = current_time

        # 计算流年详细信息
        self._calculate_liunian_details()

        # 计算大运详细信息
        self._calculate_dayun_details()

        # 预先计算起运信息供后续大运序列使用（先静默计算一次以获得准确年龄）
        with contextlib.redirect_stdout(io.StringIO()):
            self._calculate_qiyun_jiaoyun()

        # 计算大运序列
        self._calculate_dayun_sequence()

        # ✅ 性能优化：
        # - skip_liunian_sequence=True: 完全跳过流年计算（用于只获取大运列表）
        # - dayun_index 不为 None: 只计算指定大运的流年（性能提升约10倍）
        if not skip_liunian_sequence:
            if dayun_index is not None:
                # ✅ 性能优化：只计算指定大运的流年，而非所有大运
                self._calculate_liunian_sequence_for_dayun(dayun_index)
            else:
                # 计算所有大运的流年序列
                self._calculate_liunian_sequence()

            # 计算流日序列
            self._calculate_liuri_sequence()

            # 计算流时序列
            self._calculate_liushi_sequence()

        # 计算起运交运信息
        self._calculate_qiyun_jiaoyun()

        # 构建上下文并生成当前窗口的流年/流月
        if dayun_index is not None:
            # 如果指定了大运索引，使用指定的索引
            context = self._build_current_context(dayun_index=dayun_index, target_year=target_year)
        else:
            context = self._build_current_context(target_year=target_year)
        self.details['current_context'] = context
        self._generate_current_liunian_window(context)

        return self._format_dayun_liunian_result()

    def _calculate_liunian_details(self):
        """计算流年详细信息 - 基于当前时间计算，使用lunar-python"""
        from lunar_python import Solar

        calculator = StarFortuneCalculator()
        deities_calc = DeitiesCalculator()

        # 使用lunar-python计算当前日期的干支
        solar = Solar.fromYmdHms(self.current_time.year, self.current_time.month, self.current_time.day, 12, 0, 0)
        lunar = solar.getLunar()
        bazi = lunar.getBaZi()

        # 获取当前日期的年柱干支
        liunian_stem = bazi[0][0]
        liunian_branch = bazi[0][1]
        day_stem = self.bazi_pillars['day']['stem']

        # 计算详细信息
        liunian_main_star = self.get_main_star(day_stem, liunian_stem, 'liunian')
        liunian_hidden_stems = HIDDEN_STEMS.get(liunian_branch, [])
        liunian_hidden_stars = self.get_branch_ten_gods(day_stem, liunian_branch)
        liunian_star_fortune = calculator.get_stem_fortune(day_stem, liunian_branch)
        liunian_self_sitting = calculator.get_stem_fortune(liunian_stem, liunian_branch)
        liunian_kongwang = calculator.get_kongwang(f"{liunian_stem}{liunian_branch}")
        liunian_nayin = NAYIN_MAP.get((liunian_stem, liunian_branch), '')

        try:
            liunian_deities = deities_calc.calculate_year_deities(liunian_stem, liunian_branch, self.bazi_pillars)
        except:
            liunian_deities = []

        self.details['liunian'] = {
            'stem': liunian_stem,
            'branch': liunian_branch,
            'main_star': liunian_main_star,
            'hidden_stems': liunian_hidden_stems,
            'hidden_stars': liunian_hidden_stars,
            'star_fortune': liunian_star_fortune,
            'self_sitting': liunian_self_sitting,
            'kongwang': liunian_kongwang,
            'nayin': liunian_nayin,
            'deities': liunian_deities
        }

    def _calculate_dayun_details(self):
        """计算大运详细信息 - 基于bazi_calculator_detail1104.py的逻辑"""
        calculator = StarFortuneCalculator()
        deities_calc = DeitiesCalculator()

        day_stem = self.bazi_pillars['day']['stem']
        month_stem = self.bazi_pillars['month']['stem']
        month_branch = self.bazi_pillars['month']['branch']

        # 判断大运排法 - 基于年柱，不是日柱
        year_stem = self.bazi_pillars['year']['stem']
        year_yinyang = STEM_YINYANG[year_stem]
        is_male = (self.gender == 'male')

        # 阳男阴女正排，阳女阴男逆排
        if (year_yinyang == '阳' and is_male) or (year_yinyang == '阴' and not is_male):
            dayun_direction = '正排'
            # 正排：从月柱的第3步开始（对应第3步大运）
            first_stem_index = (HEAVENLY_STEMS.index(month_stem) + 3) % 10
            first_branch_index = (EARTHLY_BRANCHES.index(month_branch) + 3) % 12
        else:
            dayun_direction = '逆排'
            # 逆排：从月柱的第3步开始
            first_stem_index = (HEAVENLY_STEMS.index(month_stem) - 3) % 10
            first_branch_index = (EARTHLY_BRANCHES.index(month_branch) - 3) % 12

        first_dayun_stem = HEAVENLY_STEMS[first_stem_index]
        first_dayun_branch = EARTHLY_BRANCHES[first_branch_index]

        # 计算大运详细信息（基于第3步大运）
        dayun_main_star = self.get_main_star(day_stem, first_dayun_stem, 'dayun')
        dayun_hidden_stems = HIDDEN_STEMS.get(first_dayun_branch, [])
        dayun_hidden_stars = self.get_branch_ten_gods(day_stem, first_dayun_branch)
        dayun_star_fortune = calculator.get_stem_fortune(day_stem, first_dayun_branch)
        dayun_self_sitting = calculator.get_stem_fortune(first_dayun_stem, first_dayun_branch)
        dayun_kongwang = calculator.get_kongwang(f"{first_dayun_stem}{first_dayun_branch}")
        dayun_nayin = NAYIN_MAP.get((first_dayun_stem, first_dayun_branch), '')

        try:
            dayun_deities = deities_calc.calculate_day_deities(first_dayun_stem, first_dayun_branch, self.bazi_pillars)
        except:
            dayun_deities = []

        self.details['dayun'] = {
            'stem': first_dayun_stem,
            'branch': first_dayun_branch,
            'main_star': dayun_main_star,
            'hidden_stems': dayun_hidden_stems,
            'hidden_stars': dayun_hidden_stars,
            'star_fortune': dayun_star_fortune,
            'self_sitting': dayun_self_sitting,
            'kongwang': dayun_kongwang,
            'nayin': dayun_nayin,
            'deities': dayun_deities,
            'direction': dayun_direction
        }

    def _calculate_xiaoyun_ganzhi(self) -> Tuple[str, str]:
        """
        计算小运干支（方法2：从时柱的下一个干支开始）
        
        规则：
        - 阳年(年干阳)生男、阴年(年干阴)生女 → 顺推
        - 阴年(年干阴)生男、阳年(年干阳)生女 → 逆推
        - 从时柱的下一个干支开始
        
        Returns:
            Tuple[str, str]: (小运天干, 小运地支)
        """
        hour_stem = self.bazi_pillars['hour']['stem']
        hour_branch = self.bazi_pillars['hour']['branch']
        year_stem = self.bazi_pillars['year']['stem']
        
        year_yinyang = STEM_YINYANG.get(year_stem, '阳')
        is_male = self.gender == 'male'
        
        # 阳年生男、阴年生女 → 顺推；阴年生男、阳年生女 → 逆推
        if (year_yinyang == '阳' and is_male) or (year_yinyang == '阴' and not is_male):
            direction = 1  # 顺推
        else:
            direction = -1  # 逆推
        
        stem_index = HEAVENLY_STEMS.index(hour_stem)
        branch_index = EARTHLY_BRANCHES.index(hour_branch)
        
        # 从时柱的下一个干支开始
        xiaoyun_stem = HEAVENLY_STEMS[(stem_index + direction) % 10]
        xiaoyun_branch = EARTHLY_BRANCHES[(branch_index + direction) % 12]
        
        return xiaoyun_stem, xiaoyun_branch

    def _get_shishen_short(self, shishen_full: str) -> str:
        """
        获取十神简称
        
        Args:
            shishen_full: 十神全称（如"正印"、"七杀"）
            
        Returns:
            str: 十神简称（如"印"、"杀"），如果找不到则返回原值
        """
        return SHISHEN_SHORT_MAP.get(shishen_full, shishen_full)

    def _calculate_xiaoyun_for_age(self, age: int) -> Tuple[str, str]:
        """
        计算指定年龄（虚岁）的小运干支
        
        规则：
        - 从时柱的下一个干支开始
        - 阳年生男、阴年生女 → 顺推
        - 阴年生男、阳年生女 → 逆推
        - 每岁推进一个干支
        
        Args:
            age: 虚岁年龄（1岁开始）
            
        Returns:
            Tuple[str, str]: (小运天干, 小运地支)
        """
        hour_stem = self.bazi_pillars['hour']['stem']
        hour_branch = self.bazi_pillars['hour']['branch']
        year_stem = self.bazi_pillars['year']['stem']
        
        year_yinyang = STEM_YINYANG.get(year_stem, '阳')
        is_male = self.gender == 'male'
        
        # 阳年生男、阴年生女 → 顺推；阴年生男、阳年生女 → 逆推
        if (year_yinyang == '阳' and is_male) or (year_yinyang == '阴' and not is_male):
            direction = 1  # 顺推
        else:
            direction = -1  # 逆推
        
        stem_index = HEAVENLY_STEMS.index(hour_stem)
        branch_index = EARTHLY_BRANCHES.index(hour_branch)
        
        # 从时柱的下一个干支开始，每岁推进一个干支
        # age=1 对应时柱的下一个干支
        offset = age  # age=1时，offset=1，即下一个干支
        
        xiaoyun_stem = HEAVENLY_STEMS[(stem_index + direction * offset) % 10]
        xiaoyun_branch = EARTHLY_BRANCHES[(branch_index + direction * offset) % 12]
        
        return xiaoyun_stem, xiaoyun_branch

    def _calculate_dayun_sequence(self):
        """计算大运序列 - 基于起运时间动态计算"""

        day_stem = self.bazi_pillars['day']['stem']
        month_stem = self.bazi_pillars['month']['stem']
        month_branch = self.bazi_pillars['month']['branch']

        # 获取出生年份
        birth_year = int(self.solar_date.split('-')[0])

        # 获取起运信息
        qiyun_info = self.details.get('qiyun', {})
        qiyun_years = qiyun_info.get('years', 0)
        qiyun_months = qiyun_info.get('months', 0)
        qiyun_days = qiyun_info.get('days', 0)
        
        # ✅ 获取交运信息（用于计算大运年份）
        jiaoyun_info = self.details.get('jiaoyun', {})
        jiaoyun_stems = jiaoyun_info.get('stems', [])

        # 计算起运总年龄（年+月换算为年）
        # 比如 7年2月21天，换算为大约7.25岁（2月=2/12≈0.17年）
        qiyun_total_age = qiyun_years + qiyun_months / 12.0
        if qiyun_total_age < 0:
            qiyun_total_age = 0

        qiyun_total_age = max(qiyun_total_age, 0)
        
        # ✅ 计算第一个交运年（出生年之后第一个匹配交运天干的年份）
        def _get_year_stem(year: int) -> str:
            """获取年份的天干"""
            base_year = 1984  # 甲子年
            year_diff = year - base_year
            stem_index = (year_diff % 10 + 10) % 10
            return HEAVENLY_STEMS[stem_index]
        
        # ✅ 修复：计算起运年（直接使用出生年 + 起运年数，不做月份调整）
        # 与问真一致：起运年 = 出生年 + 起运年数
        qiyun_year = birth_year + qiyun_years
        
        # 找出起运年之后第一个匹配交运天干的年份
        first_jiaoyun_year = qiyun_year
        if jiaoyun_stems:
            for year in range(qiyun_year, qiyun_year + 10):
                if _get_year_stem(year) in jiaoyun_stems:
                    first_jiaoyun_year = year
                    break

        # 判断大运排法
        year_stem = self.bazi_pillars['year']['stem']
        year_yinyang = STEM_YINYANG[year_stem]
        is_male = (self.gender == 'male')

        if (year_yinyang == '阳' and is_male) or (year_yinyang == '阴' and not is_male):
            dayun_direction = '正排'
        else:
            dayun_direction = '逆排'

        month_stem_index = HEAVENLY_STEMS.index(month_stem)
        month_branch_index = EARTHLY_BRANCHES.index(month_branch)

        dayun_sequence = []

        # ✅ 修复：增加最大年龄限制，确保能计算到2110年（对应126岁虚岁）
        # 将限制从120岁增加到150岁，以覆盖更远的年份
        max_age_limit = 150
        # ✅ 虚岁计算：小运结束年龄 = 第一个交运年的虚岁（与问真一致）
        first_end_age_virtual = first_jiaoyun_year - birth_year + 1

        # 第一段：小运阶段（从 1 岁开始，虚岁）
        age_start = 1  # 虚岁从1开始
        age_end = min(first_end_age_virtual, max_age_limit)  # 1 + 起运年数
        year_start = birth_year
        # ✅ 修复：小运结束年份 = 第一个交运年 - 1（而非基于虚岁计算）
        year_end = first_jiaoyun_year - 1

        step = 1
        age_display = f"{age_start}-{age_end}岁"  # 小运显示范围格式
        
        # ✅ 计算小运真正的干支（从时柱的下一个开始）
        xiaoyun_stem, xiaoyun_branch = self._calculate_xiaoyun_ganzhi()
        
        # 初始化计算器（用于计算小运详细信息）
        star_calc = StarFortuneCalculator()
        deities_calc = DeitiesCalculator()
        
        # ✅ 计算小运的详细信息（按真正的干支计算）
        xiaoyun_detail = self._build_pillar_detail(xiaoyun_stem, xiaoyun_branch, star_calc, deities_calc, level='dayun')
        
        # 生成小运期间的简化流年列表
        xiaoyun_liunian_simple = []
        for y in range(year_start, year_end + 1):
            y_stem = _get_year_stem(y)
            y_branch = EARTHLY_BRANCHES[(y - 1984) % 12]
            xiaoyun_liunian_simple.append({
                'year': y,
                'ganzhi': y_stem + y_branch
            })
        
        dayun_sequence.append({
            'step': step,
            'stem': xiaoyun_stem,  # ✅ 使用真正的干支
            'branch': xiaoyun_branch,  # ✅ 使用真正的干支
            'is_xiaoyun': True,  # ✅ 新增：标识这是小运
            'main_star': xiaoyun_detail.get('main_star', ''),  # ✅ 按干支计算
            'hidden_stems': xiaoyun_detail.get('hidden_stems', []),
            'hidden_stars': xiaoyun_detail.get('hidden_stars', []),
            'star_fortune': xiaoyun_detail.get('star_fortune', ''),
            'self_sitting': xiaoyun_detail.get('self_sitting', ''),
            'kongwang': xiaoyun_detail.get('kongwang', ''),
            'nayin': xiaoyun_detail.get('nayin', ''),
            'deities': xiaoyun_detail.get('deities', []),
            # ✅ 新增：十神简称字段
            'stem_shishen': xiaoyun_detail.get('stem_shishen', ''),
            'branch_shishen': xiaoyun_detail.get('branch_shishen', ''),
            'shishen_combined': xiaoyun_detail.get('shishen_combined', ''),
            'age_display': age_display,
            'age_range': {"start": age_start, "end": age_end},  # 便于前端使用
            'year_start': year_start,
            'year_end': year_end,
            'liunian_simple': xiaoyun_liunian_simple  # ✅ 新增：简化流年列表
        })

        # 第二段：第一个大运（从小运结束年龄开始，虚岁）
        age_start = age_end  # 第一个大运从小运结束年龄开始（虚岁）
        age_end = min(age_start + 9, max_age_limit)
        
        # ✅ 修复：大运年份基于交运年计算（而非虚岁）
        # 第一个大运从 first_jiaoyun_year 开始
        dayun_year_start = first_jiaoyun_year
        year_start = dayun_year_start
        year_end = dayun_year_start + 9

        # 注：star_calc 和 deities_calc 已在小运计算时初始化，此处复用

        offset = 0
        dayun_index = 0  # 大运计数器（用于计算年份）
        while age_start <= max_age_limit:
            if dayun_direction == '正排':
                stem_index = (month_stem_index + offset + 1) % 10
                branch_index = (month_branch_index + offset + 1) % 12
            else:
                stem_index = (month_stem_index - offset - 1) % 10
                branch_index = (month_branch_index - offset - 1) % 12

            stem = HEAVENLY_STEMS[stem_index]
            branch = EARTHLY_BRANCHES[branch_index]
            
            # ✅ 添加大运详细信息（用于细盘表格）
            dayun_detail = self._build_pillar_detail(stem, branch, star_calc, deities_calc, level='dayun')

            # 生成该大运的简化流年列表
            dayun_liunian_simple = []
            for y in range(year_start, year_end + 1):
                y_stem = _get_year_stem(y)
                y_branch = EARTHLY_BRANCHES[(y - 1984) % 12]
                dayun_liunian_simple.append({
                    'year': y,
                    'ganzhi': y_stem + y_branch
                })
            
            step += 1
            dayun_sequence.append({
                'step': step,
                'stem': stem,
                'branch': branch,
                'main_star': dayun_detail.get('main_star', ''),
                'hidden_stems': dayun_detail.get('hidden_stems', []),
                'hidden_stars': dayun_detail.get('hidden_stars', []),
                'star_fortune': dayun_detail.get('star_fortune', ''),
                'self_sitting': dayun_detail.get('self_sitting', ''),
                'kongwang': dayun_detail.get('kongwang', ''),
                'nayin': dayun_detail.get('nayin', ''),
                'deities': dayun_detail.get('deities', []),
                # ✅ 新增：十神简称字段
                'stem_shishen': dayun_detail.get('stem_shishen', ''),
                'branch_shishen': dayun_detail.get('branch_shishen', ''),
                'shishen_combined': dayun_detail.get('shishen_combined', ''),
                'age_display': f"{age_start}岁",  # 大运只显示起始年龄
                'age_range': {"start": age_start, "end": age_end},  # 新增：便于前端使用
                'year_start': year_start,
                'year_end': year_end,
                'liunian_simple': dayun_liunian_simple  # ✅ 新增：简化流年列表
            })

            age_start = age_end + 1
            if age_start > max_age_limit:
                break
            age_end = min(age_start + 9, max_age_limit)
            
            # ✅ 修复：大运年份基于交运年计算
            dayun_index += 1
            year_start = first_jiaoyun_year + (dayun_index * 10)
            year_end = year_start + 9
            
            offset += 1

        self.details['dayun_sequence'] = dayun_sequence

    def _calculate_liunian_relations(
        self,
        liunian_stem: str,
        liunian_branch: str,
        dayun_stem: str,
        dayun_branch: str,
        bazi_pillars: Dict[str, Dict[str, str]]
    ) -> list:
        """
        计算流年关系（与问真八字一致，只返回三种关系类型）
        
        Args:
            liunian_stem: 流年天干
            liunian_branch: 流年地支
            dayun_stem: 大运天干
            dayun_branch: 大运地支
            bazi_pillars: 四柱信息字典，格式：{'year': {'stem': '甲', 'branch': '子'}, ...}
        
        Returns:
            List[Dict]: 关系列表，每个关系包含 type 和 description 字段
            只返回三种关系类型（与问真八字一致）：
            - 岁运并临：流年与大运干支完全相同
            - 天克地冲：天干相克（双向）且地支相冲
            - 天合地合：天干相合且地支相合
        """
        from core.data.relations import (
            STEM_HE, BRANCH_LIUHE, BRANCH_CHONG, STEM_KE
        )
        
        relations = []
        pillar_names = {'year': '年柱', 'month': '月柱', 'day': '日柱', 'hour': '时柱'}
        
        # 1. 岁运并临：流年天干地支与大运天干地支完全相同
        if liunian_stem == dayun_stem and liunian_branch == dayun_branch:
            relations.append({
                "type": "岁运并临",
                "description": f"流年{liunian_stem}{liunian_branch}与大运{dayun_stem}{dayun_branch}完全相同"
            })
        
        # 2. 流年与四柱的关系（只检查天克地冲、天合地合）
        for pillar_type, pillar in bazi_pillars.items():
            pillar_stem = pillar.get('stem', '')
            pillar_branch = pillar.get('branch', '')
            pillar_name = pillar_names.get(pillar_type, pillar_type)
            
            if not pillar_stem or not pillar_branch:
                continue
            
            # 2.1 天干关系
            is_stem_he = STEM_HE.get(liunian_stem) == pillar_stem  # 天干相合
            is_stem_ke = pillar_stem in STEM_KE.get(liunian_stem, [])  # 天干相克（流年克四柱）
            is_stem_ke_reverse = liunian_stem in STEM_KE.get(pillar_stem, [])  # 天干相克（四柱克流年）
            
            # 2.2 地支关系
            is_branch_chong = BRANCH_CHONG.get(liunian_branch) == pillar_branch  # 地支相冲
            is_branch_he = BRANCH_LIUHE.get(liunian_branch) == pillar_branch  # 地支相合
            
            # 2.3 天克地冲：天干相克（双向）且地支相冲
            if (is_stem_ke or is_stem_ke_reverse) and is_branch_chong:
                relations.append({
                    "type": f"{pillar_name}-天克地冲",
                    "description": f"流年{liunian_stem}{liunian_branch}与{pillar_name}{pillar_stem}{pillar_branch}天克地冲"
                })
            # 2.4 天合地合：天干相合且地支相合
            elif is_stem_he and is_branch_he:
                relations.append({
                    "type": f"{pillar_name}-天合地合",
                    "description": f"流年{liunian_stem}{liunian_branch}与{pillar_name}{pillar_stem}{pillar_branch}天合地合"
                })
        
        return relations

    def _generate_liunian_for_range(self, day_stem: str, start_year: int, end_year: int, 
                                     dayun_stem: str = None, dayun_branch: str = None, 
                                     bazi_pillars: Dict[str, Dict[str, str]] = None):
        """根据年份区间生成流年列表，并附带流月信息"""
        from lunar_python import Solar

        # 获取出生年份（用于计算年龄）
        birth_year = int(self.solar_date.split('-')[0])

        liunians = []
        
        # ✅ 修复：如果传入的 dayun_stem 和 dayun_branch 为 None，尝试从 self.details 中查找
        # 这确保了即使传入的参数为 None，也能正确计算关系
        if (dayun_stem is None or dayun_branch is None) and hasattr(self, 'details') and self.details:
            dayun_sequence = self.details.get('dayun_sequence', [])
            if dayun_sequence:
                # 查找包含 start_year 到 end_year 范围内的大运
                for d in dayun_sequence:
                    d_stem = d.get('stem', '')
                    d_branch = d.get('branch', '')
                    d_year_start = d.get('year_start', 0)
                    d_year_end = d.get('year_end', 0)
                    d_is_xiaoyun = d.get('is_xiaoyun', False)
                    # 如果大运年份范围与流年年份范围有重叠（排除小运）
                    if (d_stem and not d_is_xiaoyun and 
                        d_branch and
                        not (d_year_end < start_year or d_year_start > end_year)):
                        dayun_stem = d_stem
                        dayun_branch = d_branch
                        break
        # 初始化计算器（用于计算流年详细信息）
        star_calc = StarFortuneCalculator()
        deities_calc = DeitiesCalculator()
        
        for year in range(start_year, end_year + 1):
            # 计算年龄（虚岁：出生即1岁）
            age = year - birth_year + 1  # 虚岁计算
            age_display = f"{age}岁"
            
            solar = Solar.fromYmdHms(year, 2, 5, 0, 0, 0)
            lunar = solar.getLunar()
            bazi = lunar.getBaZi()

            year_stem = bazi[0][0]
            year_branch = bazi[0][1]
            # 计算流年详细信息（十神、藏干、星运、神煞等）
            detail = self._build_pillar_detail(year_stem, year_branch, star_calc, deities_calc, level='year')
            # 传递年份参数，用于获取实际年份的节气日期
            liuyue_sequence = self._generate_liuyue_for_year(year_stem, year)

            # 计算流年关系（如果提供了大运和四柱信息）
            # ✅ 修复：优先从 self.details 中查找包含该流年的大运，如果找不到则使用传入的大运
            relations = []
            if bazi_pillars:
                # 查找包含该流年的大运
                year_dayun_stem = None
                year_dayun_branch = None
                
                # 从 self.details 中查找（dayun_sequence 应该已经计算完成）
                if hasattr(self, 'details') and self.details:
                    dayun_sequence = self.details.get('dayun_sequence', [])
                    # ✅ 调试日志：记录dayun_sequence状态和self.details的keys
                    if year == 2024:
                        try:
                            with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                                f.write(f"[关系计算] 流年2024年 self.details.keys(): {list(self.details.keys())}\n")
                                f.write(f"[关系计算] 流年2024年 dayun_sequence长度: {len(dayun_sequence)}\n")
                                if dayun_sequence:
                                    for i, d in enumerate(dayun_sequence[:5]):  # 显示前5个
                                        f.write(f"  dayun_sequence[{i}]: stem={d.get('stem')}, branch={d.get('branch')}, year_start={d.get('year_start')}, year_end={d.get('year_end')}\n")
                                else:
                                    f.write(f"[关系计算] 流年2024年 dayun_sequence为空！\n")
                        except Exception as e:
                            try:
                                with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                                    f.write(f"[关系计算] 调试日志写入失败: {e}\n")
                            except:
                                pass
                    if dayun_sequence:
                        for d in dayun_sequence:
                            d_stem = d.get('stem', '')
                            d_branch = d.get('branch', '')
                            d_year_start = d.get('year_start', 0)
                            d_year_end = d.get('year_end', 0)
                            d_is_xiaoyun = d.get('is_xiaoyun', False)
                            # ✅ 修复：确保正确匹配大运（排除小运，确保有stem和branch）
                            # 注意：stem 和 branch 应该是字符串，不是字典
                            if (d_stem and isinstance(d_stem, str) and not d_is_xiaoyun and 
                                d_branch and isinstance(d_branch, str) and
                                d_year_start <= year <= d_year_end):
                                year_dayun_stem = d_stem
                                year_dayun_branch = d_branch
                                # ✅ 调试日志：记录找到的大运（使用文件写入，避免被redirect_stdout抑制）
                                try:
                                    with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                                        f.write(f"[关系计算] 流年{year}年({year_stem}{year_branch}) 找到大运: {year_dayun_stem}{year_dayun_branch} (年份范围: {d_year_start}-{d_year_end})\n")
                                except:
                                    pass
                                break
                    else:
                        # ✅ 调试日志：记录dayun_sequence为空的情况
                        if year == 2024:
                            try:
                                with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                                    f.write(f"[关系计算] 流年2024年 dayun_sequence为空，无法查找大运\n")
                            except:
                                pass
                
                # 如果找到了对应的大运，使用它；否则使用传入的大运（向后兼容）
                final_dayun_stem = year_dayun_stem if year_dayun_stem else dayun_stem
                final_dayun_branch = year_dayun_branch if year_dayun_branch else dayun_branch
                
                # ✅ 修复：如果仍然没有找到大运，尝试从传入的dayun_stem和dayun_branch使用（如果它们不为None）
                # 这确保了即使dayun_sequence查找失败，也能使用传入的大运信息
                if (final_dayun_stem is None or final_dayun_branch is None) and dayun_stem and dayun_branch:
                    final_dayun_stem = dayun_stem
                    final_dayun_branch = dayun_branch
                
                # ✅ 修复：确保所有参数都存在且不为空
                # 注意：year_stem 和 year_branch 是从 bazi[0] 获取的，应该是字符串
                if (final_dayun_stem is not None and final_dayun_branch is not None and 
                    bazi_pillars and year_stem and year_branch):
                    # ✅ 确保 year_stem 和 year_branch 是字符串
                    if isinstance(year_stem, str) and isinstance(year_branch, str):
                        relations = self._calculate_liunian_relations(
                            year_stem, year_branch, final_dayun_stem, final_dayun_branch, bazi_pillars
                        )
                    else:
                        relations = []
                else:
                    relations = []

            # ✅ 新增：计算该流年的小运干支
            xiaoyun_stem, xiaoyun_branch = self._calculate_xiaoyun_for_age(age)
            xiaoyun_ganzhi = xiaoyun_stem + xiaoyun_branch
            
            liunians.append({
                'year': year,
                'age': age,  # 年龄（整数）
                'age_display': age_display,  # 年龄显示格式
                'stem': year_stem,
                'branch': year_branch,
                **detail,  # 详细信息（十神、藏干、星运、神煞等，已包含十神简称字段）
                'liuyue_sequence': liuyue_sequence,
                'relations': relations,  # 关系列表
                # ✅ 新增字段：小运
                'xiaoyun_ganzhi': xiaoyun_ganzhi,
                'xiaoyun_stem': xiaoyun_stem,
                'xiaoyun_branch': xiaoyun_branch,
            })
        return liunians

    def _generate_liuyue_for_year(self, year_stem: str, year: int):
        """根据年份天干生成对应的流月列表（按节气顺序），使用实际年份的节气日期
        
        Args:
            year_stem: 年份天干
            year: 实际年份（用于获取该年份的实际节气日期）
        """
        from lunar_python import Solar
        
        month_start_map = {
            '甲': '丙', '己': '丙',
            '乙': '戊', '庚': '戊',
            '丙': '庚', '辛': '庚',
            '丁': '壬', '壬': '壬',
            '戊': '甲', '癸': '甲',
        }
        solar_terms = ['立春', '惊蛰', '清明', '立夏', '芒种', '小暑', '立秋', '白露', '寒露', '立冬', '大雪', '小寒']
        
        # ✅ 性能优化：使用节气表缓存，避免重复计算
        if year not in BaziCalculator._jieqi_table_cache:
            base_solar = Solar.fromYmdHms(year, 1, 1, 0, 0, 0)
            lunar_year = base_solar.getLunar()
            BaziCalculator._jieqi_table_cache[year] = lunar_year.getJieQiTable()
        jieqi_table = BaziCalculator._jieqi_table_cache[year]
        
        # 从节气表获取实际日期
        term_dates = []
        for term_name in solar_terms:
            solar_obj = jieqi_table.get(term_name)
            if solar_obj is None:
                # 如果找不到，尝试不区分大小写匹配
                target_key = None
                for key in jieqi_table.keys():
                    if isinstance(key, str) and key == term_name:
                        target_key = key
                        break
                if target_key:
                    solar_obj = jieqi_table[target_key]
            
            if solar_obj:
                # 获取节气的实际日期
                term_month = solar_obj.getMonth()
                term_day = solar_obj.getDay()
                term_dates.append(f"{term_month}/{term_day}")
            else:
                # 降级方案：使用默认日期（如果获取失败）
                default_dates = ['2/4', '3/6', '4/5', '5/5', '6/6', '7/7', '8/7', '9/7', '10/8', '11/7', '12/7', '1/5']
                term_dates.append(default_dates[solar_terms.index(term_name)])

        first_month_stem = month_start_map.get(year_stem, '丙')
        start_index = HEAVENLY_STEMS.index(first_month_stem)
        month_branch_index = EARTHLY_BRANCHES.index('寅')

        liuyue_sequence = []
        # ✅ 性能优化：排盘页面不需要流月的详细信息（十神、藏干、星运、神煞等）
        # 详细信息可在需要时通过专门的接口获取
        # ✅ 但需要添加十神简称字段（用于显示）
        day_stem = self.bazi_pillars['day']['stem']
        
        # ✅ 新增：初始化计算器（用于计算流月完整详细信息）
        star_calc = StarFortuneCalculator()
        deities_calc = DeitiesCalculator()
        
        for i in range(12):
            stem = HEAVENLY_STEMS[(start_index + i) % 10]
            branch = EARTHLY_BRANCHES[(month_branch_index + i) % 12]
            
            # ✅ 新增：计算流月完整详细信息
            detail = self._build_pillar_detail(stem, branch, star_calc, deities_calc, level='month')
            
            # ✅ 保留原有：计算流月十神简称（使用新映射表）
            # 天干十神简称 - 直接使用映射表
            stem_shishen = TIANGAN_SHISHEN_MAP.get(day_stem, {}).get(stem, '')
            
            # 地支十神简称 - 直接使用映射表
            branch_shishen = DIZHI_SHISHEN_MAP.get(day_stem, {}).get(branch, '')
            
            # 合并显示
            shishen_combined = ''
            if stem_shishen and branch_shishen:
                shishen_combined = stem_shishen + branch_shishen
            elif stem_shishen:
                shishen_combined = stem_shishen
            elif branch_shishen:
                shishen_combined = branch_shishen
            
            liuyue_item = {
                'month': i + 1,
                'solar_term': solar_terms[i],
                'term_date': term_dates[i],  # 使用实际年份的节气日期
                'stem': stem,
                'branch': branch,
                # ✅ 保留原有字段：十神简称
                'stem_shishen': stem_shishen,
                'branch_shishen': branch_shishen,
                'shishen_combined': shishen_combined,
                # ✅ 新增字段：完整详细信息（主星、藏干、星运、自坐、空亡、神煞等）
                'main_star': detail.get('main_star', ''),
                'hidden_stems': detail.get('hidden_stems', []),
                'hidden_stars': detail.get('hidden_stars', []),
                'star_fortune': detail.get('star_fortune', ''),
                'self_sitting': detail.get('self_sitting', ''),
                'kongwang': detail.get('kongwang', ''),
                'nayin': detail.get('nayin', ''),
                'deities': detail.get('deities', []),
            }
            liuyue_sequence.append(liuyue_item)
        return liuyue_sequence

    def _build_pillar_detail(
        self,
        stem: str,
        branch: str,
        star_calc: StarFortuneCalculator,
        deities_calc: DeitiesCalculator,
        level: str = 'year'
    ) -> Dict[str, Any]:
        day_stem = self.bazi_pillars['day']['stem']
        main_star = self.get_main_star(day_stem, stem, level)
        hidden_stems = HIDDEN_STEMS.get(branch, [])
        hidden_stars = self.get_branch_ten_gods(day_stem, branch)
        star_fortune = star_calc.get_stem_fortune(day_stem, branch)
        self_sitting = star_calc.get_stem_fortune(stem, branch)
        kongwang = star_calc.get_kongwang(f"{stem}{branch}")
        nayin = NAYIN_MAP.get((stem, branch), '')

        deities: list = []
        try:
            if level == 'year':
                deities = deities_calc.calculate_year_deities(stem, branch, self.bazi_pillars)
            elif level == 'month':
                deities = deities_calc.calculate_month_deities(stem, branch, self.bazi_pillars)
            elif level == 'dayun':
                # 大运使用日柱神煞计算方法
                deities = deities_calc.calculate_day_deities(stem, branch, self.bazi_pillars)
        except Exception:
            deities = []

        # ✅ 新增：计算十神简称（使用新映射表）
        # 天干十神简称 - 直接使用映射表
        stem_shishen = TIANGAN_SHISHEN_MAP.get(day_stem, {}).get(stem, '')
        
        # 地支十神简称 - 直接使用映射表
        branch_shishen = DIZHI_SHISHEN_MAP.get(day_stem, {}).get(branch, '')
        
        # 合并显示
        shishen_combined = ''
        if stem_shishen and branch_shishen:
            shishen_combined = stem_shishen + branch_shishen
        elif stem_shishen:
            shishen_combined = stem_shishen
        elif branch_shishen:
            shishen_combined = branch_shishen

        return {
            'main_star': main_star,
            'hidden_stems': hidden_stems,
            'hidden_stars': hidden_stars,
            'star_fortune': star_fortune,
            'self_sitting': self_sitting,
            'kongwang': kongwang,
            'nayin': nayin,
            'deities': deities,
            # ✅ 新增字段
            'stem_shishen': stem_shishen,
            'branch_shishen': branch_shishen,
            'shishen_combined': shishen_combined,
        }

    # 节气表缓存（类级别，避免重复计算）
    _jieqi_table_cache: dict = {}
    
    def _calculate_liunian_sequence(self):
        """为每个大运生成流年序列"""
        dayun_sequence = self.details.get('dayun_sequence', [])
        
        all_liunians = []
        for dayun in dayun_sequence:
            # ✅ 修复：小运期间也需要生成流年序列并计算关系
            # 问真八字显示小运期间的流年也有天克地冲等关系
            # 原逻辑跳过小运导致1990年等小运期间的流年未被计算
            
            year_start = dayun.get('year_start', 0)
            year_end = dayun.get('year_end', 0)
            dayun_stem = dayun.get('stem', '')
            dayun_branch = dayun.get('branch', '')
            
            # 为每个大运生成流年序列
            liunians = self._generate_liunian_for_range(
                self.bazi_pillars['day']['stem'],
                year_start,
                year_end,
                dayun_stem=dayun_stem,
                dayun_branch=dayun_branch,
                bazi_pillars=self.bazi_pillars
            )
            dayun['liunian_sequence'] = liunians
            all_liunians.extend(liunians)
        
        # 设置全局流年序列
        self.details['liunian_sequence'] = all_liunians

    def _calculate_liunian_sequence_for_dayun(self, dayun_index: int):
        """
        ✅ 性能优化：只为指定的大运生成流年序列
        
        Args:
            dayun_index: 大运索引（step值），只计算该大运的流年
        """
        dayun_sequence = self.details.get('dayun_sequence', [])
        
        # 查找指定的大运
        target_dayun = None
        for dayun in dayun_sequence:
            if dayun.get('step') == dayun_index:
                target_dayun = dayun
                break
        
        # 如果没找到，使用数组索引作为降级方案
        if target_dayun is None and 0 <= dayun_index < len(dayun_sequence):
            target_dayun = dayun_sequence[dayun_index]
        
        if target_dayun is None:
            return
        
        # 跳过小运（小运没有流年）
        if target_dayun.get('is_xiaoyun', False):
            target_dayun['liunian_sequence'] = []
            return
        
        year_start = target_dayun.get('year_start', 0)
        year_end = target_dayun.get('year_end', 0)
        dayun_stem = target_dayun.get('stem', '')
        dayun_branch = target_dayun.get('branch', '')
        
        # 只为指定大运生成流年序列
        liunians = self._generate_liunian_for_range(
            self.bazi_pillars['day']['stem'],
            year_start,
            year_end,
            dayun_stem=dayun_stem,
            dayun_branch=dayun_branch,
            bazi_pillars=self.bazi_pillars
        )
        target_dayun['liunian_sequence'] = liunians
        
        # 全局流年序列只包含该大运的流年
        self.details['liunian_sequence'] = liunians

    def _calculate_liuyue_sequence(self):
        """计算流月序列 - 使用统一的农历转换方法"""

        # 获取当前年份的干支
        current_year = self.current_time.year
        current_liunian_ganzhi = LunarConverter.get_year_ganzhi(current_year)
        current_liunian_stem = current_liunian_ganzhi['stem']

        # 根据年干确定正月天干
        first_month_stem = ''
        if current_liunian_stem in ['甲', '己']:
            first_month_stem = '丙'
        elif current_liunian_stem in ['乙', '庚']:
            first_month_stem = '戊'
        elif current_liunian_stem in ['丙', '辛']:
            first_month_stem = '庚'
        elif current_liunian_stem in ['丁', '壬']:
            first_month_stem = '壬'
        elif current_liunian_stem in ['戊', '癸']:
            first_month_stem = '甲'

        liuyue_sequence = []

        # 计算10个月份的流月
        for i in range(10):
            stem_index = (HEAVENLY_STEMS.index(first_month_stem) + i) % 10
            branch_index = (EARTHLY_BRANCHES.index('寅') + i) % 12

            stem = HEAVENLY_STEMS[stem_index]
            branch = EARTHLY_BRANCHES[branch_index]

            liuyue_sequence.append({
                'month': i + 1,
                'stem': stem,
                'branch': branch
            })

        self.details['liuyue_sequence'] = liuyue_sequence

    def _calculate_liuri_sequence(self):
        """计算流日序列 - 使用统一的农历转换方法"""

        from datetime import timedelta

        liuri_sequence = []

        for i in range(-3, 4):  # 前后3天
            target_date = self.current_time + timedelta(days=i)

            # 使用统一的农历转换方法计算该日的干支
            solar_date = target_date.strftime('%Y-%m-%d')
            day_ganzhi = LunarConverter.get_day_ganzhi(
                target_date.year, target_date.month, target_date.day
            )

            day_stem = day_ganzhi['stem']
            day_branch = day_ganzhi['branch']
            main_star = self.get_main_star(self.bazi_pillars['day']['stem'], day_stem, 'liuri')

            liuri_sequence.append({
                'date': target_date.strftime('%m/%d'),
                'stem': day_stem,
                'branch': day_branch,
                'main_star': main_star
            })

        self.details['liuri_sequence'] = liuri_sequence

    def _calculate_liushi_sequence(self):
        """计算流时序列 - 使用统一的农历转换方法"""

        from datetime import timedelta

        liushi_sequence = []

        for i in range(-3, 4):  # 前后3小时
            target_time = self.current_time + timedelta(hours=i)

            # 使用统一的农历转换方法计算该时的干支
            hour_ganzhi = LunarConverter.get_hour_ganzhi(
                target_time.year, target_time.month, target_time.day,
                target_time.hour, target_time.minute
            )

            hour_stem = hour_ganzhi['stem']
            hour_branch = hour_ganzhi['branch']
            main_star = self.get_main_star(self.bazi_pillars['day']['stem'], hour_stem, 'liushi')

            liushi_sequence.append({
                'time': target_time.strftime('%H:%M'),
                'stem': hour_stem,
                'branch': hour_branch,
                'main_star': main_star
            })

        self.details['liushi_sequence'] = liushi_sequence

    def _calculate_qiyun_jiaoyun(self):
        """计算起运与交运信息 - 按照表格标准算法"""

        from datetime import datetime, timedelta
        from calendar import monthrange
        import math
        from lunar_python import Solar

        # 解析出生日期时间
        birth_date = datetime.strptime(f"{self.solar_date} {self.solar_time}", "%Y-%m-%d %H:%M")

        # 使用lunar-python获取农历信息
        solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, birth_date.hour, birth_date.minute, 0)
        lunar = solar.getLunar()

        # 判断大运排法（根据表格：阳男、阴女顺排；阴男、阳女逆排）
        year_stem = self.bazi_pillars['year']['stem']
        year_yinyang = STEM_YINYANG[year_stem]
        is_male = (self.gender == 'male')

        # 阳男、阴女顺排；阴男、阳女逆排
        if (year_yinyang == '阳' and is_male) or (year_yinyang == '阴' and not is_male):
            dayun_direction = '顺排'
        else:
            dayun_direction = '逆排'

        # 1. 首先确认每一年的节气具体时间
        current_jieqi = lunar.getJieQi()
        # getJieQi()返回的是字符串，需要获取节气的名称
        if isinstance(current_jieqi, str):
            current_jieqi_name = current_jieqi
        else:
            current_jieqi_name = current_jieqi.getName()

        # 2. 根据大运排法确定起运节气
        if dayun_direction == '顺排':
            # 顺排：用户出生时间至下一个节气的具体时间
            start_jieqi = lunar.getNextJie()
        else:
            # 逆排：用户出生时间至上一个节气的具体时间
            start_jieqi = lunar.getPrevJie()

        # 3. 计算从出生到起运节气的精确时间差
        start_solar = start_jieqi.getSolar()
        birth_solar = solar

        # 将Solar对象转换为datetime对象以计算精确时间差
        start_datetime = datetime(
            start_solar.getYear(), 
            start_solar.getMonth(), 
            start_solar.getDay(),
            start_solar.getHour(),
            start_solar.getMinute(),
            start_solar.getSecond()
        )
        birth_datetime = datetime(
            birth_solar.getYear(),
            birth_solar.getMonth(),
            birth_solar.getDay(),
            birth_solar.getHour(),
            birth_solar.getMinute(),
            birth_solar.getSecond()
        )
        
        # 计算时间差（精确到秒）
        time_diff = start_datetime - birth_datetime
        
        # 如果时间差为负数（逆排情况），取绝对值
        if time_diff.total_seconds() < 0:
            time_diff = birth_datetime - start_datetime
        
        # 转换为总秒数
        total_seconds = time_diff.total_seconds()
        
        # 计算天数、小时、分钟、秒
        total_days = total_seconds / 86400.0  # 1天 = 86400秒
        actual_days = int(total_days)
        remaining_seconds = total_seconds - actual_days * 86400
        actual_hours = remaining_seconds / 3600.0
        actual_minutes = (remaining_seconds % 3600) / 60.0
        
        # 转换为时辰（1时辰 = 2小时）
        shichen = actual_hours / 2.0

        # 4. 按照表格换算规则计算起运时间
        # 换算规则：1天=4个月，1时辰=10天
        # 天数转换为月份
        months_from_days = actual_days * 4
        
        # 时辰数转换为天数
        days_from_shichen = int(shichen * 10)
        hours_from_shichen_fraction = (shichen * 10 - days_from_shichen) * 24  # 剩余的小数部分转换为小时
        
        # 归一化：合并所有月份、天数、小时
        total_months = months_from_days
        total_days_final = days_from_shichen
        total_hours_final = int(hours_from_shichen_fraction)
        
        # 归一化：月份转换为年+月
        qiyun_years = total_months // 12
        qiyun_months_remainder = int(total_months % 12)
        
        # 归一化：天数需要转换为月+天（30天=1个月）
        # 将天数转换为月份（30天=1个月）
        months_from_total_days = total_days_final // 30
        days_remainder = total_days_final % 30
        
        # 合并月份
        total_all_months = qiyun_months_remainder + months_from_total_days
        
        # 再次归一化：月份可能超过12，需要转换为年+月
        additional_years = total_all_months // 12
        qiyun_years = qiyun_years + additional_years
        qiyun_months = int(total_all_months % 12)
        
        # 归一化：天数（剩余天数）
        qiyun_days = days_remainder
        
        # 归一化：小时（保持原样）
        qiyun_hours = total_hours_final

        # 5. 计算交运信息
        # ✅ 修复：交运计算逻辑（与问真八字一致）
        # 步骤：
        # 1. 计算起运时间点 = 出生时间 + 起运年月日时
        # 2. 交运天干 = 起运时间点所在年份的天干，以及+5年的天干
        # 3. 找到起运时间点所在的节气（该时间点之前最近的节气）
        # 4. 节气后天数 = 起运时间点 - 这个节气的时间
        
        birth_year = birth_date.year
        
        def _add_years_months_days_hours(dt, years, months, days, hours):
            year = dt.year + years
            month = dt.month + months
            while month > 12:
                month -= 12
                year += 1
            while month < 1:
                month += 12
                year -= 1
            day = min(dt.day, monthrange(year, month)[1])
            result = datetime(year, month, day, dt.hour, dt.minute, dt.second)
            result += timedelta(days=days, hours=hours)
            return result

        # 计算起运时间点
        start_luck_datetime = _add_years_months_days_hours(
            birth_datetime,
            qiyun_years,
            qiyun_months,
            qiyun_days,
            qiyun_hours
        )

        # ✅ 找到起运时间点所在的节气（该时间点之前最近的节气）
        def _find_current_solar_term(target_datetime):
            """找到目标时间点所在的节气（即该时间点之前最近的节气）"""
            year = target_datetime.year
            base_solar = Solar.fromYmdHms(year, 1, 1, 0, 0, 0)
            lunar_year = base_solar.getLunar()
            jieqi_table = lunar_year.getJieQiTable()
            
            # 收集所有节气及其时间
            jieqi_list = []
            for name, jq_solar in jieqi_table.items():
                if jq_solar and isinstance(name, str):
                    jq_dt = datetime(jq_solar.getYear(), jq_solar.getMonth(), jq_solar.getDay(), 
                                     jq_solar.getHour(), jq_solar.getMinute(), jq_solar.getSecond())
                    jieqi_list.append((name, jq_dt))
            
            # 按时间排序
            jieqi_list.sort(key=lambda x: x[1])
            
            # 找到目标时间点之前最近的节气
            current_jieqi = None
            current_jieqi_dt = None
            for name, jq_dt in jieqi_list:
                if jq_dt <= target_datetime:
                    current_jieqi = name
                    current_jieqi_dt = jq_dt
                else:
                    break
            
            return current_jieqi, current_jieqi_dt
        
        # 找到起运时间点所在的节气
        qiyun_solar_term, solar_term_datetime = _find_current_solar_term(start_luck_datetime)
        
        # 如果找不到节气（不太可能），降级使用原始起运节气
        if qiyun_solar_term is None:
            qiyun_solar_term = start_jieqi.getName()
            solar_term_datetime = datetime(
                start_jieqi.getSolar().getYear(),
                start_jieqi.getSolar().getMonth(),
                start_jieqi.getSolar().getDay(),
                start_jieqi.getSolar().getHour(),
                start_jieqi.getSolar().getMinute(),
                start_jieqi.getSolar().getSecond()
            )

        # ✅ 计算节气后天数 = 起运时间点 - 节气时间
        diff_days = (start_luck_datetime - solar_term_datetime).total_seconds() / 86400.0
        
        # 使用向下取整（与问真一致）
        jiaoyun_days_after = max(int(diff_days), 0)

        # ✅ 修复：交运天干使用起运时间点所在年份来计算（与问真一致）
        # 而不是简单的 出生年 + 起运年数
        # 例如：1988年9月出生，起运7年4月，起运时间点是1996年2月，所以用1996年的天干
        qiyun_year = start_luck_datetime.year
        base_year = 1984  # 甲子年
        year_diff = qiyun_year - base_year
        qiyun_year_stem_index = (year_diff % 10 + 10) % 10
        qiyun_year_stem = HEAVENLY_STEMS[qiyun_year_stem_index]
        
        # 起运年+5年天干
        qiyun_year_plus5_stem_index = (qiyun_year_stem_index + 5) % 10
        qiyun_year_plus5_stem = HEAVENLY_STEMS[qiyun_year_plus5_stem_index]

        # 交运年天干列表
        jiaoyun_stems = [qiyun_year_stem, qiyun_year_plus5_stem]

        # 保存结果
        self.details['qiyun'] = {
            'years': qiyun_years,
            'months': qiyun_months,
            'days': qiyun_days,
            'hours': qiyun_hours,
            'description': f'出生后{qiyun_years}年{qiyun_months}月{qiyun_days}天{qiyun_hours}时起运'
        }

        self.details['jiaoyun'] = {
            'stems': jiaoyun_stems,
            'branch': '',  # 暂时不设置地支
            'solar_term': qiyun_solar_term,
            'days_after': jiaoyun_days_after,
            'description': f'逢{"、".join(jiaoyun_stems)}年{qiyun_solar_term}后{jiaoyun_days_after}天交大运'
        }

    def _build_current_context(self, dayun_index: Optional[int] = None, target_year: Optional[int] = None) -> Dict[str, Any]:
        current_year = self.current_time.year
        dayun_sequence = self.details.get('dayun_sequence', [])

        if not dayun_sequence:
            selected_year = target_year if target_year is not None else current_year
            return {'dayun_index': 0, 'selected_year': selected_year, 'year_index': 0}

        # 如果指定了大运索引，直接使用
        if dayun_index is not None:
            # ✅ 修复：dayun_index是step值，不是数组索引，需要根据step查找对应的大运
            selected_dayun = None
            actual_index = 0
            for idx, dayun in enumerate(dayun_sequence):
                if dayun.get('step') == dayun_index:
                    selected_dayun = dayun
                    actual_index = idx
                    break
            
            # 如果没找到，使用数组索引作为降级方案
            if selected_dayun is None:
                actual_index = max(0, min(dayun_index, len(dayun_sequence) - 1))
                selected_dayun = dayun_sequence[actual_index]
            
            # 如果指定了目标年份，使用目标年份；否则使用大运起始年份
            if target_year is not None:
                # 确保目标年份在大运范围内
                selected_year = min(max(target_year, selected_dayun['year_start']), selected_dayun['year_end'])
            else:
                selected_year = selected_dayun['year_start']
            return {
                'dayun_index': actual_index,  # 返回实际数组索引，用于后续访问
                'selected_year': selected_year,
                'year_index': 0,
            }

        # 否则，根据当前年份自动查找
        selected_index = 0
        for idx, dayun in enumerate(dayun_sequence):
            start = dayun['year_start']
            end = dayun['year_end']
            if current_year < start:
                selected_index = max(0, idx - 1)
                break
            if current_year == start:
                selected_index = max(0, idx - 1)
                break
            if current_year <= end:
                selected_index = idx
                break
            selected_index = idx

        selected_dayun = dayun_sequence[selected_index]
        # 如果指定了目标年份，使用目标年份；否则使用大运起始年份或当前年份
        if target_year is not None:
            # 确保目标年份在大运范围内
            selected_year = min(max(target_year, selected_dayun['year_start']), selected_dayun['year_end'])
        else:
            # 如果当前年份在大运范围内，使用当前年份；否则使用大运起始年份
            if selected_dayun['year_start'] <= current_year <= selected_dayun['year_end']:
                selected_year = current_year
            else:
                selected_year = selected_dayun['year_start']

        return {
            'dayun_index': selected_index,
            'selected_year': selected_year,
            'year_index': 0,
        }

    def _generate_current_liunian_window(self, context: Dict[str, Any]) -> None:
        # ✅ 调试日志：记录函数被调用
        try:
            with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"[_generate_current_liunian_window] 函数被调用\n")
                f.write(f"[_generate_current_liunian_window] self.details.keys(): {list(self.details.keys())}\n")
        except:
            pass
        
        dayun_sequence = self.details.get('dayun_sequence', [])
        # ✅ 调试日志：记录dayun_sequence状态
        try:
            with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"[_generate_current_liunian_window] dayun_sequence长度: {len(dayun_sequence)}\n")
                if dayun_sequence:
                    for i, d in enumerate(dayun_sequence[:5]):  # 显示前5个
                        f.write(f"  dayun_sequence[{i}]: stem={d.get('stem')}, branch={d.get('branch')}, year_start={d.get('year_start')}, year_end={d.get('year_end')}\n")
                else:
                    f.write(f"[_generate_current_liunian_window] ⚠️  dayun_sequence为空！\n")
        except Exception as e:
            try:
                with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                    f.write(f"[_generate_current_liunian_window] 调试日志写入失败: {e}\n")
            except:
                pass
        
        if not dayun_sequence:
            self.details['liunian_sequence'] = []
            self.details['liuyue_sequence'] = []
            return

        dayun_idx = context.get('dayun_index', 0)
        dayun_idx = max(0, min(dayun_idx, len(dayun_sequence) - 1))
        dayun = dayun_sequence[dayun_idx]

        # 获取大运天干地支（用于关系计算，但不改变原有逻辑）
        # 如果是小运，设置为None，关系计算会被跳过
        is_xiaoyun = dayun.get('is_xiaoyun', False)
        dayun_stem = dayun.get('stem', '') if not is_xiaoyun else None
        dayun_branch = dayun.get('branch', '') if not is_xiaoyun else None
        
        # ✅ 修复：确保使用正确的大运信息计算关系
        # 如果当前大运是小运，需要查找包含目标年份的大运
        selected_year = context.get('selected_year', dayun.get('year_start'))
        
        # ✅ 修复：如果当前大运是小运，查找包含目标年份的大运（用于关系计算）
        # 注意：这里只用于关系计算，不改变原有的 dayun 对象（保持原有逻辑不变）
        relation_dayun_stem = dayun_stem
        relation_dayun_branch = dayun_branch
        
        # ✅ 修复：如果当前大运是小运，或者年份范围不包含目标年份，查找包含目标年份的大运
        if (dayun_stem is None or is_xiaoyun or 
            (dayun.get('year_start', 0) > selected_year or dayun.get('year_end', 0) < selected_year)):
            # 查找包含目标年份的大运（优先查找非小运的大运）
            for d in dayun_sequence:
                d_stem = d.get('stem', '')
                d_branch = d.get('branch', '')
                d_is_xiaoyun = d.get('is_xiaoyun', False)
                if (d_stem and not d_is_xiaoyun and 
                    d_branch and
                    d.get('year_start', 0) <= selected_year <= d.get('year_end', 0)):
                    relation_dayun_stem = d_stem
                    relation_dayun_branch = d_branch
                    break
        
        # 使用找到的大运信息（用于关系计算）
        dayun_stem = relation_dayun_stem
        dayun_branch = relation_dayun_branch
        
        # ✅ 调试日志：记录调用参数
        try:
            with open('/tmp/bazi_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"[_generate_current_liunian_window] 调用_generate_liunian_for_range\n")
                f.write(f"  dayun_stem: {dayun_stem}, dayun_branch: {dayun_branch}\n")
                f.write(f"  year_start: {dayun['year_start']}, year_end: {dayun['year_end']}\n")
                f.write(f"  selected_year: {selected_year}\n")
                f.write(f"  self.details.keys(): {list(self.details.keys())}\n")
                f.write(f"  dayun_sequence长度: {len(self.details.get('dayun_sequence', []))}\n")
        except:
            pass
        
        # 生成流年列表，传入大运和四柱信息用于计算关系（可选参数，不影响原有逻辑）
        # ✅ 修复：如果当前大运已经有流年序列，直接使用；否则生成
        if not dayun.get('liunian_sequence'):
            liunians = self._generate_liunian_for_range(
                self.bazi_pillars['day']['stem'],
                dayun['year_start'],
                dayun['year_end'],
                dayun_stem=dayun_stem,  # 新增：可选参数，用于关系计算
                dayun_branch=dayun_branch,  # 新增：可选参数，用于关系计算
                bazi_pillars=self.bazi_pillars  # 新增：可选参数，用于关系计算
            )
            dayun['liunian_sequence'] = liunians
        else:
            liunians = dayun.get('liunian_sequence', [])
        
        # ✅ 修复：不覆盖全局流年序列，而是合并（如果全局流年序列已存在）
        if 'liunian_sequence' not in self.details or not self.details.get('liunian_sequence'):
            # 如果全局流年序列不存在，使用当前大运的流年序列
            self.details['liunian_sequence'] = liunians
        # 否则，保持全局流年序列不变（已在 _calculate_liunian_sequence 中生成）

        selected_year = context.get('selected_year', dayun['year_start'])
        selected_year = min(max(selected_year, dayun['year_start']), dayun['year_end'])
        year_index = selected_year - dayun['year_start']

        context['selected_year'] = selected_year
        context['year_index'] = year_index

        selected_liunian = liunians[year_index] if liunians else {}
        liuyue_sequence = selected_liunian.get('liuyue_sequence', [])
        self.details['liuyue_sequence'] = liuyue_sequence
        context['selected_month'] = liuyue_sequence[0]['month'] if liuyue_sequence else None

    def _format_dayun_liunian_result(self):
        """格式化大运流年结果"""
        result = {
            'basic_info': {
                'solar_date': self.solar_date,
                'solar_time': self.solar_time,
                'lunar_date': self.lunar_date,
                'gender': self.gender,
                'current_time': self.current_time
            },
            'bazi_pillars': self.bazi_pillars,
            'details': self.details
        }
        return result

    def get_dayun_liunian_result(self, current_time=None):
        """获取大运流年计算结果"""
        return self.calculate_dayun_liunian(current_time)