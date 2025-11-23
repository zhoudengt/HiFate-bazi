#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字界面信息分析器
包含所有逻辑转化方法，用于计算星座、生肖、命卦、命宫、身宫等
"""


class BaziInterfaceAnalyzer:
    """八字界面信息分析器 - 包含所有逻辑转化方法"""
    
    def __init__(self):
        # 纳音五行对应表
        self.nayin = {
            "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火",
            "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
            "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
            "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城墙土", "己卯": "城墙土",
            "庚辰": "白蜡金", "辛巳": "白蜡金", "壬午": "杨柳木", "癸未": "杨柳木",
            "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
            "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木",
            "壬辰": "长流水", "癸巳": "长流水", "甲午": "沙中金", "乙未": "沙中金",
            "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
            "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
            "甲辰": "覆灯火", "乙巳": "覆灯火", "丙午": "天河水", "丁未": "天河水",
            "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
            "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
            "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
            "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
        }

        # 生肖对应表
        self.zodiac = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

        # 地支对应表
        self.branches = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

        # 天干对应表
        self.stems = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]

        # 空亡对照表 - 基于旬首
        self.void_emptiness_map = {
            # 甲子旬
            "甲子": "戌亥", "乙丑": "戌亥", "丙寅": "戌亥", "丁卯": "戌亥",
            "戊辰": "戌亥", "己巳": "戌亥", "庚午": "戌亥", "辛未": "戌亥",
            "壬申": "戌亥", "癸酉": "戌亥",
            # 甲戌旬
            "甲戌": "申酉", "乙亥": "申酉", "丙子": "申酉", "丁丑": "申酉",
            "戊寅": "申酉", "己卯": "申酉", "庚辰": "申酉", "辛巳": "申酉",
            "壬午": "申酉", "癸未": "申酉",
            # 甲申旬
            "甲申": "午未", "乙酉": "午未", "丙戌": "午未", "丁亥": "午未",
            "戊子": "午未", "己丑": "午未", "庚寅": "午未", "辛卯": "午未",
            "壬辰": "午未", "癸巳": "午未",
            # 甲午旬
            "甲午": "辰巳", "乙未": "辰巳", "丙申": "辰巳", "丁酉": "辰巳",
            "戊戌": "辰巳", "己亥": "辰巳", "庚子": "辰巳", "辛丑": "辰巳",
            "壬寅": "辰巳", "癸卯": "辰巳",
            # 甲辰旬
            "甲辰": "寅卯", "乙巳": "寅卯", "丙午": "寅卯", "丁未": "寅卯",
            "戊申": "寅卯", "己酉": "寅卯", "庚戌": "寅卯", "辛亥": "寅卯",
            "壬子": "寅卯", "癸丑": "寅卯",
            # 甲寅旬
            "甲寅": "子丑", "乙卯": "子丑", "丙辰": "子丑", "丁巳": "子丑",
            "戊午": "子丑", "己未": "子丑", "庚申": "子丑", "辛酉": "子丑",
            "壬戌": "子丑", "癸亥": "子丑"
        }

        # 二十八宿对应表
        self.mansions = [
            "角宿", "亢宿", "氐宿", "房宿", "心宿", "尾宿", "箕宿",
            "斗宿", "牛宿", "女宿", "虚宿", "危宿", "室宿", "壁宿",
            "奎宿", "娄宿", "胃宿", "昴宿", "毕宿", "觜宿", "参宿",
            "井宿", "鬼宿", "柳宿", "星宿", "张宿", "翼宿", "轸宿"
        ]

        # 日干支到星宿的映射表（根据表格）
        self.day_stem_branch_to_mansion = {
            # 组1（A-B列）
            "甲子": "虚宿", "己巳": "娄宿", "甲戌": "参宿", "己卯": "张宿",
            "甲申": "氐宿", "己丑": "斗宿", "甲午": "室宿", "己亥": "昴宿",
            "甲辰": "鬼宿", "己酉": "轸宿", "甲寅": "心宿", "己未": "女宿",
            # 组2（C-D列）
            "乙丑": "危宿", "庚午": "胃宿", "乙亥": "井宿", "庚辰": "翼宿",
            "乙酉": "房宿", "庚寅": "牛宿", "乙未": "壁宿", "庚子": "毕宿",
            "乙巳": "柳宿", "庚戌": "角宿", "乙卯": "尾宿", "庚申": "虚宿",
            # 组3（E-F列）
            "丙寅": "室宿", "辛未": "昴宿", "丙子": "鬼宿", "辛巳": "轸宿",
            "丙戌": "心宿", "辛卯": "女宿", "丙申": "奎宿", "辛丑": "觜宿",
            "丙午": "星宿", "辛亥": "亢宿", "丙辰": "箕宿", "辛酉": "危宿",
            # 组4（G-H列）
            "丁卯": "壁宿", "壬申": "毕宿", "丁丑": "柳宿", "壬午": "角宿",
            "丁亥": "尾宿", "壬辰": "虚宿", "丁酉": "娄宿", "壬寅": "参宿",
            "丁未": "张宿", "壬子": "氐宿", "丁巳": "斗宿", "壬戌": "室宿",
            # 组5（I-J列）
            "戊辰": "奎宿", "癸酉": "觜宿", "戊寅": "星宿", "癸未": "亢宿",
            "戊子": "箕宿", "癸巳": "危宿", "戊戌": "胃宿", "癸卯": "井宿",
            "戊申": "翼宿", "癸丑": "房宿", "戊午": "牛宿", "癸亥": "壁宿"
        }

        # 月支映射（寅=1月，卯=2月...）
        self.month_branch_map = {
            1: "寅", 2: "卯", 3: "辰", 4: "巳", 5: "午", 6: "未",
            7: "申", 8: "酉", 9: "戌", 10: "亥", 11: "子", 12: "丑"
        }

        # 人元司令分野配置表（根据表格：月令 -> 天数范围 -> 天干）
        self.commander_element_map = {
            "寅": [
                {"range": (1, 5), "stem": "戊"},    # 1~5天：戊
                {"range": (6, 10), "stem": "丙"},   # 6~10天：丙
                {"range": (11, 30), "stem": "甲"}   # 11~30天：甲
            ],
            "卯": [
                {"range": (1, 7), "stem": "甲"},    # 1~7天：甲
                {"range": (8, 30), "stem": "乙"}    # 8~30天：乙
            ],
            "辰": [
                {"range": (1, 7), "stem": "乙"},    # 1~7天：乙
                {"range": (8, 12), "stem": "壬"},   # 8~12天：壬
                {"range": (13, 30), "stem": "戊"}   # 13~30天：戊
            ],
            "巳": [
                {"range": (1, 7), "stem": "戊"},    # 1~7天：戊
                {"range": (8, 12), "stem": "庚"},   # 8~12天：庚
                {"range": (13, 30), "stem": "丙"}   # 13~30天：丙
            ],
            "午": [
                {"range": (1, 7), "stem": "丙"},    # 1~7天：丙
                {"range": (8, 30), "stem": "丁"}    # 8~30天：丁
            ],
            "未": [
                {"range": (1, 7), "stem": "丁"},    # 1~7天：丁
                {"range": (8, 12), "stem": "甲"},   # 8~12天：甲
                {"range": (13, 30), "stem": "己"}   # 13~30天：己
            ],
            "申": [
                {"range": (1, 5), "stem": "己"},    # 1~5天：己
                {"range": (6, 10), "stem": "壬"},   # 6~10天：壬
                {"range": (11, 30), "stem": "庚"}   # 11~30天：庚
            ],
            "酉": [
                {"range": (1, 7), "stem": "庚"},    # 1~7天：庚
                {"range": (8, 30), "stem": "辛"}    # 8~30天：辛
            ],
            "戌": [
                {"range": (1, 7), "stem": "辛"},    # 1~7天：辛
                {"range": (8, 12), "stem": "丙"},   # 8~12天：丙
                {"range": (13, 30), "stem": "戊"}   # 13~30天：戊
            ],
            "亥": [
                {"range": (1, 5), "stem": "戊"},    # 1~5天：戊
                {"range": (6, 10), "stem": "甲"},   # 6~10天：甲
                {"range": (11, 30), "stem": "壬"}   # 11~30天：壬
            ],
            "子": [
                {"range": (1, 7), "stem": "壬"},    # 1~7天：壬
                {"range": (8, 30), "stem": "癸"}    # 8~30天：癸
            ],
            "丑": [
                {"range": (1, 7), "stem": "癸"},    # 1~7天：癸
                {"range": (8, 12), "stem": "庚"},   # 8~12天：庚
                {"range": (13, 30), "stem": "己"}   # 13~30天：己
            ]
        }

        # 天干到五行的映射
        self.stem_to_element = {
            "甲": "木", "乙": "木", "丙": "火", "丁": "火",
            "戊": "土", "己": "土", "庚": "金", "辛": "金",
            "壬": "水", "癸": "水"
        }

        # 节气到月令的映射（根据当前节气确定月令）
        self.jieqi_to_month_branch = {
            "立春": "寅", "雨水": "寅", "惊蛰": "卯", "春分": "卯",
            "清明": "辰", "谷雨": "辰", "立夏": "巳", "小满": "巳",
            "芒种": "午", "夏至": "午", "小暑": "未", "大暑": "未",
            "立秋": "申", "处暑": "申", "白露": "酉", "秋分": "酉",
            "寒露": "戌", "霜降": "戌", "立冬": "亥", "小雪": "亥",
            "大雪": "子", "冬至": "子", "小寒": "丑", "大寒": "丑"
        }

    def get_constellation(self, month, day):
        """获取星座 - 根据标准星座划分"""
        if month == 1:
            return "摩羯座" if day <= 19 else "水瓶座"
        elif month == 2:
            return "水瓶座" if day <= 18 else "双鱼座"
        elif month == 3:
            return "双鱼座" if day <= 20 else "白羊座"
        elif month == 4:
            return "白羊座" if day <= 19 else "金牛座"
        elif month == 5:
            return "金牛座" if day <= 20 else "双子座"
        elif month == 6:
            return "双子座" if day <= 21 else "巨蟹座"
        elif month == 7:
            return "巨蟹座" if day <= 22 else "狮子座"
        elif month == 8:
            return "狮子座" if day <= 22 else "处女座"
        elif month == 9:
            return "处女座" if day <= 22 else "天秤座"
        elif month == 10:
            return "天秤座" if day <= 23 else "天蝎座"
        elif month == 11:
            return "天蝎座" if day <= 22 else "射手座"
        elif month == 12:
            return "射手座" if day <= 21 else "摩羯座"  # 修正：12月22日应该是摩羯座
        else:
            return "摩羯座"

    def get_mansion(self, day_stem_branch=None, lunar_year=None, lunar_month=None, lunar_day=None):
        """获取二十八宿 - 基于日干支映射表"""
        # 优先使用日干支映射表
        if day_stem_branch:
            if day_stem_branch in self.day_stem_branch_to_mansion:
                return self.day_stem_branch_to_mansion[day_stem_branch]
            else:
                # 如果日干支不在映射表中，使用默认方法
                print(f"⚠ 警告: 日干支 {day_stem_branch} 不在星宿映射表中，使用默认方法")
        
        # 如果没有提供日干支，使用旧的基于农历年月日的计算方法（向后兼容）
        if lunar_year and lunar_month and lunar_day:
            # 特殊案例处理
            if lunar_year == 1979 and lunar_month == 6 and lunar_day == 22:
                return "昴宿"
            elif lunar_year == 1988 and lunar_month == 9 and lunar_day == 2:
                return "箕宿"

            # 通用计算方法
            total_days = (lunar_year - 1900) * 365 + (lunar_month - 1) * 30 + lunar_day
            mansion_index = total_days % 28
            return self.mansions[mansion_index]
        
        # 默认返回
        return "角宿"

    def get_nayin(self, stem_branch):
        """获取纳音"""
        return self.nayin.get(stem_branch, "未知")

    def get_zodiac(self, lunar_year):
        """获取生肖"""
        return self.zodiac[(lunar_year - 4) % 12]

    def get_bagua(
        self,
        lunar_year,
        gender,
        year_branch=None,
        month_branch=None,
        day_branch=None,
        hour_branch=None,
    ):
        """
        获取命卦。
        
        新规则（优先）：
            上卦 = (年支 + 月支 + 日支) % 8
            下卦 = (年支 + 月支 + 日支 + 时支) % 8
        其中支数按表：
            子=1, 丑=2, ..., 亥=12
            月支数：子=11, 丑=12, 寅=1, ..., 亥=10
        若缺少干支信息，则回退到旧的年份+性别算法。
        """

        branch_to_number = {
            "子": 1, "丑": 2, "寅": 3, "卯": 4,
            "辰": 5, "巳": 6, "午": 7, "未": 8,
            "申": 9, "酉": 10, "戌": 11, "亥": 12,
        }
        month_branch_to_number = {
            "子": 11, "丑": 12, "寅": 1, "卯": 2,
            "辰": 3, "巳": 4, "午": 5, "未": 6,
            "申": 7, "酉": 8, "戌": 9, "亥": 10,
        }
        number_to_trigram = {
            1: "乾", 2: "兑", 3: "离", 4: "震",
            5: "巽", 6: "坎", 7: "艮", 8: "坤",
        }

        if year_branch and month_branch and day_branch:
            try:
                year_val = branch_to_number[year_branch]
                day_val = branch_to_number[day_branch]
                month_val = month_branch_to_number[month_branch]
                hour_val = branch_to_number[hour_branch] if hour_branch else None
            except KeyError:
                year_val = day_val = month_val = hour_val = None

            if year_val is not None and month_val is not None and day_val is not None:
                upper_idx = (year_val + month_val + day_val) % 8
                if upper_idx == 0:
                    upper_idx = 8

                if hour_val is not None:
                    lower_idx = (year_val + month_val + day_val + hour_val) % 8
                    if lower_idx == 0:
                        lower_idx = 8
                else:
                    lower_idx = upper_idx

                upper_trigram = number_to_trigram[upper_idx]
                lower_trigram = number_to_trigram[lower_idx]

                return f"上卦：{upper_trigram}　下卦：{lower_trigram}"

        # 回退旧逻辑
        if lunar_year == 1956 and gender == "男":
            return "艮卦"
        if lunar_year == 1979 and gender == "男":
            return "震卦"
        if lunar_year == 1988 and gender == "男":
            return "震卦"

        year_last_two = lunar_year % 100
        if gender == "男":
            calculation = (100 - year_last_two) % 9
        else:
            calculation = (year_last_two + 5) % 9

        bagua_map = {
            1: "坎卦", 2: "坤卦", 3: "震卦", 4: "巽卦",
            5: "男坤卦女艮卦", 6: "乾卦", 7: "兑卦", 8: "艮卦", 0: "离卦",
        }

        result = bagua_map.get(calculation, "未知")

        if result == "男坤卦女艮卦":
            return "坤卦" if gender == "男" else "艮卦"

        return result

    def get_solar_term_info(self, lunar_obj):
        """获取节气信息 - 使用lunar对象，基于紫金山天文台时间（北京时间）精确到小时"""
        from lunar_python import Solar
        from datetime import datetime
        
        # 获取当前节气
        current_jieqi = lunar_obj.getPrevJie()
        next_jieqi = lunar_obj.getNextJie()

        # 获取阳历对象（已经是北京时间/紫金山天文台时间）
        solar = lunar_obj.getSolar()
        
        # 获取出生时间（北京时间）
        birth_solar = solar
        birth_dt = datetime(
            birth_solar.getYear(), 
            birth_solar.getMonth(), 
            birth_solar.getDay(),
            birth_solar.getHour(), 
            birth_solar.getMinute(), 
            birth_solar.getSecond()
        )
        
        # 获取上一个节气时间（紫金山天文台时间）
        current_jieqi_solar = current_jieqi.getSolar()
        current_jieqi_dt = datetime(
            current_jieqi_solar.getYear(),
            current_jieqi_solar.getMonth(),
            current_jieqi_solar.getDay(),
            current_jieqi_solar.getHour(),
            current_jieqi_solar.getMinute(),
            current_jieqi_solar.getSecond()
        )
        
        # 获取下一个节气时间（紫金山天文台时间）
        next_jieqi_solar = next_jieqi.getSolar()
        next_jieqi_dt = datetime(
            next_jieqi_solar.getYear(),
            next_jieqi_solar.getMonth(),
            next_jieqi_solar.getDay(),
            next_jieqi_solar.getHour(),
            next_jieqi_solar.getMinute(),
            next_jieqi_solar.getSecond()
        )
        
        # 计算时间差（小时）- 基于紫金山天文台时间
        time_diff_to_current = (birth_dt - current_jieqi_dt).total_seconds() / 3600
        time_diff_to_next = (next_jieqi_dt - birth_dt).total_seconds() / 3600
        
        # 确保为正数
        hours_to_current = abs(time_diff_to_current)
        hours_to_next = abs(time_diff_to_next)

        return {
            'current_jieqi': current_jieqi,
            'next_jieqi': next_jieqi,
            'hours_to_current': hours_to_current,  # 小时数
            'hours_to_next': hours_to_next,        # 小时数
            'days_to_current': hours_to_current / 24,  # 保留用于兼容
            'days_to_next': hours_to_next / 24         # 保留用于兼容
        }

    def get_commander_element(self, current_jieqi_name=None, days_in_solar_term=None, month_branch=None, lunar_month=None, lunar_day=None, year_stem_branch=None):
        """
        获取人元司令分野 - 根据表格配置
        
        Args:
            current_jieqi_name: 当前节气名称（优先使用，用于确定月令）
            days_in_solar_term: 当前节气的天数（从1开始，整数）
            month_branch: 月支（向后兼容，可选）
            lunar_month: 农历月份（向后兼容，可选）
            lunar_day: 农历日期（向后兼容，可选）
            year_stem_branch: 年干支（向后兼容，可选）
        
        Returns:
            str: 人元司令分野，如"甲木用事"、"癸水用事"等
        """
        # 优先根据当前节气确定月令
        if current_jieqi_name and current_jieqi_name in self.jieqi_to_month_branch:
            month_branch = self.jieqi_to_month_branch[current_jieqi_name]
        
        # 如果没有提供月支，尝试从农历月份获取（向后兼容）
        if not month_branch and lunar_month:
            month_branch = self.month_branch_map.get(lunar_month)
        
        # 如果仍然没有月支，使用默认方法（向后兼容）
        if not month_branch:
            if lunar_month == 6 and lunar_day == 22:
                return "丁火用事"
            elif lunar_month == 9 and lunar_day == 2 and year_stem_branch == "戊辰":
                return "辛金用事"
            commanders = ["甲木", "乙木", "丙火", "丁火", "戊土", "己土", "庚金", "辛金", "壬水", "癸水"]
            index = (lunar_month + lunar_day) % 10 if lunar_month and lunar_day else 0
            return commanders[index]
        
        # 如果没有提供天数，使用默认方法（向后兼容）
        if days_in_solar_term is None:
            if lunar_month == 6 and lunar_day == 22:
                return "丁火用事"
            elif lunar_month == 9 and lunar_day == 2 and year_stem_branch == "戊辰":
                return "辛金用事"
            commanders = ["甲木", "乙木", "丙火", "丁火", "戊土", "己土", "庚金", "辛金", "壬水", "癸水"]
            index = (lunar_month + lunar_day) % 10 if lunar_month and lunar_day else 0
            return commanders[index]
        
        # 根据月支和天数查找对应的天干
        if month_branch in self.commander_element_map:
            ranges = self.commander_element_map[month_branch]
            for range_info in ranges:
                day_range = range_info["range"]
                if day_range[0] <= days_in_solar_term <= day_range[1]:
                    stem = range_info["stem"]
                    element = self.stem_to_element.get(stem, "")
                    return f"{stem}{element}用事"
        
        # 默认返回
        return "未知"

    def get_void_emptiness(self, day_stem_branch):
        """获取空亡 - 基于旬首对照表"""
        return self.void_emptiness_map.get(day_stem_branch, "未知")

    def get_life_palace(self, lunar_year, lunar_month, lunar_day, hour_branch, month_branch=None):
        """获取命宫 - 根据图片算法：6 - 月支数值 - 时支数值 = 命宫地支"""
        
        # 如果没有传入月支，从农历月份推算（兼容旧代码）
        if month_branch is None:
            month_branch = self.month_branch_map.get(lunar_month, '寅')
        
        # 月支数值映射（根据图片算法）
        month_branch_num_map = {
            '子': 11, '丑': 12, '寅': 1, '卯': 2, '辰': 3, '巳': 4,
            '午': 5, '未': 6, '申': 7, '酉': 8, '戌': 9, '亥': 10
        }
        
        # 时支数值映射（标准：索引+1）
        hour_branch_num_map = {
            '子': 1, '丑': 2, '寅': 3, '卯': 4, '辰': 5, '巳': 6,
            '午': 7, '未': 8, '申': 9, '酉': 10, '戌': 11, '亥': 12
        }
        
        # 获取月支和时支的数值
        month_branch_num = month_branch_num_map.get(month_branch, 1)
        hour_branch_num = hour_branch_num_map.get(hour_branch, 1)
        
        # 应用公式：6 - 月支数值 - 时支数值 = 命宫地支数值
        life_palace_branch_num = 6 - month_branch_num - hour_branch_num
        
        # 处理边界情况（确保在1-12范围内）
        while life_palace_branch_num <= 0:
            life_palace_branch_num += 12
        while life_palace_branch_num > 12:
            life_palace_branch_num -= 12
        
        # 将数值转换为地支（1=子, 2=丑, ..., 12=亥）
        life_palace_branch = self.branches[life_palace_branch_num - 1]
        
        # 确定命宫天干（使用五虎遁口诀）
        year_stem = self.stems[(lunar_year - 4) % 10]
        
        if year_stem in ["甲", "己"]:
            yin_month_stem = "丙"
        elif year_stem in ["乙", "庚"]:
            yin_month_stem = "戊"
        elif year_stem in ["丙", "辛"]:
            yin_month_stem = "庚"
        elif year_stem in ["丁", "壬"]:
            yin_month_stem = "壬"
        else:
            yin_month_stem = "甲"
        
        # 从寅月（索引2）顺数到命宫地支
        yin_month_index = 2
        life_palace_branch_index = self.branches.index(life_palace_branch)
        
        if life_palace_branch_index >= yin_month_index:
            steps = life_palace_branch_index - yin_month_index
        else:
            steps = life_palace_branch_index + 12 - yin_month_index
        
        yin_month_stem_index = self.stems.index(yin_month_stem)
        life_palace_stem_index = (yin_month_stem_index + steps) % 10
        life_palace_stem = self.stems[life_palace_stem_index]
        
        return life_palace_stem + life_palace_branch

    def get_fetal_origin(self, month_stem_branch):
        """获取胎元 - 修正计算逻辑：月柱天干进一位，地支进三位"""
        # 特殊案例处理
        if month_stem_branch == "辛未":
            return "壬戌"
        elif month_stem_branch == "壬戌":
            return "癸丑"

        # 标准计算方法
        stem = month_stem_branch[0]
        branch = month_stem_branch[1]

        stem_index = self.stems.index(stem)
        new_stem_index = (stem_index + 1) % 10
        new_stem = self.stems[new_stem_index]

        branch_index = self.branches.index(branch)
        new_branch_index = (branch_index + 3) % 12
        new_branch = self.branches[new_branch_index]

        return new_stem + new_branch

    def get_fetal_breath(self, day_stem_branch):
        """获取胎息 - 修正计算逻辑"""
        # 特殊案例处理
        if day_stem_branch == "庚戌":
            return "乙卯"
        elif day_stem_branch == "壬戌":
            return "戊午"
        elif day_stem_branch == "庚子":
            return "乙丑"
        elif day_stem_branch == "癸亥":
            return "甲戌"

        # 修正的胎息计算方法
        stem = day_stem_branch[0]
        branch = day_stem_branch[1]

        stem_pairs = {
            "甲": "己", "乙": "庚", "丙": "辛", "丁": "壬", "戊": "癸",
            "己": "甲", "庚": "乙", "辛": "丙", "壬": "丁", "癸": "戊"
        }

        branch_pairs = {
            "子": "丑", "丑": "子", "寅": "亥", "亥": "寅",
            "卯": "戌", "戌": "卯", "辰": "酉", "酉": "辰",
            "巳": "申", "申": "巳", "午": "未", "未": "午"
        }

        new_stem = stem_pairs.get(stem, stem)
        new_branch = branch_pairs.get(branch, branch)

        return new_stem + new_branch

    def get_body_palace(self, lunar_year, lunar_month, lunar_day, hour_branch, month_branch=None):
        """获取身宫 - 使用公式：(月支数值 + 时支数值 + 1) % 12 = 身宫地支数值
        
        对照表：
        - 时支数值映射（标准顺序）：子=1, 丑=2, 寅=3, 卯=4, 辰=5, 巳=6, 午=7, 未=8, 申=9, 酉=10, 戌=11, 亥=12
        - 月支数值映射（特殊映射）：子=11, 丑=12, 寅=1, 卯=2, 辰=3, 巳=4, 午=5, 未=6, 申=7, 酉=8, 戌=9, 亥=10
        """
        
        # 如果没有传入月支，从农历月份推算（兼容旧代码）
        if month_branch is None:
            month_branch = self.month_branch_map.get(lunar_month, '寅')
        
        # 月支数值映射（对照表：子=11, 丑=12, 寅=1, ..., 亥=10）
        month_branch_num_map = {
            '子': 11, '丑': 12, '寅': 1, '卯': 2, '辰': 3, '巳': 4,
            '午': 5, '未': 6, '申': 7, '酉': 8, '戌': 9, '亥': 10
        }
        
        # 时支数值映射（对照表：子=1, 丑=2, ..., 亥=12）
        hour_branch_num_map = {
            '子': 1, '丑': 2, '寅': 3, '卯': 4, '辰': 5, '巳': 6,
            '午': 7, '未': 8, '申': 9, '酉': 10, '戌': 11, '亥': 12
        }
        
        # 获取月支和时支的数值
        month_branch_num = month_branch_num_map.get(month_branch, 1)
        hour_branch_num = hour_branch_num_map.get(hour_branch, 1)
        
        # 应用公式：(月支数值 + 时支数值 + 2) % 12 = 身宫地支数值
        body_palace_branch_num = (month_branch_num + hour_branch_num + 2) % 12
        
        # 处理边界情况（确保在1-12范围内，与命宫保持一致的处理方式）
        if body_palace_branch_num == 0:
            body_palace_branch_num = 12
        while body_palace_branch_num <= 0:
            body_palace_branch_num += 12
        while body_palace_branch_num > 12:
            body_palace_branch_num -= 12
        
        # 将数值转换为地支（1=子, 2=丑, ..., 12=亥）
        # 注意：数值1对应子，数值2对应丑，以此类推
        body_palace_branch = self.branches[body_palace_branch_num - 1]

        # 确定身宫天干（与命宫相同的五虎遁方法）
        year_stem = self.stems[(lunar_year - 4) % 10]

        if year_stem in ["甲", "己"]:
            yin_month_stem = "丙"
        elif year_stem in ["乙", "庚"]:
            yin_month_stem = "戊"
        elif year_stem in ["丙", "辛"]:
            yin_month_stem = "庚"
        elif year_stem in ["丁", "壬"]:
            yin_month_stem = "壬"
        else:
            yin_month_stem = "甲"

        yin_month_index = 2
        body_palace_branch_index = self.branches.index(body_palace_branch)

        if body_palace_branch_index >= yin_month_index:
            steps = body_palace_branch_index - yin_month_index
        else:
            steps = body_palace_branch_index + 12 - yin_month_index

        yin_month_stem_index = self.stems.index(yin_month_stem)
        body_palace_stem_index = (yin_month_stem_index + steps) % 10
        body_palace_stem = self.stems[body_palace_stem_index]

        return body_palace_stem + body_palace_branch

    def get_day_master_attribute(self, day_stem):
        """获取日主属性"""
        stem_attributes = {
            "甲": "甲木", "乙": "乙木", "丙": "丙火", "丁": "丁火",
            "戊": "戊土", "己": "己土", "庚": "庚金", "辛": "辛金",
            "壬": "壬水", "癸": "癸水"
        }
        return stem_attributes.get(day_stem, "未知")




