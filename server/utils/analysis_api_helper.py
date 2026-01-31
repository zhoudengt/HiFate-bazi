#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析类 API 的公共辅助函数
"""

from typing import Any, Dict

SCENE_MODULES_CONFIG: Dict[str, Any] = {
    "health": {
        "bazi": True,
        "wangshuai": True,
        "detail": True,
        "rules": {"types": ["health"]},
    },
    "career": {
        "bazi": True,
        "wangshuai": True,
        "detail": True,
        "rules": {"types": ["career"]},
    },
    "marriage": {
        "bazi": True,
        "wangshuai": True,
        "detail": True,
        "rules": {"types": ["marriage"]},
    },
    "children": {
        "bazi": True,
        "wangshuai": True,
        "detail": True,
        "rules": {"types": ["children"]},
    },
    "general": {
        "bazi": True,
        "wangshuai": True,
        "detail": True,
        "rules": True,
    },
}


def get_modules_config(scene: str) -> Dict[str, Any]:
    """获取场景对应的 modules 配置。"""
    return SCENE_MODULES_CONFIG.get(scene, {}).copy()
