# -*- coding: utf-8 -*-
"""
评测配置管理

定义评测脚本的各种配置项。
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class EvaluationConfig:
    """评测配置"""
    
    # API服务配置
    base_url: str = "http://8.210.52.217:8001"
    api_prefix: str = "/api/v1"
    
    # 默认参数
    default_hour: str = "12:00"
    default_calendar_type: str = "solar"
    
    # 超时配置（秒）- 大模型接口响应较慢，需要足够长的超时时间
    request_timeout: int = 60
    stream_timeout: int = 300  # 5分钟，用于流式大模型分析
    
    # 批量处理配置
    batch_concurrency: int = 3
    retry_count: int = 1
    retry_delay: float = 2.0
    
    # AI问答业务场景选项
    ai_qa_categories: List[str] = field(default_factory=lambda: [
        "事业财富", "婚姻", "健康", "子女", "流年运势", "年运报告"
    ])
    
    @property
    def full_api_url(self) -> str:
        """获取完整的API URL"""
        return f"{self.base_url}{self.api_prefix}"


# 接口端点定义
class ApiEndpoints:
    """API端点常量"""
    
    # 基础八字数据
    BAZI_DATA = "/bazi/data"  # 统一数据接口
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
    
    # 智能问答（注意：前缀是 /smart-fortune）
    SMART_ANALYZE_STREAM = "/smart-fortune/smart-analyze-stream"


# Excel列映射配置
class ExcelColumns:
    """Excel列索引映射（基于0索引）"""
    
    # 输入列
    USER_ID = 0
    USER_NAME = 1
    USER_BIRTH = 2
    GENDER = 3
    
    # 基础输出列（排盘数据）
    DAY_STEM = 4           # 日元
    WUXING = 5             # 五行
    SHISHEN = 6            # 十神
    XI_JI = 7              # 喜忌
    WANGSHUAI = 8          # 旺衰
    GEJU = 9               # 格局
    DAYUN_LIUNIAN = 10     # 大运流年
    
    # 跳过的列（11-14: 豆包/千问对比数据）
    
    # 大模型分析输出列
    RIZHU_LIUJIAZI = 15    # 日元-六十甲子
    WUXING_ANALYSIS = 16   # 五行占比分析
    XISHEN_JISHEN = 17     # 喜神与忌神
    CAREER_WEALTH = 18     # 事业财富
    MARRIAGE = 19          # 感情婚姻
    HEALTH = 20            # 身体健康
    CHILDREN_STUDY = 21    # 子女学习
    GENERAL_REVIEW = 22    # 总评
    DAILY_FORTUNE = 23     # 每日运势
    
    # 年运/大运（24-25）
    YEAR_FORTUNE = 24      # 年运
    DAYUN = 25             # 大运
    
    # AI问答列
    AI_CATEGORY = 26       # 业务场景（菜单）
    AI_OUTPUT1 = 27        # output模型回答
    AI_INPUT2 = 28         # CUSMOTER_input2
    AI_OUTPUT2 = 29        # output2模型回答
    AI_INPUT3 = 30         # CUSMOTER_input3
    AI_OUTPUT3 = 31        # output3模型回答


# 默认配置实例
DEFAULT_CONFIG = EvaluationConfig()

