#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百炼平台流式服务

包装 scripts/evaluation/bailian/BailianClient 为统一的 BaseLLMStreamService 接口。
复用现有代码，确保 scripts/evaluation/bazi_evaluator.py 不受影响。
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, AsyncGenerator

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.services.base_llm_stream_service import BaseLLMStreamService
from server.config.config_loader import get_config_from_db_only

# 导入百炼客户端（复用 scripts/evaluation/bailian/ 的代码）
try:
    from scripts.evaluation.bailian import BailianClient, BailianConfig
    BAILIAN_AVAILABLE = True
except ImportError:
    BAILIAN_AVAILABLE = False
    BailianClient = None
    BailianConfig = None

logger = logging.getLogger(__name__)


class BailianStreamService(BaseLLMStreamService):
    """百炼流式服务 - 包装 BailianClient 为统一接口"""
    
    # 场景名称到配置键的映射
    SCENE_CONFIG_MAP = {
        "marriage": "BAILIAN_MARRIAGE_APP_ID",
        "career_wealth": "BAILIAN_CAREER_WEALTH_APP_ID",
        "health": "BAILIAN_HEALTH_APP_ID",
        "children_study": "BAILIAN_CHILDREN_STUDY_APP_ID",
        "general_review": "BAILIAN_GENERAL_REVIEW_APP_ID",
        "daily_fortune": "BAILIAN_DAILY_FORTUNE_APP_ID",
        "wuxing_proportion": "BAILIAN_WUXING_PROPORTION_APP_ID",
        "xishen_jishen": "BAILIAN_XISHEN_JISHEN_APP_ID",
    }
    
    def __init__(self, scene: str, api_key: Optional[str] = None):
        """
        初始化百炼流式服务
        
        Args:
            scene: 场景名称（如 "marriage", "career_wealth"）
            api_key: API Key（可选，默认从数据库读取）
        """
        if not BAILIAN_AVAILABLE:
            raise ImportError("百炼平台模块不可用，请确保已安装 dashscope SDK: pip install dashscope")
        
        # 从数据库读取配置
        if not api_key:
            api_key = get_config_from_db_only("BAILIAN_API_KEY")
        
        if not api_key:
            raise ValueError("数据库配置缺失: BAILIAN_API_KEY，请在 service_configs 表中配置")
        
        # 创建配置（使用默认的 app_ids 映射）
        config = BailianConfig(api_key=api_key)
        
        # 根据场景从数据库读取 app_id（如果配置了则覆盖默认值）
        app_id_config_key = self.SCENE_CONFIG_MAP.get(scene)
        if app_id_config_key:
            app_id = get_config_from_db_only(app_id_config_key)
            if app_id:
                config.app_ids[scene] = app_id
                logger.info(f"使用数据库配置的 App ID: {scene} -> {app_id}")
            else:
                # 使用默认配置中的 app_id
                default_app_id = config.get_app_id(scene)
                if default_app_id:
                    logger.info(f"使用默认配置的 App ID: {scene} -> {default_app_id}")
                else:
                    logger.warning(f"未找到 {scene} 场景的 App ID 配置")
        
        self.client = BailianClient(config)
        self.scene = scene
        logger.info(f"百炼流式服务初始化完成: scene={scene}")
    
    async def stream_analysis(
        self,
        prompt: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式生成分析结果
        
        Args:
            prompt: 提示词
            trace_id: 请求追踪ID（可选，用于日志关联）
            **kwargs: 其他参数（如 session_id 等）
            
        Yields:
            dict: 包含 type 和 content 的字典
                - type: 'progress' 或 'complete' 或 'error'
                - content: 内容文本
        """
        app_id = self.client.config.get_app_id(self.scene)
        if not app_id:
            error_msg = f'百炼平台未配置 {self.scene} 场景的 App ID，请配置 {self.SCENE_CONFIG_MAP.get(self.scene, "BAILIAN_APP_ID")}'
            logger.error(error_msg)
            yield {
                'type': 'error',
                'content': error_msg
            }
            return
        
        session_id = kwargs.get('session_id')
        
        logger.info(f"[{trace_id or 'N/A'}] 调用百炼平台: scene={self.scene}, app_id={app_id}, prompt长度={len(prompt)}")
        
        try:
            async for chunk in self.client.call_stream(app_id, prompt, session_id=session_id, **kwargs):
                yield chunk
        except Exception as e:
            error_msg = f"百炼平台调用异常: {str(e)}"
            logger.error(f"[{trace_id or 'N/A'}] {error_msg}")
            yield {
                'type': 'error',
                'content': error_msg
            }
