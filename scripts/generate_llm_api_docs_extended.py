#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成大模型接口参数文档（扩展版）
包含统一接口和完整响应参数
"""

import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    from docx.enum.table import WD_TABLE_ALIGNMENT
except ImportError:
    print("错误: 需要安装 python-docx 库")
    print("请运行: pip install python-docx")
    sys.exit(1)


# 统一接口定义
UNIFIED_INTERFACE = {
    'name': '统一数据获取接口',
    'path': '/api/v1/bazi/data',
    'method': 'POST',
    'description': '统一数据获取接口，通过配置参数按需获取数据，支持并行计算、多级缓存和性能优化',
    'request_fields': [
        {'name': 'solar_date', 'type': 'string', 'required': '必填', 'description': '阳历日期，格式：YYYY-MM-DD（当calendar_type=lunar时，可为农历日期）', 'example': '1990-05-15'},
        {'name': 'solar_time', 'type': 'string', 'required': '必填', 'description': '出生时间，格式：HH:MM', 'example': '14:30'},
        {'name': 'gender', 'type': 'string', 'required': '必填', 'description': '性别：male(男) 或 female(女)', 'example': 'male'},
        {'name': 'calendar_type', 'type': 'string', 'required': '可选', 'description': '历法类型：solar(阳历) 或 lunar(农历)，默认solar', 'example': 'solar'},
        {'name': 'location', 'type': 'string', 'required': '可选', 'description': '出生地点（用于时区转换，优先级1）', 'example': '北京'},
        {'name': 'latitude', 'type': 'float', 'required': '可选', 'description': '纬度（用于时区转换，优先级2）', 'example': '39.90'},
        {'name': 'longitude', 'type': 'float', 'required': '可选', 'description': '经度（用于时区转换和真太阳时计算，优先级2）', 'example': '116.40'},
        {'name': 'modules', 'type': 'dict', 'required': '可选', 'description': '数据模块配置，例如: {"dayun": {"mode": "current_with_neighbors"}, "rules": {"types": ["shishen"]}}', 'example': '{}'},
        {'name': 'use_cache', 'type': 'boolean', 'required': '可选', 'description': '是否使用缓存，默认True', 'example': 'True'},
        {'name': 'parallel', 'type': 'boolean', 'required': '可选', 'description': '是否并行获取数据，默认True', 'example': 'True'},
        {'name': 'timeout', 'type': 'integer', 'required': '可选', 'description': '超时时间（秒），默认30', 'example': '30'},
        {'name': 'verify_consistency', 'type': 'boolean', 'required': '可选', 'description': '是否验证数据一致性（与前端页面数据对比），默认True', 'example': 'True'},
    ],
    'response_fields': [
        # 响应结构顶层字段
        {'path': 'success', 'type': 'boolean', 'description': '是否成功', 'source': 'BaziDataResponse模型'},
        {'path': 'data', 'type': 'dict', 'description': '数据内容（包含所有请求模块的数据）', 'source': 'BaziDataOrchestrator.fetch_data()'},
        {'path': 'message', 'type': 'string', 'description': '消息', 'source': 'BaziDataResponse模型'},
        {'path': 'error', 'type': 'string', 'description': '错误信息', 'source': 'BaziDataResponse模型'},
        {'path': 'validation_errors', 'type': 'list', 'description': '数据一致性验证错误列表', 'source': 'BaziDataValidator.validate_consistency()'},
        
        # data字段下的模块（展开所有嵌套字段）
        # bazi模块
        {'path': 'data.bazi', 'type': 'dict', 'description': '基础八字数据', 'source': 'BaziService.calculate_bazi_full()'},
        {'path': 'data.bazi.basic_info', 'type': 'dict', 'description': '基本信息', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.basic_info.solar_date', 'type': 'string', 'description': '阳历日期', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.basic_info.solar_time', 'type': 'string', 'description': '出生时间', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.basic_info.lunar_date', 'type': 'dict', 'description': '农历日期', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.basic_info.gender', 'type': 'string', 'description': '性别', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars', 'type': 'dict', 'description': '四柱八字', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.year', 'type': 'dict', 'description': '年柱', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.year.stem', 'type': 'string', 'description': '年干', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.year.branch', 'type': 'string', 'description': '年支', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.month', 'type': 'dict', 'description': '月柱', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.month.stem', 'type': 'string', 'description': '月干', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.month.branch', 'type': 'string', 'description': '月支', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.day', 'type': 'dict', 'description': '日柱', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.day.stem', 'type': 'string', 'description': '日干', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.day.branch', 'type': 'string', 'description': '日支', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.hour', 'type': 'dict', 'description': '时柱', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.hour.stem', 'type': 'string', 'description': '时干', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.bazi_pillars.hour.branch', 'type': 'string', 'description': '时支', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.details', 'type': 'dict', 'description': '详细信息（包含各柱的详细信息）', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.ten_gods_stats', 'type': 'dict', 'description': '十神统计', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.elements', 'type': 'dict', 'description': '五行元素', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.element_counts', 'type': 'dict', 'description': '五行计数', 'source': 'BaziService._format_bazi_result()'},
        {'path': 'data.bazi.relationships', 'type': 'dict', 'description': '关系信息（包含地支关系等）', 'source': 'BaziService._format_bazi_result()'},
        
        # wangshuai模块
        {'path': 'data.wangshuai', 'type': 'dict', 'description': '旺衰数据', 'source': 'WangShuaiService.calculate_wangshuai()'},
        {'path': 'data.wangshuai.success', 'type': 'boolean', 'description': '是否成功', 'source': 'WangShuaiService.calculate_wangshuai()'},
        {'path': 'data.wangshuai.data', 'type': 'dict', 'description': '旺衰分析结果', 'source': 'WangShuaiAnalyzer.analyze()'},
        {'path': 'data.wangshuai.data.wangshuai', 'type': 'string', 'description': '旺衰结果（如：身旺、身弱等）', 'source': 'WangShuaiAnalyzer.analyze()'},
        {'path': 'data.wangshuai.data.total_score', 'type': 'float', 'description': '总分', 'source': 'WangShuaiAnalyzer.analyze()'},
        {'path': 'data.wangshuai.data.tiaohou', 'type': 'dict', 'description': '调候信息', 'source': 'WangShuaiAnalyzer.calculate_tiaohou()'},
        
        # xishen_jishen模块
        {'path': 'data.xishen_jishen', 'type': 'dict', 'description': '喜神忌神数据', 'source': 'get_xishen_jishen()'},
        
        # wuxing模块
        {'path': 'data.wuxing', 'type': 'dict', 'description': '五行数据', 'source': '从bazi数据中提取'},
        {'path': 'data.wuxing.elements', 'type': 'dict', 'description': '五行元素', 'source': 'data.bazi.elements'},
        {'path': 'data.wuxing.element_counts', 'type': 'dict', 'description': '五行计数', 'source': 'data.bazi.element_counts'},
        
        # dayun模块
        {'path': 'data.dayun', 'type': 'list', 'description': '大运列表', 'source': 'BaziDetailService.calculate_detail_full() -> dayun_sequence'},
        {'path': 'data.dayun[].step', 'type': 'integer', 'description': '大运步数', 'source': 'BaziCalculator计算'},
        {'path': 'data.dayun[].ganzhi', 'type': 'string', 'description': '大运干支', 'source': 'BaziCalculator计算'},
        {'path': 'data.dayun[].year_start', 'type': 'integer', 'description': '起始年份', 'source': 'BaziCalculator计算'},
        {'path': 'data.dayun[].year_end', 'type': 'integer', 'description': '结束年份', 'source': 'BaziCalculator计算'},
        {'path': 'data.dayun[].age_range', 'type': 'dict', 'description': '年龄范围', 'source': 'BaziCalculator计算'},
        {'path': 'data.dayun[].liunian_sequence', 'type': 'list', 'description': '该大运下的流年序列', 'source': '从全局流年序列中提取'},
        
        # liunian模块
        {'path': 'data.liunian', 'type': 'list', 'description': '流年列表', 'source': 'BaziDetailService.calculate_detail_full() -> liunian_sequence'},
        {'path': 'data.liunian[].year', 'type': 'integer', 'description': '流年年份', 'source': 'BaziCalculator计算'},
        {'path': 'data.liunian[].ganzhi', 'type': 'string', 'description': '流年干支', 'source': 'BaziCalculator计算'},
        
        # liuyue模块
        {'path': 'data.liuyue', 'type': 'list', 'description': '流月列表', 'source': 'BaziDetailService.calculate_detail_full() -> liuyue_sequence'},
        
        # special_liunians模块
        {'path': 'data.special_liunians', 'type': 'dict', 'description': '特殊流年数据', 'source': 'SpecialLiunianService.get_special_liunians_batch()'},
        {'path': 'data.special_liunians.list', 'type': 'list', 'description': '原始列表格式', 'source': 'SpecialLiunianService.get_special_liunians_batch()'},
        {'path': 'data.special_liunians.by_dayun', 'type': 'dict', 'description': '按大运分组格式', 'source': '按dayun_step分组'},
        {'path': 'data.special_liunians.formatted', 'type': 'string', 'description': '格式化后的提示词', 'source': 'SpecialLiunianService.format_special_liunians_for_prompt()'},
        
        # rules模块
        {'path': 'data.rules', 'type': 'list', 'description': '匹配的规则列表', 'source': 'RuleService.match_rules()'},
        {'path': 'data.rules[].id', 'type': 'integer', 'description': '规则ID', 'source': '数据库'},
        {'path': 'data.rules[].type', 'type': 'string', 'description': '规则类型', 'source': '数据库'},
        {'path': 'data.rules[].content', 'type': 'string', 'description': '规则内容', 'source': '数据库'},
        {'path': 'data.rules[].match_score', 'type': 'float', 'description': '匹配分数', 'source': 'RuleService.match_rules()'},
        
        # health模块
        {'path': 'data.health', 'type': 'dict', 'description': '健康分析数据', 'source': 'HealthAnalysisService.analyze()'},
        
        # personality模块
        {'path': 'data.personality', 'type': 'dict', 'description': '性格分析数据', 'source': 'RizhuGenderAnalyzer.analyze_rizhu_gender()'},
        
        # rizhu模块
        {'path': 'data.rizhu', 'type': 'dict', 'description': '日柱六十甲子数据', 'source': 'RizhuLiujiaziService.get_rizhu_analysis()'},
        
        # wuxing_proportion模块
        {'path': 'data.wuxing_proportion', 'type': 'dict', 'description': '五行占比数据', 'source': 'WuxingProportionService.calculate_proportion()'},
        
        # liunian_enhanced模块
        {'path': 'data.liunian_enhanced', 'type': 'dict', 'description': '流年增强分析数据', 'source': 'LiunianEnhancedService.analyze_liunian_enhanced()'},
        
        # detail模块
        {'path': 'data.detail', 'type': 'dict', 'description': '详细八字数据（包含所有大运流年信息）', 'source': 'BaziDetailService.calculate_detail_full()'},
        {'path': 'data.detail.dayun_sequence', 'type': 'list', 'description': '完整大运序列', 'source': 'BaziCalculator计算'},
        {'path': 'data.detail.liunian_sequence', 'type': 'list', 'description': '完整流年序列', 'source': 'BaziCalculator计算'},
        {'path': 'data.detail.liuyue_sequence', 'type': 'list', 'description': '流月序列', 'source': 'BaziCalculator计算'},
        {'path': 'data.detail.matched_rules', 'type': 'list', 'description': '匹配的规则', 'source': 'RuleService.match_rules()'},
        {'path': 'data.detail.wangshuai', 'type': 'dict', 'description': '旺衰数据', 'source': 'WangShuaiService.calculate_wangshuai()'},
        {'path': 'data.detail.wuxing_proportion', 'type': 'dict', 'description': '五行占比数据', 'source': 'WuxingProportionService.calculate_proportion()'},
        {'path': 'data.detail.rizhu_liujiazi', 'type': 'dict', 'description': '日柱六十甲子数据', 'source': 'RizhuLiujiaziService.get_rizhu_analysis()'},
        
        # fortune_display模块
        {'path': 'data.fortune_display', 'type': 'dict', 'description': '大运流年流月统一展示数据', 'source': 'BaziDisplayService.get_fortune_display()'},
        
        # 其他模块
        {'path': 'data.deities', 'type': 'dict', 'description': '神煞数据', 'source': '从bazi.details中提取'},
        {'path': 'data.branch_relations', 'type': 'dict', 'description': '地支关系数据', 'source': '从bazi.relationships中提取'},
        {'path': 'data.career_star', 'type': 'list', 'description': '事业星数据', 'source': '从bazi.ten_gods中提取'},
        {'path': 'data.wealth_star', 'type': 'list', 'description': '财富星数据', 'source': '从bazi.ten_gods中提取'},
        {'path': 'data.children_star', 'type': 'list', 'description': '子女星数据', 'source': '从bazi.ten_gods中提取'},
        {'path': 'data.shengong_minggong', 'type': 'dict', 'description': '身宫命宫数据', 'source': 'BaziInterfaceService.generate_interface_full()'},
        {'path': 'data.daily_fortune', 'type': 'dict', 'description': '每日运势数据', 'source': 'DailyFortuneService.calculate_daily_fortune()'},
        {'path': 'data.monthly_fortune', 'type': 'dict', 'description': '每月运势数据', 'source': 'MonthlyFortuneService.calculate_monthly_fortune()'},
        {'path': 'data.daily_fortune_calendar', 'type': 'dict', 'description': '每日运势日历数据', 'source': 'DailyFortuneCalendarService.get_daily_fortune_calendar()'},
        {'path': 'data.yigua', 'type': 'dict', 'description': '易卦数据', 'source': 'YiGuaService.divinate()'},
        {'path': 'data.bazi_interface', 'type': 'dict', 'description': '八字界面数据', 'source': 'BaziInterfaceService.generate_interface_full()'},
        {'path': 'data.bazi_ai', 'type': 'dict', 'description': '八字AI分析数据', 'source': 'BaziAIService.analyze_bazi_with_ai()'},
    ],
}

# 接口定义列表（包含响应参数）
INTERFACES = [
    {
        'name': 'LLM生成完整报告',
        'path': '/api/v1/bazi/llm-generate',
        'method': 'POST',
        'description': '使用 LLM 直接生成完整的命理报告（类似 FateTell 的实时生成模式）',
        'stream': False,
        'request_fields': [
            {'name': 'solar_date', 'type': 'string', 'required': '必填', 'description': '阳历日期，格式：YYYY-MM-DD', 'example': '1990-05-15'},
            {'name': 'solar_time', 'type': 'string', 'required': '必填', 'description': '出生时间，格式：HH:MM', 'example': '14:30'},
            {'name': 'gender', 'type': 'string', 'required': '必填', 'description': '性别：male(男) 或 female(女)', 'example': 'male'},
            {'name': 'user_question', 'type': 'string', 'required': '可选', 'description': '用户问题或分析需求（可选）', 'example': '我想了解我的事业运势'},
            {'name': 'access_token', 'type': 'string', 'required': '可选', 'description': 'Coze Access Token（可选）', 'example': ''},
            {'name': 'bot_id', 'type': 'string', 'required': '可选', 'description': 'Coze Bot ID（可选）', 'example': ''},
            {'name': 'api_base', 'type': 'string', 'required': '可选', 'description': 'Coze API 基础URL（可选）', 'example': ''},
        ],
        'response_fields': [
            {'path': 'success', 'type': 'boolean', 'description': '是否成功', 'source': 'LLMGenerateResponse模型'},
            {'path': 'report', 'type': 'string', 'description': 'LLM生成的完整报告', 'source': 'Coze Bot API响应 -> analysis字段'},
            {'path': 'bazi_data', 'type': 'dict', 'description': '八字数据', 'source': '统一接口 -> data.bazi'},
            {'path': 'prompt_length', 'type': 'integer', 'description': '提示词长度', 'source': 'len(prompt)'},
            {'path': 'report_length', 'type': 'integer', 'description': '报告长度', 'source': 'len(report)'},
            {'path': 'error', 'type': 'string', 'description': '错误信息', 'source': 'LLMGenerateResponse模型'},
            {'path': 'error_detail', 'type': 'string', 'description': '原始错误信息（供调试）', 'source': 'LLMGenerateResponse模型'},
            {'path': 'suggestion', 'type': 'string', 'description': '建议的替代方案', 'source': 'LLMGenerateResponse模型'},
        ],
        'frontend': ['index.html'],
        'bot_id_config': 'COZE_BOT_ID (环境变量)',
    },
    # ... 其他接口定义（由于篇幅限制，这里先展示一个示例，完整版本需要包含所有接口）
]

# SSE事件类型定义
SSE_EVENTS = {
    'smart-analyze-stream': [
        {'event': 'status', 'description': '状态更新', 'data_fields': ['stage', 'message']},
        {'event': 'brief_response_start', 'description': '简要回答开始', 'data_fields': []},
        {'event': 'brief_response_chunk', 'description': '简要回答内容块', 'data_fields': ['content']},
        {'event': 'brief_response_end', 'description': '简要回答结束', 'data_fields': ['content']},
        {'event': 'brief_response_error', 'description': '简要回答错误', 'data_fields': ['message']},
        {'event': 'preset_questions', 'description': '预设问题', 'data_fields': ['questions']},
        {'event': 'basic_analysis', 'description': '基础分析结果', 'data_fields': ['analysis']},
        {'event': 'llm_start', 'description': 'LLM分析开始', 'data_fields': []},
        {'event': 'llm_chunk', 'description': 'LLM分析内容块', 'data_fields': ['content']},
        {'event': 'llm_end', 'description': 'LLM分析结束', 'data_fields': []},
        {'event': 'llm_error', 'description': 'LLM分析错误', 'data_fields': ['message']},
        {'event': 'related_questions', 'description': '相关问题', 'data_fields': ['questions']},
        {'event': 'performance', 'description': '性能统计', 'data_fields': ['summary']},
        {'event': 'error', 'description': '错误', 'data_fields': ['message', 'performance']},
        {'event': 'end', 'description': '流结束', 'data_fields': []},
    ],
    'stream-analysis': [
        {'event': 'progress', 'description': '进度更新', 'data_fields': ['content']},
        {'event': 'complete', 'description': '完成', 'data_fields': ['content']},
        {'event': 'error', 'description': '错误', 'data_fields': ['content']},
    ],
}

