#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理大运流年流月展示缓存
用于字段名更新后清理旧格式的缓存数据（如十神简称、小运干支等新字段）
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.redis_config import get_redis_client

def clear_fortune_display_cache():
    """清理大运流年流月展示相关的缓存"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            print("⚠️  Redis 不可用，无法清理缓存")
            return False
        
        # 清理 fortune_display 相关的缓存
        pattern = "fortune_display:*"
        
        # 使用 SCAN 迭代删除（避免阻塞）
        cursor = 0
        deleted_count = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted_count += redis_client.delete(*keys)
            if cursor == 0:
                break
        
        if deleted_count > 0:
            print(f"✅ 已清理 {deleted_count} 个 fortune_display 缓存键")
            return True
        else:
            print("ℹ️  没有找到需要清理的缓存")
            return True
    except Exception as e:
        print(f"⚠️  清理缓存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = clear_fortune_display_cache()
    sys.exit(0 if success else 1)
