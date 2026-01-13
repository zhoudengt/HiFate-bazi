#!/bin/bash
# 启用所有优化功能的环境变量配置
# 
# 使用方法：
#   source scripts/test/enable_all_features.sh
#   或者
#   . scripts/test/enable_all_features.sh

echo "=========================================="
echo "启用所有优化功能"
echo "=========================================="

# 熔断器配置
export ENABLE_CIRCUIT_BREAKER=true
export CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
export CIRCUIT_BREAKER_TIMEOUT=30.0
export CIRCUIT_BREAKER_SUCCESS_THRESHOLD=3

# 重试配置
export GRPC_MAX_RETRIES=3
export GRPC_RETRY_DELAY=1.0

# 缓存版本控制
export ENABLE_CACHE_VERSION=true
export CACHE_VERSION=v1

# 监控指标收集
export ENABLE_METRICS_COLLECTION=true

echo "✓ 熔断器: 已启用 (失败阈值=${CIRCUIT_BREAKER_FAILURE_THRESHOLD}, 超时=${CIRCUIT_BREAKER_TIMEOUT}s)"
echo "✓ 自动重试: 已启用 (最大重试=${GRPC_MAX_RETRIES}次, 延迟=${GRPC_RETRY_DELAY}s)"
echo "✓ 缓存版本控制: 已启用 (版本=${CACHE_VERSION})"
echo "✓ 监控指标收集: 已启用"
echo ""
echo "所有优化功能已启用！"
echo "=========================================="
