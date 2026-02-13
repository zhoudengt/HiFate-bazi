# -*- coding: utf-8 -*-
"""
评测配置管理

定义评测脚本的各种配置项。
支持 Coze 和 百炼 双平台对比评测。
"""

from dataclasses import dataclass, field
from typing import List, Literal


# 平台类型
PlatformType = Literal["coze", "bailian", "both"]


@dataclass
class EvaluationConfig:
    """评测配置"""
    
    # API服务配置（Coze 平台通过后端代理）
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
    
    # ==================== 双平台评测配置 ====================
    
    # 平台选择: "coze" | "bailian" | "both"
    platform: PlatformType = "coze"
    
    # 百炼平台配置
    bailian_api_key: str = ""  # 如果为空，从环境变量 DASHSCOPE_API_KEY 获取
    
    @property
    def full_api_url(self) -> str:
        """获取完整的API URL"""
        return f"{self.base_url}{self.api_prefix}"
    
    @property
    def use_coze(self) -> bool:
        """是否使用 Coze 平台"""
        return self.platform in ("coze", "both")
    
    @property
    def use_bailian(self) -> bool:
        """是否使用百炼平台"""
        return self.platform in ("bailian", "both")


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
    ANNUAL_REPORT_STREAM = "/annual-report/stream"
    
    # 智能问答（注意：前缀是 /smart-fortune）
    SMART_ANALYZE_STREAM = "/smart-fortune/smart-analyze-stream"
    
    # ==================== 调试/测试接口（返回 formatted_data）====================
    # ✅ 优先使用 debug 接口，确保与流式接口使用完全相同的逻辑，保证评测一致性
    # 用于获取与 Coze 相同的结构化数据，供百炼平台使用
    CAREER_WEALTH_TEST = "/career-wealth/debug"  # ✅ 使用 debug 接口，与流式接口一致
    GENERAL_REVIEW_TEST = "/general-review/debug"  # ✅ 使用 debug 接口，与流式接口一致
    MARRIAGE_ANALYSIS_TEST = "/bazi/marriage-analysis/debug"  # ✅ 使用 debug 接口，与流式接口一致
    HEALTH_ANALYSIS_TEST = "/health/debug"  # ✅ 使用 debug 接口，与流式接口一致
    CHILDREN_STUDY_TEST = "/children-study/debug"  # ✅ 使用 debug 接口，与流式接口一致
    ANNUAL_REPORT_TEST = "/annual-report/debug"  # 与 stream 数据一致，供评测使用
    WUXING_PROPORTION_TEST = "/bazi/wuxing-proportion/test"  # TODO: 检查 test 接口是否与流式接口一致
    XISHEN_JISHEN_TEST = "/bazi/xishen-jishen/test"  # TODO: 检查 test 接口是否与流式接口一致
    DAILY_FORTUNE_CALENDAR_TEST = "/daily-fortune-calendar/test"  # TODO: 检查 test 接口是否与流式接口一致


# Excel列映射配置
class ExcelColumns:
    """Excel列索引映射（基于0索引）"""
    
    # 输入列
    USER_ID = 0
    USER_NAME = 1
    USER_BIRTH = 2
    BAZI = 3               # 八字（年柱・月柱・日柱・时柱）
    GENDER = 4             # 性别（男/女）
    
    # 基础输出列（排盘数据）
    DAY_STEM = 5           # 日元（日柱）
    WUXING = 6             # 五行数量
    SHISHEN = 7            # 十神（主星，副星）
    XI_JI = 8              # 五行喜忌
    WANGSHUAI = 9          # 旺衰
    GEJU = 10              # 十神格局
    DAYUN_LIUNIAN = 11     # 大运流年
    
    # 跳过的列（12-15: 豆包/千问对比数据）
    
    # Coze 平台大模型分析输出列
    RIZHU_LIUJIAZI = 16    # 日元-六十甲子
    WUXING_ANALYSIS = 17   # 五行占比分析
    XISHEN_JISHEN = 18     # 喜神与忌神
    CAREER_WEALTH = 19     # 事业财富
    MARRIAGE = 20          # 感情婚姻
    HEALTH = 21            # 身体健康
    CHILDREN_STUDY = 22    # 子女学习
    GENERAL_REVIEW = 23    # 总评
    DAILY_FORTUNE = 24     # 每日运势
    
    # 年运/大运（25-26）
    YEAR_FORTUNE = 25      # 年运
    DAYUN = 26             # 大运
    
    # AI问答列
    AI_CATEGORY = 27       # 业务场景（菜单）
    AI_OUTPUT1 = 28        # output模型回答
    AI_INPUT2 = 29         # CUSMOTER_input2
    AI_OUTPUT2 = 30        # output2模型回答
    AI_INPUT3 = 31         # CUSMOTER_input3
    AI_OUTPUT3 = 32        # output3模型回答
    
    # ==================== 百炼平台对比列（新增）====================
    # 百炼平台大模型分析输出列（在 AI问答列之后）
    BAILIAN_WUXING_ANALYSIS = 33     # 百炼-五行占比分析
    BAILIAN_XISHEN_JISHEN = 34       # 百炼-喜神与忌神
    BAILIAN_CAREER_WEALTH = 35       # 百炼-事业财富
    BAILIAN_MARRIAGE = 36            # 百炼-感情婚姻
    BAILIAN_HEALTH = 37              # 百炼-身体健康
    BAILIAN_CHILDREN_STUDY = 38      # 百炼-子女学习
    BAILIAN_GENERAL_REVIEW = 39      # 百炼-总评
    BAILIAN_DAILY_FORTUNE = 40       # 百炼-每日运势


# 默认配置实例
DEFAULT_CONFIG = EvaluationConfig()

