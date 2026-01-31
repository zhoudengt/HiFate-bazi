#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging

logger = logging.getLogger(__name__)
import os

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer


class BaziPrinter:
    """八字打印类 - 专门用于格式化打印八字排盘结果"""

    def __init__(self, bazi_calculator):
        self.calculator = bazi_calculator
        self.result = None

    def print_result(self):
        """打印排盘结果"""
        self.result = self.calculator.calculate()
        if not self.result:
            logger.info("排盘失败，请检查输入参数")
            return

        logger.info("=" * 60)
        logger.info("HiFate排盘 - 最完整版本")
        logger.info("=" * 60)

        basic = self.result['basic_info']
        logger.info(f"阳历: {basic['solar_date']} {basic['solar_time']}")

        # 如果日期被调整过，显示调整后的日期
        if basic['is_zi_shi_adjusted']:
            logger.info(f"调整后: {basic['adjusted_solar_date']} {basic['adjusted_solar_time']} (子时调整)")

        # 显示农历日期
        lunar = basic['lunar_date']
        lunar_year = lunar['year']
        lunar_month_name = lunar.get('month_name', '')
        lunar_day_name = lunar.get('day_name', '')

        if not lunar_month_name:
            lunar_month_name = f"{lunar['month']}月"
        if not lunar_day_name:
            lunar_day_name = f"{lunar['day']}日"

        logger.info(f"农历: {lunar_year}年{lunar_month_name}{lunar_day_name}")
        logger.info(f"性别: {'男' if basic['gender'] == 'male' else '女'}")
        logger.info("")

        pillars = self.result['bazi_pillars']
        details = self.result['details']

        self._print_detailed_table(pillars, details)

    def _print_detailed_table(self, pillars, details):
        """打印详细排盘表格"""
        headers = ["", "年柱", "月柱", "日柱", "时柱"]

        # 构建表格行
        rows = [
            ["主星"] + [details.get(p, {}).get('main_star', '') for p in ['year', 'month', 'day', 'hour']],
            ["天干"] + [pillars[p]['stem'] for p in ['year', 'month', 'day', 'hour']],
            ["地支"] + [pillars[p]['branch'] for p in ['year', 'month', 'day', 'hour']],
            ]

        # 处理藏干和副星 - 将逗号分隔的值分行显示
        hidden_stems_data = [details.get(p, {}).get('hidden_stems', []) for p in ['year', 'month', 'day', 'hour']]
        hidden_stars_data = [details.get(p, {}).get('hidden_stars', []) for p in ['year', 'month', 'day', 'hour']]

        # 计算最大行数（用于对齐）
        max_hidden_rows = max(len(stems) for stems in hidden_stems_data) if any(hidden_stems_data) else 0
        max_stars_rows = max(len(stars) for stars in hidden_stars_data) if any(hidden_stars_data) else 0

        # 添加藏干行
        if max_hidden_rows > 0:
            rows.append(["藏干"] + ["" for _ in range(4)])  # 标题行
            for i in range(max_hidden_rows):
                row_data = []
                for j in range(4):
                    if i < len(hidden_stems_data[j]):
                        row_data.append(hidden_stems_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        # 添加副星行
        if max_stars_rows > 0:
            rows.append(["副星"] + ["" for _ in range(4)])  # 标题行
            for i in range(max_stars_rows):
                row_data = []
                for j in range(4):
                    if i < len(hidden_stars_data[j]):
                        row_data.append(hidden_stars_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        # 添加其他行
        other_rows = [
            ["星运"] + [details.get(p, {}).get('star_fortune', '') for p in ['year', 'month', 'day', 'hour']],
            ["自坐"] + [details.get(p, {}).get('self_sitting', '') for p in ['year', 'month', 'day', 'hour']],
            ["空亡"] + [details.get(p, {}).get('kongwang', '') for p in ['year', 'month', 'day', 'hour']],
            ["纳音"] + [details.get(p, {}).get('nayin', '') for p in ['year', 'month', 'day', 'hour']]
        ]
        rows.extend(other_rows)

        # 处理神煞 - 将逗号分隔的值分行显示（放在最后）
        deities_data = [details.get(p, {}).get('deities', []) for p in ['year', 'month', 'day', 'hour']]

        # 计算最大行数（用于对齐）
        max_deities_rows = max(len(deities) for deities in deities_data) if any(deities_data) else 0

        # 添加神煞行
        if max_deities_rows > 0:
            rows.append(["神煞"] + ["" for _ in range(4)])  # 标题行
            for i in range(max_deities_rows):
                row_data = []
                for j in range(4):
                    if i < len(deities_data[j]):
                        row_data.append(deities_data[j][i])
                    else:
                        row_data.append("")
                rows.append([""] + row_data)

        col_widths = [8, 20, 20, 20, 20]

        header_line = "".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
        logger.info(header_line)
        logger.info("-" * len(header_line))

        for row in rows:
            row_line = "".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row)))
            logger.info(row_line)

    def print_rizhu_gender_analysis(self):
        """打印日柱性别查询分析结果"""
        logger.info("\n" + "=" * 80)

        # 确保已经计算了八字
        if not self.calculator.bazi_pillars or not self.calculator.details:
            self.result = self.calculator.calculate()

        # 创建日柱性别分析器
        analyzer = RizhuGenderAnalyzer(self.calculator.bazi_pillars, self.calculator.gender)

        # 获取分析结果
        analysis_output = analyzer.get_formatted_output()
        logger.info(analysis_output)

    def get_formatted_result(self):
        """获取格式化结果（不打印）"""
        self.result = self.calculator.calculate()
        if not self.result:
            return "排盘失败，请检查输入参数"

        output_lines = []
        basic = self.result['basic_info']

        output_lines.append("=" * 60)
        output_lines.append("HiFate排盘 - 最完整版本")
        output_lines.append("=" * 60)
        output_lines.append(f"阳历: {basic['solar_date']} {basic['solar_time']}")

        if basic['is_zi_shi_adjusted']:
            output_lines.append(f"调整后: {basic['adjusted_solar_date']} {basic['adjusted_solar_time']} (子时调整)")

        lunar = basic['lunar_date']
        lunar_year = lunar['year']
        lunar_month_name = lunar.get('month_name', '')
        lunar_day_name = lunar.get('day_name', '')

        if not lunar_month_name:
            lunar_month_name = f"{lunar['month']}月"
        if not lunar_day_name:
            lunar_day_name = f"{lunar['day']}日"

        output_lines.append(f"农历: {lunar_year}年{lunar_month_name}{lunar_day_name}")
        output_lines.append(f"性别: {'男' if basic['gender'] == 'male' else '女'}")
        output_lines.append("")

        # 这里可以添加表格格式化的代码，返回字符串而不是打印
        # 由于表格格式化较复杂，这里简化处理
        pillars = self.result['bazi_pillars']
        details = self.result['details']

        output_lines.append("四柱八字:")
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar = pillars[pillar_type]
            detail = details[pillar_type]
            output_lines.append(f"{pillar_type.capitalize()}柱: {pillar['stem']}{pillar['branch']} "
                                f"主星: {detail.get('main_star', '')} "
                                f"纳音: {detail.get('nayin', '')}")

        return "\n".join(output_lines)