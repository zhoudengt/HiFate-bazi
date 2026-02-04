#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理每日运势日历缓存
用于字段名更新后清理旧格式的缓存数据
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from shared.config.redis import get_redis_client

def clear_daily_fortune_cache():
    """清理每日运势日历相关的缓存"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("⚠️  Redis 不可用，无法清理缓存")
            return False
        
        # 清理每日运势日历相关的缓存
        pattern = "daily_fortune:calendar:*"
        keys = redis_client.keys(pattern)
        
        if keys:
            redis_client.delete(*keys)
            print(f"✅ 已清理 {len(keys)} 个每日运势日历缓存键")
            return True
        else:
            print("ℹ️  没有找到需要清理的缓存")
            return True
    except Exception as e:
        print(f"⚠️  清理缓存失败: {e}")
        return False

if __name__ == '__main__':
    success = clear_daily_fortune_cache()
    sys.exit(0 if success else 1)
