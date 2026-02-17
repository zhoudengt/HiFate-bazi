#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
八字排盘主模块 - WenZhenBazi 类

自动检测并使用项目虚拟环境 (.venv)
如果检测到项目根目录下有 .venv，自动切换到 .venv/bin/python3

模块化重构完成：
- core/calculators/bazi_data/service_client.py - 微服务调用（BaziServiceClientMixin）
- core/calculators/bazi_data/builders.py - 数据构建与打印（BaziDataBuilderMixin）
- core/calculators/bazi_rules/matcher.py - 规则匹配（BaziRuleMatcherMixin）
- core/calculators/bazi_rules/condition_debug.py - 条件调试（BaziConditionDebugMixin）
- core/calculators/bazi_logging.py - 共享日志工具

本文件仅保留核心排盘计算逻辑（WenZhenBazi.__init__ + calculate + _calculate_*）。
"""
import sys
import os
from pathlib import Path

# 检测并确保使用 .venv
def _ensure_venv():
    """确保使用项目的 .venv 虚拟环境"""
    # 获取项目根目录（假设脚本在 src/ 目录下）
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    venv_python = project_root / ".venv" / "bin" / "python3"
    
    # 如果 .venv 存在
    if venv_python.exists():
        current_python = Path(sys.executable).resolve()
        venv_python_resolved = venv_python.resolve()
        # 如果当前 Python 不是 .venv 中的，提示用户
        if current_python != venv_python_resolved:
            logger.info("=" * 60, file=sys.stderr)
            logger.info("⚠️  检测到未使用项目虚拟环境 (.venv)", file=sys.stderr)
            logger.info("=" * 60, file=sys.stderr)
            logger.info(f"当前 Python: {current_python}", file=sys.stderr)
            logger.info(f"项目虚拟环境: {venv_python_resolved}", file=sys.stderr)
            logger.info("", file=sys.stderr)
            logger.info("请使用以下方式执行：", file=sys.stderr)
            script_path = Path(__file__).resolve()
            logger.info(f"  {venv_python_resolved} {script_path}", file=sys.stderr)
            logger.info("", file=sys.stderr)
            logger.info("或者激活虚拟环境后执行：", file=sys.stderr)
            logger.info(f"  source {project_root}/.venv/bin/activate", file=sys.stderr)
            logger.info(f"  python {script_path}", file=sys.stderr)
            logger.info("=" * 60, file=sys.stderr)
            sys.exit(1)

_ensure_venv()

import json
import logging
from datetime import datetime

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载微服务环境变量配置（如果直接运行脚本）
def _load_services_env():
    """加载微服务环境变量配置"""
    project_root = Path(__file__).resolve().parent.parent
    services_env_file = project_root / "config" / "services.env"
    if services_env_file.exists():
        try:
            with open(services_env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "export " in line:
                        # 解析 export KEY="VALUE" 格式
                        if "=" in line:
                            key_value = line.replace("export ", "").strip()
                            if "=" in key_value:
                                key, value = key_value.split("=", 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                # 只在环境变量未设置时设置默认值
                                if key not in os.environ:
                                    os.environ[key] = value
        except Exception as exc:
            logger.info(f"⚠️  加载环境变量配置失败: {exc}", file=sys.stderr)

# 自动加载环境变量
_load_services_env()

from core.data.constants import *
from core.data.stems_branches import *
from core.config.deities_config import DeitiesCalculator
from core.config.star_fortune_config import StarFortuneCalculator
from core.calculators.LunarConverter import LunarConverter
from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer
from core.data.relations import (
    STEM_HE,
    BRANCH_LIUHE,
    BRANCH_CHONG,
    BRANCH_XING,
    BRANCH_HAI,
    BRANCH_PO,
    BRANCH_SANHE_GROUPS,
    BRANCH_SANHUI_GROUPS,
)

# 日志和安全输出（共享模块）
from core.calculators.bazi_logging import SafeStreamHandler, logger, safe_log

# Mixin 模块（从本文件提取的方法）
from core.calculators.bazi_data.service_client import BaziServiceClientMixin
from core.calculators.bazi_data.builders import BaziDataBuilderMixin
from core.calculators.bazi_rules.matcher import BaziRuleMatcherMixin
from core.calculators.bazi_rules.condition_debug import BaziConditionDebugMixin




class WenZhenBazi(
    BaziServiceClientMixin,
    BaziDataBuilderMixin,
    BaziRuleMatcherMixin,
    BaziConditionDebugMixin,
):
    """HiFate排盘主类 - 最完整版本

    方法已模块化拆分到 Mixin 中：
    - BaziServiceClientMixin: 微服务调用（bazi-core/fortune/rule）
    - BaziDataBuilderMixin:  数据构建与打印
    - BaziRuleMatcherMixin:  规则匹配（本地+微服务）
    - BaziConditionDebugMixin: 条件调试输出
    """

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
        self.last_fortune_detail = None
        self.last_fortune_snapshot = None
        self.last_matched_rules = []
        self.last_rule_context = {}
        self.last_unmatched_rules = []

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
        """执行八字排盘计算（优先微服务，无微服务时使用本地计算）"""
        # 尝试使用微服务（如果配置了）
        try:
            service_result = self._calculate_via_core_service()
            if service_result is not None:
                return service_result
        except Exception as e:
            safe_log('warning', f"⚠️  微服务调用跳过: {e}")

        # 使用本地计算
        safe_log('info', "ℹ️  使用本地计算")
        try:
            # 1. 使用lunar-python计算四柱和农历（包含子时处理）
            self._calculate_with_lunar()

            # 2. 计算十神 - 使用修正后的计算器
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
            safe_log('error', f"本地计算也失败: {e}")
            import traceback
            try:
                traceback.print_exc()
            except (BrokenPipeError, OSError):
                # 忽略 Broken pipe 错误
                pass
            raise RuntimeError(f"微服务调用失败，本地计算也失败: {e}") from e

    def _calculate_with_lunar(self):
        """使用 LunarConverter 统一计算四柱八字和农历日期（含23点不换日柱逻辑）"""
        lunar_result = LunarConverter.solar_to_lunar(self.solar_date, self.solar_time)
        self.lunar_date = lunar_result['lunar_date']
        self.bazi_pillars = lunar_result['bazi_pillars']
        self.adjusted_solar_date = lunar_result['adjusted_solar_date']
        self.adjusted_solar_time = lunar_result['adjusted_solar_time']
        self.is_zi_shi_adjusted = lunar_result['is_zi_shi_adjusted']

    def _calculate_ten_gods(self):
        """计算十神 - 使用修正后的计算器"""
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
                'hidden_stars': branch_gods
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

