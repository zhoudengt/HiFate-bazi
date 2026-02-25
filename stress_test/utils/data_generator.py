#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据生成器
用于生成八字计算、运势查询等API所需的测试数据
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List
from faker import Faker

# 初始化 Faker（支持中文）
fake = Faker('zh_CN')


class DataGenerator:
    """测试数据生成器"""
    
    # 常见城市及其经纬度（用于时区转换测试）
    CITIES = {
        "北京": {"latitude": 39.90, "longitude": 116.40},
        "上海": {"latitude": 31.23, "longitude": 121.47},
        "广州": {"latitude": 23.13, "longitude": 113.27},
        "深圳": {"latitude": 22.54, "longitude": 114.07},
        "成都": {"latitude": 30.67, "longitude": 104.07},
        "杭州": {"latitude": 30.27, "longitude": 120.15},
        "西安": {"latitude": 34.27, "longitude": 108.95},
        "南京": {"latitude": 32.04, "longitude": 118.78},
    }
    
    @staticmethod
    def generate_birth_date() -> str:
        """
        生成随机出生日期（阳历）
        
        Returns:
            日期字符串，格式：YYYY-MM-DD
        """
        # 生成 1950-2010 年之间的随机日期
        start_date = datetime(1950, 1, 1)
        end_date = datetime(2010, 12, 31)
        
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        random_date = start_date + timedelta(days=random_days)
        
        return random_date.strftime("%Y-%m-%d")
    
    @staticmethod
    def generate_birth_time() -> str:
        """
        生成随机出生时间
        
        Returns:
            时间字符串，格式：HH:MM
        """
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        return f"{hour:02d}:{minute:02d}"
    
    @staticmethod
    def generate_gender() -> str:
        """
        生成随机性别
        
        Returns:
            'male' 或 'female'
        """
        return random.choice(['male', 'female'])
    
    @staticmethod
    def generate_calendar_type() -> str:
        """
        生成随机历法类型
        
        Returns:
            'solar' 或 'lunar'（80% 概率为 solar）
        """
        return 'solar' if random.random() < 0.8 else 'lunar'
    
    @staticmethod
    def generate_location() -> tuple:
        """
        生成随机地点信息
        
        Returns:
            (location_name, latitude, longitude) 或 (None, None, None)
        """
        if random.random() < 0.7:  # 70% 概率包含地点信息
            city = random.choice(list(DataGenerator.CITIES.keys()))
            city_info = DataGenerator.CITIES[city]
            return (city, city_info["latitude"], city_info["longitude"])
        return (None, None, None)
    
    @classmethod
    def generate_bazi_request(cls) -> Dict[str, Any]:
        """
        生成八字计算请求数据
        
        Returns:
            请求数据字典
        """
        location, latitude, longitude = cls.generate_location()
        
        request_data = {
            "solar_date": cls.generate_birth_date(),
            "solar_time": cls.generate_birth_time(),
            "gender": cls.generate_gender(),
            "calendar_type": cls.generate_calendar_type(),
        }
        
        # 可选字段
        if location:
            request_data["location"] = location
        if latitude:
            request_data["latitude"] = latitude
        if longitude:
            request_data["longitude"] = longitude
        
        return request_data
    
    @classmethod
    def generate_bazi_interface_request(cls) -> Dict[str, Any]:
        """
        生成八字界面数据请求（与八字计算类似，但可能包含额外参数）
        
        Returns:
            请求数据字典
        """
        return cls.generate_bazi_request()
    
    @classmethod
    def generate_daily_fortune_request(cls) -> Dict[str, Any]:
        """
        生成每日运势查询请求数据
        
        Returns:
            请求数据字典
        """
        # 生成查询日期（可选，默认今天）
        date = None
        if random.random() < 0.5:  # 50% 概率指定日期
            days_offset = random.randint(-30, 30)  # 前后30天
            query_date = datetime.now() + timedelta(days=days_offset)
            date = query_date.strftime("%Y-%m-%d")
        
        request_data = {
            "date": date,
        }
        
        # 可选：包含用户生辰信息（30% 概率）
        if random.random() < 0.3:
            location, latitude, longitude = cls.generate_location()
            request_data.update({
                "solar_date": cls.generate_birth_date(),
                "solar_time": cls.generate_birth_time(),
                "gender": cls.generate_gender(),
                "calendar_type": cls.generate_calendar_type(),
            })
            
            if location:
                request_data["location"] = location
            if latitude:
                request_data["latitude"] = latitude
            if longitude:
                request_data["longitude"] = longitude
        
        return request_data

    # ---------- 300 用户压测：不重复用户、不命中缓存 ----------
    _UNIQUE_POOL: List[Dict[str, Any]] = []
    _POOL_SIZE = 300

    @classmethod
    def _build_unique_pool(cls) -> None:
        """预生成 300 个互不相同的 (solar_date, solar_time, gender) 档案，用于 300 用户压测。"""
        if cls._UNIQUE_POOL:
            return
        seen = set()
        pool = []
        for _ in range(cls._POOL_SIZE * 2):  # 多试几次以防重复
            if len(pool) >= cls._POOL_SIZE:
                break
            req = cls.generate_bazi_request()
            key = (req["solar_date"], req["solar_time"], req["gender"])
            if key not in seen:
                seen.add(key)
                pool.append(req)
        cls._UNIQUE_POOL = pool[: cls._POOL_SIZE]

    @classmethod
    def get_unique_profile(cls, user_index: int) -> Dict[str, Any]:
        """获取第 user_index 个唯一档案（0..299），保证 300 用户不重复。"""
        cls._build_unique_pool()
        idx = user_index % len(cls._UNIQUE_POOL)
        return cls._UNIQUE_POOL[idx].copy()

    @classmethod
    def perturb_profile(cls, profile: Dict[str, Any]) -> Dict[str, Any]:
        """在档案上做小幅扰动，使本次请求的缓存 key 与之前不同，避免命中缓存。"""
        from datetime import datetime, timedelta
        out = profile.copy()
        base_date = datetime.strptime(out["solar_date"], "%Y-%m-%d")
        day_offset = random.randint(-5, 5)
        new_date = base_date + timedelta(days=day_offset)
        out["solar_date"] = new_date.strftime("%Y-%m-%d")
        h, m = map(int, out["solar_time"].split(":"))
        m = (m + random.randint(-25, 25)) % 60
        h = (h + (m // 60) if m < 0 else h) % 24
        m = m % 60
        out["solar_time"] = f"{h:02d}:{m:02d}"
        return out

    @classmethod
    def generate_daily_fortune_stream_request(cls) -> Dict[str, Any]:
        """生成每日运势流式接口请求（需含 date、solar_date、solar_time、gender）"""
        days_offset = random.randint(-30, 30)
        query_date = datetime.now() + timedelta(days=days_offset)
        return {
            "date": query_date.strftime("%Y-%m-%d"),
            "solar_date": cls.generate_birth_date(),
            "solar_time": cls.generate_birth_time(),
            "gender": cls.generate_gender(),
            "calendar_type": cls.generate_calendar_type(),
        }

    @classmethod
    def generate_payment_create_request(cls) -> Dict[str, Any]:
        """生成支付创建订单请求（Stripe 测试用）"""
        return {
            "provider": "stripe",
            "amount": "4.10",
            "currency": "USD",
            "product_name": "压测产品",
            "customer_email": "stress_test@example.com",
            "success_url": "http://localhost:5173/payment/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "http://localhost:5173/payment/cancel",
        }

    @staticmethod
    def get_minimal_png_base64() -> str:
        """最小 1x1 PNG Base64（面相/风水等文件上传用）"""
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    
    @staticmethod
    def generate_test_scenarios() -> List[Dict[str, Any]]:
        """
        生成预设的测试场景（覆盖边界情况）
        
        Returns:
            测试场景列表
        """
        scenarios = [
            # 场景1：标准阳历日期
            {
                "name": "标准阳历日期",
                "solar_date": "1990-05-15",
                "solar_time": "14:30",
                "gender": "male",
                "calendar_type": "solar",
            },
            # 场景2：农历日期
            {
                "name": "农历日期",
                "solar_date": "1990-05-15",
                "solar_time": "08:00",
                "gender": "female",
                "calendar_type": "lunar",
            },
            # 场景3：带地点信息
            {
                "name": "带地点信息",
                "solar_date": "1985-10-20",
                "solar_time": "12:00",
                "gender": "male",
                "calendar_type": "solar",
                "location": "北京",
                "latitude": 39.90,
                "longitude": 116.40,
            },
            # 场景4：边界时间（午夜）
            {
                "name": "午夜时间",
                "solar_date": "2000-01-01",
                "solar_time": "00:00",
                "gender": "female",
                "calendar_type": "solar",
            },
            # 场景5：边界时间（23:59）
            {
                "name": "接近午夜",
                "solar_date": "1995-12-31",
                "solar_time": "23:59",
                "gender": "male",
                "calendar_type": "solar",
            },
        ]
        
        return scenarios
