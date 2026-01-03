#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全链路诊断脚本 - 从网络到数据库到API的完整诊断
"""

import sys
import os
import time
import socket

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

def test_port(host: str, port: int, timeout: int = 5) -> dict:
    """测试端口连接"""
    result = {'success': False, 'time': 0, 'error': None}
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        code = sock.connect_ex((host, port))
        elapsed = time.time() - start
        sock.close()
        result['success'] = (code == 0)
        result['time'] = elapsed
        if code != 0:
            result['error'] = f"错误码: {code}"
    except socket.timeout:
        result['error'] = f"超时（>{timeout}秒）"
    except Exception as e:
        result['error'] = str(e)
    return result


def diagnose():
    """全链路诊断"""
    print("=" * 80)
    print("全链路诊断 - 从网络到数据库到API")
    print("=" * 80)
    
    # 1. 检查环境变量
    print("\n1️⃣ 检查环境变量...")
    mysql_host = os.getenv('MYSQL_HOST', '8.210.52.217')
    mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
    print(f"  MYSQL_HOST: {mysql_host}")
    print(f"  MYSQL_PORT: {mysql_port}")
    
    # 2. 测试网络连接
    print(f"\n2️⃣ 测试网络连接...")
    print(f"  🔍 Ping测试 ({mysql_host})...")
    import subprocess
    try:
        result = subprocess.run(['ping', '-c', '3', mysql_host], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"    ✅ Ping成功")
        else:
            print(f"    ❌ Ping失败")
    except:
        print(f"    ⚠️  Ping测试跳过")
    
    print(f"  🔍 端口连接测试 ({mysql_host}:{mysql_port})...")
    port_result = test_port(mysql_host, mysql_port, timeout=10)
    if port_result['success']:
        print(f"    ✅ 端口连接成功（耗时: {port_result['time']:.3f}秒）")
    else:
        print(f"    ❌ 端口连接失败: {port_result['error']}")
        print(f"\n  💡 问题分析：")
        print(f"     - 数据库服务器可能未启动")
        print(f"     - 防火墙可能阻止了3306端口")
        print(f"     - 网络路由可能有问题")
        print(f"     - 公网IP可能已变更或不可用")
        print(f"\n  🔧 建议检查：")
        print(f"     1. 检查生产服务器MySQL服务是否运行")
        print(f"     2. 检查防火墙是否开放3306端口")
        print(f"     3. 检查网络连接是否正常")
        print(f"     4. 如果是本地开发，检查是否需要使用内网IP")
        return
    
    # 3. 测试数据库连接
    print(f"\n3️⃣ 测试数据库连接...")
    try:
        from server.config.mysql_config import get_mysql_connection, return_mysql_connection
        
        start = time.time()
        conn = get_mysql_connection()
        elapsed = time.time() - start
        
        if not conn:
            print("  ❌ 无法获取数据库连接")
            return
        
        print(f"  ✅ 数据库连接成功（耗时: {elapsed:.3f}秒）")
        
        # 4. 检查表
        print(f"\n4️⃣ 检查必需的表...")
        tables = ['rizhu_liujiazi', 'wuxing_attributes', 'shishen_patterns']
        with conn.cursor() as cursor:
            for table in tables:
                cursor.execute("SHOW TABLES LIKE %s", (table,))
                exists = cursor.fetchone() is not None
                if exists:
                    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                    cnt = cursor.fetchone().get('cnt', 0)
                    print(f"  ✅ {table}: 存在（{cnt}条）")
                else:
                    print(f"  ❌ {table}: 不存在")
        
        return_mysql_connection(conn)
        
    except Exception as e:
        print(f"  ❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    diagnose()

