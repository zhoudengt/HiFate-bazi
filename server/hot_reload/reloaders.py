#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
热更新重载器 - 各种模块的重载器

支持的模块类型：
- rules: 规则配置
- content: 规则内容
- config: 系统配置
- cache: 缓存数据
- source: Python源代码
- microservice: gRPC微服务代码
- singleton: 单例实例重置
"""

import sys
import os
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
# 从 server/hot_reload/reloaders.py 到项目根目录：上移3级
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
    
    _SEARCH_DIRECTORIES = ("src", "server", "services")  # 包含 services 目录
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
                    
                    # 从sys.modules中获取模块，如果未加载则尝试导入
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                    else:
                        # ⭐ 如果模块未加载，尝试导入（延迟加载的模块）
                        try:
                            import importlib
                            module = importlib.import_module(module_name)
                            print(f"     🔄 模块未加载，已导入: {module_name}")
                        except ImportError as e:
                            print(f"     ⚠ 模块未加载且无法导入: {module_name} ({e})")
                            continue
                    
                    # 打印模块信息（无论是否已加载）
                    print(f"\n  📦 模块: {module_name}")
                    print(f"     📄 文件: {file_path}")
                    print(f"     📝 功能: {description}")
                    print(f"     🕒 修改时间: {mtime_str}")
                    
                    # ⭐ 特殊处理：如果是 grpc_gateway 模块，需要先处理端点注册
                    if module_name == 'server.api.grpc_gateway':
                        try:
                            # 1. 先获取当前的端点字典
                            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
                            old_count = len(SUPPORTED_ENDPOINTS)
                            print(f"     🔄 重新注册前端点数量: {old_count}")
                            
                            # 2. 清空端点字典（避免残留旧端点）
                            SUPPORTED_ENDPOINTS.clear()
                            
                            # 3. 重新加载模块（触发装饰器 @_register 重新执行）
                            importlib.reload(module)
                            
                            # 4. 重新获取端点字典（装饰器已执行）
                            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as NEW_ENDPOINTS
                            new_count = len(NEW_ENDPOINTS)
                            print(f"     🔄 重新加载后端点数量: {new_count}")
                            
                            # 5. 如果端点仍未注册，手动触发重新注册函数
                            if new_count == 0:
                                print(f"     ⚠️  装饰器未注册端点，尝试手动重新注册...")
                                # 重新获取模块对象（因为 reload 后模块对象已更新）
                                import server.api.grpc_gateway as gateway_module
                                if hasattr(gateway_module, '_reload_endpoints'):
                                    success = gateway_module._reload_endpoints()
                                    if success:
                                        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as FINAL_ENDPOINTS
                                        final_count = len(FINAL_ENDPOINTS)
                                        print(f"     ✅ 手动重新注册成功（端点数量: {final_count}）")
                                    else:
                                        print(f"     ❌ 手动重新注册失败")
                                else:
                                    print(f"     ❌ 未找到 _reload_endpoints 函数")
                            else:
                                print(f"     ✅ gRPC 端点已重新注册（端点数量: {new_count}）")
                            
                            # 6. 验证关键端点是否已注册
                            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as FINAL_CHECK
                            key_endpoints = ['/bazi/interface', '/bazi/shengong-minggong', '/bazi/rizhu-liujiazi', '/auth/login']
                            missing_endpoints = [ep for ep in key_endpoints if ep not in FINAL_CHECK]
                            if missing_endpoints:
                                print(f"     ⚠️  关键端点未注册: {missing_endpoints}")
                            else:
                                print(f"     ✅ 关键端点验证通过")
                                
                        except Exception as e:
                            print(f"     ❌ gRPC 端点重新注册失败: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        # 普通模块：直接重新加载
                        importlib.reload(module)
                    
                    # ⭐ 特殊处理：如果是 server.main 模块，需要重新注册路由
                    if module_name == 'server.main':
                        try:
                            print(f"     🔄 检测到 server.main 模块更新，重新注册路由...")
                            # 等待模块重新加载完成
                            import time
                            time.sleep(0.1)  # 短暂延迟，确保模块重新加载完成
                            
                            from server.utils.router_manager import RouterManager
                            router_manager = RouterManager.get_instance()
                            if router_manager:
                                # 尝试重新注册路由信息（如果 server.main 已重新加载，_register_all_routers_to_manager 会被重新执行）
                                # 但是为了确保路由信息是最新的，我们需要确保它已执行
                                try:
                                    # 尝试调用 _register_all_routers_to_manager（如果存在）
                                    if 'server.main' in sys.modules:
                                        main_module = sys.modules['server.main']
                                        if hasattr(main_module, '_register_all_routers_to_manager'):
                                            main_module._register_all_routers_to_manager()
                                            print(f"     ✅ 路由信息已重新注册到管理器")
                                except Exception as e2:
                                    print(f"     ⚠️  重新注册路由信息到管理器失败: {e2}")
                                
                                # 清除注册状态，强制重新注册到 FastAPI 应用
                                router_manager.clear_registered_state()
                                # 重新注册所有路由到 FastAPI 应用
                                results = router_manager.register_all_routers(force=True)
                                success_count = sum(1 for v in results.values() if v)
                                failed_count = sum(1 for v in results.values() if not v)
                                print(f"     ✅ 路由重新注册到 FastAPI 应用完成: {success_count} 成功, {failed_count} 失败")
                            else:
                                print(f"     ⚠️  路由管理器未初始化，跳过路由重新注册")
                        except Exception as e:
                            print(f"     ⚠️  路由重新注册失败（不影响模块重载）: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    reloaded_modules.append({
                        'module': module_name,
                        'file': file_path,
                        'description': description,
                        'mtime': mtime_str
                    })
                    print(f"     ✅ 重载成功")
                        
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


class MicroserviceReloaderProxy:
    """微服务重载器代理 - 触发所有微服务的热更新"""
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载所有微服务
        
        Returns:
            bool: 是否成功
        """
        try:
            from .microservice_reloader import get_all_microservice_reloaders, reload_all_microservices
            
            reloaders = get_all_microservice_reloaders()
            if not reloaders:
                print("⚠ 没有注册的微服务热更新器")
                return True
            
            print(f"\n🔄 开始重载 {len(reloaders)} 个微服务...")
            results = reload_all_microservices()
            
            success_count = sum(1 for v in results.values() if v)
            failed_count = len(results) - success_count
            
            if failed_count > 0:
                print(f"⚠ 微服务重载: {success_count} 成功, {failed_count} 失败")
                for service_name, success in results.items():
                    if not success:
                        print(f"   ❌ {service_name}")
                return False
            
            print(f"✓ 所有微服务重载成功 ({success_count} 个)")
            return True
            
        except ImportError:
            print("⚠ 微服务热更新模块未加载")
            return True
        except Exception as e:
            print(f"⚠ 微服务重载失败: {e}")
            return False


