#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则客户端适配器
将现有的 BaziRuleClient 适配为接口实现

增强功能（可选启用）：
- 熔断器保护
- 自动重试
- 监控指标收集
"""

import sys
import os
import time
import logging
from typing import Dict, Any, Optional, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.interfaces.bazi_rule_client_interface import IBaziRuleClient

logger = logging.getLogger(__name__)


class BaziRuleClientAdapter(IBaziRuleClient):
    """规则客户端适配器（实现接口）"""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        """
        初始化适配器
        
        Args:
            base_url: 服务地址
            timeout: 超时时间
        """
        # 延迟导入，避免导入时依赖 gRPC
        from src.clients.bazi_rule_client_grpc import BaziRuleClient as GrpcBaziRuleClient
        self._client = GrpcBaziRuleClient(base_url=base_url, timeout=timeout)
        self._base_url = base_url
        self._timeout = timeout
        
        # 新增：熔断器（可选，默认关闭）
        self._enable_circuit_breaker = os.getenv("ENABLE_CIRCUIT_BREAKER", "false").lower() == "true"
        self._circuit_breaker = None
        
        if self._enable_circuit_breaker:
            try:
                from server.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
                config = CircuitBreakerConfig(
                    failure_threshold=int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")),
                    timeout=float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "30.0"))
                )
                self._circuit_breaker = CircuitBreaker.get("bazi-rule", config=config)
                logger.info("熔断器已启用: bazi-rule")
            except Exception as e:
                logger.warning(f"启用熔断器失败: {e}，将使用原有逻辑")
                self._enable_circuit_breaker = False
        
        # 新增：监控指标收集（可选，默认启用）
        self._enable_metrics = os.getenv("ENABLE_METRICS_COLLECTION", "true").lower() == "true"
        self._metrics_collector = None
        
        if self._enable_metrics:
            try:
                from server.utils.metrics_collector import get_metrics_collector
                self._metrics_collector = get_metrics_collector()
            except Exception as e:
                logger.warning(f"启用监控指标收集失败: {e}")
                self._enable_metrics = False
    
    def match_rules(self, 
                   solar_date: str, 
                   solar_time: str, 
                   gender: str,
                   rule_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        匹配规则（实现接口）
        
        增强功能（可选）：
        - 熔断器保护
        - 自动重试
        - 监控指标收集
        """
        if self._enable_circuit_breaker or self._enable_metrics:
            return self._call_with_protection(solar_date, solar_time, gender, rule_types)
        
        # 原有逻辑不变（默认情况）
        return self._client.match_rules(solar_date, solar_time, gender, rule_types)
    
    def _call_with_protection(
        self,
        solar_date: str,
        solar_time: str,
        gender: str,
        rule_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """带熔断和重试的调用"""
        start_time = time.time()
        success = True
        error_type = None
        
        # 熔断器检查
        if self._enable_circuit_breaker and self._circuit_breaker:
            if not self._circuit_breaker.allow_request():
                from server.core.circuit_breaker import CircuitBreakerOpen
                error_type = "CircuitBreakerOpen"
                if self._enable_metrics and self._metrics_collector:
                    duration = time.time() - start_time
                    self._metrics_collector.record_grpc_call(
                        "bazi-rule", "match_rules",
                        success=False, duration=duration, error_type=error_type
                    )
                raise CircuitBreakerOpen("bazi-rule", "Circuit breaker is open")
        
        # 重试逻辑
        max_retries = int(os.getenv("GRPC_MAX_RETRIES", "3"))
        retry_delay = float(os.getenv("GRPC_RETRY_DELAY", "1.0"))
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                result = self._client.match_rules(solar_date, solar_time, gender, rule_types)
                
                # 记录成功
                if self._enable_circuit_breaker and self._circuit_breaker:
                    self._circuit_breaker.record_success()
                
                # 记录监控指标
                if self._enable_metrics and self._metrics_collector:
                    duration = time.time() - start_time
                    self._metrics_collector.record_grpc_call(
                        "bazi-rule", "match_rules",
                        success=True, duration=duration
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                
                # 记录失败
                if self._enable_circuit_breaker and self._circuit_breaker:
                    self._circuit_breaker.record_failure(e)
                
                # 如果是最后一次重试，记录失败并抛出异常
                if attempt == max_retries - 1:
                    if self._enable_metrics and self._metrics_collector:
                        duration = time.time() - start_time
                        self._metrics_collector.record_grpc_call(
                            "bazi-rule", "match_rules",
                            success=False, duration=duration, error_type=error_type
                        )
                    raise
                
                # 等待后重试
                logger.warning(
                    f"bazi-rule 调用失败（尝试 {attempt + 1}/{max_retries}）: {e}，"
                    f"{retry_delay} 秒后重试..."
                )
                time.sleep(retry_delay)
        
        # 所有重试都失败
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("调用失败，但未捕获异常")

