# -*- coding: utf-8 -*-
"""
Excel处理器

处理Excel文件的读取和写入。
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

from .config import ExcelColumns
from .data_parser import DataParser


@dataclass
class TestCase:
    """测试用例数据"""
    row_index: int          # Excel行索引（从0开始）
    user_id: str            # 用户ID
    user_name: str          # 用户名
    birth_text: str         # 原始出生日期文本
    gender_text: str        # 原始性别文本
    solar_date: str         # 解析后的日期 YYYY-MM-DD
    solar_time: str         # 解析后的时间 HH:MM
    gender: str             # 解析后的性别 male/female
    parse_error: Optional[str] = None  # 解析错误信息


class ExcelHandler:
    """Excel处理器"""
    
    def __init__(self, filepath: str):
        """
        初始化Excel处理器
        
        Args:
            filepath: Excel文件路径
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Excel文件不存在: {filepath}")
        
        self.filepath = filepath
        self._workbook = None
        self._sheet = None
        self._df = None
        
        # 加载Excel（使用openpyxl以支持写入）
        self._workbook = load_workbook(filepath)
        self._sheet = self._workbook.active
        
        # 同时使用pandas读取数据
        self._df = pd.read_excel(filepath, header=1)  # 第2行为表头
    
    def read_test_cases(self, data_row_start: Optional[int] = None, 
                        data_row_end: Optional[int] = None) -> List[TestCase]:
        """
        读取测试用例
        
        Args:
            data_row_start: 起始数据行号（从1开始，1表示第一条数据）
            data_row_end: 结束数据行号（包含）
            
        Returns:
            测试用例列表
        """
        test_cases = []
        
        # pandas的索引从0开始
        for idx, row in self._df.iterrows():
            data_row_num = idx + 1  # 数据行号（从1开始）
            
            # 行号过滤（基于数据行号）
            if data_row_start is not None and data_row_num < data_row_start:
                continue
            if data_row_end is not None and data_row_num > data_row_end:
                break
            
            # 读取原始数据
            user_id = str(row.iloc[ExcelColumns.USER_ID]) if pd.notna(row.iloc[ExcelColumns.USER_ID]) else str(idx + 1)
            user_name = str(row.iloc[ExcelColumns.USER_NAME]) if pd.notna(row.iloc[ExcelColumns.USER_NAME]) else ""
            birth_text = str(row.iloc[ExcelColumns.USER_BIRTH]) if pd.notna(row.iloc[ExcelColumns.USER_BIRTH]) else ""
            gender_text = str(row.iloc[ExcelColumns.GENDER]) if pd.notna(row.iloc[ExcelColumns.GENDER]) else ""
            
            # 跳过空行
            if not birth_text or birth_text == "nan":
                continue
            
            # 创建测试用例
            test_case = TestCase(
                row_index=idx,
                user_id=user_id,
                user_name=user_name,
                birth_text=birth_text,
                gender_text=gender_text,
                solar_date="",
                solar_time="",
                gender=""
            )
            
            # 解析日期和性别
            try:
                test_case.solar_date, test_case.solar_time = DataParser.parse_birth_date(birth_text)
            except ValueError as e:
                test_case.parse_error = f"日期解析失败: {e}"
            
            try:
                test_case.gender = DataParser.parse_gender(gender_text)
            except ValueError as e:
                if test_case.parse_error:
                    test_case.parse_error += f"; 性别解析失败: {e}"
                else:
                    test_case.parse_error = f"性别解析失败: {e}"
            
            test_cases.append(test_case)
        
        return test_cases
    
    def write_cell(self, row: int, col: int, value: Any):
        """
        写入单元格
        
        Args:
            row: Excel行号（从1开始）
            col: Excel列号（从1开始）
            value: 值
        """
        self._sheet.cell(row=row, column=col + 1, value=value)
    
    def write_result(self, test_case: TestCase, results: Dict[str, Any]):
        """
        写入评测结果到Excel
        
        Args:
            test_case: 测试用例
            results: 评测结果字典
        """
        # Excel行号 = pandas索引 + 3（第1行分类 + 第2行表头 + 1因为pandas从0开始）
        excel_row = test_case.row_index + 3
        
        # 写入基础八字数据
        if 'basic' in results:
            basic = results['basic']
            self.write_cell(excel_row, ExcelColumns.DAY_STEM, basic.get('day_stem', ''))
            self.write_cell(excel_row, ExcelColumns.WUXING, basic.get('wuxing', ''))
            self.write_cell(excel_row, ExcelColumns.SHISHEN, basic.get('shishen', ''))
            self.write_cell(excel_row, ExcelColumns.XI_JI, basic.get('xi_ji', ''))
            self.write_cell(excel_row, ExcelColumns.WANGSHUAI, basic.get('wangshuai', ''))
            self.write_cell(excel_row, ExcelColumns.GEJU, basic.get('geju', ''))
            self.write_cell(excel_row, ExcelColumns.DAYUN_LIUNIAN, basic.get('dayun_liunian', ''))
        
        # 写入日元-六十甲子
        if 'rizhu_liujiazi' in results:
            self.write_cell(excel_row, ExcelColumns.RIZHU_LIUJIAZI, results['rizhu_liujiazi'])
        
        # 写入大模型分析
        if 'wuxing_analysis' in results:
            self.write_cell(excel_row, ExcelColumns.WUXING_ANALYSIS, results['wuxing_analysis'])
        
        if 'xishen_jishen' in results:
            self.write_cell(excel_row, ExcelColumns.XISHEN_JISHEN, results['xishen_jishen'])
        
        if 'career_wealth' in results:
            self.write_cell(excel_row, ExcelColumns.CAREER_WEALTH, results['career_wealth'])
        
        if 'marriage' in results:
            self.write_cell(excel_row, ExcelColumns.MARRIAGE, results['marriage'])
        
        if 'health' in results:
            self.write_cell(excel_row, ExcelColumns.HEALTH, results['health'])
        
        if 'children_study' in results:
            self.write_cell(excel_row, ExcelColumns.CHILDREN_STUDY, results['children_study'])
        
        if 'general_review' in results:
            self.write_cell(excel_row, ExcelColumns.GENERAL_REVIEW, results['general_review'])
        
        if 'daily_fortune' in results:
            self.write_cell(excel_row, ExcelColumns.DAILY_FORTUNE, results['daily_fortune'])
        
        # 写入AI问答结果
        if 'ai_qa' in results:
            ai_qa = results['ai_qa']
            self.write_cell(excel_row, ExcelColumns.AI_CATEGORY, ai_qa.get('category', ''))
            self.write_cell(excel_row, ExcelColumns.AI_OUTPUT1, ai_qa.get('output1', ''))
            self.write_cell(excel_row, ExcelColumns.AI_INPUT2, ai_qa.get('input2', ''))
            self.write_cell(excel_row, ExcelColumns.AI_OUTPUT2, ai_qa.get('output2', ''))
            self.write_cell(excel_row, ExcelColumns.AI_INPUT3, ai_qa.get('input3', ''))
            self.write_cell(excel_row, ExcelColumns.AI_OUTPUT3, ai_qa.get('output3', ''))
    
    def save(self, output_path: Optional[str] = None):
        """
        保存Excel文件
        
        Args:
            output_path: 输出路径，默认覆盖原文件
        """
        save_path = output_path or self.filepath
        self._workbook.save(save_path)
    
    def close(self):
        """关闭工作簿"""
        if self._workbook:
            self._workbook.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

