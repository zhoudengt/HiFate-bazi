#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务健康检查

功能：
- 定期检查服务健康状态
- 支持多种检查方式
- 自动更新服务状态
"""

import time
import threading
import logging
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"      # 降级（部分功能可用）
    UNKNOWN = "unknown"


class CheckType(Enum):
    """检查类型"""
    TCP = "tcp"               # TCP 连接检查
    HTTP = "http"             # HTTP 端点检查
    GRPC = "grpc"             # gRPC 健康检查
    CUSTOM = "custom"         # 自定义检查


@dataclass
class HealthCheckConfig:
    """健康检查配置"""
    interval: float = 30.0           # 检查间隔（秒）
    timeout: float = 5.0             # 超时时间（秒）
    healthy_threshold: int = 2       # 健康阈值（连续成功次数）
    unhealthy_threshold: int = 3     # 不健康阈值（连续失败次数）
    check_type: CheckType = CheckType.TCP


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    status: HealthStatus
    latency: float = 0               # 响应延迟（毫秒）
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    健康检查器
    
    使用示例：
        checker = HealthChecker()
        
        # 注册服务检查
        checker.register("bazi-core", "localhost", 9001)
        checker.register("bazi-fortune", "localhost", 9002)
        
        # 启动定期检查
        checker.start()
        
        # 获取服务状态
        status = checker.get_status("bazi-core")
        
        # 获取所有状态
        all_status = checker.get_all_status()
    """
    
    _instance: Optional['HealthChecker'] = None
    _lock = threading.Lock()
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config or HealthCheckConfig()
        self._services: Dict[str, Dict[str, Any]] = {}
        self._results: Dict[str, HealthCheckResult] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._callbacks: List[Callable] = []
    
    @classmethod
    def get_instance(cls, config: Optional[HealthCheckConfig] = None) -> 'HealthChecker':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance
    
    def register(
        self,
        name: str,
        host: str,
        port: int,
        check_type: CheckType = CheckType.TCP,
        check_path: str = "/health",
        custom_check: Optional[Callable] = None
    ):
        """
        注册服务检查
        
        Args:
            name: 服务名称
            host: 服务地址
            port: 服务端口
            check_type: 检查类型
            check_path: HTTP 检查路径
            custom_check: 自定义检查函数
        """
        self._services[name] = {
            "host": host,
            "port": port,
            "check_type": check_type,
            "check_path": check_path,
            "custom_check": custom_check,
            "consecutive_success": 0,
            "consecutive_failure": 0,
        }
        
        # 初始化结果
        self._results[name] = HealthCheckResult(
            status=HealthStatus.UNKNOWN,
            message="Not checked yet"
        )
        
        logger.info(f"注册健康检查: {name} @ {host}:{port} ({check_type.value})")
    
    def unregister(self, name: str):
        """注销服务检查"""
        if name in self._services:
            del self._services[name]
            del self._results[name]
            logger.info(f"注销健康检查: {name}")
    
    def start(self):
        """启动定期检查"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()
        logger.info(f"健康检查已启动 (间隔: {self.config.interval}s)")
    
    def stop(self):
        """停止定期检查"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("健康检查已停止")
    
    def _check_loop(self):
        """检查循环"""
        while self._running:
            try:
                self.check_all()
            except Exception as e:
                logger.error(f"健康检查循环错误: {e}")
            
            time.sleep(self.config.interval)
    
    def check_all(self):
        """检查所有服务"""
        futures = []
        for name in self._services:
            future = self._executor.submit(self._check_service, name)
            futures.append((name, future))
        
        for name, future in futures:
            try:
                result = future.result(timeout=self.config.timeout + 1)
                self._update_result(name, result)
            except Exception as e:
                logger.error(f"检查服务 {name} 失败: {e}")
                self._update_result(name, HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=str(e)
                ))
    
    def check_service(self, name: str) -> HealthCheckResult:
        """检查单个服务"""
        if name not in self._services:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Service {name} not registered"
            )
        
        result = self._check_service(name)
        self._update_result(name, result)
        return result
    
    def _check_service(self, name: str) -> HealthCheckResult:
        """执行服务检查"""
        service = self._services[name]
        check_type = service["check_type"]
        
        start_time = time.time()
        
        try:
            if check_type == CheckType.TCP:
                result = self._tcp_check(service["host"], service["port"])
            elif check_type == CheckType.HTTP:
                result = self._http_check(
                    service["host"],
                    service["port"],
                    service["check_path"]
                )
            elif check_type == CheckType.GRPC:
                result = self._grpc_check(service["host"], service["port"])
            elif check_type == CheckType.CUSTOM and service["custom_check"]:
                result = service["custom_check"](service["host"], service["port"])
            else:
                result = HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message="Unknown check type"
                )
            
            result.latency = (time.time() - start_time) * 1000
            return result
            
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency=(time.time() - start_time) * 1000,
                message=str(e)
            )
    
    def _tcp_check(self, host: str, port: int) -> HealthCheckResult:
        """TCP 连接检查"""
        import socket
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="TCP connection successful"
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"TCP connection failed: error code {result}"
                )
        except socket.timeout:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="TCP connection timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"TCP check error: {str(e)}"
            )
    
    def _http_check(self, host: str, port: int, path: str) -> HealthCheckResult:
        """HTTP 端点检查"""
        import urllib.request
        import urllib.error
        
        url = f"http://{host}:{port}{path}"
        
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                if response.status == 200:
                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        message="HTTP check successful",
                        details={"status_code": response.status}
                    )
                else:
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        message=f"HTTP returned status {response.status}",
                        details={"status_code": response.status}
                    )
        except urllib.error.URLError as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP check failed: {str(e)}"
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP check error: {str(e)}"
            )
    
    def _grpc_check(self, host: str, port: int) -> HealthCheckResult:
        """gRPC 健康检查"""
        try:
            import grpc
            from grpc_health.v1 import health_pb2, health_pb2_grpc
            
            channel = grpc.insecure_channel(
                f"{host}:{port}",
                options=[('grpc.enable_http_proxy', 0)]
            )
            
            try:
                stub = health_pb2_grpc.HealthStub(channel)
                request = health_pb2.HealthCheckRequest()
                response = stub.Check(request, timeout=self.config.timeout)
                
                if response.status == health_pb2.HealthCheckResponse.SERVING:
                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        message="gRPC health check successful"
                    )
                else:
                    return HealthCheckResult(
                        status=HealthStatus.UNHEALTHY,
                        message=f"gRPC service not serving: {response.status}"
                    )
            finally:
                channel.close()
                
        except ImportError:
            # 如果没有安装 grpc_health，使用 TCP 检查
            return self._tcp_check(host, port)
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"gRPC check error: {str(e)}"
            )
    
    def _update_result(self, name: str, result: HealthCheckResult):
        """更新检查结果"""
        service = self._services.get(name)
        if not service:
            return
        
        old_status = self._results.get(name, HealthCheckResult(status=HealthStatus.UNKNOWN)).status
        
        # 更新连续成功/失败计数
        if result.status == HealthStatus.HEALTHY:
            service["consecutive_success"] += 1
            service["consecutive_failure"] = 0
        else:
            service["consecutive_failure"] += 1
            service["consecutive_success"] = 0
        
        # 根据阈值判断最终状态
        if service["consecutive_success"] >= self.config.healthy_threshold:
            result.status = HealthStatus.HEALTHY
        elif service["consecutive_failure"] >= self.config.unhealthy_threshold:
            result.status = HealthStatus.UNHEALTHY
        
        self._results[name] = result
        
        # 状态变化时触发回调
        if old_status != result.status:
            logger.info(f"服务状态变更: {name} {old_status.value} -> {result.status.value}")
            self._notify_callbacks(name, old_status, result.status)
    
    def on_status_change(self, callback: Callable):
        """注册状态变化回调"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, name: str, old_status: HealthStatus, new_status: HealthStatus):
        """通知回调"""
        for callback in self._callbacks:
            try:
                callback(name, old_status, new_status)
            except Exception as e:
                logger.error(f"健康检查回调失败: {e}")
    
    def get_status(self, name: str) -> HealthCheckResult:
        """获取服务状态"""
        return self._results.get(name, HealthCheckResult(
            status=HealthStatus.UNKNOWN,
            message=f"Service {name} not registered"
        ))
    
    def get_all_status(self) -> Dict[str, HealthCheckResult]:
        """获取所有服务状态"""
        return self._results.copy()
    
    def is_healthy(self, name: str) -> bool:
        """检查服务是否健康"""
        result = self.get_status(name)
        return result.status == HealthStatus.HEALTHY
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = len(self._services)
        healthy = sum(1 for r in self._results.values() if r.status == HealthStatus.HEALTHY)
        unhealthy = sum(1 for r in self._results.values() if r.status == HealthStatus.UNHEALTHY)
        
        return {
            "total_services": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "degraded": total - healthy - unhealthy,
            "services": {
                name: {
                    "status": result.status.value,
                    "latency_ms": result.latency,
                    "message": result.message,
                    "last_check": result.timestamp
                }
                for name, result in self._results.items()
            }
        }


# 便捷函数
def get_health_checker(config: Optional[HealthCheckConfig] = None) -> HealthChecker:
    """获取健康检查器实例"""
    return HealthChecker.get_instance(config)
