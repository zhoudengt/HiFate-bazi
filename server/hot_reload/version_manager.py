#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本号管理模块 - 用于检测模块变化
"""

import sys
import logging

logger = logging.getLogger(__name__)
import os
from typing import Dict, Optional

# 添加项目根目录到路径
# 从 server/hot_reload/version_manager.py 到项目根目录：上移3级
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.db.rule_content_dao import RuleContentDAO


def get_source_code_version() -> int:
    """
    获取源代码版本号（基于文件修改时间）
    
    监控所有源代码文件，返回最新的修改时间戳作为版本号
    
    Returns:
        int: 版本号（最新文件修改时间的timestamp）
    """
    # 需要监控的源代码文件列表（从SourceCodeReloader获取）
    try:
        from .reloaders import SourceCodeReloader
        source_files = [
            info['file'] for info in SourceCodeReloader.MONITORED_MODULES.values()
        ]
    except Exception:
        # 如果无法导入，使用默认列表
        source_files = [
            'src/analyzers/bazi_interface_analyzer.py',
            'src/bazi_interface_generator.py',
            'src/analyzers/rizhu_gender_analyzer.py',
            'src/analyzers/deities_analyzer.py',
            'src/tool/BaziCalculator.py',
            'src/ai/bazi_ai_analyzer.py',
        ]
    
    max_mtime = 0
    for file_path in source_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            try:
                mtime = os.path.getmtime(full_path)
                max_mtime = max(max_mtime, int(mtime))
            except Exception:
                pass
    
    return max_mtime


class VersionManager:
    """版本号管理器 - 统一管理所有模块的版本号"""
    
    _cached_versions: Dict[str, int] = {}
    _version_checkers: Dict[str, callable] = {}
    
    @classmethod
    def register_version_checker(cls, module_name: str, checker_func: callable):
        """
        注册版本号检查器
        
        Args:
            module_name: 模块名称（如 'rules', 'content', 'config'）
            checker_func: 检查版本号的函数，返回 int
        """
        cls._version_checkers[module_name] = checker_func
        # 初始化缓存版本号
        try:
            cls._cached_versions[module_name] = checker_func()
        except Exception:
            cls._cached_versions[module_name] = 0
    
    @classmethod
    def get_version(cls, module_name: str) -> int:
        """
        获取模块版本号
        
        Args:
            module_name: 模块名称
            
        Returns:
            int: 版本号
        """
        if module_name in cls._version_checkers:
            try:
                return cls._version_checkers[module_name]()
            except Exception:
                return cls._cached_versions.get(module_name, 0)
        return 0
    
    @classmethod
    def get_cached_version(cls, module_name: str) -> int:
        """获取缓存的版本号"""
        return cls._cached_versions.get(module_name, 0)
    
    @classmethod
    def update_cached_version(cls, module_name: str, version: int):
        """更新缓存的版本号"""
        cls._cached_versions[module_name] = version
    
    @classmethod
    def check_version_changed(cls, module_name: str) -> bool:
        """
        检查版本号是否变化
        
        Args:
            module_name: 模块名称
            
        Returns:
            bool: True表示版本号变化，需要重新加载
        """
        current_version = cls.get_version(module_name)
        cached_version = cls.get_cached_version(module_name)
        
        if current_version > cached_version:
            cls.update_cached_version(module_name, current_version)
            return True
        return False
    
    @classmethod
    def check_all_modules(cls) -> Dict[str, bool]:
        """
        检查所有模块的版本号
        
        Returns:
            Dict[str, bool]: 模块名称 -> 是否变化
        """
        changes = {}
        for module_name in cls._version_checkers.keys():
            changes[module_name] = cls.check_version_changed(module_name)
        return changes
    
    @classmethod
    def init_versions(cls):
        """初始化所有模块的版本号"""
        for module_name in cls._version_checkers.keys():
            try:
                version = cls._version_checkers[module_name]()
                cls._cached_versions[module_name] = version
            except Exception as e:
                logger.info(f"⚠ 初始化 {module_name} 版本号失败: {e}")
                cls._cached_versions[module_name] = 0


# 注册默认的版本号检查器
def register_default_version_checkers():
    """注册默认的版本号检查器"""
    try:
        # 规则版本号
        VersionManager.register_version_checker(
            'rules',
            RuleContentDAO.get_rule_version
        )
        
        # 内容版本号
        VersionManager.register_version_checker(
            'content',
            RuleContentDAO.get_content_version
        )
        
        # 源代码版本号（基于文件修改时间）
        VersionManager.register_version_checker(
            'source',
            get_source_code_version
        )
        
        logger.info("✓ 版本号检查器注册成功（规则、内容、源代码）")
    except Exception as e:
        logger.info(f"⚠ 注册版本号检查器失败: {e}")


# 自动注册
register_default_version_checkers()



