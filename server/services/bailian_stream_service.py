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
from typing import Dict, Any, Optional, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.evaluation.bailian import BailianClient

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

# ✅ 优化：单例缓存，避免每次请求重复初始化
_bailian_service_cache: Dict[str, 'BailianStreamService'] = {}
_bailian_client_cache: Optional['BailianClient'] = None


class BailianStreamService(BaseLLMStreamService):
    """百炼流式服务 - 包装 BailianClient 为统一接口（支持单例模式）"""
    
    @classmethod
    def get_instance(cls, scene: str, api_key: Optional[str] = None) -> 'BailianStreamService':
        """
        获取单例实例（推荐使用此方法）
        
        优化点：
        1. 同一场景复用实例，避免重复初始化
        2. 所有场景共享 BailianClient，减少 SDK 初始化开销
        
        Args:
            scene: 场景名称
            api_key: API Key（可选）
        
        Returns:
            BailianStreamService 实例
        """
        global _bailian_service_cache
        
        if scene not in _bailian_service_cache:
            logger.info(f"[BailianStreamService] 创建新实例: scene={scene}")
            _bailian_service_cache[scene] = cls(scene, api_key)
        else:
            logger.debug(f"[BailianStreamService] 复用已有实例: scene={scene}")
        
        return _bailian_service_cache[scene]
    
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
        
        # 根据场景从数据库读取 app_id（统一命名规则：BAILIAN_{SCENE.upper()}_APP_ID）
        app_id_config_key = f"BAILIAN_{scene.upper()}_APP_ID"
        app_id = get_config_from_db_only(app_id_config_key)
        if app_id:
            config.app_ids[scene] = app_id
            logger.info(f"使用数据库配置的 App ID: {scene} -> {app_id}")
        else:
            # 如果数据库没有配置，尝试使用默认配置中的 app_id
            default_app_id = config.get_app_id(scene)
            if default_app_id:
                logger.info(f"使用默认配置的 App ID: {scene} -> {default_app_id}")
            else:
                logger.warning(f"未找到 {scene} 场景的 App ID 配置（数据库配置键: {app_id_config_key}）")
        
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
            error_msg = f'百炼平台未配置 {self.scene} 场景的 App ID，请在 service_configs 表中配置 BAILIAN_{self.scene.upper()}_APP_ID'
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
