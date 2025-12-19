#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版全面诊断：对比数据库、逻辑代码、前端展示
"""

import sys
import os
import json
import requests
import subprocess

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def check_local_db_via_sql():
    """通过 SQL 直接检查本地数据库"""
    print("\n" + "="*80)
    print("📊 步骤 1: 检查本地数据库规则（通过 SQL）")
    print("="*80)
    
    try:
        # 使用 mysql 命令行工具
        cmd = [
            'mysql',
            '-h', 'localhost',
            '-u', 'root',
            '-p123456',  # 根据实际情况修改
            'hifate_bazi',
            '-e', """
            SELECT 
                rule_type,
                COUNT(*) as total,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
            GROUP BY rule_type
            ORDER BY rule_type;
            """
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"⚠️  SQL 查询失败，尝试使用 Python 连接...")
            return False
    except Exception as e:
        print(f"⚠️  无法使用 mysql 命令行: {e}")
        return False


def check_local_db_via_python():
    """通过 Python 检查本地数据库"""
    try:
        from server.config.mysql_config import get_mysql_connection, return_mysql_connection
        import pymysql.cursors
        
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT 
                rule_type,
                COUNT(*) as total,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
            GROUP BY rule_type
            ORDER BY rule_type
        """)
        stats = cursor.fetchall()
        
        print(f"\n✅ 本地数据库规则统计:")
        total = 0
        enabled_total = 0
        for stat in stats:
            print(f"  - {stat['rule_type']}: {stat['enabled_count']} 条启用 (总计 {stat['total']} 条)")
            total += stat['total']
            enabled_total += stat['enabled_count']
        
        print(f"\n  总规则数: {total} 条")
        print(f"  启用规则数: {enabled_total} 条")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return {'total': total, 'enabled': enabled_total, 'stats': stats}
    except Exception as e:
        print(f"❌ Python 连接失败: {e}")
        return None


def test_local_api():
    """测试本地 API"""
    print("\n" + "="*80)
    print("🧪 步骤 2: 测试本地 API")
    print("="*80)
    
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    try:
        url = "http://localhost:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=10)
        response.raise_for_status()
        result = response.json()
        stats = result.get('data', {}).get('statistics', {})
        
        print(f"\n✅ 本地 API 返回:")
        print(f"  总匹配数: {stats.get('total_matched', 0)} 条")
        for key, value in stats.items():
            if key.endswith('_count'):
                print(f"  - {key}: {value}")
        
        return stats
    except Exception as e:
        print(f"⚠️  本地服务未运行: {e}")
        return None


def test_production_api():
    """测试生产环境 API"""
    print("\n" + "="*80)
    print("🧪 步骤 3: 测试生产环境 API")
    print("="*80)
    
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    try:
        url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        stats = result.get('data', {}).get('statistics', {})
        
        print(f"\n✅ 生产环境 API 返回:")
        print(f"  总匹配数: {stats.get('total_matched', 0)} 条")
        for key, value in stats.items():
            if key.endswith('_count'):
                print(f"  - {key}: {value}")
        
        return stats
    except Exception as e:
        print(f"❌ 生产环境测试失败: {e}")
        return None


