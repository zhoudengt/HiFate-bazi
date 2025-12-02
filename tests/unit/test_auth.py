#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证服务单元测试
"""

import pytest
import sys
import os
from datetime import datetime, timedelta, timezone

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.utils.auth import create_access_token, verify_token


class TestAuth:
    """认证工具测试类"""
    
    def test_create_access_token(self):
        """测试创建 Token"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data, expires_minutes=60)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_success(self):
        """测试验证有效 Token"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data, expires_minutes=60)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"
        assert "exp" in payload
    
    def test_verify_token_expired(self):
        """测试验证过期 Token"""
        data = {"sub": "test_user"}
        # 创建已过期的 Token（过期时间设为过去）
        token = create_access_token(data, expires_minutes=-1)
        
        # 等待一秒确保过期
        import time
        time.sleep(1)
        
        with pytest.raises(Exception):  # 可能是 HTTPException 或其他异常
            verify_token(token)
    
    def test_verify_token_invalid(self):
        """测试验证无效 Token"""
        invalid_token = "invalid_token_string"
        
        with pytest.raises(Exception):
            verify_token(invalid_token)
    
    def test_token_expires_in(self):
        """测试 Token 过期时间"""
        data = {"sub": "test_user"}
        token = create_access_token(data, expires_minutes=30)
        
        payload = verify_token(token)
        exp = payload["exp"]
        
        # 验证过期时间在合理范围内（30分钟左右）
        now = datetime.now(timezone.utc).timestamp()
        expected_exp = now + 30 * 60
        
        # 允许 5 秒误差
        assert abs(exp - expected_exp) < 5

