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
import logging
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
# 从 server/hot_reload/reloaders.py 到项目根目录：上移3级
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

# ============================================================
# 全局重载保护标志
# 在 reload_all_modules() 执行期间为 True
# 支付等关键端点检查此标志，在重载窗口期返回 503 而非报错
# ============================================================
_reload_in_progress = False

# 重载事件历史记录（内存中保存最近 20 条）
_reload_history: list = []
_RELOAD_HISTORY_MAX = 20


def is_reload_in_progress() -> bool:
    """检查当前是否正在执行热更新重载"""
    return _reload_in_progress


def get_reload_history() -> list:
    """获取重载事件历史（最新在前）"""
    return list(reversed(_reload_history))


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
            logger.info("✓ 规则已重新加载")
            return True
        except Exception as e:
            logger.warning(f"⚠ 规则重载失败: {e}")
            return False


class InferenceRuleReloader:
    """推理规则重载器（inference_rules 表）"""

    @staticmethod
    def reload() -> bool:
        try:
            from core.inference.rule_loader import InferenceRuleLoader
            InferenceRuleLoader.reload_all()
            from core.inference.base_engine import BaseInferenceEngine
            for instance in BaseInferenceEngine._instances.values():
                instance.reload_rules()
            logger.info("✓ 推理规则已重新加载")
            return True
        except Exception as e:
            logger.warning(f"⚠ 推理规则重载失败: {e}")
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
            logger.info("✓ 内容缓存已清空")
            return True
        except Exception as e:
            logger.warning(f"⚠ 内容重载失败: {e}")
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
            logger.info("✓ 配置已重新加载")
            return True
        except Exception as e:
            logger.warning(f"⚠ 配置重载失败: {e}")
            return False


