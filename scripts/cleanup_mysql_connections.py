#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理长时间未使用的MySQL连接
"""

import sys
import os

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from server.config.mysql_config import cleanup_idle_mysql_connections

def main():
    print("=" * 60)
    print("清理长时间未使用的MySQL连接")
    print("=" * 60)
    
    # 清理超过5分钟未使用的连接
    cleaned = cleanup_idle_mysql_connections(max_idle_time=300)
    
    print(f"\n清理完成: 释放了 {cleaned} 个连接")
    print("=" * 60)

if __name__ == '__main__':
    main()

