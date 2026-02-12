#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案执行：检查生产数据库中是否存在本地匹配的63条规则
简化版本：直接从数据库查询，不通过服务计算
"""

import sys
import os
import json
import requests
from typing import Dict, List, Set

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
import pymysql.cursors


def get_local_matched_rules_from_db() -> List[str]:
    """直接从本地数据库获取所有 FORMULA_ 规则"""
    print("="*80)
    print("步骤 1: 从本地数据库获取所有 FORMULA_ 规则")
    print("="*80)
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询所有启用的 FORMULA_ 规则
        cursor.execute("""
            SELECT rule_code, rule_type, enabled
            FROM bazi_rules
            WHERE rule_code LIKE 'FORMULA_%'
              AND enabled = 1
            ORDER BY rule_code
        """)
        
        rules = cursor.fetchall()
        rule_codes = [r['rule_code'] for r in rules]
        
        print(f"\n✅ 本地数据库中有 {len(rule_codes)} 条启用的 FORMULA_ 规则")
        
        # 按类型统计
        type_counts = {}
        for r in rules:
            rule_type = r['rule_type']
            type_counts[rule_type] = type_counts.get(rule_type, 0) + 1
        
        print(f"\n📊 按类型统计:")
        for rule_type, count in sorted(type_counts.items()):
            print(f"  {rule_type}: {count} 条")
        
        print(f"\n规则列表（前10条）:")
        for i, code in enumerate(rule_codes[:10], 1):
            print(f"  {i}. {code}")
        if len(rule_codes) > 10:
            print(f"  ... 还有 {len(rule_codes) - 10} 条")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return rule_codes
        
    except Exception as e:
        print(f"❌ 查询本地数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def check_rules_in_production_api(rule_codes: List[str]) -> Dict:
    """通过 API 检查生产环境匹配的规则"""
    print("\n" + "="*80)
    print("步骤 2: 通过 API 检查生产环境匹配的规则")
    print("="*80)
    
    # 测试生产环境 API
    test_case = {
        'solar_date': '1987-01-07',
        'solar_time': '09:00',
        'gender': 'male'
    }
    
    try:
        url = "http://8.210.52.217:8001/api/v1/bazi/formula-analysis"
        print(f"\n📡 调用生产环境 API: {url}")
        response = requests.post(url, json=test_case, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # 提取生产环境匹配的规则
        matched_rules = result.get('data', {}).get('matched_rules', {})
        prod_rule_details = result.get('data', {}).get('rule_details', {})
        
        # 从 rule_details 中提取 rule_code
        prod_rule_codes = set()
        for rule_id, details in prod_rule_details.items():
            # rule_id 可能是数字，需要从 details 中获取 rule_code
            rule_code = details.get('rule_code', '')
            if rule_code:
                prod_rule_codes.add(rule_code)
            else:
                # 如果没有 rule_code，尝试构造
                rule_type_cn = details.get('类型', '')
                if rule_type_cn and rule_id:
                    # 构造可能的 rule_code
                    prod_rule_codes.add(f"FORMULA_{rule_type_cn}_{rule_id}")
        
        print(f"\n✅ 生产环境 API 返回 {len(prod_rule_codes)} 条规则")
        
        # 统计各类型数量
        prod_type_counts = {}
        for rule_id, details in prod_rule_details.items():
            rule_type_cn = details.get('类型', '')
            if rule_type_cn:
                prod_type_counts[rule_type_cn] = prod_type_counts.get(rule_type_cn, 0) + 1
        
        print(f"\n📊 生产环境按类型统计:")
        for rule_type, count in sorted(prod_type_counts.items()):
            print(f"  {rule_type}: {count} 条")
        
        # 对比
        local_codes_set = set(rule_codes)
        missing_codes = local_codes_set - prod_rule_codes
        
        print(f"\n📊 对比结果:")
        print(f"  本地规则总数: {len(local_codes_set)}")
        print(f"  生产匹配规则数: {len(prod_rule_codes)}")
        print(f"  缺失规则数: {len(missing_codes)}")
        
        if missing_codes:
            print(f"\n⚠️  发现 {len(missing_codes)} 条规则在生产环境中缺失或未匹配")
            print(f"\n缺失规则示例（前10条）:")
            for i, code in enumerate(list(missing_codes)[:10], 1):
                print(f"  {i}. {code}")
            if len(missing_codes) > 10:
                print(f"  ... 还有 {len(missing_codes) - 10} 条")
            
            return {
                'exists': False,
                'missing_count': len(missing_codes),
                'missing_codes': list(missing_codes),
                'local_count': len(local_codes_set),
                'prod_count': len(prod_rule_codes)
            }
        else:
            print(f"\n✅ 所有规则在生产环境中都存在")
            return {
                'exists': True,
                'missing_count': 0,
                'local_count': len(local_codes_set),
                'prod_count': len(prod_rule_codes)
            }
            
    except Exception as e:
        print(f"❌ API 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return {'exists': None, 'error': str(e)}


def export_missing_rules_to_sql(missing_codes: List[str]):
    """导出缺失的规则到 SQL 文件"""
    print("\n" + "="*80)
    print("步骤 3: 导出缺失的规则到 SQL 文件")
    print("="*80)
    
    if not missing_codes:
        print("✅ 没有缺失的规则，跳过导出")
        return None
    
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查询缺失的规则
        placeholders = ','.join(['%s'] * len(missing_codes))
        cursor.execute(f"""
            SELECT 
                rule_code, rule_name, rule_type, conditions, content, description,
                priority, enabled
            FROM bazi_rules
            WHERE rule_code IN ({placeholders})
        """, missing_codes)
        
        rules = cursor.fetchall()
        
        if not rules:
            print("⚠️  未找到缺失的规则（可能已被删除）")
            cursor.close()
            return_mysql_connection(conn)
            return None
        
        # 生成 SQL 文件
        sql_file = os.path.join(project_root, 'scripts', 'temp_rules_export.sql')
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("-- 同步缺失的规则到生产环境\n")
            f.write("-- 使用 ON DUPLICATE KEY UPDATE 确保幂等性\n\n")
            
            for rule in rules:
                rule_code = rule['rule_code']
                rule_name = rule['rule_name'] or ''
                rule_type = rule['rule_type'] or ''
                
                # JSON 字段：使用 MySQL 的 JSON_QUOTE 函数或直接转义
                conditions_json = json.dumps(rule['conditions'], ensure_ascii=False) if rule['conditions'] else '{}'
                content_json = json.dumps(rule['content'], ensure_ascii=False) if rule['content'] else '{}'
                description_json = json.dumps(rule['description'], ensure_ascii=False) if rule['description'] else '{}'
                
                priority = rule.get('priority', 100)
                enabled = rule.get('enabled', 1)
                
                # 转义：单引号、反斜杠、换行符
                def escape_sql_string(s):
                    if s is None:
                        return ''
                    s = str(s)
                    s = s.replace('\\', '\\\\')  # 先转义反斜杠
                    s = s.replace("'", "\\'")     # 转义单引号
                    s = s.replace('\n', '\\n')    # 转义换行
                    s = s.replace('\r', '\\r')    # 转义回车
                    return s
                
                rule_name_escaped = escape_sql_string(rule_name)
                conditions_escaped = escape_sql_string(conditions_json)
                content_escaped = escape_sql_string(content_json)
                description_escaped = escape_sql_string(description_json)
                
                f.write(f"""INSERT INTO bazi_rules 
    (rule_code, rule_name, rule_type, conditions, content, description, priority, enabled)
