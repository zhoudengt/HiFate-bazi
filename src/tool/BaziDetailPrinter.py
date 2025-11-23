#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime

from src.clients.bazi_fortune_client_grpc import BaziFortuneClient
from src.bazi_fortune.helpers import compute_local_detail


class BaziDetailPrinter:
    """八字详细打印类 - 用于打印包含大运流年的详细结果"""

    def __init__(self, bazi_calculator):
        self.calculator = bazi_calculator
        self.result = None

    def print_detailed_result(self, current_time=None):
        """打印详细排盘结果"""
        fortune_service_url = os.getenv("BAZI_FORTUNE_SERVICE_URL")
        current_time_obj = current_time if isinstance(current_time, datetime) else None

        if fortune_service_url:
            try:
                client = BaziFortuneClient(base_url=fortune_service_url)
                current_time_iso = current_time_obj.isoformat() if current_time_obj else None
                self.result = client.calculate_detail(
                    solar_date=self.calculator.solar_date,
                    solar_time=self.calculator.solar_time,
                    gender=self.calculator.gender,
                    current_time=current_time_iso,
                )
            except Exception as exc:
                print(f"⚠️  调用 bazi-fortune-service 失败，自动回退本地计算: {exc}")
                self.result = compute_local_detail(
                    self.calculator.solar_date,
                    self.calculator.solar_time,
                    self.calculator.gender,
                    current_time=current_time_obj,
                )
        else:
            print("提示: 未检测到环境变量 BAZI_FORTUNE_SERVICE_URL，使用本地算法计算大运流年。")
            self.result = compute_local_detail(
                self.calculator.solar_date,
                self.calculator.solar_time,
                self.calculator.gender,
                current_time=current_time_obj,
            )

        if not self.result:
            print("排盘失败，请检查输入参数")
            return

        print("=" * 120)
        print("HiFate详细排盘 - 大运流年版本")
        print("=" * 120)

        self._print_basic_info()
        self._print_bazi_pillars_with_dayun_liunian()
        self._print_dayun_sequence_info()
        self._print_liunian_sequence_info()
        self._print_liuyue_info()
        self._print_liuri_info()
        self._print_liushi_info()
        self._print_qiyun_jiaoyun_info()

    def _print_basic_info(self):
        """打印基本信息"""
        basic = self.result['basic_info']
        print(f"阳历生日: {basic['solar_date']} {basic['solar_time']}")

        lunar = basic['lunar_date']
        print(f"农历生日: {lunar['year']}年{lunar['month_name']}{lunar['day_name']}")

        print(f"性别: {'男' if basic['gender'] == 'male' else '女'}")

        if 'current_time' in basic and basic['current_time']:
            current_time = basic['current_time']
            if isinstance(current_time, datetime):
                print(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M')}")
            else:
                print(f"当前时间: {current_time}")

        print()

    def _print_bazi_pillars_with_dayun_liunian(self):
        """打印四柱信息 - 包含流年和大运的横向表格格式"""
        pillars = self.result['bazi_pillars']
        details = self.result['details']

        # 获取流年和大运的详细信息
        liunian_details = self._get_current_liunian_details()
        dayun_details = self._get_current_dayun_details()

        print("四柱八字:")
        print("-" * 120)

        # 定义表头
        headers = ["日期", "流年", "大运", "年柱", "月柱", "日柱", "时柱"]
        col_widths = [12, 12, 12, 12, 12, 12, 12]

        # 打印表头
        header_line = "".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
        print(header_line)
        print("-" * len(header_line))

        # 构建各行数据
        rows = []

        # 主星行
        main_star_row = ["主星"]
        main_star_row.append(liunian_details.get('main_star', ''))
        main_star_row.append(dayun_details.get('main_star', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            main_star_row.append(details[pillar_type]['main_star'])
        rows.append(main_star_row)

        # 天干行
        stem_row = ["天干"]
        stem_row.append(liunian_details.get('stem', ''))
        stem_row.append(dayun_details.get('stem', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            stem_row.append(pillars[pillar_type]['stem'])
        rows.append(stem_row)

        # 地支行
        branch_row = ["地支"]
        branch_row.append(liunian_details.get('branch', ''))
        branch_row.append(dayun_details.get('branch', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            branch_row.append(pillars[pillar_type]['branch'])
        rows.append(branch_row)

        # 藏干行 - 只显示第一个藏干
        hidden_stem_row = ["藏干"]
        hidden_stem_row.append(liunian_details.get('hidden_stems', [''])[0] if liunian_details.get('hidden_stems') else '')
        hidden_stem_row.append(dayun_details.get('hidden_stems', [''])[0] if dayun_details.get('hidden_stems') else '')
        for pillar_type in ['year', 'month', 'day', 'hour']:
            hidden_stems = details[pillar_type].get('hidden_stems', [])
            hidden_stem_row.append(hidden_stems[0] if hidden_stems else '')
        rows.append(hidden_stem_row)

        # 副星行 - 只显示第一个副星
        hidden_star_row = ["副星"]
        hidden_star_row.append(liunian_details.get('hidden_stars', [''])[0] if liunian_details.get('hidden_stars') else '')
        hidden_star_row.append(dayun_details.get('hidden_stars', [''])[0] if dayun_details.get('hidden_stars') else '')
        for pillar_type in ['year', 'month', 'day', 'hour']:
            hidden_stars = details[pillar_type].get('hidden_stars', [])
            hidden_star_row.append(hidden_stars[0] if hidden_stars else '')
        rows.append(hidden_star_row)

        # 星运行
        star_fortune_row = ["星运"]
        star_fortune_row.append(liunian_details.get('star_fortune', ''))
        star_fortune_row.append(dayun_details.get('star_fortune', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            star_fortune_row.append(details[pillar_type]['star_fortune'])
        rows.append(star_fortune_row)

        # 自坐行
        self_sitting_row = ["自坐"]
        self_sitting_row.append(liunian_details.get('self_sitting', ''))
        self_sitting_row.append(dayun_details.get('self_sitting', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            self_sitting_row.append(details[pillar_type]['self_sitting'])
        rows.append(self_sitting_row)

        # 空亡行
        kongwang_row = ["空亡"]
        kongwang_row.append(liunian_details.get('kongwang', ''))
        kongwang_row.append(dayun_details.get('kongwang', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            kongwang_row.append(details[pillar_type]['kongwang'])
        rows.append(kongwang_row)

        # 纳音行
        nayin_row = ["纳音"]
        nayin_row.append(liunian_details.get('nayin', ''))
        nayin_row.append(dayun_details.get('nayin', ''))
        for pillar_type in ['year', 'month', 'day', 'hour']:
            nayin_row.append(details[pillar_type]['nayin'])
        rows.append(nayin_row)

        # 打印除了神煞之外的所有行
        for row in rows:
            row_line = "".join(f"{str(row[i]):<{col_widths[i]}}" for i in range(len(row)))
            print(row_line)

        # 神煞列输出 - 每个神煞占一行
        self._print_deities_in_columns(headers, col_widths, liunian_details, dayun_details, details)

        print()

    def _print_deities_in_columns(self, headers, col_widths, liunian_details, dayun_details, details):
        """打印神煞列输出 - 每个神煞占一行"""
        # 收集所有柱的神煞列表
        all_deities = []

        # 流年神煞
        liunian_deities = liunian_details.get('deities', [])
        all_deities.append(liunian_deities)

        # 大运神煞
        dayun_deities = dayun_details.get('deities', [])
        all_deities.append(dayun_deities)

        # 四柱神煞
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_deities = details[pillar_type].get('deities', [])
            all_deities.append(pillar_deities)

        # 找出最大神煞数量
        max_deities_count = max(len(deities_list) for deities_list in all_deities) if all_deities else 0

        # 如果没有神煞，打印一行空行
        if max_deities_count == 0:
            deities_row = ["神煞"] + [''] * (len(headers) - 1)
            row_line = "".join(f"{str(deities_row[i]):<{col_widths[i]}}" for i in range(len(deities_row)))
            print(row_line)
            return

        # 打印神煞标题行
        deities_title_row = ["神煞"] + [''] * (len(headers) - 1)
        row_line = "".join(f"{str(deities_title_row[i]):<{col_widths[i]}}" for i in range(len(deities_title_row)))
        print(row_line)

        # 逐行打印每个神煞
        for i in range(max_deities_count):
            deities_row = [""]  # 第一列（标签列）为空，因为已经打印了"神煞"标题

            # 流年神煞
            if i < len(liunian_deities):
                deities_row.append(liunian_deities[i])
            else:
                deities_row.append('')

            # 大运神煞
            if i < len(dayun_deities):
                deities_row.append(dayun_deities[i])
            else:
                deities_row.append('')

            # 四柱神煞
            for pillar_type in ['year', 'month', 'day', 'hour']:
                pillar_deities = details[pillar_type].get('deities', [])
                if i < len(pillar_deities):
                    deities_row.append(pillar_deities[i])
                else:
                    deities_row.append('')

            # 打印这一行
            row_line = "".join(f"{str(deities_row[j]):<{col_widths[j]}}" for j in range(len(deities_row)))
            print(row_line)

    def _get_current_liunian_details(self):
        """获取当前流年详细信息"""
        details = self.result['details']

        # 如果有单独的liunian详细信息，直接使用
        if 'liunian' in details:
            return details['liunian']

        # 否则从流年序列中获取当前年份的流年
        if 'liunian_sequence' in details:
            current_year = datetime.now().year
            for liunian in details['liunian_sequence']:
                if liunian['year'] == current_year:
                    return liunian

        # 返回空字典
        return {}

    def _get_current_dayun_details(self):
        """获取当前大运详细信息"""
        details = self.result['details']

        # 如果有单独的dayun详细信息，直接使用
        if 'dayun' in details:
            return details['dayun']

        # 否则从大运序列中获取第一步大运
        if 'dayun_sequence' in details and details['dayun_sequence']:
            return details['dayun_sequence'][0]

        # 返回空字典
        return {}

    def _print_dayun_sequence_info(self):
        """打印大运序列信息"""
        if 'dayun_sequence' not in self.result['details']:
            return

        dayun_sequence = self.result['details']['dayun_sequence']

        print("大运序列:")
        print("-" * 80)

        # 打印年份行
        years_line = "  ".join([f"{dayun['year_start']}-{dayun['year_end']}" for dayun in dayun_sequence])
        print(f"  年份: {years_line}")

        # 打印年龄行
        ages_line = "  ".join([f"{dayun['age_display']}" for dayun in dayun_sequence])
        print(f"  年龄: {ages_line}")

        # 打印干支行
        ganzhi_line = "  ".join([f"{dayun['stem']}{dayun['branch']}" if i > 0 else "小运"
                                  for i, dayun in enumerate(dayun_sequence)])
        print(f"  干支: {ganzhi_line}")

        # 打印十神行
        stars_line = "  ".join([f"{dayun['main_star']}" if i > 0 else "小运"
                                for i, dayun in enumerate(dayun_sequence)])
        print(f"  十神: {stars_line}")

        print()

    def _print_liunian_sequence_info(self):
        """打印流年序列信息"""
        if 'liunian_sequence' not in self.result['details']:
            return

        liunian_sequence = self.result['details']['liunian_sequence']

        print("流年序列:")
        print("-" * 80)

        # 打印年份行
        years_line = "  ".join([f"{item['year']}" for item in liunian_sequence])
        print(f"  年份: {years_line}")

        # 打印干支行
        ganzhi_line = "  ".join([f"{item['stem']}{item['branch']}" for item in liunian_sequence])
        print(f"  干支: {ganzhi_line}")

        # 打印十神行
        stars_line = "  ".join([f"{item['main_star']}" for item in liunian_sequence])
        print(f"  十神: {stars_line}")

        print()

    def _print_liuyue_info(self):
        """打印流月信息"""
        if 'liuyue_sequence' not in self.result['details']:
            return

        liuyue_sequence = self.result['details']['liuyue_sequence']

        print("流月信息:")
        print("-" * 80)

        months_line = "  ".join([f"{item['month']}月" for item in liuyue_sequence])
        print(f"  月份: {months_line}")

        terms_line = "  ".join([f"{item['solar_term']}" for item in liuyue_sequence])
        print(f"  节气: {terms_line}")

        ganzhi_line = "  ".join([f"{item['stem']}{item['branch']}" for item in liuyue_sequence])
        print(f"  干支: {ganzhi_line}")

        print()

    def _print_liuri_info(self):
        """打印流日信息"""
        if 'liuri_sequence' not in self.result['details']:
            return

        liuri_sequence = self.result['details']['liuri_sequence']

        print("流日信息:")
        print("-" * 80)

        # 打印日期行
        dates_line = "  ".join([f"{item['date']}" for item in liuri_sequence])
        print(f"  日期: {dates_line}")

        # 打印干支行
        ganzhi_line = "  ".join([f"{item['stem']}{item['branch']}" for item in liuri_sequence])
        print(f"  干支: {ganzhi_line}")

        # 打印十神行
        stars_line = "  ".join([f"{item['main_star']}" for item in liuri_sequence])
        print(f"  十神: {stars_line}")

        print()

    def _print_liushi_info(self):
        """打印流时信息"""
        if 'liushi_sequence' not in self.result['details']:
            return

        liushi_sequence = self.result['details']['liushi_sequence']

        print("流时信息:")
        print("-" * 80)

        # 打印时间行
        times_line = "  ".join([f"{item['time']}" for item in liushi_sequence])
        print(f"  时间: {times_line}")

        # 打印干支行
        ganzhi_line = "  ".join([f"{item['stem']}{item['branch']}" for item in liushi_sequence])
        print(f"  干支: {ganzhi_line}")

        # 打印十神行
        stars_line = "  ".join([f"{item['main_star']}" for item in liushi_sequence])
        print(f"  十神: {stars_line}")

        print()

    def _print_qiyun_jiaoyun_info(self):
        """打印起运交运信息"""
        qiyun_info = self.result['details'].get('qiyun', {})
        jiaoyun_info = self.result['details'].get('jiaoyun', {})

        if qiyun_info or jiaoyun_info:
            print("起运交运信息:")
            print("-" * 40)

            if qiyun_info:
                print(f"起运: {qiyun_info.get('description', '')}")

            if jiaoyun_info:
                print(f"交运: {jiaoyun_info.get('description', '')}")

            print()