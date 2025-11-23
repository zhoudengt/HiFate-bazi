#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lunar_python import Solar, Lunar
from datetime import datetime, timedelta
import sys
import os

# 添加模块路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.constants import *
from src.data.stems_branches import *
from src.bazi_config.deities_config import DeitiesCalculator
from src.bazi_config.star_fortune_config import StarFortuneCalculator
from src.analyzers.rizhu_gender_analyzer import RizhuGenderAnalyzer




class WenZhenBazi:
    """HiFate排盘主类 - 最完整版本"""

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
        """执行八字排盘计算"""
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

            return self._format_result()
        except Exception as e:
            print(f"计算错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_with_lunar(self):
        """使用lunar-python计算四柱八字和农历日期，修正年柱计算"""
        # 解析日期时间
        year, month, day = map(int, self.solar_date.split('-'))
        hour, minute = map(int, self.solar_time.split(':'))

        # 处理子时情况（23:00-24:00）
        adjusted_year, adjusted_month, adjusted_day = year, month, day
        adjusted_hour, adjusted_minute = hour, minute

        self.is_zi_shi_adjusted = False

        if hour >= 23:
            # 日期加1天，时间设为0点
            current_date = datetime(year, month, day)
            next_date = current_date + timedelta(days=1)
            adjusted_year, adjusted_month, adjusted_day = next_date.year, next_date.month, next_date.day
            adjusted_hour = 0
            self.is_zi_shi_adjusted = True
            print(f"注意：23点以后，日期调整为: {adjusted_year:04d}-{adjusted_month:02d}-{adjusted_day:02d} 00:{minute:02d}")

        # 保存调整后的日期和时间
        self.adjusted_solar_date = f"{adjusted_year:04d}-{adjusted_month:02d}-{adjusted_day:02d}"
        self.adjusted_solar_time = f"{adjusted_hour:02d}:{minute:02d}"

        # 创建阳历对象（使用调整后的日期时间）
        solar = Solar.fromYmdHms(adjusted_year, adjusted_month, adjusted_day, adjusted_hour, adjusted_minute, 0)

        # 转换为农历
        lunar = solar.getLunar()

        # 获取八字信息
        bazi = lunar.getBaZi()

        # 【关键修正】确保年柱始终基于原始日期计算
        # 获取原始日期的年柱
        original_solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        original_lunar = original_solar.getLunar()
        original_bazi = original_lunar.getBaZi()

        # 解析四柱 - 年柱使用原始日期，其他柱使用调整后日期
        self.bazi_pillars = {
            'year': {'stem': original_bazi[0][0], 'branch': original_bazi[0][1]},  # 使用原始日期年柱
            'month': {'stem': bazi[1][0], 'branch': bazi[1][1]},  # 使用调整后日期
            'day': {'stem': bazi[2][0], 'branch': bazi[2][1]},    # 使用调整后日期
            'hour': {'stem': bazi[3][0], 'branch': bazi[3][1]}    # 使用调整后日期
        }

        # 保存农历日期
        self.lunar_date = {
            'year': lunar.getYear(),
            'month': lunar.getMonth(),
            'day': lunar.getDay(),
            'month_name': lunar.getMonthInChinese(),
            'day_name': lunar.getDayInChinese()
        }

        # 输出调试信息
        if self.is_zi_shi_adjusted:
            print(f"年柱保持为: {self.bazi_pillars['year']['stem']}{self.bazi_pillars['year']['branch']}")

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

    def _format_result(self):
        """格式化输出结果"""
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
            'details': self.details
        }
        return result

    def print_result(self):
        """打印排盘结果"""
        result = self.calculate()
        if not result:
            print("排盘失败，请检查输入参数")
            return

        print("=" * 60)
        print("HiFate排盘 - 最完整版本")
        print("=" * 60)

        basic = result['basic_info']
        print(f"阳历: {basic['solar_date']} {basic['solar_time']}")

        # 如果日期被调整过，显示调整后的日期
        if basic['is_zi_shi_adjusted']:
            print(f"调整后: {basic['adjusted_solar_date']} {basic['adjusted_solar_time']} (子时调整)")

        # 显示农历日期
        lunar = basic['lunar_date']
        lunar_year = lunar['year']
        lunar_month_name = lunar.get('month_name', '')
        lunar_day_name = lunar.get('day_name', '')

        if not lunar_month_name:
            lunar_month_name = f"{lunar['month']}月"
        if not lunar_day_name:
            lunar_day_name = f"{lunar['day']}日"

        print(f"农历: {lunar_year}年{lunar_month_name}{lunar_day_name}")
        print(f"性别: {'男' if basic['gender'] == 'male' else '女'}")
        print()

        pillars = result['bazi_pillars']
        details = result['details']



        self._print_detailed_table(pillars, details)

    def _print_detailed_table(self, pillars, details):
        """打印详细排盘表格"""
        headers = ["日期", "年柱", "月柱", "日柱", "时柱"]

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
        print(header_line)
        print("-" * len(header_line))

        for row in rows:
            row_line = "".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row)))
            print(row_line)



    # 新增日柱性别分析方法：
    def print_rizhu_gender_analysis(self):
        """打印日柱性别查询分析结果"""
        print("\n" + "=" * 80)
        #print("日柱性别命理分析")
        #print("=" * 80)

        # 确保已经计算了八字
        if not self.bazi_pillars or not self.details:
            self.calculate()

        # 创建日柱性别分析器
        analyzer = RizhuGenderAnalyzer(self.bazi_pillars, self.gender)

        # 获取分析结果
        analysis_output = analyzer.get_formatted_output()
        print(analysis_output)


if __name__ == "__main__":

    bazi = WenZhenBazi(
        solar_date='1990-03-15',
        solar_time='10:30',
        gender='male'    #female
    )
    bazi.print_result()

    bazi.print_rizhu_gender_analysis()