class CacheReloader:
    """缓存重载器"""
    
    @staticmethod
    def reload() -> bool:
        """
        清空缓存（包括 Redis 缓存和服务类缓存）
        
        Returns:
            bool: 是否成功
        """
        success = True
        
        # 0. 清理 bazi_cache 内存 LRU 缓存（遍历所有模块引用）
        # 原因：bazi_cache 是 OrderedDict 实现的内存缓存，importlib.reload 后
        # 旧模块引用仍持有旧 bazi_cache 实例，必须显式清理所有引用
        try:
            cleared_refs = 0
            for mod_name in list(sys.modules.keys()):
                mod = sys.modules.get(mod_name)
                if mod is None:
                    continue
                bc = getattr(mod, 'bazi_cache', None)
                if bc is not None and hasattr(bc, 'clear') and hasattr(bc, '_cache'):
                    bc.clear()
                    cleared_refs += 1
            if cleared_refs > 0:
                logger.info(f"   ✓ bazi_cache 内存 LRU 缓存已清理（{cleared_refs} 个引用）")
        except Exception as e:
            logger.warning(f"   ⚠ bazi_cache 清理失败: {e}")
        
        # 1. 清理 Redis 缓存（L1内存 + L2 Redis）
        try:
            from server.utils.cache_multi_level import get_multi_cache
            cache = get_multi_cache()
            # 清理 L1 内存缓存
            cache.clear()
            
            # 清理 L2 Redis 缓存（与 gate_clear_business_cache 模式一致，含 bazi_full:* 等）
            try:
                from shared.config.redis import get_redis_client
                from server.utils.cache_patterns import get_redis_clear_patterns
                from server.utils.cache_multi_level import bump_cache_version, _is_cache_version_enabled

                redis_client = get_redis_client()
                if redis_client:
                    # 若启用缓存版本，先 bump 使所有旧 key 自动失效
                    if _is_cache_version_enabled():
                        bump_cache_version(redis_client)
                        logger.info("   ✓ 缓存版本已 bump，旧缓存自动失效")
                    total_deleted = 0
                    for pattern in get_redis_clear_patterns():
                        cursor = 0
                        deleted = 0
                        while True:
                            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                            if keys:
                                redis_client.delete(*keys)
                                deleted += len(keys)
                            if cursor == 0:
                                break
                        if deleted > 0:
                            logger.info(f"   ✓ 清理了 {deleted} 个 {pattern} 缓存键")
                            total_deleted += deleted
                    if total_deleted > 0:
                        logger.info(f"   ✓ Redis 业务缓存共清理 {total_deleted} 个 key")
            except Exception as e:
                logger.warning(f"   ⚠ Redis 特定缓存清理失败: {e}")
                # 不设置 success = False，因为这是可选的
            
            logger.info("   ✓ 缓存已清空（L1内存 + L2 Redis）")
        except Exception as e:
            logger.warning(f"   ⚠ 缓存清理失败: {e}")
            success = False
        
        # 2. 清理 IndustryService 缓存
        try:
            from server.services.industry_service import IndustryService
            IndustryService.clear_cache()
            logger.info("   ✓ IndustryService 缓存已清理")
        except Exception as e:
            logger.warning(f"   ⚠ IndustryService 缓存清理失败: {e}")
            # 不设置 success = False，因为这是可选的
        
        # 3. 清理 ConfigService 缓存（如果存在）
        try:
            from server.services.config_service import ConfigService
            # ConfigService 使用类级别缓存，直接设置为 None
            ConfigService._element_cache = None
            ConfigService._mingge_cache = None
            logger.info("   ✓ ConfigService 缓存已清理")
        except Exception as e:
            logger.warning(f"   ⚠ ConfigService 缓存清理失败: {e}")
            # 不设置 success = False，因为这是可选的
        
        # 4. 清理支付客户端实例缓存（使配置修改生效）
        try:
            from services.payment_service.client_factory import payment_client_factory
            payment_client_factory.clear_cache()
            logger.info("   ✓ 支付客户端实例缓存已清理")
        except (ImportError, AttributeError) as e:
            logger.debug(f"   ⚠ 支付客户端模块未加载（可忽略）: {e}")
        except Exception as e:
            logger.warning(f"   ⚠ 支付客户端缓存清理失败: {e}")
            # 不设置 success = False，因为这是可选的
        
        if success:
            logger.info("✓ 缓存重载完成")
        else:
            logger.warning("⚠ 缓存重载部分失败")
        
        return success


