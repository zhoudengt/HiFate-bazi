#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字计算相关测试任务
"""

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

from utils.data_generator import DataGenerator


class BaziTasks(FastHttpUser):
    """八字计算测试任务类"""
    
    # 请求间隔：1-3秒
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户启动时执行（每个虚拟用户只执行一次）"""
        # 初始化数据生成器
        self.data_generator = DataGenerator()
    
    @task(40)  # 权重40（40%）
    def test_bazi_calculate(self):
        """
        测试八字计算接口
        POST /api/v1/bazi/calculate
        """
        request_data = self.data_generator.generate_bazi_request()
        
        with self.client.post(
            "/api/v1/bazi/calculate",
            json=request_data,
            catch_response=True,
            name="八字计算"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("success", False):
                        response.success()
                    else:
                        response.failure(f"业务逻辑失败: {result.get('message', '未知错误')}")
                except Exception as e:
                    response.failure(f"响应解析失败: {str(e)}")
            elif response.status_code == 429:
                response.failure("触发限流")
            else:
                response.failure(f"HTTP错误: {response.status_code}")
    
    @task(30)  # 权重30（30%）
    def test_bazi_interface(self):
        """
        测试八字界面数据接口
        POST /api/v1/bazi/interface
        """
        request_data = self.data_generator.generate_bazi_interface_request()
        
        with self.client.post(
            "/api/v1/bazi/interface",
            json=request_data,
            catch_response=True,
            name="八字界面数据"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("success", False):
                        response.success()
                    else:
                        response.failure(f"业务逻辑失败: {result.get('message', '未知错误')}")
                except Exception as e:
                    response.failure(f"响应解析失败: {str(e)}")
            elif response.status_code == 429:
                response.failure("触发限流")
            else:
                response.failure(f"HTTP错误: {response.status_code}")
