#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运势分析相关测试任务
"""

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

from utils.data_generator import DataGenerator


class FortuneTasks(FastHttpUser):
    """运势分析测试任务类"""
    
    # 请求间隔：1-3秒
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户启动时执行"""
        self.data_generator = DataGenerator()
    
    @task(20)  # 权重20（20%）
    def test_daily_fortune_calendar(self):
        """
        测试每日运势日历查询接口
        POST /api/v1/daily-fortune-calendar/query
        """
        request_data = self.data_generator.generate_daily_fortune_request()
        
        with self.client.post(
            "/api/v1/daily-fortune-calendar/query",
            json=request_data,
            catch_response=True,
            name="每日运势查询"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    # 每日运势接口可能返回不同的数据结构，只要不是错误就认为成功
                    if "error" not in result or not result.get("error"):
                        response.success()
                    else:
                        response.failure(f"业务逻辑失败: {result.get('error', '未知错误')}")
                except Exception as e:
                    response.failure(f"响应解析失败: {str(e)}")
            elif response.status_code == 429:
                response.failure("触发限流")
            else:
                response.failure(f"HTTP错误: {response.status_code}")
