#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字界面信息生成器 - 重构版
使用 tool/LunarConverter 进行公历转农历
使用 analyzers/bazi_interface_analyzer 进行逻辑计算
使用 printer/bazi_interface_printer 进行输出
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.tool.LunarConverter import LunarConverter
from src.analyzers.bazi_interface_analyzer import BaziInterfaceAnalyzer
from src.printer.bazi_interface_printer import BaziInterfacePrinter


class BaziInterfaceGenerator:
    """八字界面信息生成器 - 重构版"""
    
    def __init__(self):
        self.lunar_converter = LunarConverter()
        self.analyzer = BaziInterfaceAnalyzer()
        self.printer = BaziInterfacePrinter()

    def _fetch_bazi_core(self, birth_date: str, birth_time: str, gender: str):
        """尝试通过 bazi-core-service 获取排盘结果（已禁用，直接使用本地算法）"""
        # 直接返回 None，使用本地算法（避免 gRPC 调用阻塞）
        return None

    def generate_interface_info(self, name, gender, birth_date_str, birth_time_str,
                                latitude=39.00, longitude=120.00, location="未知地"):
        """
        生成八字界面信息

        Args:
            name: 姓名
            gender: 性别 (male/female 或 男/女)
            birth_date_str: 出生日期 (YYYY-MM-DD)
            birth_time_str: 出生时间 (HH:MM)
            latitude: 纬度
            longitude: 经度
            location: 出生地点

        Returns:
            dict: 包含所有界面信息的字典（JSON格式）
        """
        # 转换性别格式：支持 "male"/"female" 和 "男"/"女"
        gender_normalized = gender
        if gender in ["male", "男"]:
            gender_normalized = "male"
            gender_chinese = "男"
        elif gender in ["female", "女"]:
            gender_normalized = "female"
            gender_chinese = "女"
        else:
            gender_chinese = gender  # 如果已经是中文或其他格式，保持原样
        
        core_result = self._fetch_bazi_core(birth_date_str, birth_time_str, gender_normalized)
        if core_result:
            basic_info = core_result.get('basic_info', {})
            if not isinstance(basic_info, dict):
                basic_info = {}
            lunar_date = basic_info.get('lunar_date', {})
            if not isinstance(lunar_date, dict):
                lunar_date = {}
            bazi_pillars = core_result.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
        else:
            lunar_result = self.lunar_converter.solar_to_lunar(birth_date_str, birth_time_str)
            lunar_date = lunar_result.get('lunar_date', {})
            if not isinstance(lunar_date, dict):
                lunar_date = {}
            bazi_pillars = lunar_result.get('bazi_pillars', {})
            if not isinstance(bazi_pillars, dict):
                bazi_pillars = {}
        
        lunar_year = lunar_date.get('year', '')
        lunar_month = lunar_date.get('month', '')
        lunar_day = lunar_date.get('day', '')
        lunar_month_name = lunar_date.get('month_name', '')
        lunar_day_name = lunar_date.get('day_name', '')
        
        # 安全地获取八字四柱
        year_pillar = bazi_pillars.get('year', {})
        month_pillar = bazi_pillars.get('month', {})
        day_pillar = bazi_pillars.get('day', {})
        hour_pillar = bazi_pillars.get('hour', {})
        
        if not isinstance(year_pillar, dict):
            year_pillar = {}
        if not isinstance(month_pillar, dict):
            month_pillar = {}
        if not isinstance(day_pillar, dict):
            day_pillar = {}
        if not isinstance(hour_pillar, dict):
            hour_pillar = {}
        
        year_stem = year_pillar.get('stem', '')
        year_branch = year_pillar.get('branch', '')
        month_stem = month_pillar.get('stem', '')
        month_branch = month_pillar.get('branch', '')
        day_stem = day_pillar.get('stem', '')
        day_branch = day_pillar.get('branch', '')
        hour_stem = hour_pillar.get('stem', '')
        hour_branch = hour_pillar.get('branch', '')
        
        year_stem_branch = year_stem + year_branch
        month_stem_branch = month_stem + month_branch
        day_stem_branch = day_stem + day_branch
        hour_stem_branch = hour_stem + hour_branch
        
        # 获取时支（用于命宫、身宫计算）
        hour_branch_char = hour_branch
        
        # 使用 lunar_python 获取更多信息（节气等）
        from lunar_python import Solar
        year, month, day = map(int, birth_date_str.split('-'))
        hour, minute = map(int, birth_time_str.split(':'))
        solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
        lunar = solar.getLunar()

        # 使用 analyzer 进行各种计算
        # 星座（使用公历）
        constellation = self.analyzer.get_constellation(month, day)
        
        # 生肖
        zodiac = self.analyzer.get_zodiac(lunar_year)

        # 二十八宿（基于日干支）
        mansion = self.analyzer.get_mansion(day_stem_branch=day_stem_branch)
        
        # 命卦
        bagua = self.analyzer.get_bagua(lunar_year, gender_chinese)

        # 节气信息
        solar_term_info = self.analyzer.get_solar_term_info(lunar)
        if not isinstance(solar_term_info, dict):
            solar_term_info = {}
        
        current_jieqi = solar_term_info.get('current_jieqi')
        next_jieqi = solar_term_info.get('next_jieqi')
        
        if current_jieqi:
            current_jieqi_name = current_jieqi.getName()
            current_jieqi_solar = current_jieqi.getSolar()
            current_jieqi_time = current_jieqi_solar.toYmdHms() if current_jieqi_solar else ''
        else:
            current_jieqi_name = ''
            current_jieqi_time = ''
        
        if next_jieqi:
            next_jieqi_name = next_jieqi.getName()
            next_jieqi_solar = next_jieqi.getSolar()
            next_jieqi_time = next_jieqi_solar.toYmdHms() if next_jieqi_solar else ''
        else:
            next_jieqi_name = ''
            next_jieqi_time = ''
        
        hours_to_current = solar_term_info.get('hours_to_current', 0)  # 小时数
        hours_to_next = solar_term_info.get('hours_to_next', 0)        # 小时数
        days_to_current = solar_term_info.get('days_to_current', hours_to_current / 24 if hours_to_current else 0)
        days_to_next = solar_term_info.get('days_to_next', hours_to_next / 24 if hours_to_next else 0)
        
        # 人元司令分野（根据当前节气和当前节气的天数）
        # 计算当前节气的天数（从1开始，整数）
        # days_to_current 是从当前节气到出生时间的天数，需要转换为出生时间在当前节气的第几天
        # 如果 days_to_current = 14.875，表示出生时间在当前节气后14.875天，即第15天（从1开始计数）
        days_in_solar_term = int(days_to_current) + 1  # 从1开始计数
        commander = self.analyzer.get_commander_element(
            current_jieqi_name=current_jieqi_name,
            days_in_solar_term=days_in_solar_term,
            month_branch=month_branch,
            lunar_month=lunar_month,
            lunar_day=lunar_day,
            year_stem_branch=year_stem_branch
        )
        
        # 空亡
        void_emptiness = self.analyzer.get_void_emptiness(day_stem_branch)
        
        # 命宫
        life_palace = self.analyzer.get_life_palace(lunar_year, lunar_month, lunar_day, hour_branch_char, month_branch)
        life_palace_nayin = self.analyzer.get_nayin(life_palace)
        
        # 身宫
        body_palace = self.analyzer.get_body_palace(lunar_year, lunar_month, lunar_day, hour_branch_char, month_branch)
        body_palace_nayin = self.analyzer.get_nayin(body_palace)
        
        # 胎元
        fetal_origin = self.analyzer.get_fetal_origin(month_stem_branch)
        fetal_origin_nayin = self.analyzer.get_nayin(fetal_origin)
        
        # 胎息
        fetal_breath = self.analyzer.get_fetal_breath(day_stem_branch)
        fetal_breath_nayin = self.analyzer.get_nayin(fetal_breath)
        
        # 日主属性
        day_master = self.analyzer.get_day_master_attribute(day_stem)
        
        # 构建完整数据
        interface_data = {
            "name": name,
            "gender": gender_chinese,
            "solar_date": birth_date_str,
            "solar_time": birth_time_str,
            "lunar_date": f"{lunar_year}年{lunar_month_name}{lunar_day_name}",
            "lunar_date_info": lunar_date,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
            "year_stem_branch": year_stem_branch,
            "month_stem_branch": month_stem_branch,
            "day_stem_branch": day_stem_branch,
            "hour_stem_branch": hour_stem_branch,
            "hour_branch": hour_branch_char,
            "zodiac": zodiac,
            "constellation": constellation,
            "mansion": mansion,
            "bagua": bagua,
            "life_palace": life_palace,
            "life_palace_nayin": life_palace_nayin,
            "body_palace": body_palace,
            "body_palace_nayin": body_palace_nayin,
            "fetal_origin": fetal_origin,
            "fetal_origin_nayin": fetal_origin_nayin,
            "fetal_breath": fetal_breath,
            "fetal_breath_nayin": fetal_breath_nayin,
            "commander": commander,
            "void_emptiness": void_emptiness,
            "day_master": day_master,
            "current_jieqi_name": current_jieqi_name,
            "current_jieqi_time": current_jieqi_time,
            "next_jieqi_name": next_jieqi_name,
            "next_jieqi_time": next_jieqi_time,
            "hours_to_current": hours_to_current,  # 小时数
            "hours_to_next": hours_to_next,        # 小时数
            "days_to_current": days_to_current,
            "days_to_next": days_to_next
        }
        
        # 使用 printer 生成格式化文本
        formatted_text = self.printer.print_formatted_text(interface_data)
        interface_data["formatted_text"] = formatted_text
        
        # 使用 printer 格式化输出
        result = self.printer.format_interface_info(interface_data)

        return result

    def generate_json_output(self, name, gender, birth_date_str, birth_time_str,
                            latitude=39.00, longitude=120.00, location="未知地"):
        """
        生成 JSON 格式的输出
        
        Args:
            参数同 generate_interface_info
        
        Returns:
            str: JSON 字符串
        """
        result = self.generate_interface_info(
            name, gender, birth_date_str, birth_time_str,
            latitude, longitude, location
        )
        return self.printer.format_to_json(result, indent=2)
    
    def print_interface_info(self, result):
        """打印界面信息 - 兼容原有方法"""
        formatted_text = result.get("formatted_text", {})
        if formatted_text:
            for key, value in formatted_text.items():
                print(value)
        else:
            # 如果没有格式化文本，直接打印 JSON
            self.printer.print_json(result)


