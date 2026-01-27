#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Locust 压力测试主入口文件

使用方式：
    # Web UI 模式
    locust -f locustfile.py --host=http://your-server:8001

    # 命令行模式
    locust -f locustfile.py --host=http://your-server:8001 \
        --users 30 --spawn-rate 5 --run-time 5m --headless
"""

from locust import HttpUser, task, between
from locust.contrib.fasthttp import FastHttpUser


class WebsiteUser(HttpUser):
    """
    综合测试用户类
    组合所有测试任务，按权重分配请求
    """
    
    # 请求间隔：1-3秒（避免触发限流）
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户启动时执行"""
        # 可以在这里添加登录等初始化操作（如果需要）
        pass
    
    # 八字计算任务（权重40%）
    @task(40)
    def test_bazi_calculate(self):
        """测试八字计算接口"""
        from utils.data_generator import DataGenerator
        generator = DataGenerator()
        request_data = generator.generate_bazi_request()
        
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
    
    # 八字界面数据任务（权重30%）
    @task(30)
    def test_bazi_interface(self):
        """测试八字界面数据接口"""
        from utils.data_generator import DataGenerator
        generator = DataGenerator()
        request_data = generator.generate_bazi_interface_request()
        
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
    
    # 每日运势任务（权重20%）
    @task(20)
    def test_daily_fortune(self):
        """测试每日运势查询接口"""
        from utils.data_generator import DataGenerator
        generator = DataGenerator()
        request_data = generator.generate_daily_fortune_request()
        
        with self.client.post(
            "/api/v1/daily-fortune-calendar/query",
            json=request_data,
            catch_response=True,
            name="每日运势查询"
        ) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
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
    
    # 健康检查任务（权重10%）
    @task(10)
    def test_health_check(self):
        """测试健康检查接口"""
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


# 可选：使用 FastHttpUser 提升性能（如果服务器支持 HTTP/2）
# class FastWebsiteUser(FastHttpUser):
#     """使用 FastHttpUser 的版本（性能更好）"""
#     wait_time = between(1, 3)
#     # ... 任务定义同上 ...