class SingletonReloader:
    """单例重置器 - 重置所有注册的单例实例"""
    
    # 需要重置的单例列表
    SINGLETON_CLASSES = [
        ('server.services.rule_service', 'RuleService', ['_engine', '_cache', '_cached_content_version', '_cached_rule_version']),
        ('server.observability.metrics_collector', 'MetricsCollector', ['_instance']),
        ('server.observability.alert_manager', 'AlertManager', ['_instance']),
        ('server.observability.tracer', 'Tracer', ['_instance']),
    ]
    
    @staticmethod
    def reload() -> bool:
        """
        重置所有单例实例
        
        Returns:
            bool: 是否成功
        """
        print("\n🔄 开始重置单例实例...")
        success_count = 0
        failed_count = 0
        
        for module_path, class_name, attrs in SingletonReloader.SINGLETON_CLASSES:
            try:
                if module_path in sys.modules:
                    module = sys.modules[module_path]
                    cls = getattr(module, class_name, None)
                    
                    if cls is not None:
                        for attr in attrs:
                            if hasattr(cls, attr):
                                setattr(cls, attr, None)
                        print(f"   ✓ 重置 {class_name}")
                        success_count += 1
                    else:
                        print(f"   ⚠ 类未找到: {class_name}")
                else:
                    print(f"   ⚠ 模块未加载: {module_path}")
                    
            except Exception as e:
                print(f"   ❌ 重置失败 {class_name}: {e}")
                failed_count += 1
        
        if failed_count > 0:
            print(f"⚠ 单例重置: {success_count} 成功, {failed_count} 失败")
            return False
        
        print(f"✓ 单例重置完成 ({success_count} 个)")
        return True
    
    @staticmethod
    def register_singleton(module_path: str, class_name: str, attrs: List[str]):
        """
        注册需要重置的单例
        
        Args:
            module_path: 模块路径
            class_name: 类名
            attrs: 需要重置的属性列表
        """
        SingletonReloader.SINGLETON_CLASSES.append((module_path, class_name, attrs))


