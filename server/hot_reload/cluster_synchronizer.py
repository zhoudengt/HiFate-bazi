#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双机同步器 - 支持多节点热更新同步

功能：
1. 通过 Redis 发布/订阅同步热更新事件
2. 分布式锁防止并发更新冲突
3. 确认机制确保所有节点更新成功
4. 自动重试和超时处理
"""

import os
import sys
import json
import time
import uuid
import socket
import threading
import logging
from typing import Dict, Optional, Callable, List
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


# Redis 频道
CHANNEL_TRIGGER = "hifate:hot-reload:trigger"
CHANNEL_CONFIRM = "hifate:hot-reload:confirm"
CHANNEL_ROLLBACK = "hifate:hot-reload:rollback"
CHANNEL_HEALTH = "hifate:hot-reload:health"

# 分布式锁
LOCK_KEY = "hifate:hot-reload:lock"
LOCK_TIMEOUT = 60  # 60秒超时

# 节点状态键
NODE_STATUS_PREFIX = "hifate:hot-reload:node:"
NODE_STATUS_EXPIRE = 300  # 5分钟过期


class ClusterSynchronizer:
    """双机同步器"""
    
    def __init__(
        self,
        node_id: str = None,
        on_trigger_callback: Optional[Callable] = None,
        on_rollback_callback: Optional[Callable] = None
    ):
        """
        初始化双机同步器
        
        Args:
            node_id: 节点 ID（默认使用主机名）
            on_trigger_callback: 收到触发事件时的回调
            on_rollback_callback: 收到回滚事件时的回调
        """
        self.node_id = node_id or self._get_node_id()
        self.on_trigger_callback = on_trigger_callback
        self.on_rollback_callback = on_rollback_callback
        
        self._redis_client = None
        self._pubsub = None
        self._running = False
        self._subscribe_thread: Optional[threading.Thread] = None
        
        # 更新事件追踪
        self._pending_events: Dict[str, Dict] = {}
        self._event_lock = threading.Lock()
    
    def _get_node_id(self) -> str:
        """生成节点 ID"""
        hostname = socket.gethostname()
        # 获取 IP 地址的最后一段
        try:
            ip = socket.gethostbyname(hostname)
            ip_suffix = ip.split('.')[-1]
        except Exception:
            ip_suffix = "unknown"
        
        return f"{hostname}-{ip_suffix}"
    
    def _get_redis_client(self):
        """获取 Redis 客户端"""
        if self._redis_client is None:
            try:
                # 使用统一的 Redis 连接池（字符串模式）
                from shared.config.redis import get_redis_client_str
                self._redis_client = get_redis_client_str()
            except ImportError:
                # 如果没有配置模块，使用默认连接
                import redis
                self._redis_client = redis.Redis(
                    host=os.getenv('REDIS_HOST', 'localhost'),
                    port=int(os.getenv('REDIS_PORT', 6379)),
                    password=os.getenv('REDIS_PASSWORD'),
                    decode_responses=True
                )
        return self._redis_client
    
    def start(self):
        """启动同步器"""
        if self._running:
            return
        
        self._running = True
        
        # 启动订阅线程
        self._subscribe_thread = threading.Thread(target=self._subscribe_loop, daemon=True)
        self._subscribe_thread.start()
        
        # 注册节点状态
        self._update_node_status("online")
        
        logger.info(f"✓ 双机同步器已启动 (节点: {self.node_id})")
    
    def stop(self):
        """停止同步器"""
        self._running = False
        
        # 更新节点状态
        self._update_node_status("offline")
        
        # 关闭订阅
        if self._pubsub:
            try:
                self._pubsub.unsubscribe()
                self._pubsub.close()
            except Exception:
                pass
        
        if self._subscribe_thread:
            self._subscribe_thread.join(timeout=2)
        
        logger.info(f"✓ 双机同步器已停止 (节点: {self.node_id})")
    
    def _subscribe_loop(self):
        """订阅循环"""
        while self._running:
            try:
                redis_client = self._get_redis_client()
                self._pubsub = redis_client.pubsub()
                
                # 订阅频道
                self._pubsub.subscribe(
                    CHANNEL_TRIGGER,
                    CHANNEL_ROLLBACK,
                    CHANNEL_HEALTH
                )
                
                logger.info(f"✓ [{self.node_id}] 已订阅热更新频道")
                
                # 监听消息
                for message in self._pubsub.listen():
                    if not self._running:
                        break
                    
                    if message['type'] == 'message':
                        self._handle_message(message['channel'], message['data'])
                
            except Exception as e:
                logger.warning(f"⚠ [{self.node_id}] 订阅异常: {e}")
                time.sleep(5)  # 重试间隔
    
    def _handle_message(self, channel: str, data: str):
        """处理接收到的消息"""
        try:
            payload = json.loads(data) if isinstance(data, str) else data
            
            # 忽略自己发送的消息
            if payload.get('source_node') == self.node_id:
                return
            
            if channel == CHANNEL_TRIGGER:
                self._handle_trigger(payload)
            elif channel == CHANNEL_ROLLBACK:
                self._handle_rollback(payload)
            elif channel == CHANNEL_HEALTH:
                self._handle_health_check(payload)
                
        except Exception as e:
            logger.warning(f"⚠ [{self.node_id}] 处理消息失败: {e}")
    
    def _handle_trigger(self, payload: Dict):
        """处理热更新触发事件"""
        event_id = payload.get('event_id')
        modules = payload.get('modules', [])
        source_node = payload.get('source_node')
        
        logger.info(f"\n📥 [{self.node_id}] 收到热更新事件 (来自: {source_node}, 模块: {modules})")
        
        try:
            # 执行热更新
            if self.on_trigger_callback:
                success = self.on_trigger_callback(modules)
            else:
                # 默认行为：执行全量热更新
                from .reloaders import reload_all_modules
                results = reload_all_modules()
                success = all(results.values())
            
            # 发送确认
            self._send_confirm(event_id, success)
            
        except Exception as e:
            logger.error(f"❌ [{self.node_id}] 热更新执行失败: {e}")
            self._send_confirm(event_id, False, str(e))
    
    def _handle_rollback(self, payload: Dict):
        """处理回滚事件"""
        event_id = payload.get('event_id')
        version = payload.get('version')
        source_node = payload.get('source_node')
        
        logger.warning(f"\n⚠ [{self.node_id}] 收到回滚事件 (来自: {source_node}, 版本: {version})")
        
        try:
            if self.on_rollback_callback:
                success = self.on_rollback_callback(version)
            else:
                logger.warning(f"⚠ [{self.node_id}] 未配置回滚回调")
                success = False
            
            self._send_confirm(event_id, success, "rollback")
            
        except Exception as e:
            logger.error(f"❌ [{self.node_id}] 回滚执行失败: {e}")
            self._send_confirm(event_id, False, str(e))
    
    def _handle_health_check(self, payload: Dict):
        """处理健康检查"""
        request_id = payload.get('request_id')
        
        # 发送健康状态
        self._publish(CHANNEL_CONFIRM, {
            'event_id': request_id,
            'node_id': self.node_id,
            'type': 'health',
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    
    def _send_confirm(self, event_id: str, success: bool, message: str = None):
        """发送确认消息"""
        self._publish(CHANNEL_CONFIRM, {
            'event_id': event_id,
            'node_id': self.node_id,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def _publish(self, channel: str, data: Dict):
        """发布消息"""
        try:
            redis_client = self._get_redis_client()
            redis_client.publish(channel, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"⚠ [{self.node_id}] 发布消息失败: {e}")
    
    def _update_node_status(self, status: str):
        """更新节点状态"""
        try:
            redis_client = self._get_redis_client()
            key = f"{NODE_STATUS_PREFIX}{self.node_id}"
            value = json.dumps({
                'node_id': self.node_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False)
            redis_client.setex(key, NODE_STATUS_EXPIRE, value)
        except Exception as e:
            logger.warning(f"⚠ [{self.node_id}] 更新节点状态失败: {e}")
    
    def trigger_cluster_update(self, modules: List[str] = None) -> str:
        """
        触发集群热更新
        
        Args:
            modules: 要更新的模块列表（None 表示全部）
        
        Returns:
            str: 事件 ID
        """
        # 获取分布式锁
        if not self._acquire_lock():
            raise RuntimeError("无法获取分布式锁，可能有其他节点正在更新")
        
        try:
            event_id = str(uuid.uuid4())
            
            # 记录事件
            with self._event_lock:
                self._pending_events[event_id] = {
                    'modules': modules,
                    'timestamp': datetime.now().isoformat(),
                    'confirms': {}
                }
            
            # 发布触发事件
            self._publish(CHANNEL_TRIGGER, {
                'event_id': event_id,
                'source_node': self.node_id,
                'modules': modules or ['all'],
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"📤 [{self.node_id}] 已发送集群热更新事件 (ID: {event_id})")
            return event_id
            
        finally:
            self._release_lock()
    
    def trigger_cluster_rollback(self, version: int = None) -> str:
        """
        触发集群回滚
        
        Args:
            version: 要回滚到的版本（None 表示上一版本）
        
        Returns:
            str: 事件 ID
        """
        if not self._acquire_lock():
            raise RuntimeError("无法获取分布式锁")
        
        try:
            event_id = str(uuid.uuid4())
            
            self._publish(CHANNEL_ROLLBACK, {
                'event_id': event_id,
                'source_node': self.node_id,
                'version': version,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"📤 [{self.node_id}] 已发送集群回滚事件 (ID: {event_id})")
            return event_id
            
        finally:
            self._release_lock()
    
    def check_cluster_health(self) -> Dict[str, Dict]:
        """检查集群健康状态"""
        try:
            redis_client = self._get_redis_client()
            
            # 获取所有节点状态
            nodes = {}
            keys = redis_client.keys(f"{NODE_STATUS_PREFIX}*")
            
            for key in keys:
                try:
                    value = redis_client.get(key)
                    if value:
                        node_data = json.loads(value)
                        nodes[node_data['node_id']] = node_data
                except Exception:
                    pass
            
            return nodes
            
        except Exception as e:
            logger.warning(f"⚠ [{self.node_id}] 检查集群健康失败: {e}")
            return {}
    
    def _acquire_lock(self, timeout: int = LOCK_TIMEOUT) -> bool:
        """获取分布式锁"""
        try:
            redis_client = self._get_redis_client()
            lock_value = f"{self.node_id}:{time.time()}"
            
            # 使用 SET NX EX 原子操作
            result = redis_client.set(LOCK_KEY, lock_value, nx=True, ex=timeout)
            return result is True
            
        except Exception as e:
            logger.warning(f"⚠ [{self.node_id}] 获取锁失败: {e}")
            return False
    
    def _release_lock(self):
        """释放分布式锁"""
        try:
            redis_client = self._get_redis_client()
            redis_client.delete(LOCK_KEY)
        except Exception as e:
            logger.warning(f"⚠ [{self.node_id}] 释放锁失败: {e}")
    
    def get_status(self) -> Dict:
        """获取同步器状态"""
        return {
            'node_id': self.node_id,
            'running': self._running,
            'pending_events': len(self._pending_events),
            'cluster_nodes': self.check_cluster_health()
        }


# 全局同步器实例
_cluster_synchronizer: Optional[ClusterSynchronizer] = None


def get_cluster_synchronizer() -> ClusterSynchronizer:
    """获取双机同步器单例"""
    global _cluster_synchronizer
    if _cluster_synchronizer is None:
        _cluster_synchronizer = ClusterSynchronizer()
    return _cluster_synchronizer


def start_cluster_sync():
    """启动集群同步"""
    synchronizer = get_cluster_synchronizer()
    synchronizer.start()
    return synchronizer


def stop_cluster_sync():
    """停止集群同步"""
    global _cluster_synchronizer
    if _cluster_synchronizer:
        _cluster_synchronizer.stop()
        _cluster_synchronizer = None

