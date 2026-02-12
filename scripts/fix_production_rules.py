#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复生产环境规则匹配问题

1. 检查生产环境数据库规则数量
2. 对比本地和生产环境规则差异
3. 同步规则到生产环境
4. 清除缓存
5. 验证修复结果
"""

import sys
import os
import json
import requests
import subprocess
from typing import Dict, List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
import pymysql.cursors


def check_local_rules() -> Dict:
    """检查本地数据库规则"""
    print("\n" + "="*80)
    print("📊 检查本地数据库规则")
    print("="*80)
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 按类型统计 FORMULA_ 规则（只统计标准格式类型）
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
        type_stats = cursor.fetchall()
        
        # 总规则数
        cursor.execute("""
            SELECT COUNT(*) as total
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
        """)
        total = cursor.fetchone()['total']
        
        result = {
            'total': total,
            'type_stats': {stat['rule_type']: stat['enabled_count'] for stat in type_stats}
        }
        
        print(f"\n✅ 本地数据库规则统计:")
        print(f"  总规则数: {total}")
        print(f"\n按类型统计:")
        for stat in type_stats:
            print(f"  - {stat['rule_type']}: {stat['enabled_count']} 条 (总计 {stat['total']} 条)")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return result
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def check_production_rules_via_api() -> Dict:
    """通过 API 检查生产环境规则（间接方式）"""
    print("\n" + "="*80)
    print("📊 检查生产环境规则（通过 API 测试）")
    print("="*80)
    
    # 测试多个用例来推断规则数量
    test_cases = [
        {'solar_date': '1987-01-07', 'solar_time': '09:00', 'gender': 'male'},
        {'solar_date': '1990-05-15', 'solar_time': '14:30', 'gender': 'female'},
    ]
    
    results = []
    for test_case in test_cases:
        try:
            url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
            response = requests.post(url, json=test_case, timeout=30)
            response.raise_for_status()
            result = response.json()
            stats = result.get('data', {}).get('statistics', {})
            results.append(stats)
            print(f"✅ 测试用例 {test_case['solar_date']}: 总匹配 {stats.get('total_matched', 0)} 条")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    return results


def export_rules_to_sql() -> str:
    """导出规则到 SQL 文件"""
    print("\n" + "="*80)
    print("📤 导出本地规则到 SQL")
    print("="*80)
    
    sql_file = os.path.join(project_root, 'scripts', 'temp_rules_export.sql')
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询所有 FORMULA_ 规则（标准格式类型）
        cursor.execute("""
            SELECT 
                rule_code, rule_name, rule_type, conditions, content, description,
                priority, enabled
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%' 
              AND rule_type IN ('wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents')
            ORDER BY rule_type, rule_code
        """)
        rules = cursor.fetchall()
        
        # 生成 SQL
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("-- 规则导出 SQL\n")
            f.write("-- 生成时间: " + str(os.popen('date').read().strip()) + "\n\n")
            f.write("START TRANSACTION;\n\n")
            
            for rule in rules:
                rule_code = rule['rule_code']
                rule_name = rule['rule_name'].replace("'", "''")
                rule_type = rule['rule_type']
                conditions = json.dumps(rule['conditions'], ensure_ascii=False).replace("'", "''")
                content = json.dumps(rule['content'], ensure_ascii=False).replace("'", "''")
                description = json.dumps(rule['description'], ensure_ascii=False).replace("'", "''") if rule['description'] else 'NULL'
                priority = rule['priority']
                enabled = 1 if rule['enabled'] else 0
                
                f.write(f"""
INSERT INTO bazi_rules (rule_code, rule_name, rule_type, conditions, content, description, priority, enabled)
VALUES ('{rule_code}', '{rule_name}', '{rule_type}', '{conditions}', '{content}', {f"'{description}'" if description != 'NULL' else 'NULL'}, {priority}, {enabled})
ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    rule_type = VALUES(rule_type),
    conditions = VALUES(conditions),
    content = VALUES(content),
    description = VALUES(description),
    priority = VALUES(priority),
    enabled = VALUES(enabled);
""")
            
            f.write("\nCOMMIT;\n")
        
        print(f"✅ 已导出 {len(rules)} 条规则到: {sql_file}")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return sql_file
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return ""


def sync_rules_to_production(sql_file: str) -> bool:
    """同步规则到生产环境"""
    print("\n" + "="*80)
    print("📤 同步规则到生产环境")
    print("="*80)
    
    if not sql_file or not os.path.exists(sql_file):
        print("❌ SQL 文件不存在")
        return False
    
    try:
        # 上传 SQL 文件到生产环境
        print("📤 上传 SQL 文件到生产环境...")
        result = subprocess.run(
            ['scp', sql_file, 'root@8.210.52.217:/tmp/rules_import.sql'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ 上传失败: {result.stderr}")
            print("💡 提示: 可能需要手动上传文件或配置 SSH 密钥")
            return False
        
        print("✅ 文件上传成功")
        
        # 在生产环境执行 SQL
        print("🔄 在生产环境执行 SQL...")
        ssh_cmd = """