class ConfigReloaderEnhanced:
    """增强的配置重载器 - 支持环境变量和 Redis 配置热加载"""
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载配置
        
        Returns:
            bool: 是否成功
        """
        try:
            print("\n🔄 开始重载配置...")
            
            # 1. 重新加载环境变量
            from dotenv import load_dotenv
            load_dotenv(override=True)
            print("   ✓ 环境变量已重新加载")
            
            # 2. 重置配置单例
            try:
                from server.config.app_config import AppConfig
                if hasattr(AppConfig, '_instance'):
                    AppConfig._instance = None
                    print("   ✓ AppConfig 已重置")
            except ImportError:
                pass
            
            # 3. 重新加载数据库连接池配置
            try:
                from server.config.mysql_config import refresh_connection_pool
                refresh_connection_pool()
                print("   ✓ MySQL 连接池已刷新")
            except (ImportError, AttributeError):
                pass
            
            # 4. 重新加载 Redis 配置
            try:
                from server.config.redis_config import refresh_redis_connection
                refresh_redis_connection()
                print("   ✓ Redis 连接已刷新")
            except (ImportError, AttributeError):
                pass
            
            print("✓ 配置重载完成")
            return True
            
        except Exception as e:
            print(f"⚠ 配置重载失败: {e}")
            return False


# 重载器注册表
RELOADERS = {
    'rules': RuleReloader,
    'content': ContentReloader,
    'config': ConfigReloaderEnhanced,  # 使用增强版配置重载器
    'cache': CacheReloader,
    'source': SourceCodeReloader,  # 源代码重载器
    'microservice': MicroserviceReloaderProxy,  # 微服务重载器
    'singleton': SingletonReloader,  # 单例重置器
}

# 重载顺序（按依赖关系）
RELOAD_ORDER = [
    'config',       # 1. 先更新配置
    'singleton',    # 2. 重置单例
    'rules',        # 3. 更新规则
    'content',      # 4. 更新内容
    'source',       # 5. 更新源代码
    'microservice', # 6. 更新微服务
    'cache',        # 7. 最后清理缓存
]


def get_reloader(module_name: str) -> Optional[Any]:
    """获取重载器"""
    return RELOADERS.get(module_name)


def reload_all_modules() -> Dict[str, bool]:
    """按顺序重载所有模块"""
    from datetime import datetime
    
    print("\n" + "="*60)
    print(f"🔄 全量热更新开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    for module_name in RELOAD_ORDER:
        reloader = RELOADERS.get(module_name)
        if reloader:
            try:
                results[module_name] = reloader.reload()
            except Exception as e:
                print(f"❌ {module_name} 重载失败: {e}")
                results[module_name] = False
    
    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count
    
    print("\n" + "-"*60)
    if failed_count > 0:
        print(f"⚠ 全量热更新完成: {success_count} 成功, {failed_count} 失败")
    else:
        print(f"✅ 全量热更新完成: 所有 {success_count} 个模块更新成功")
    print("="*60 + "\n")
    
    return results



