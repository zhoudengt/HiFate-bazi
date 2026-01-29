#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 服务工厂

根据数据库配置返回对应的 LLM 服务实例（Coze 或百炼）。
支持全局配置和场景级配置。
"""

import logging
from typing import Optional

from server.services.base_llm_stream_service import BaseLLMStreamService
from server.services.coze_stream_service import CozeStreamService
from server.services.bailian_stream_service import BailianStreamService
from server.config.config_loader import get_config_from_db_only

logger = logging.getLogger(__name__)


class LLMServiceFactory:
    """LLM 服务工厂 - 根据配置返回对应的 LLM 服务"""
    
    @classmethod
    def get_service(cls, scene: str, bot_id: Optional[str] = None) -> BaseLLMStreamService:
        """
        获取 LLM 服务实例
        
        Args:
            scene: 场景名称 (如 "marriage", "career_wealth")
            bot_id: Bot ID（可选，用于 Coze）
        
        Returns:
            LLM 服务实例
        """
        platform = cls._get_platform_for_scene(scene)
        
        logger.info(f"为场景 {scene} 选择平台: {platform}")
        
        if platform == "bailian":
            try:
                return BailianStreamService(scene=scene)
            except Exception as e:
                logger.error(f"创建百炼服务失败: {e}，回退到 Coze")
                # 如果百炼服务创建失败，回退到 Coze
                return CozeStreamService(bot_id=bot_id)
        else:
            return CozeStreamService(bot_id=bot_id)
    
    @classmethod
    def _get_platform_for_scene(cls, scene: str) -> str:
        """
        获取场景使用的平台
        
        配置优先级：
        1. 场景级配置：{SCENE}_LLM_PLATFORM（如 MARRIAGE_LLM_PLATFORM）
        2. 全局配置：LLM_PLATFORM（默认值：coze）
        
        Args:
            scene: 场景名称
        
        Returns:
            平台名称（"coze" 或 "bailian"）
        """
        # 1. 先查场景级配置（直接从配置表读取，使用统一的命名规则）
        scene_platform = get_config_from_db_only(f"{scene.upper()}_LLM_PLATFORM")
        if scene_platform:
            platform = scene_platform.lower().strip()
            logger.debug(f"场景 {scene} 使用场景级配置: {platform}")
            return platform if platform in ("coze", "bailian") else "coze"
        
        # 2. 使用全局配置
        global_platform = get_config_from_db_only("LLM_PLATFORM")
        if global_platform:
            platform = global_platform.lower().strip()
            logger.debug(f"场景 {scene} 使用全局配置: {platform}")
            return platform if platform in ("coze", "bailian") else "coze"
        
        # 3. 默认使用 Coze
        logger.debug(f"场景 {scene} 使用默认平台: coze")
        return "coze"
