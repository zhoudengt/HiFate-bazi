#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
健康检查相关测试任务
"""

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser


class HealthTasks(FastHttpUser):
    """健康检查测试任务类"""
    
    # 请求间隔：1-3秒
    wait_time = between(1, 3)
    
    @task(10)  # 权重10（10%）
    def test_health_check(self):
        """
        测试健康检查接口
        GET /health
        """
        with self.client.get(
            "/health",
            catch_response=True,
            name="健康检查"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("status") in ["healthy", "warning"]:
                        response.success()
                    else:
                        response.failure(f"健康状态异常: {result.get('status', 'unknown')}")
                except Exception as e:
                    response.failure(f"响应解析失败: {str(e)}")
            else:
                response.failure(f"HTTP错误: {response.status_code}")
