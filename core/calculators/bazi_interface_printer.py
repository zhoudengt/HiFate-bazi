#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字界面信息打印器
负责将分析结果格式化为 JSON 输出
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BaziInterfacePrinter:
    """八字界面信息打印器 - 负责格式化输出"""
    
    @staticmethod
    def format_to_json(data: Dict[str, Any], indent: int = 2) -> str:
        """
        将数据格式化为 JSON 字符串
        
        Args:
            data: 要格式化的数据字典
            indent: JSON 缩进空格数
        
        Returns:
            str: JSON 字符串
        """
        return json.dumps(data, ensure_ascii=False, indent=indent)
    
    @staticmethod
    def format_interface_info(interface_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化八字界面信息为结构化 JSON
        
        Args:
            interface_data: 包含所有界面信息的字典
        
        Returns:
            dict: 格式化后的 JSON 结构
        """
        # 获取命造类型，如果没有则根据性别计算
        mingzao_type = interface_data.get("mingzao_type", "")
        if not mingzao_type:
            gender = interface_data.get("gender", "")
            if gender in ["male", "男"]:
                mingzao_type = "阳 乾造"
            elif gender in ["female", "女"]:
                mingzao_type = "阴 坤造"
            else:
                mingzao_type = "未知"
        
        return {
            "basic_info": {
                "name": interface_data.get("name", ""),
                "gender": interface_data.get("gender", ""),
                "mingzao_type": mingzao_type,
                "solar_date": interface_data.get("solar_date", ""),
                "solar_time": interface_data.get("solar_time", ""),
                "lunar_date": interface_data.get("lunar_date", ""),
                "location": interface_data.get("location", ""),
                "latitude": interface_data.get("latitude", 0),
                "longitude": interface_data.get("longitude", 0)
            },
            "bazi_pillars": {
                "year": interface_data.get("year_stem_branch", ""),
                "month": interface_data.get("month_stem_branch", ""),
                "day": interface_data.get("day_stem_branch", ""),
                "hour": interface_data.get("hour_stem_branch", "")
            },
            "astrology": {
                "zodiac": interface_data.get("zodiac", ""),
                "constellation": interface_data.get("constellation", ""),
                "mansion": interface_data.get("mansion", ""),
                "bagua": interface_data.get("bagua", "")
            },
            "palaces": {
                "life_palace": {
                    "ganzhi": interface_data.get("life_palace", ""),
                    "nayin": interface_data.get("life_palace_nayin", "")
                },
                "body_palace": {
                    "ganzhi": interface_data.get("body_palace", ""),
                    "nayin": interface_data.get("body_palace_nayin", "")
                },
                "fetal_origin": {
                    "ganzhi": interface_data.get("fetal_origin", ""),
                    "nayin": interface_data.get("fetal_origin_nayin", "")
                },
                "fetal_breath": {
                    "ganzhi": interface_data.get("fetal_breath", ""),
                    "nayin": interface_data.get("fetal_breath_nayin", "")
                }
            },
            "solar_terms": {
                "current_jieqi": interface_data.get("current_jieqi_name", ""),
                "current_jieqi_time": interface_data.get("current_jieqi_time", ""),
                "next_jieqi": interface_data.get("next_jieqi_name", ""),
                "next_jieqi_time": interface_data.get("next_jieqi_time", ""),
                "days_to_current": interface_data.get("days_to_current", 0),
                "days_to_next": interface_data.get("days_to_next", 0)
            },
            "other_info": {
                "commander_element": interface_data.get("commander", ""),
                "void_emptiness": interface_data.get("void_emptiness", ""),
                "day_master": interface_data.get("day_master", "")
            },
            "formatted_text": interface_data.get("formatted_text", {})
        }
    
    @staticmethod
    def print_formatted_text(result_data: Dict[str, Any]) -> Dict[str, str]:
        """
        生成格式化的文本信息（兼容原有格式）
        
        Args:
            result_data: 包含所有计算结果的字典
        
        Returns:
            dict: 格式化的文本字典
        """
        # 识别性别：支持 "male"/"female" 和 "男"/"女"
        gender = result_data.get("gender", "")
        if gender in ["male", "男"]:
            gender_text = "男"
        elif gender in ["female", "女"]:
            gender_text = "女"
        else:
            gender_text = "女"  # 默认值
        gender_type = "乾造" if gender_text == "男" else "坤造"
        yin_yang = "阳" if gender_text == "男" else "阴"
        
        lunar_date = result_data.get("lunar_date_info", {})
        if not isinstance(lunar_date, dict):
            lunar_date = {}
        lunar_year = lunar_date.get("year", "")
        lunar_month = lunar_date.get("month", "")
        lunar_day = lunar_date.get("day", "")
        lunar_month_name = lunar_date.get("month_name", "")
        lunar_day_name = lunar_date.get("day_name", "")
        hour_zhi = result_data.get("hour_branch", "")
        
        return {
            "姓名": f"姓名：{result_data.get('name', '')} ({yin_yang} {gender_type})",
            "性别": f"性别：{gender_text}",
            "农历": f"农历：{lunar_year}年{lunar_month_name}{lunar_day_name} {hour_zhi}时",
            "四柱": f"四柱：{result_data.get('year_stem_branch', '')} {result_data.get('month_stem_branch', '')} {result_data.get('day_stem_branch', '')} {result_data.get('hour_stem_branch', '')}",
            "生肖": f"生肖：{result_data.get('zodiac', '')}",
            "阳历": f"阳历：{result_data.get('solar_date', '')} {result_data.get('solar_time', '')}",
            "真太阳时": f"真太阳时：{result_data.get('solar_date', '')} {result_data.get('solar_time', '')}",
            "出生地区": f"出生地区：{result_data.get('location', '')} 北京时间 --",
            "人元司令分野": f"人元司令分野：{result_data.get('commander', '')}",
            "出生节气": f"出生节气：出生于{result_data.get('current_jieqi_name', '')}后{BaziInterfacePrinter._format_hours(result_data.get('hours_to_current', 0))}，{result_data.get('next_jieqi_name', '')}前{BaziInterfacePrinter._format_hours(result_data.get('hours_to_next', 0))}（紫金山天文台时间）",
            "节气时间1": f"{result_data.get('current_jieqi_name', '')}：{result_data.get('current_jieqi_time', '')}",
            "节气时间2": f"{result_data.get('next_jieqi_name', '')}：{result_data.get('next_jieqi_time', '')}",
            "星座": f"星座：{result_data.get('constellation', '')}",
            "星宿": f"星宿：{result_data.get('mansion', '')}",
            "胎元": f"胎元：{result_data.get('fetal_origin', '')} ({result_data.get('fetal_origin_nayin', '')})",
            "空亡": f"空亡：{result_data.get('void_emptiness', '')}",
            "命宫": f"命宫：{result_data.get('life_palace', '')} ({result_data.get('life_palace_nayin', '')})",
            "胎息": f"胎息：{result_data.get('fetal_breath', '')} ({result_data.get('fetal_breath_nayin', '')})",
            "身宫": f"身宫：{result_data.get('body_palace', '')} ({result_data.get('body_palace_nayin', '')})",
            "命卦": f"命卦：{result_data.get('bagua', '')}",
            "日主属性": result_data.get('day_master', '')
        }
    
    @staticmethod
    def print_json(data: Dict[str, Any], indent: int = 2) -> None:
        """
        打印 JSON 格式的数据
        
        Args:
            data: 要打印的数据字典
            indent: JSON 缩进空格数
        """
        logger.info(BaziInterfacePrinter.format_to_json(data, indent))

    @staticmethod
    def _format_hours(total_hours):
        """
        格式化小时显示（基于紫金山天文台时间）
        如果小于24小时，显示小时；如果大于等于24小时，显示天和小时
        """
        if total_hours < 24:
            return f"{int(total_hours)}小时"
        else:
            days = int(total_hours // 24)
            hours = int(total_hours % 24)
            if hours == 0:
                return f"{days}天"
            else:
                return f"{days}天{hours}小时"