class SourceCodeReloader:
    """源代码重载器 - 支持Python源代码热更新
    
    重载顺序保证（解决 importlib.reload 模块依赖问题）：
    底层模块先重载，上层模块后重载，确保 from X import Y 绑定到最新的类/函数。
    
    顺序：core/ → shared/ → src/ → server/services/ → server/engines/
          → server/utils/ → server/api/ → server/ (其他) → services/
    """
    
    _SEARCH_DIRECTORIES = ("core", "shared", "src", "server", "services")
    _EXCLUDE_DIRS = {"__pycache__", ".mypy_cache", ".pytest_cache"}
    
    # 依赖感知的重载优先级（数值越小越先重载）
    # 规则：被依赖方先加载，依赖方后加载
    _RELOAD_PRIORITY = [
        ("core.",              10),   # 最底层：核心计算
        ("shared.",            20),   # 共享模块：数据库/Redis
        ("src.",               30),   # src 模块
        ("server.config.",     40),   # 服务配置
        ("server.engines.",    50),   # 规则引擎
        ("server.services.",   60),   # 业务服务（被 API 层调用）
        ("server.utils.",      70),   # 工具类
        ("server.orchestrators.", 75),# 编排器
        ("server.hot_reload.", 80),   # 热更新自身
        ("server.api.",        90),   # API 层（最上层消费者）
        ("server.",           100),   # server 其他
        ("services.",         110),   # 独立微服务
    ]
    
    @classmethod
    def _get_module_priority(cls, module_name: str) -> int:
        """根据模块名返回重载优先级（越小越先重载）"""
        for prefix, priority in cls._RELOAD_PRIORITY:
            if module_name.startswith(prefix):
                return priority
        return 200  # 未匹配的放最后
    
    @classmethod
    def _discover_source_modules(cls) -> Dict[str, Dict[str, str]]:
        """
        动态扫描项目中的 Python 文件，生成监控列表
        返回结果按依赖优先级排序：底层模块在前，上层模块在后
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
        
        # 按依赖优先级排序：底层模块先重载
        sorted_modules = dict(
            sorted(modules.items(),
                   key=lambda item: (cls._get_module_priority(item[0]), item[0]))
        )
        return sorted_modules
    
    MONITORED_MODULES: Dict[str, Dict[str, str]] = {}
    
    @staticmethod
    def reload() -> bool:
        """
        重新加载源代码模块（依赖感知顺序）
        
        Returns:
            bool: 是否成功
        """
        import importlib
        from datetime import datetime
        
        monitored_modules = SourceCodeReloader._discover_source_modules()
        SourceCodeReloader.MONITORED_MODULES = monitored_modules
        
        reloaded_modules = []
        failed_modules = []
        
        logger.info("\n" + "="*60)
        logger.info(f"🔄 源代码热更新开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   模块总数: {len(monitored_modules)} | 依赖排序: 已启用")
        logger.info("="*60)
        
        try:
            # 禁止重载自身：reload 会重新执行模块顶层代码，导致 _reload_in_progress
            # 变量被重置为新对象，finally 块清除的是旧引用，503 标志永远清不掉。
            _SKIP_MODULES = {'server.hot_reload.reloaders'}
            
            for module_name, module_info in monitored_modules.items():
                if module_name in _SKIP_MODULES:
                    continue
                
                file_path = module_info['file']
                description = module_info['description']
                
                try:
                    # 检查文件是否存在
                    full_path = os.path.join(project_root, file_path)
                    if not os.path.exists(full_path):
                        logger.warning(f"  ⚠ 文件不存在: {file_path}")
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
                            logger.info(f"     🔄 模块未加载，已导入: {module_name}")
                        except ImportError as e:
                            logger.warning(f"     ⚠ 模块未加载且无法导入: {module_name} ({e})")
                            continue
                    
                    # 打印模块信息（无论是否已加载）
                    logger.info(f"\n  📦 模块: {module_name}")
                    logger.info(f"     📄 文件: {file_path}")
                    logger.info(f"     📝 功能: {description}")
                    logger.info(f"     🕒 修改时间: {mtime_str}")
                    
                    # ⭐ 特殊处理：如果是 grpc_gateway 模块，需要先处理端点注册
                    if module_name == 'server.api.grpc_gateway':
                        try:
                            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
                            old_count = len(SUPPORTED_ENDPOINTS)
                            logger.info(f"     🔄 重新注册前端点数量: {old_count}")
                            
                            # 🔴 备份当前端点（如果 reload 失败可以恢复）
                            endpoints_backup = dict(SUPPORTED_ENDPOINTS)
                            
                            # 清空端点字典（避免残留旧端点）
                            SUPPORTED_ENDPOINTS.clear()
                            
                            # 重新加载模块（触发装饰器 @_register 重新执行）
                            try:
                                importlib.reload(module)
                            except Exception as reload_err:
                                # 🔴 reload 失败时恢复备份，避免端点全部丢失
                                logger.error(f"     ❌ grpc_gateway reload 失败，恢复 {old_count} 个端点: {reload_err}")
                                SUPPORTED_ENDPOINTS.update(endpoints_backup)
                                raise
                            
                            # 重新获取端点字典（装饰器已执行）
                            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as NEW_ENDPOINTS
                            new_count = len(NEW_ENDPOINTS)
                            logger.info(f"     🔄 重新加载后端点数量: {new_count}")
                            
                            # 如果端点仍未注册，直接调用 _ensure_endpoints_registered 手动注册
                            if new_count == 0:
                                logger.warning(f"     ⚠️  装饰器未注册端点，手动注册 + 恢复备份...")
                                try:
                                    from server.api.grpc_gateway import _ensure_endpoints_registered
                                    _ensure_endpoints_registered()
                                    from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as FINAL_ENDPOINTS
                                    final_count = len(FINAL_ENDPOINTS)
                                    if final_count == 0:
                                        # 手动注册也失败，恢复备份
                                        logger.warning(f"     ⚠️  手动注册也为空，恢复备份的 {old_count} 个端点")
                                        SUPPORTED_ENDPOINTS.update(endpoints_backup)
                                    else:
                                        logger.info(f"     ✅ 手动注册成功（端点数量: {final_count}）")
                                except Exception as e:
                                    logger.error(f"     ❌ 手动注册失败，恢复备份: {e}")
                                    SUPPORTED_ENDPOINTS.update(endpoints_backup)
                            else:
                                logger.info(f"     ✅ gRPC 端点已重新注册（端点数量: {new_count}）")
                            
                            # 验证关键端点是否已注册
                            from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as FINAL_CHECK
                            key_endpoints = ['/bazi/interface', '/bazi/shengong-minggong', '/bazi/rizhu-liujiazi']
                            missing_endpoints = [ep for ep in key_endpoints if ep not in FINAL_CHECK]
                            if missing_endpoints:
                                logger.warning(f"     ⚠️  关键端点未注册: {missing_endpoints}，从备份恢复缺失端点...")
                                # 仅恢复缺失的端点，不覆盖已更新的
                                for ep in missing_endpoints:
                                    if ep in endpoints_backup:
                                        SUPPORTED_ENDPOINTS[ep] = endpoints_backup[ep]
                                        logger.info(f"     🔄 从备份恢复端点: {ep}")
                                # 再次尝试 _ensure_endpoints_registered
                                try:
                                    from server.api.grpc_gateway import _ensure_endpoints_registered
                                    _ensure_endpoints_registered()
                                except Exception:
                                    pass
                                # 最终验证
                                from server.api.grpc_gateway import SUPPORTED_ENDPOINTS as FINAL_CHECK2
                                still_missing = [ep for ep in key_endpoints if ep not in FINAL_CHECK2]
                                if still_missing:
                                    logger.error(f"     ❌ 关键端点仍然缺失: {still_missing}")
                                else:
                                    logger.info(f"     ✅ 关键端点验证通过（端点数量: {len(FINAL_CHECK2)}）")
                            else:
                                logger.info(f"     ✅ 关键端点验证通过")
                                
                        except Exception as e:
                            logger.error(f"     ❌ gRPC 端点重新注册失败: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        # 普通模块：直接重新加载
                        importlib.reload(module)
                    
                    # ⭐ 特殊处理：如果是 server.main 模块，需要重新注册路由
                    if module_name == 'server.main':
                        try:
                            logger.info(f"     🔄 检测到 server.main 模块更新，重新注册路由...")
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
                                            logger.info(f"     ✅ 路由信息已重新注册到管理器")
                                except Exception as e2:
                                    logger.warning(f"     ⚠️  重新注册路由信息到管理器失败: {e2}")
                                
                                # 清除注册状态，强制重新注册到 FastAPI 应用
                                router_manager.clear_registered_state()
                                # 重新注册所有路由到 FastAPI 应用
                                results = router_manager.register_all_routers(force=True)
                                success_count = sum(1 for v in results.values() if v)
                                failed_count = sum(1 for v in results.values() if not v)
                                logger.info(f"     ✅ 路由重新注册到 FastAPI 应用完成: {success_count} 成功, {failed_count} 失败")
                            else:
                                logger.warning(f"     ⚠️  路由管理器未初始化，跳过路由重新注册")
                        except Exception as e:
                            logger.warning(f"     ⚠️  路由重新注册失败（不影响模块重载）: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    reloaded_modules.append({
                        'module': module_name,
                        'file': file_path,
                        'description': description,
                        'mtime': mtime_str
                    })
                    logger.info(f"     ✅ 重载成功")
                        
                except Exception as e:
                    error_msg = str(e)
                    failed_modules.append({
                        'module': module_name,
                        'file': file_path,
                        'error': error_msg
                    })
                    logger.error(f"  ❌ 重载模块 {module_name} 失败: {error_msg}")
            
            # ────────────────────────────────────────────────────────────
            # 🔴 最终步骤：所有模块重载完成后，重新注册路由
            # 原因：os.walk 遍历时 server/main.py 在 server/hot_reload/api.py 之前，
            # 导致 server.main 重载时看到的是旧的 hot_reload router。
            # 这里确保在所有模块都已更新后，用最新的 router 对象重新注册。
            # ────────────────────────────────────────────────────────────
            try:
                from server.utils.router_manager import RouterManager
                router_manager = RouterManager.get_instance()
                if router_manager and 'server.main' in sys.modules:
                    main_module = sys.modules['server.main']
                    
                    # 1. 重新绑定 server.main 中的 router 变量到最新的模块对象
                    router_bindings = {
                        'server.hot_reload.api': 'hot_reload_router',
                    }
                    for src_module, var_name in router_bindings.items():
                        if src_module in sys.modules:
                            new_router = getattr(sys.modules[src_module], 'router', None)
                            if new_router and hasattr(main_module, var_name):
                                setattr(main_module, var_name, new_router)
                    
                    # 2. 重新注册路由信息到管理器
                    if hasattr(main_module, '_register_all_routers_to_manager'):
                        main_module._register_all_routers_to_manager()
                    
                    # 3. 强制重新注册到 FastAPI 应用
                    router_manager.clear_registered_state()
                    results = router_manager.register_all_routers(force=True)
                    success_count_r = sum(1 for v in results.values() if v)
                    logger.info(f"  🔄 最终路由重新注册: {success_count_r} 个路由已挂载")
            except Exception as e:
                logger.warning(f"  ⚠️  最终路由重新注册失败（不影响模块重载）: {e}")
            
            # 打印总结
            logger.info("\n" + "-"*60)
            if reloaded_modules:
                logger.info(f"✅ 源代码热更新完成 - 成功重载 {len(reloaded_modules)} 个模块:")
                for info in reloaded_modules:
                    logger.info(f"   • {info['module']}")
                    logger.info(f"     文件: {info['file']}")
                    logger.info(f"     功能: {info['description']}")
                    logger.info(f"     修改时间: {info['mtime']}")
            
            if failed_modules:
                logger.warning(f"\n⚠️  失败 {len(failed_modules)} 个模块:")
                for info in failed_modules:
                    logger.error(f"   • {info['module']}: {info['error']}")
            
            logger.info("="*60 + "\n")
            
            return len(reloaded_modules) > 0
            
        except Exception as e:
            logger.error(f"❌ 源代码热更新失败: {e}", exc_info=True)
            logger.error("="*60 + "\n")
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
                logger.warning("⚠ 没有注册的微服务热更新器")
                return True
            
            logger.info(f"\n🔄 开始重载 {len(reloaders)} 个微服务...")
            results = reload_all_microservices()
            
            success_count = sum(1 for v in results.values() if v)
            failed_count = len(results) - success_count
            
            if failed_count > 0:
                logger.warning(f"⚠ 微服务重载: {success_count} 成功, {failed_count} 失败")
                for service_name, success in results.items():
                    if not success:
                        logger.error(f"   ❌ {service_name}")
                return False
            
            logger.info(f"✓ 所有微服务重载成功 ({success_count} 个)")
            return True
            
        except ImportError:
            logger.warning("⚠ 微服务热更新模块未加载")
            return True
        except Exception as e:
            logger.error(f"⚠ 微服务重载失败: {e}", exc_info=True)
            return False


class SingletonReloader:
    """单例重置器 - 重置所有注册的单例实例"""
    
    # 需要重置的单例列表（完整清单，包含所有已知单例）
    SINGLETON_CLASSES = [
        ('server.services.rule_service', 'RuleService', ['_engine', '_cache', '_cached_content_version', '_cached_rule_version']),
        ('server.observability.metrics_collector', 'MetricsCollector', ['_instance']),
        ('server.observability.alert_manager', 'AlertManager', ['_instance']),
        ('server.observability.tracer', 'Tracer', ['_instance']),
        # 以下为新增的遗漏单例
        ('server.config.config_loader', 'ConfigService', ['_instance']),
        ('server.config.env_config', 'EnvConfig', ['_instance']),
        ('server.config.input_format_loader', 'InputFormatLoader', ['_instance']),
        ('server.config.app_config', 'AppConfig', ['_instance']),
        ('server.utils.cache_version_manager', 'CacheVersionManager', ['_instance']),
        ('server.utils.secret_manager', 'SecretManager', ['_instance']),
        ('server.utils.unified_logger', 'UnifiedLogger', ['_instance']),
        ('server.core.service_registry', 'ServiceRegistry', ['_instance']),
        ('server.services.shensha_sort_service', 'ShenshaSortService', ['_instance']),
        ('server.services.stream_call_logger', 'StreamCallLogger', ['_instance']),
    ]
    
    @staticmethod
    def reload() -> bool:
        """
        重置所有单例实例
        
        Returns:
            bool: 是否成功
        """
        logger.info("\n🔄 开始重置单例实例...")
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
                        logger.info(f"   ✓ 重置 {class_name}")
                        success_count += 1
                    else:
                        logger.warning(f"   ⚠ 类未找到: {class_name}")
                else:
                    logger.warning(f"   ⚠ 模块未加载: {module_path}")
                    
            except Exception as e:
                logger.error(f"   ❌ 重置失败 {class_name}: {e}")
                failed_count += 1
        
        if failed_count > 0:
            logger.warning(f"⚠ 单例重置: {success_count} 成功, {failed_count} 失败")
            return False
        
        logger.info(f"✓ 单例重置完成 ({success_count} 个)")
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
            logger.info("\n🔄 开始重载配置...")
            
            # 1. 重新加载环境变量
            from dotenv import load_dotenv
            load_dotenv(override=True)
            logger.info("   ✓ 环境变量已重新加载")
            
            # 2. 重置配置单例
            try:
                from server.config.app_config import AppConfig
                if hasattr(AppConfig, '_instance'):
                    AppConfig._instance = None
                    logger.info("   ✓ AppConfig 已重置")
            except ImportError:
                pass
            
            # 3. 重新加载数据库连接池配置
            try:
                from shared.config.database import refresh_connection_pool
                refresh_connection_pool()
                logger.info("   ✓ MySQL 连接池已刷新")
            except (ImportError, AttributeError) as e:
                logger.debug(f"   ⚠ MySQL 连接池模块未加载（可忽略）: {e}")
            except Exception as e:
                logger.warning(f"   ⚠ MySQL 连接池刷新失败: {e}")
            
            # 4. 重新加载 Redis 配置
            try:
                from shared.config.redis import refresh_redis_connection
                refresh_redis_connection()
                logger.info("   ✓ Redis 连接已刷新")
            except (ImportError, AttributeError) as e:
                logger.debug(f"   ⚠ Redis 连接模块未加载（可忽略）: {e}")
            except Exception as e:
                logger.warning(f"   ⚠ Redis 连接刷新失败: {e}")
            
            # 5. 重新加载支付配置缓存（从数据库重新读取）
            try:
                from services.payment_service.payment_config_loader import reload_payment_config
                reload_payment_config()  # 清除所有支付配置缓存
                logger.info("   ✓ 支付配置缓存已清除")
            except (ImportError, AttributeError) as e:
                logger.debug(f"   ⚠ 支付配置模块未加载（可忽略）: {e}")
            except Exception as e:
                logger.warning(f"   ⚠ 支付配置缓存清除失败: {e}")
            
            logger.info("✓ 配置重载完成")
            return True
            
        except Exception as e:
            logger.warning(f"⚠ 配置重载失败: {e}")
            return False


# 重载器注册表
RELOADERS = {
    'rules': RuleReloader,
    'inference_rules': InferenceRuleReloader,
    'content': ContentReloader,
    'config': ConfigReloaderEnhanced,  # 使用增强版配置重载器
    'cache': CacheReloader,
    'source': SourceCodeReloader,  # 源代码重载器
    'microservice': MicroserviceReloaderProxy,  # 微服务重载器
    'singleton': SingletonReloader,  # 单例重置器
}

# 重载顺序（按依赖关系）
# 🔴 重要：singleton 必须在 source 之后！
# 原因：source 重载会触发 __init__.py 重新注册支付客户端等组件。
# 如果 singleton 先执行（重置 _clients=None），则 source 重载前的窗口期
# 内任何支付请求都会失败。正确顺序：先加载新代码 → 再清理旧状态。
RELOAD_ORDER = [
    'config',       # 1. 先更新配置（环境变量、数据库连接等）
    'rules',        # 2. 更新规则
    'inference_rules',  # 2.5 更新推理规则
    'content',      # 3. 更新内容
    'source',       # 4. 更新源代码（触发模块重新导入和注册）
    'singleton',    # 5. 重置单例（清理旧实例，强制用新代码重建）
    'microservice', # 6. 更新微服务
    'cache',        # 7. 最后清理缓存
]


def get_reloader(module_name: str) -> Optional[Any]:
    """获取重载器"""
    return RELOADERS.get(module_name)


def reload_all_modules() -> Dict[str, bool]:
    """按顺序重载所有模块（带保护标志）"""
    global _reload_in_progress
    from datetime import datetime
    import time as _time
    
    logger.info("\n" + "="*60)
    logger.info(f"🔄 全量热更新开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    # 🔴 设置保护标志：重载期间阻止关键端点处理请求
    _reload_in_progress = True
    _t_start = _time.perf_counter()
    
    results = {}
    try:
        for module_name in RELOAD_ORDER:
            reloader = RELOADERS.get(module_name)
            if reloader:
                try:
                    results[module_name] = reloader.reload()
                except Exception as e:
                    logger.error(f"❌ {module_name} 重载失败: {e}")
                    results[module_name] = False
    finally:
        # 🔴 无论成功失败，必须清除保护标志
        _reload_in_progress = False
        _elapsed_ms = int((_time.perf_counter() - _t_start) * 1000)
    
    success_count = sum(1 for v in results.values() if v)
    failed_count = len(results) - success_count
    
    logger.info("\n" + "-"*60)
    if failed_count > 0:
        logger.warning(f"⚠ 全量热更新完成: {success_count} 成功, {failed_count} 失败 (耗时: {_elapsed_ms}ms)")
    else:
        logger.info(f"✅ 全量热更新完成: 所有 {success_count} 个模块更新成功 (耗时: {_elapsed_ms}ms)")
    logger.info("="*60 + "\n")
    
    # 🔴 记录重载事件到历史
    event = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "worker_pid": os.getpid(),
        "elapsed_ms": _elapsed_ms,
        "success_count": success_count,
        "failed_count": failed_count,
        "results": {k: v for k, v in results.items()},
        "all_success": failed_count == 0
    }
    _reload_history.append(event)
    if len(_reload_history) > _RELOAD_HISTORY_MAX:
        _reload_history.pop(0)
    
    return results



