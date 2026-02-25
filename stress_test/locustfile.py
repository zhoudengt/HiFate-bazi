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
    
    # ===== 基础接口 =====
    @task(4)
    def test_pan_display(self):
        """基本排盘"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_json_check("/api/v1/bazi/pan/display", req, "基本排盘")

    @task(4)
    def test_fortune_display(self):
        """专业排盘-大运流年流月"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_json_check("/api/v1/bazi/fortune/display", req, "专业排盘")

    @task(4)
    def test_shengong_minggong(self):
        """身宫命宫胎元"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_json_check("/api/v1/bazi/shengong-minggong", req, "身宫命宫")

    @task(4)
    def test_rizhu_liujiazi(self):
        """日元六十甲子"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_json_check("/api/v1/bazi/rizhu-liujiazi", req, "日元六十甲子")

    # ===== 流式接口（需消费响应体）=====
    @task(3)
    def test_wuxing_proportion_stream(self):
        """五行占比流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/bazi/wuxing-proportion/stream", req, "五行占比流式")

    @task(3)
    def test_xishen_jishen_stream(self):
        """喜神忌神流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/bazi/xishen-jishen/stream", req, "喜神忌神流式")

    @task(2)
    def test_marriage_stream(self):
        """感情婚姻流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/bazi/marriage-analysis/stream", req, "婚姻流式")

    @task(2)
    def test_career_wealth_stream(self):
        """事业财富流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/career-wealth/stream", req, "事业流式")

    @task(2)
    def test_children_study_stream(self):
        """子女学习流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/children-study/stream", req, "子女流式")

    @task(2)
    def test_health_stream(self):
        """身体健康流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/health/stream", req, "健康流式")

    @task(2)
    def test_general_review_stream(self):
        """总评分析流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/general-review/stream", req, "总评流式")

    @task(2)
    def test_annual_report_stream(self):
        """年运报告流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_bazi_request()
        self._post_stream_check("/api/v1/annual-report/stream", req, "年运流式")

    @task(2)
    def test_daily_fortune_stream(self):
        """每日运势日历流式"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_daily_fortune_stream_request()
        self._post_stream_check("/api/v1/daily-fortune-calendar/stream", req, "每日运势流式")

    # ===== 面相/办公桌风水（multipart）=====
    @task(1)
    def test_face_analyze_stream(self):
        """面相分析流式"""
        self._post_multipart_stream("/api/v2/face/analyze/stream", {"analysis_types": "gongwei,liuqin"}, "面相流式")

    @task(1)
    def test_desk_fengshui_stream(self):
        """办公桌风水流式"""
        self._post_multipart_stream("/api/v2/desk-fengshui/analyze/stream", {}, "办公桌风水流式")

    # ===== 支付接口 =====
    @task(2)
    def test_payment_providers(self):
        """支付渠道状态"""
        with self.client.get("/api/v1/payment/providers", catch_response=True, name="支付渠道") as r:
            self._check_http_200(r)

    @task(1)
    def test_payment_create(self):
        """Stripe创建订单"""
        from utils.data_generator import DataGenerator
        req = DataGenerator.generate_payment_create_request()
        with self.client.post("/api/v1/payment/unified/create", json=req, catch_response=True, name="支付创建") as r:
            self._check_http_200(r)

    # ===== 辅助方法 =====
    def _post_json_check(self, path, payload, name):
        with self.client.post(path, json=payload, catch_response=True, name=name) as r:
            if r.status_code == 200:
                try:
                    d = r.json()
                    if d.get("success", False):
                        r.success()
                    else:
                        r.failure(d.get("message", "业务失败"))
                except Exception as e:
                    r.failure(str(e))
            elif r.status_code == 429:
                r.failure("限流")
            else:
                r.failure(f"HTTP{r.status_code}")

    def _post_stream_check(self, path, payload, name):
        with self.client.post(path, json=payload, stream=True, catch_response=True, name=name, timeout=100) as r:
            if r.status_code != 200:
                r.failure(f"HTTP{r.status_code}")
            else:
                n = 0
                for _ in r.iter_lines(decode_unicode=True):
                    n += 1
                    if n > 100:
                        break
                r.success()

    def _post_multipart_stream(self, path, form_data, name):
        import base64
        from utils.data_generator import DataGenerator
        raw = base64.b64decode(DataGenerator.get_minimal_png_base64())
        files = {"image": ("test.png", raw, "image/png")}
        with self.client.post(path, files=files, data=form_data, stream=True, catch_response=True, name=name, timeout=90) as r:
            if r.status_code != 200:
                r.failure(f"HTTP{r.status_code}")
            else:
                n = 0
                for _ in r.iter_lines(decode_unicode=True):
                    n += 1
                    if n > 50:
                        break
                r.success()

    def _check_http_200(self, r):
        if r.status_code == 200:
            try:
                d = r.json()
                if d.get("success", True):
                    r.success()
                else:
                    r.failure(d.get("message", "业务失败"))
            except Exception:
                r.success()
        elif r.status_code == 429:
            r.failure("限流")
        else:
            r.failure(f"HTTP{r.status_code}")

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