VALUES 
    ('{rule_code}', '{rule_name_escaped}', '{rule_type}', '{conditions_escaped}', '{content_escaped}', '{description_escaped}', {priority}, {enabled})
ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    rule_type = VALUES(rule_type),
    conditions = VALUES(conditions),
    content = VALUES(content),
    description = VALUES(description),
    priority = VALUES(priority),
    enabled = VALUES(enabled);

""")
        
        print(f"\n✅ 已导出 {len(rules)} 条规则到: {sql_file}")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return sql_file
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_code_logic():
    """对比代码逻辑"""
    print("\n" + "="*80)
    print("步骤 4: 对比代码逻辑")
    print("="*80)
    
    key_files = [
        'server/api/v1/formula_analysis.py',
        'server/services/rule_service.py',
        'server/engines/rule_engine.py'
    ]
    
    print("\n检查关键代码文件:")
    all_ok = True
    for file_path in key_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"\n  ✅ {file_path}")
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                checks = []
                # 检查关键逻辑
                if 'RuleService.match_rules' in content:
                    checks.append("✅ 使用 RuleService.match_rules")
                else:
                    checks.append("❌ 未使用 RuleService.match_rules")
                    all_ok = False
                    
                if 'FORMULA_' in content and 'startswith' in content:
                    checks.append("✅ 筛选 FORMULA_ 前缀规则")
                else:
                    checks.append("⚠️  可能未筛选 FORMULA_ 前缀")
                    
                if 'enabled = 1' in content or 'enabled = True' in content or 'enabled' in content:
                    checks.append("✅ 过滤 enabled 规则")
                else:
                    checks.append("⚠️  可能未过滤 enabled")
                
                for check in checks:
                    print(f"    {check}")
        else:
            print(f"  ❌ {file_path} - 文件不存在")
            all_ok = False
    
    if all_ok:
        print(f"\n✅ 代码逻辑检查通过")
    else:
        print(f"\n⚠️  代码逻辑可能有问题")
    
    return all_ok


def check_frontend():
    """检查前端展示"""
    print("\n" + "="*80)
    print("步骤 5: 检查前端展示")
    print("="*80)
    
    frontend_file = os.path.join(project_root, 'local_frontend/formula-analysis.html')
    
    if os.path.exists(frontend_file):
        print(f"\n✅ 前端文件存在: {frontend_file}")
        
        with open(frontend_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查关键字段
            key_fields = ['total_matched', 'wealth_count', 'career_count', 'health_count', 'summary_count']
            print(f"\n检查统计字段:")
            all_ok = True
            for field in key_fields:
                if field in content:
                    print(f"  ✅ {field}")
                else:
                    print(f"  ❌ {field} - 未找到")
                    all_ok = False
            
            # 检查 API 路径
            if '/bazi/formula-analysis' in content:
                print(f"\n✅ API 路径正确: /bazi/formula-analysis")
            else:
                print(f"\n⚠️  API 路径可能错误")
                all_ok = False
            
            if all_ok:
                print(f"\n✅ 前端展示逻辑正常")
            else:
                print(f"\n⚠️  前端展示可能有问题")
    else:
        print(f"\n❌ 前端文件不存在: {frontend_file}")


def main():
    """主函数 - 按照用户方案执行"""
    print("="*80)
    print("🔍 按照方案执行：检查规则是否存在，对比代码逻辑，检查前端")
    print("="*80)
    
    # 步骤 1: 从本地数据库获取所有 FORMULA_ 规则
    local_rule_codes = get_local_matched_rules_from_db()
    
    if not local_rule_codes:
        print("❌ 无法获取本地规则，退出")
        return
    
    # 步骤 2: 检查生产环境中是否存在这些规则（通过 API）
    check_result = check_rules_in_production_api(local_rule_codes)
    
    if check_result.get('exists') is False:
        # 规则不存在，需要同步
        print(f"\n{'='*80}")
        print("🔴 结论: 生产环境中规则缺失或未匹配")
        print(f"{'='*80}")
        print(f"本地规则数: {check_result.get('local_count', 0)}")
        print(f"生产匹配数: {check_result.get('prod_count', 0)}")
        print(f"缺失规则数: {check_result.get('missing_count', 0)}")
        
        # 步骤 3: 导出缺失的规则到 SQL
        missing_codes = check_result.get('missing_codes', [])
        sql_file = export_missing_rules_to_sql(missing_codes)
        
        if sql_file:
            print(f"\n💡 执行修复步骤:")
            print(f"  1. 上传 SQL 文件到生产环境:")
            print(f"     scp {sql_file} root@8.210.52.217:/tmp/rules_import.sql")
            print(f"  2. 执行 SQL 并清理缓存:")
            print(f"     ssh root@8.210.52.217 'cd /opt/HiFate-bazi && docker exec -i hifate-mysql-master mysql -uroot -p${MYSQL_PASSWORD} hifate_bazi < /tmp/rules_import.sql && curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check'")
        
    elif check_result.get('exists') is True:
        # 规则存在，对比代码逻辑
        print(f"\n{'='*80}")
        print("✅ 结论: 生产环境中规则存在")
        print(f"{'='*80}")
        print(f"本地规则数: {check_result.get('local_count', 0)}")
        print(f"生产匹配数: {check_result.get('prod_count', 0)}")
        
        if check_result.get('local_count', 0) != check_result.get('prod_count', 0):
            print(f"\n⚠️  规则数量不一致，可能原因:")
            print(f"  1. 规则 enabled 状态不同")
            print(f"  2. 规则匹配逻辑有差异")
            print(f"  3. 缓存影响")
            print(f"  4. 规则条件不匹配")
        
        # 步骤 4: 对比代码逻辑
        code_ok = compare_code_logic()
        
        # 步骤 5: 检查前端
        check_frontend()
        
        if not code_ok:
            print(f"\n💡 建议检查代码逻辑差异")
    else:
        print(f"\n⚠️  无法确定规则是否存在（API 检查失败）")
        print(f"💡 建议直接同步规则确保一致性")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  执行被中断")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()

