# -*- coding: utf-8 -*-
"""
评测配置管理

定义评测脚本的各种配置项。
评测脚本批量调用流式接口，数据与流式接口完全同源。
"""

from dataclasses import dataclass


@dataclass
class EvaluationConfig:
    """评测配置"""
    
    # API服务配置
    base_url: str = "http://8.210.52.217:8001"
    api_prefix: str = "/api/v1"
    
    # 默认参数
    default_hour: str = "12:00"
    default_calendar_type: str = "solar"
    
    # 超时配置（秒）- 大模型接口响应较慢
    request_timeout: int = 60
    stream_timeout: int = 300  # 5分钟，用于流式大模型分析
    
    # 批量处理配置
    batch_concurrency: int = 3
    retry_count: int = 1
    retry_delay: float = 2.0
    
    @property
    def full_api_url(self) -> str:
        """获取完整的API URL"""
        return f"{self.base_url}{self.api_prefix}"


# 接口端点定义
class ApiEndpoints:
    """API端点常量"""
    
    # 非流式接口
    RIZHU_LIUJIAZI = "/bazi/rizhu-liujiazi"
    
    # 流式分析接口
    WUXING_PROPORTION_STREAM = "/bazi/wuxing-proportion/stream"
    XISHEN_JISHEN_STREAM = "/bazi/xishen-jishen/stream"
    CAREER_WEALTH_STREAM = "/career-wealth/stream"
    MARRIAGE_ANALYSIS_STREAM = "/bazi/marriage-analysis/stream"
    HEALTH_STREAM = "/health/stream"
    CHILDREN_STUDY_STREAM = "/children-study/stream"
    GENERAL_REVIEW_STREAM = "/general-review/stream"
    DAILY_FORTUNE_CALENDAR_STREAM = "/daily-fortune-calendar/stream"
    ANNUAL_REPORT_STREAM = "/annual-report/stream"


# Excel列映射配置
class ExcelColumns:
    """Excel列索引映射（基于0索引）
    
    新版布局：基础数据从流式接口 type=data 事件提取，LLM 分析从流式接口 content 提取。
    """
    
    # 输入列
    USER_ID = 0
    USER_NAME = 1
    USER_BIRTH = 2
    BAZI = 3               # 八字（年柱・月柱・日柱・时柱）
    GENDER = 4             # 性别（男/女）
    
    # 基础输出列（排盘数据，从 wuxing_proportion/xishen_jishen 的 type=data 提取）
    DAY_STEM = 5           # 日柱
    WUXING = 6             # 五行
    SHISHEN = 7            # 十神（主星，副星）
    XI_JI = 8              # 五行喜忌
    WANGSHUAI = 9          # 旺衰
    GEJU = 10              # 十神格局
    DAYUN_LIUNIAN = 11     # 大运流年
    
    # 日元六十甲子（非流式接口）
    RIZHU_LIUJIAZI = 12
    
    # LLM 分析输出列（从各流式接口 content 提取）
    WUXING_ANALYSIS = 13   # 五行占比分析
    XISHEN_JISHEN = 14     # 喜神与忌神
    CAREER_WEALTH = 15     # 事业财富
    MARRIAGE = 16          # 感情婚姻
    HEALTH = 17            # 身体健康
    CHILDREN_STUDY = 18    # 子女学习
    GENERAL_REVIEW = 19    # 总评
    DAILY_FORTUNE = 20     # 每日运势
    YEAR_FORTUNE = 21      # 年运报告


# 默认配置实例
DEFAULT_CONFIG = EvaluationConfig()
