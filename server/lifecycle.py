#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""应用生命周期管理（从 main.py 提取）"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    try:
        # 打印所有已注册的 gRPC 端点
        from server.api.grpc_gateway import SUPPORTED_ENDPOINTS
        logger.info(f"✓ 已注册 {len(SUPPORTED_ENDPOINTS)} 个 gRPC 端点:")
        for endpoint in sorted(SUPPORTED_ENDPOINTS.keys()):
            logger.info(f"  - {endpoint}")
    except Exception as e:
        logger.warning(f"⚠ 打印 gRPC 端点失败: {e}")
    
    # ⭐ 第一层防护：服务启动时强制注册所有端点（不依赖装饰器）
    try:
        from server.api.grpc_gateway import _ensure_endpoints_registered, SUPPORTED_ENDPOINTS
        _ensure_endpoints_registered()
        
        # 验证关键端点
        key_endpoints = ["/daily-fortune-calendar/query", "/bazi/interface", "/bazi/shengong-minggong", "/bazi/rizhu-liujiazi"]
        missing = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
        if missing:
            logger.error(f"🚨 服务启动后关键端点缺失: {missing}，当前端点数量: {len(SUPPORTED_ENDPOINTS)}")
            # 再次尝试注册
            _ensure_endpoints_registered()
            missing_after = [ep for ep in key_endpoints if ep not in SUPPORTED_ENDPOINTS]
            if missing_after:
                logger.critical(f"🚨🚨 服务启动后关键端点仍然缺失: {missing_after}，系统可能无法正常工作！")
            else:
                logger.info(f"✅ 关键端点已恢复（总端点数: {len(SUPPORTED_ENDPOINTS)}）")
        else:
            logger.info(f"✅ 所有关键端点已注册（总端点数: {len(SUPPORTED_ENDPOINTS)}）")
    except Exception as e:
        logger.critical(f"🚨🚨 端点注册失败: {e}", exc_info=True)
    
    try:
        # 启动统一的热更新管理器（替代原来的规则热加载）
        from server.hot_reload.hot_reload_manager import HotReloadManager
        manager = HotReloadManager.get_instance(interval=60)  # 1分钟检查一次（减少延迟）
        manager.start()
        logger.info("✓ 热更新管理器已启动")
    except Exception as e:
        logger.warning(f"⚠ 热更新管理器启动失败: {e}")
        # 降级到原来的规则热加载
        try:
            from server.services.rule_service import RuleService
            RuleService.start_auto_reload(interval=300)
            logger.info("✓ 规则热加载机制已启动（降级模式）")
        except Exception as e2:
            logger.warning(f"⚠ 规则热加载启动失败: {e2}")
    
    # 启动集群同步器（双机同步）
    try:
        from server.hot_reload.cluster_synchronizer import start_cluster_sync
        start_cluster_sync()
        logger.info("✓ 集群同步器已启动")
    except Exception as e:
        logger.warning(f"⚠ 集群同步器启动失败（单机模式）: {e}")
    
    # 启动缓存同步订阅器（双机缓存同步）
    try:
        from server.utils.cache_sync_subscriber import start_cache_sync_subscriber
        start_cache_sync_subscriber()
        logger.info("✓ 缓存同步订阅器已启动")
    except Exception as e:
        logger.warning(f"⚠ 缓存同步订阅器启动失败（单机模式）: {e}")
    
    # ✅ 性能优化：预热节气表缓存（服务启动时预计算常用年份）
    try:
        from datetime import datetime
        from core.calculators.bazi_calculator_docs import BaziCalculator as DocsBaziCalculator
        
        current_year = datetime.now().year
        # 预热当前年份前后各5年的节气表（共11年）
        warmup_years = list(range(current_year - 5, current_year + 6))
        
        # 使用一个临时计算器实例来预热缓存
        temp_calc = DocsBaziCalculator("2000-01-01", "12:00", "male")
        
        from lunar_python import Solar
        for year in warmup_years:
            if year not in DocsBaziCalculator._jieqi_table_cache:
                base_solar = Solar.fromYmdHms(year, 1, 1, 0, 0, 0)
                lunar_year = base_solar.getLunar()
                jieqi_table = lunar_year.getJieQiTable()
                DocsBaziCalculator._jieqi_table_cache[year] = jieqi_table
        
        logger.info(f"✓ 节气表缓存预热完成（{len(warmup_years)}年: {warmup_years[0]}-{warmup_years[-1]}）")
    except Exception as e:
        logger.warning(f"⚠ 节气表缓存预热失败（不影响正常使用）: {e}")

    # 启动时预热 API 缓存（每日运势 + 热门八字组合，后台执行不阻塞）
    try:
        import asyncio
        from server.utils.cache_warmer import warmup_on_startup
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, warmup_on_startup)
        logger.info("✓ 缓存预热任务已提交（后台执行）")
    except Exception as e:
        logger.warning(f"⚠ 缓存预热任务提交失败（不影响正常使用）: {e}")

    # 启动MySQL连接清理任务（定期清理空闲连接）
    try:
        import asyncio
        from shared.config.database import cleanup_idle_mysql_connections
        
        async def connection_cleanup_task():
            """定期清理空闲MySQL连接（每60秒清理一次）"""
            while True:
                await asyncio.sleep(60)  # 每60秒清理一次
                try:
                    cleaned = cleanup_idle_mysql_connections(max_idle_time=300)
                    if cleaned > 0:
                        logger.info(f"✓ 清理了 {cleaned} 个空闲MySQL连接")
                except Exception as e:
                    logger.error(f"⚠ 清理MySQL连接失败: {e}")
        
        # 启动后台任务
        cleanup_task = asyncio.create_task(connection_cleanup_task())
        logger.info("✓ MySQL连接清理任务已启动（每60秒清理一次）")
    except Exception as e:
        logger.warning(f"⚠ MySQL连接清理任务启动失败: {e}")
    
    yield
    # 关闭时执行
    # 停止缓存同步订阅器
    try:
        from server.utils.cache_sync_subscriber import stop_cache_sync_subscriber
        stop_cache_sync_subscriber()
        logger.info("✓ 缓存同步订阅器已停止")
    except Exception as e:
        logger.warning(f"⚠ 缓存同步订阅器停止失败: {e}")
    
    # 停止集群同步器
    try:
        from server.hot_reload.cluster_synchronizer import stop_cluster_sync
        stop_cluster_sync()
        logger.info("✓ 集群同步器已停止")
    except Exception as e:
        logger.warning(f"⚠ 集群同步器停止失败: {e}")
    
    try:
        from server.hot_reload.hot_reload_manager import HotReloadManager
        manager = HotReloadManager.get_instance()
        manager.stop()
        logger.info("✓ 热更新管理器已停止")
    except Exception as e:
        logger.warning(f"⚠ 热更新管理器停止失败: {e}")
    
    # 停止告警管理器
    try:
        from server.observability.alert_manager import AlertManager
        alert_manager = AlertManager.get_instance()
        alert_manager.stop()
        logger.info("✓ 告警管理器已停止")
    except Exception as e:
        logger.warning(f"⚠ 告警管理器停止失败: {e}")
        # 停止原来的规则热加载
        try:
            from server.services.rule_service import RuleService
            if RuleService._reloader:
                RuleService._reloader.stop()
                logger.info("✓ 规则热加载机制已停止")
        except Exception as e2:
            logger.warning(f"⚠ 规则热加载停止失败: {e2}")

