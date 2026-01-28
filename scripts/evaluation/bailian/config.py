# -*- coding: utf-8 -*-
"""
百炼平台配置

存放百炼平台的 API Key 和各场景智能体的 app_id 映射。
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional


# 百炼平台各分析场景对应的 app_id
BAILIAN_APP_IDS = {
    # 基础分析
    "wuxing_proportion": "d326e553a5764d9bac629e87019ac380",      # 五行解析
    "xishen_jishen": "b9188eacd5bc4e1d8b91bd66ef8671df",          # 喜神与忌神
    
    # 专项分析
    "career_wealth": "0f97307f05d041d2b643c967f98f4cbb",          # 事业财富
    "marriage": "4bf72d82f83d439cb575856e5bcb8502",               # 感情婚姻
    "health": "1e9186468bf743a0be8748e0cddd5f44",                 # 身体健康
    "children_study": "a7d2174380be49508ecb5e014c54fc3a",         # 子女学习
    
    # 综合分析
    "general_review": "75d9a46f55374ea2be1ea28db10c8d03",         # 总评分析
    "annual_report": "a2a45b93d4c04ee1b363bdaa8cd26d35",          # 年运报告
    "daily_fortune": "df11520293eb479a985916d977904a8a",          # 每日运势
    
    # QA 问答
    "qa_question_generate": "835867a183cd4a0db861c61f632bbaa6",   # QA-问题生成
    "qa_analysis": "b9188eacd5bc4e1d8b91bd66ef8671df",            # QA-命理分析
}


@dataclass
class BailianConfig:
    """百炼平台配置"""
    
    # API Key（优先级：参数 > 环境变量）
    api_key: str = ""
    
    # API 基础 URL
    api_base: str = "https://dashscope.aliyuncs.com"
    
    # 超时配置（秒）
    request_timeout: int = 60
    stream_timeout: int = 300  # 5分钟，用于流式大模型分析
    
    # App ID 映射
    app_ids: Dict[str, str] = field(default_factory=lambda: BAILIAN_APP_IDS.copy())
    
    def __post_init__(self):
        """初始化后处理"""
        # 如果未提供 api_key，尝试从环境变量获取
        if not self.api_key:
            self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
    
    def get_app_id(self, scene: str) -> Optional[str]:
        """
        获取指定场景的 app_id
        
        Args:
            scene: 场景名称（如 "career_wealth", "marriage" 等）
            
        Returns:
            app_id 或 None
        """
        return self.app_ids.get(scene)
    
    def validate(self) -> bool:
        """验证配置是否完整"""
        if not self.api_key:
            return False
        if not self.app_ids:
            return False
        return True


# 默认配置实例（使用环境变量或预设的 API Key）
DEFAULT_BAILIAN_CONFIG = BailianConfig(
    api_key=os.getenv("DASHSCOPE_API_KEY", "sk-91ad3ec784b64fe78c4015827dfd982d")
)