cd /opt/HiFate-bazi && \
docker exec -i hifate-mysql-master mysql -uroot -p${MYSQL_PASSWORD} hifate_bazi < /tmp/rules_import.sql && \
echo "✅ 规则导入成功" || echo "❌ 规则导入失败"
"""
        
        result = subprocess.run(
            ['ssh', 'root@8.210.52.217', ssh_cmd],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ 执行失败: {result.stderr}")
            print("💡 提示: 可能需要手动执行 SQL")
            return False
            
    except Exception as e:
        print(f"❌ 同步失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_production_cache():
    """清除生产环境缓存"""
    print("\n" + "="*80)
    print("🧹 清除生产环境缓存")
    print("="*80)
    
    try:
        # 触发热更新（会自动清除缓存）
        url = "http://8.210.52.217:8001/api/v1/hot-reload/check"
        response = requests.post(url, timeout=30)
        response.raise_for_status()
        print("✅ 已触发热更新，缓存已清除")
        return True
    except Exception as e:
        print(f"⚠️  清除缓存失败: {e}")
        print("💡 提示: 可以手动清除或等待自动刷新")
        return False


def test_production_api() -> Dict:
    """测试生产环境 API"""
    print("\n" + "="*80)
    print("🧪 测试生产环境 API")
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
        
        print(f"✅ 测试成功:")
        print(f"  总匹配数: {stats.get('total_matched', 0)}")
        print(f"  财富: {stats.get('wealth_count', 0)}")
        print(f"  婚姻: {stats.get('marriage_count', 0)}")
        print(f"  事业: {stats.get('career_count', 0)}")
        print(f"  身体: {stats.get('health_count', 0)}")
        print(f"  总评: {stats.get('summary_count', 0)}")
        
        return stats
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return {}


def main():
    """主函数"""
    print("="*80)
    print("🔧 修复生产环境规则匹配问题")
    print("="*80)
    
    # 步骤 1: 检查本地规则
    local_rules = check_local_rules()
    if not local_rules:
        print("❌ 无法获取本地规则，退出")
        return
    
    # 步骤 2: 检查生产环境（通过 API）
    print("\n" + "="*80)
    print("📊 检查生产环境当前状态")
    print("="*80)
    prod_stats = test_production_api()
    
    if not prod_stats:
        print("❌ 无法连接生产环境，退出")
        return
    
    # 步骤 3: 对比差异
    print("\n" + "="*80)
    print("📊 对比分析")
    print("="*80)
    
    prod_total = prod_stats.get('total_matched', 0)
    local_total = local_rules.get('total', 0)
    
    print(f"生产环境匹配: {prod_total} 条")
    print(f"本地环境规则: {local_total} 条")
    
    if prod_total >= local_total * 0.9:  # 允许 10% 的差异
        print("✅ 规则数量基本一致，问题可能在其他方面")
        print("💡 建议检查:")
        print("  1. 缓存是否影响")
        print("  2. 规则匹配逻辑是否一致")
        return
    
    print(f"⚠️  发现明显差异，需要同步规则")
    
    # 步骤 4: 导出规则
    sql_file = export_rules_to_sql()
    if not sql_file:
        print("❌ 规则导出失败，退出")
        return
    
    # 步骤 5: 询问是否同步
    print("\n" + "="*80)
    print("❓ 是否同步规则到生产环境？")
    print("="*80)
    print("这将:")
    print("  1. 上传 SQL 文件到生产环境")
    print("  2. 在生产环境执行 SQL（使用 ON DUPLICATE KEY UPDATE，不会重复插入）")
    print("  3. 清除缓存")
    print("  4. 重新测试验证")
    
    # 自动执行（非交互模式）
    print("\n🔄 自动执行同步...")
    
    # 步骤 6: 同步规则
    if sync_rules_to_production(sql_file):
        print("✅ 规则同步成功")
    else:
        print("⚠️  自动同步失败，请手动执行:")
        print(f"  1. 上传文件: scp {sql_file} root@8.210.52.217:/tmp/rules_import.sql")
        print("  2. SSH 到生产环境: ssh root@8.210.52.217")
        print("  3. 执行 SQL: docker exec -i hifate-mysql-master mysql -uroot -p${MYSQL_PASSWORD} hifate_bazi < /tmp/rules_import.sql")
        return
    
    # 步骤 7: 清除缓存
    import time
    print("\n⏳ 等待 3 秒后清除缓存...")
    time.sleep(3)
    clear_production_cache()
    
    # 步骤 8: 等待规则重新加载
    print("\n⏳ 等待 5 秒让规则重新加载...")
    time.sleep(5)
    
    # 步骤 9: 重新测试
    print("\n" + "="*80)
    print("🧪 验证修复结果")
    print("="*80)
    
    new_prod_stats = test_production_api()
    
    if new_prod_stats:
        new_total = new_prod_stats.get('total_matched', 0)
        print(f"\n修复前: {prod_total} 条")
        print(f"修复后: {new_total} 条")
        
        if new_total >= local_total * 0.9:
            print("✅ 问题已解决！规则匹配数量已恢复正常")
        else:
            print(f"⚠️  仍有差异，建议:")
            print("  1. 检查生产环境数据库规则数量")
            print("  2. 检查规则 enabled 状态")
            print("  3. 清除缓存后重新测试")
    else:
        print("❌ 无法验证修复结果")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作被用户中断")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()