def main():
    """主函数 - 可直接执行，参数可在代码中修改"""
    import argparse
    
    # ========== 可在此处直接修改默认参数 ==========
    DEFAULT_NAME = "测试用户"
    DEFAULT_GENDER = "male"  # male/female 或 男/女
    DEFAULT_DATE = "1986-05-05"  # 出生日期 (YYYY-MM-DD)
    DEFAULT_TIME = "12:30"  # 出生时间 (HH:MM)
    DEFAULT_LOCATION = "北京"  # 出生地点
    DEFAULT_LATITUDE = 39.90  # 纬度
    DEFAULT_LONGITUDE = 116.40  # 经度
    DEFAULT_OUTPUT_JSON = False  # 是否输出 JSON 格式
    # ============================================
    
    parser = argparse.ArgumentParser(
        description="八字界面信息生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 使用默认参数
  python bazi_interface_generator.py
  
  # 使用命令行参数
  python bazi_interface_generator.py --date 1990-05-15 --time 14:30 --gender male
  
  # 输出 JSON 格式
  python bazi_interface_generator.py --date 1990-05-15 --time 14:30 --json
        """
    )
    
    parser.add_argument("--name", default=DEFAULT_NAME, 
                       help=f"姓名 (默认: {DEFAULT_NAME})")
    parser.add_argument("--gender", default=DEFAULT_GENDER, 
                       choices=["male", "female", "男", "女"],
                       help=f"性别 (默认: {DEFAULT_GENDER})")
    parser.add_argument("--date", default=DEFAULT_DATE,
                       help=f"出生日期 YYYY-MM-DD (默认: {DEFAULT_DATE})")
    parser.add_argument("--time", default=DEFAULT_TIME,
                       help=f"出生时间 HH:MM (默认: {DEFAULT_TIME})")
    parser.add_argument("--location", default=DEFAULT_LOCATION,
                       help=f"出生地点 (默认: {DEFAULT_LOCATION})")
    parser.add_argument("--latitude", type=float, default=DEFAULT_LATITUDE,
                       help=f"纬度 (默认: {DEFAULT_LATITUDE})")
    parser.add_argument("--longitude", type=float, default=DEFAULT_LONGITUDE,
                       help=f"经度 (默认: {DEFAULT_LONGITUDE})")
    parser.add_argument("--json", action="store_true", default=DEFAULT_OUTPUT_JSON,
                       help="输出 JSON 格式 (默认: False)")
    
    args = parser.parse_args()

    generator = BaziInterfaceGenerator()

    try:
        print("=" * 60)
        print("八字界面信息生成器")
        print("=" * 60)
        print(f"姓名: {args.name}")
        print(f"性别: {args.gender}")
        print(f"出生日期: {args.date}")
        print(f"出生时间: {args.time}")
        print(f"出生地点: {args.location}")
        print(f"坐标: ({args.latitude}, {args.longitude})")
        print("=" * 60)
        print()
        
        result = generator.generate_interface_info(
            args.name, 
            args.gender, 
            args.date, 
            args.time,
            args.latitude,
            args.longitude,
            args.location
        )

        if args.json:
            print("JSON 格式输出:")
            print("=" * 60)
            print(generator.printer.format_to_json(result))
        else:
            print("格式化文本输出:")
            print("=" * 60)
        generator.print_interface_info(result)

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

