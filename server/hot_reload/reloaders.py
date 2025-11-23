#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新重载器 - 各种模块的重载器
"""

import sys
import os
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


class RuleReloader:
    """规则重载器"""
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载规则
        
        Returns:
            bool: 是否成功
        """
        try:
            from server.services.rule_service import RuleService
            RuleService.reload_rules()
            print("✓ 规则已重新加载")
            return True
        except Exception as e:
            print(f"⚠ 规则重载失败: {e}")
            return False


class ContentReloader:
    """内容重载器"""
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载内容（清空缓存）
        
        Returns:
            bool: 是否成功
        """
        try:
            from server.engines.query_adapters import QueryAdapterRegistry
            # 清空内容缓存
            QueryAdapterRegistry._content_cache.clear()
            print("✓ 内容缓存已清空")
            return True
        except Exception as e:
            print(f"⚠ 内容重载失败: {e}")
            return False


class ConfigReloader:
    """配置重载器"""
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载配置
        
        Returns:
            bool: 是否成功
        """
        try:
            # 这里可以添加其他配置的重载逻辑
            # 例如：Redis配置、MySQL配置等
            print("✓ 配置已重新加载")
            return True
        except Exception as e:
            print(f"⚠ 配置重载失败: {e}")
            return False


class CacheReloader:
    """缓存重载器"""
    
    @staticmethod
    def reload() -> bool:
        """
        清空缓存
        
        Returns:
            bool: 是否成功
        """
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            cache.clear()
            print("✓ 缓存已清空")
            return True
        except Exception as e:
            print(f"⚠ 缓存重载失败: {e}")
            return False


class SourceCodeReloader:
    """源代码重载器 - 支持Python源代码热更新"""
    
    _SEARCH_DIRECTORIES = ("src", "server")
    _EXCLUDE_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache"}
    
    @classmethod
    def _discover_source_modules(cls) -> Dict[str, Dict[str, str]]:
        """
        动态扫描项目中的 Python 文件，生成监控列表
        Returns:
            Dict[str, Dict[str, str]]: 模块名称 -> 文件信息
        """
        modules: Dict[str, Dict[str, str]] = {}
        for directory in cls._SEARCH_DIRECTORIES:
            base_dir = os.path.join(project_root, directory)
            if not os.path.exists(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in cls._EXCLUDE_DIRS]
                for filename in files:
                    if not filename.endswith(".py"):
                        continue
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, project_root)
                    module_name = rel_path[:-3].replace(os.sep, ".")
                    modules[module_name] = {
                        "file": rel_path,
                        "description": f"自动监控源文件: {rel_path}"
                    }
        return modules
    
    MONITORED_MODULES: Dict[str, Dict[str, str]] = {}
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载源代码模块
        
        Returns:
            bool: 是否成功
        """
        import importlib
        from datetime import datetime
        
        monitored_modules = SourceCodeReloader._discover_source_modules()
        SourceCodeReloader.MONITORED_MODULES = monitored_modules
        
        reloaded_modules = []
        failed_modules = []
        
        print("\n" + "="*60)
        print(f"🔄 源代码热更新开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            for module_name, module_info in monitored_modules.items():
                file_path = module_info['file']
                description = module_info['description']
                
                try:
                    # 检查文件是否存在
                    full_path = os.path.join(project_root, file_path)
                    if not os.path.exists(full_path):
                        print(f"  ⚠ 文件不存在: {file_path}")
                        continue
                    
                    # 获取文件修改时间
                    mtime = os.path.getmtime(full_path)
                    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 从sys.modules中获取模块
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                        
                        # 打印模块信息
                        print(f"\n  📦 模块: {module_name}")
                        print(f"     📄 文件: {file_path}")
                        print(f"     📝 功能: {description}")
                        print(f"     🕒 修改时间: {mtime_str}")
                        
                        # 重新加载模块
                        importlib.reload(module)
                        reloaded_modules.append({
                            'module': module_name,
                            'file': file_path,
                            'description': description,
                            'mtime': mtime_str
                        })
                        print(f"     ✅ 重载成功")
                    else:
                        print(f"  ⚠ 模块 {module_name} 未加载，跳过")
                        
                except Exception as e:
                    error_msg = str(e)
                    failed_modules.append({
                        'module': module_name,
                        'file': file_path,
                        'error': error_msg
                    })
                    print(f"  ❌ 重载模块 {module_name} 失败: {error_msg}")
            
            # 打印总结
            print("\n" + "-"*60)
            if reloaded_modules:
                print(f"✅ 源代码热更新完成 - 成功重载 {len(reloaded_modules)} 个模块:")
                for info in reloaded_modules:
                    print(f"   • {info['module']}")
                    print(f"     文件: {info['file']}")
                    print(f"     功能: {info['description']}")
                    print(f"     修改时间: {info['mtime']}")
            
            if failed_modules:
                print(f"\n⚠️  失败 {len(failed_modules)} 个模块:")
                for info in failed_modules:
                    print(f"   • {info['module']}: {info['error']}")
            
            print("="*60 + "\n")
            
            return len(reloaded_modules) > 0
            
        except Exception as e:
            print(f"❌ 源代码热更新失败: {e}")
            print("="*60 + "\n")
            return False


# 初始化源代码监控列表
SourceCodeReloader.MONITORED_MODULES = SourceCodeReloader._discover_source_modules()


# 重载器注册表
RELOADERS = {
    'rules': RuleReloader,
    'content': ContentReloader,
    'config': ConfigReloader,
    'cache': CacheReloader,
    'source': SourceCodeReloader,  # 源代码重载器
}


def get_reloader(module_name: str) -> Optional[Any]:
    """获取重载器"""
    return RELOADERS.get(module_name)