def check_code_logic():
    """检查代码逻辑"""
    print("\n" + "="*80)
    print("📝 步骤 4: 检查代码逻辑")
    print("="*80)
    
    formula_file = os.path.join(project_root, 'server/api/v1/formula_analysis.py')
    rule_service_file = os.path.join(project_root, 'server/services/rule_service.py')
    
    issues = []
    
    # 检查 formula_analysis.py
    if os.path.exists(formula_file):
        with open(formula_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            print(f"\n检查 {formula_file}:")
            
            # 检查是否使用 RuleService
            if 'RuleService.match_rules' in content:
                print("  ✅ 使用 RuleService.match_rules")
            else:
                print("  ❌ 未使用 RuleService.match_rules")
                issues.append("formula_analysis.py 未使用 RuleService")
            
            # 检查是否筛选 FORMULA_ 前缀
            if 'FORMULA_' in content and 'startswith' in content:
                print("  ✅ 筛选 FORMULA_ 前缀规则")
            else:
                print("  ⚠️  未明确筛选 FORMULA_ 前缀")
            
            # 检查规则类型
            if "rule_types = ['wealth', 'marriage', 'career'" in content or "rule_types = request.rule_types" in content:
                print("  ✅ 规则类型配置正确")
            else:
                print("  ⚠️  规则类型配置可能有问题")
    else:
        print(f"  ❌ 文件不存在: {formula_file}")
        issues.append(f"文件不存在: {formula_file}")
    
    # 检查 rule_service.py
    if os.path.exists(rule_service_file):
        with open(rule_service_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            print(f"\n检查 {rule_service_file}:")
            
            # 检查 enabled 过滤
            if 'enabled = 1' in content or 'enabled = True' in content or "enabled = 1" in content:
                print("  ✅ 过滤 enabled 规则")
            else:
                print("  ⚠️  未明确过滤 enabled 规则")
                issues.append("rule_service.py 未明确过滤 enabled 规则")
            
            # 检查数据库查询
            if 'SELECT' in content and 'bazi_rules' in content:
                print("  ✅ 从数据库查询规则")
            else:
                print("  ⚠️  可能未从数据库查询规则")
    
    return issues


def check_frontend():
    """检查前端展示"""
    print("\n" + "="*80)
    print("🖥️  步骤 5: 检查前端展示")
    print("="*80)
    
    frontend_file = os.path.join(project_root, 'local_frontend/formula-analysis.html')
    
    if os.path.exists(frontend_file):
        print(f"\n✅ 前端文件存在: {frontend_file}")
        
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查关键字段
            key_fields = ['total_matched', 'wealth_count', 'career_count', 'health_count', 'summary_count']
            print(f"\n检查统计字段:")
            for field in key_fields:
                if field in content:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} - 未找到")
            
            # 检查 API 路径
            if '/api/v1/bazi/formula-analysis' in content:
                print(f"\n✅ API 路径正确")
            else:
                print(f"\n⚠️  API 路径可能错误")
    else:
        print(f"\n❌ 前端文件不存在: {frontend_file}")


def generate_fix_plan(local_stats, prod_stats, local_db):
    """生成修复计划"""
    print("\n" + "="*80)
    print("💡 修复计划")
    print("="*80)
    
    if not local_stats or not prod_stats:
        print("⚠️  数据不完整，无法生成修复计划")
        return
    
    local_total = local_stats.get('total_matched', 0)
    prod_total = prod_stats.get('total_matched', 0)
    
    print(f"\n📊 对比结果:")
    print(f"  本地匹配: {local_total} 条")
    print(f"  生产匹配: {prod_total} 条")
    print(f"  差异: {local_total - prod_total} 条")
    
    if prod_total < local_total * 0.5:
        print(f"\n🔴 严重问题: 生产环境匹配数量严重不足")
        print(f"\n修复步骤:")
        print(f"  1. 检查生产环境数据库规则数量")
        print(f"  2. 同步规则到生产环境")
        print(f"  3. 清除缓存")
        print(f"  4. 验证修复结果")
        
        sql_file = os.path.join(project_root, 'scripts/temp_rules_export.sql')
        if os.path.exists(sql_file):
            print(f"\n✅ SQL 文件已准备: {sql_file}")
            print(f"\n执行修复:")
            print(f"  bash scripts/manual_sync_rules_to_production.sh")
        else:
            print(f"\n⚠️  需要先导出 SQL 文件:")
            print(f"  python3 scripts/fix_production_rules.py")


def main():
    """主函数"""
    print("="*80)
    print("🔍 全面诊断：数据库、逻辑代码、前端展示")
    print("="*80)
    
    # 步骤 1: 检查本地数据库
    if not check_local_db_via_sql():
        local_db = check_local_db_via_python()
    else:
        local_db = None
    
    # 步骤 2: 测试本地 API
    local_stats = test_local_api()
    
    # 步骤 3: 测试生产环境 API
    prod_stats = test_production_api()
    
    # 步骤 4: 检查代码逻辑
    code_issues = check_code_logic()
    
    # 步骤 5: 检查前端
    check_frontend()
    
    # 步骤 6: 生成修复计划
    generate_fix_plan(local_stats, prod_stats, local_db)
    
    print("\n" + "="*80)
    print("✅ 诊断完成")
    print("="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  诊断被中断")
    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()

