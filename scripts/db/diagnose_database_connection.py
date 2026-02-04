#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断数据库连接问题
检查：网络连接、端口可达性、连接超时、表存在性
"""

import sys
import os
import time
import socket

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

def test_network_connectivity(host: str, port: int, timeout: int = 5) -> dict:
    """测试网络连接"""
    result = {
        'success': False,
        'time': 0,
        'error': None
    }
    
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result_code = sock.connect_ex((host, port))
        elapsed = time.time() - start_time
        sock.close()
        
        if result_code == 0:
            result['success'] = True
            result['time'] = elapsed
        else:
            result['error'] = f"连接失败，错误码: {result_code}"
    except socket.timeout:
        result['error'] = f"连接超时（>{timeout}秒）"
    except Exception as e:
        result['error'] = str(e)
    
    return result


def diagnose():
    """诊断数据库连接问题"""
    print("=" * 80)
    print("数据库连接诊断")
    print("=" * 80)
    
    # 1. 检查环境变量
    print("\n1️⃣ 检查环境变量...")
    mysql_host = os.getenv('MYSQL_HOST', '8.210.52.217')
    mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
    print(f"  MYSQL_HOST: {mysql_host}")
    print(f"  MYSQL_PORT: {mysql_port}")
    
    # 2. 测试网络连接
    print(f"\n2️⃣ 测试网络连接 ({mysql_host}:{mysql_port})...")
    net_result = test_network_connectivity(mysql_host, mysql_port, timeout=10)
    if net_result['success']:
        print(f"  ✅ 网络连接成功（耗时: {net_result['time']:.3f}秒）")
    else:
        print(f"  ❌ 网络连接失败: {net_result['error']}")
        print(f"\n  💡 可能的原因：")
        print(f"     - 数据库服务器未启动")
        print(f"     - 防火墙阻止了连接")
        print(f"     - 网络路由问题")
        print(f"     - 端口3306未开放")
        return
    
    # 3. 测试数据库连接
    print(f"\n3️⃣ 测试数据库连接...")
    try:
        from shared.config.database import get_mysql_connection, return_mysql_connection
        
        conn_start = time.time()
        conn = get_mysql_connection()
        conn_time = time.time() - conn_start
        
        if not conn:
            print("  ❌ 无法获取数据库连接")
            return
        
        print(f"  ✅ 数据库连接成功（耗时: {conn_time:.3f}秒）")
        
        # 4. 检查必需的表
        print(f"\n4️⃣ 检查必需的表...")
        required_tables = [
            'rizhu_liujiazi',
            'wuxing_attributes',
            'shishen_patterns'
        ]
        
        with conn.cursor() as cursor:
            for table_name in required_tables:
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                result = cursor.fetchone()
                exists = result is not None
                
                if exists:
                    # 检查记录数
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count_result = cursor.fetchone()
                    count = count_result.get('count', 0) if isinstance(count_result, dict) else (count_result[0] if count_result else 0)
                    print(f"  ✅ {table_name}: 存在（{count}条记录）")
                    
                    if count == 0:
                        print(f"     ⚠️  警告：表为空！")
                else:
                    print(f"  ❌ {table_name}: 不存在")
        
        # 5. 测试查询性能
        print(f"\n5️⃣ 测试查询性能...")
        with conn.cursor() as cursor:
            # 测试 rizhu_liujiazi
            print(f"  🔍 测试 rizhu_liujiazi 查询...")
            start = time.time()
            try:
                cursor.execute("SELECT id, rizhu FROM rizhu_liujiazi WHERE rizhu = '庚辰' LIMIT 1")
                result = cursor.fetchone()
                elapsed = time.time() - start
                if result:
                    print(f"    ✅ 查询成功（耗时: {elapsed:.3f}秒）")
                else:
                    print(f"    ⚠️  查询成功但无结果（耗时: {elapsed:.3f}秒）")
            except Exception as e:
                print(f"    ❌ 查询失败: {e}")
            
            # 测试 wuxing_attributes
            print(f"  🔍 测试 wuxing_attributes 查询...")
            start = time.time()
            try:
                cursor.execute("SELECT id, name FROM wuxing_attributes")
                results = cursor.fetchall()
                elapsed = time.time() - start
                print(f"    ✅ 查询成功（耗时: {elapsed:.3f}秒，{len(results)}条记录）")
            except Exception as e:
                print(f"    ❌ 查询失败: {e}")
            
            # 测试 shishen_patterns
            print(f"  🔍 测试 shishen_patterns 查询...")
            start = time.time()
            try:
                cursor.execute("SELECT id, name FROM shishen_patterns")
                results = cursor.fetchall()
                elapsed = time.time() - start
                print(f"    ✅ 查询成功（耗时: {elapsed:.3f}秒，{len(results)}条记录）")
            except Exception as e:
                print(f"    ❌ 查询失败: {e}")
        
        return_mysql_connection(conn)
        
        print("\n" + "=" * 80)
        print("✅ 诊断完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    diagnose()

