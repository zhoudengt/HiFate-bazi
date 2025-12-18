#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存同步订阅器 - 双机缓存同步机制
使用Redis发布/订阅机制，当一台服务器清理缓存时，自动通知其他服务器清理本地缓存
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 全局订阅器实例
_subscriber_thread: Optional[threading.Thread] = None
_subscriber_running = False


def _cache_sync_subscriber():
    """缓存同步订阅器（后台线程）"""
    global _subscriber_running
    
    try:
        from server.config.redis_config import get_redis_client
        
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("⚠️  Redis客户端不可用，缓存同步订阅器无法启动")
            return
        
        # 创建订阅对象
        pubsub = redis_client.pubsub()
        pubsub.subscribe('cache:invalidate:daily_fortune')
        
        logger.info("✓ 缓存同步订阅器已启动，监听频道: cache:invalidate:daily_fortune")
        _subscriber_running = True
        
        # 监听消息
        for message in pubsub.listen():
            if not _subscriber_running:
                break
            
            if message['type'] == 'message':
                target_date = message['data'].decode('utf-8') if isinstance(message['data'], bytes) else message['data']
                logger.info(f"📢 收到缓存失效事件: {target_date}")
                
                # 清理本地L1缓存
                try:
                    from server.utils.cache_multi_level import get_multi_cache
                    cache = get_multi_cache()
                    cache.l1.clear()  # 清空所有L1缓存
                    logger.info(f"✅ 已清理本地L1缓存（日期: {target_date}）")
                except Exception as e:
                    logger.warning(f"⚠️  清理本地L1缓存失败: {e}")
    
    except Exception as e:
        logger.error(f"❌ 缓存同步订阅器异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        _subscriber_running = False
        logger.info("✓ 缓存同步订阅器已停止")


def start_cache_sync_subscriber():
    """启动缓存同步订阅器"""
    global _subscriber_thread, _subscriber_running
    
    if _subscriber_running:
        logger.warning("⚠️  缓存同步订阅器已在运行")
        return
    
    try:
        _subscriber_thread = threading.Thread(
            target=_cache_sync_subscriber,
            daemon=True,
            name="CacheSyncSubscriber"
        )
        _subscriber_thread.start()
        logger.info("✓ 缓存同步订阅器线程已启动")
    except Exception as e:
        logger.error(f"❌ 启动缓存同步订阅器失败: {e}")


def stop_cache_sync_subscriber():
    """停止缓存同步订阅器"""
    global _subscriber_thread, _subscriber_running
    
    if not _subscriber_running:
        return
    
    try:
        _subscriber_running = False
        
        # 取消订阅
        try:
            from server.config.redis_config import get_redis_client
            redis_client = get_redis_client()
            if redis_client:
                pubsub = redis_client.pubsub()
                pubsub.unsubscribe('cache:invalidate:daily_fortune')
        except Exception:
            pass
        
        # 等待线程结束
        if _subscriber_thread and _subscriber_thread.is_alive():
            _subscriber_thread.join(timeout=5)
        
        logger.info("✓ 缓存同步订阅器已停止")
    except Exception as e:
        logger.warning(f"⚠️  停止缓存同步订阅器失败: {e}")

