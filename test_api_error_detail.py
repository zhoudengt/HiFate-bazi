#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json

url = "http://localhost:8001/api/v1/smart-fortune/smart-analyze-stream"
params = {
    "category": "事业财富",
    "year": 1990,
    "month": 5,
    "day": 15,
    "hour": 14,
    "gender": "male",
    "user_id": "test_user_001"
}

try:
    response = requests.get(url, params=params, timeout=5)
    print(f"状态码: {response.status_code}")
    if response.status_code == 422:
        try:
            error_detail = response.json()
            print(f"\n错误详情:")
            print(json.dumps(error_detail, ensure_ascii=False, indent=2))
        except:
            print(f"\n响应内容: {response.text}")
    else:
        print(f"响应: {response.text[:200]}")
except Exception as e:
    print(f"异常: {e}")

