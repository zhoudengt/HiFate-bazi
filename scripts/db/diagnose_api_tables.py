#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全链路诊断脚本 - 检查API接口依赖的数据库表
诊断：rizhu_liujiazi, wuxing_attributes, shishen_patterns 表
"""

import sys
import os
import time

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from shared.config.database import get_mysql_connection, return_mysql_connection
from server.services.rizhu_liujiazi_service import RizhuLiujiaziService
from server.services.config_service import ConfigService


def check_table_exists(cursor, table_name: str) -> bool:
    """检查表是否存在"""
    try:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        result = cursor.fetchone()
        if isinstance(result, dict):
            return result is not None
        else:
            return result is not None and len(result) > 0
    except Exception as e:
        print(f"  ❌ 检查表 {table_name} 失败: {e}")
        return False


def check_table_data(cursor, table_name: str) -> dict:
    """检查表数据"""
    result = {
        'exists': False,
        'count': 0,
        'enabled_count': 0,
        'error': None
    }
    
    try:
        # 检查表是否存在
        if not check_table_exists(cursor, table_name):
            result['error'] = f"表 {table_name} 不存在"
            return result
        
        result['exists'] = True
        
        # 检查总记录数
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        count_result = cursor.fetchone()
        if isinstance(count_result, dict):
            result['count'] = count_result.get('count', 0)
        else:
            result['count'] = count_result[0] if count_result else 0
        
        # 检查启用状态的记录数（如果表有enabled字段）
        try:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name} WHERE enabled = 1")
            enabled_result = cursor.fetchone()
            if isinstance(enabled_result, dict):
                result['enabled_count'] = enabled_result.get('count', 0)
            else:
                result['enabled_count'] = enabled_result[0] if enabled_result else 0
        except:
            # 表可能没有enabled字段，忽略
            pass
            
    except Exception as e:
        result['error'] = str(e)
    
    return result


def test_query_performance(cursor, table_name: str, test_value: str = None) -> dict:
    """测试查询性能"""
    result = {
        'success': False,
        'time': 0,
        'error': None
    }
    
    try:
        start_time = time.time()
        
        if table_name == 'rizhu_liujiazi' and test_value:
            # 测试rizhu_liujiazi查询
            cursor.execute("""
                SELECT id, rizhu, analysis, enabled
                FROM rizhu_liujiazi
                WHERE BINARY rizhu = %s AND enabled = 1
                LIMIT 1
            """, (test_value,))
            cursor.fetchone()
        elif table_name == 'wuxing_attributes':
            # 测试wuxing_attributes查询
            cursor.execute("SELECT id, name FROM wuxing_attributes")
            cursor.fetchall()
        elif table_name == 'shishen_patterns':
            # 测试shishen_patterns查询
            cursor.execute("SELECT id, name FROM shishen_patterns")
            cursor.fetchall()
        
        elapsed = time.time() - start_time
        result['success'] = True
        result['time'] = elapsed
        
    except Exception as e:
        result['error'] = str(e)
    
    return result


def diagnose():
    """诊断API接口依赖的数据库表"""
    print("=" * 80)
    print("全链路诊断 - API接口依赖的数据库表")
    print("=" * 80)
    
    conn = None
    try:
        # 1. 检查数据库连接
        print("\n1️⃣ 检查数据库连接...")
        conn_start = time.time()
        conn = get_mysql_connection()
        conn_time = time.time() - conn_start
        
        if not conn:
            print("  ❌ 无法连接数据库")
            return
        else:
            print(f"  ✅ 数据库连接成功（耗时: {conn_time:.3f}秒）")
        
        # 2. 检查所有必需的表
        print("\n2️⃣ 检查必需的表...")
        required_tables = [
            'rizhu_liujiazi',
            'wuxing_attributes',
            'shishen_patterns'
        ]
        
        table_status = {}
        with conn.cursor() as cursor:
            for table_name in required_tables:
                print(f"\n  📋 检查表: {table_name}")
                status = check_table_data(cursor, table_name)
                table_status[table_name] = status
                
                if status['error']:
                    print(f"    ❌ {status['error']}")
                else:
                    print(f"    ✅ 表存在")
                    print(f"    📊 总记录数: {status['count']}")
                    if 'enabled_count' in status:
                        print(f"    📊 启用记录数: {status['enabled_count']}")
                    
                    # 如果表为空，给出警告
                    if status['count'] == 0:
                        print(f"    ⚠️  警告：表 {table_name} 为空！")
        
        # 3. 测试查询性能
        print("\n3️⃣ 测试查询性能...")
        with conn.cursor() as cursor:
            # 测试 rizhu_liujiazi 查询
            print(f"\n  🔍 测试 rizhu_liujiazi 查询（测试值：庚辰）...")
            perf = test_query_performance(cursor, 'rizhu_liujiazi', '庚辰')
            if perf['success']:
                print(f"    ✅ 查询成功（耗时: {perf['time']:.3f}秒）")
                if perf['time'] > 1.0:
                    print(f"    ⚠️  警告：查询较慢（>{1.0}秒）")
            else:
                print(f"    ❌ 查询失败: {perf['error']}")
            
            # 测试 wuxing_attributes 查询
            print(f"\n  🔍 测试 wuxing_attributes 查询...")
            perf = test_query_performance(cursor, 'wuxing_attributes')
            if perf['success']:
                print(f"    ✅ 查询成功（耗时: {perf['time']:.3f}秒）")
            else:
                print(f"    ❌ 查询失败: {perf['error']}")
            
            # 测试 shishen_patterns 查询
            print(f"\n  🔍 测试 shishen_patterns 查询...")
            perf = test_query_performance(cursor, 'shishen_patterns')
            if perf['success']:
                print(f"    ✅ 查询成功（耗时: {perf['time']:.3f}秒）")
            else:
                print(f"    ❌ 查询失败: {perf['error']}")
        
        # 4. 测试服务层查询
        print("\n4️⃣ 测试服务层查询...")
        
        # 测试 RizhuLiujiaziService
        print(f"\n  🔍 测试 RizhuLiujiaziService.get_rizhu_analysis('庚辰')...")
        try:
            start_time = time.time()
            result = RizhuLiujiaziService.get_rizhu_analysis('庚辰')
            elapsed = time.time() - start_time
            if result:
                print(f"    ✅ 查询成功（耗时: {elapsed:.3f}秒）")
                print(f"    📄 ID: {result.get('id')}, 日柱: {result.get('rizhu')}")
            else:
                print(f"    ⚠️  查询返回空（耗时: {elapsed:.3f}秒）")
        except Exception as e:
            print(f"    ❌ 查询失败: {e}")
        
        # 测试 ConfigService
        print(f"\n  🔍 测试 ConfigService.get_all_elements()...")
        try:
            start_time = time.time()
            elements = ConfigService.get_all_elements()
            elapsed = time.time() - start_time
            print(f"    ✅ 查询成功（耗时: {elapsed:.3f}秒）")
            print(f"    📊 五行数量: {len(elements)}")
        except Exception as e:
            print(f"    ❌ 查询失败: {e}")
        
        print(f"\n  🔍 测试 ConfigService.get_all_mingge()...")
        try:
            start_time = time.time()
            mingge = ConfigService.get_all_mingge()
            elapsed = time.time() - start_time
            print(f"    ✅ 查询成功（耗时: {elapsed:.3f}秒）")
            print(f"    📊 命格数量: {len(mingge)}")
        except Exception as e:
            print(f"    ❌ 查询失败: {e}")
        
        # 5. 总结
        print("\n" + "=" * 80)
        print("📊 诊断总结")
        print("=" * 80)
        
        all_ok = True
        for table_name, status in table_status.items():
            if status['error']:
                print(f"  ❌ {table_name}: {status['error']}")
                all_ok = False
            elif status['count'] == 0:
                print(f"  ⚠️  {table_name}: 表存在但为空")
                all_ok = False
            else:
                print(f"  ✅ {table_name}: 正常（{status['count']}条记录）")
        
        if all_ok:
            print("\n✅ 所有表检查通过")
        else:
            print("\n⚠️  发现问题，请根据上述信息修复")
        
    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            return_mysql_connection(conn)


if __name__ == '__main__':
    diagnose()

