#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则迁移脚本：将 rules.json 中的规则迁移到数据库
"""

import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.db.mysql_connector import get_db_connection


def migrate_rules_to_database():
    """将 rules.json 中的规则迁移到数据库"""
    print("=" * 60)
    print("开始迁移规则到数据库...")
    print("=" * 60)
    
    # 1. 读取 rules.json
    rules_file = os.path.join(project_root, 'server/config/rules.json')
    if not os.path.exists(rules_file):
        print(f"❌ 规则文件不存在: {rules_file}")
        return False
    
    with open(rules_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    rules = data.get('rules', [])
    print(f"\n待迁移规则数: {len(rules)}")
    print("\n开始迁移...")
    
    db = get_db_connection()
    success_count = 0
    failed_count = 0
    
    for idx, rule in enumerate(rules, 1):
        try:
            sql = """
                INSERT INTO bazi_rules (
                    rule_code, rule_name, rule_type, priority,
                    conditions, content, enabled, description
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    rule_name = VALUES(rule_name),
                    rule_type = VALUES(rule_type),
                    priority = VALUES(priority),
                    conditions = VALUES(conditions),
                    content = VALUES(content),
                    enabled = VALUES(enabled),
                    description = VALUES(description),
                    updated_at = NOW()
            """
            
            db.execute_update(sql, (
                rule.get('rule_id', ''),
                rule.get('rule_name', ''),
                rule.get('rule_type', 'default'),
                rule.get('priority', 100),
                json.dumps(rule.get('conditions', {}), ensure_ascii=False),
                json.dumps(rule.get('content', {}), ensure_ascii=False),
                rule.get('enabled', True),
                rule.get('description', '')
            ))
            
            success_count += 1
            if idx % 2 == 0:
                print(f"  进度: {idx}/{len(rules)} ({idx*100//len(rules)}%)")
        except Exception as e:
            failed_count += 1
            print(f"  ✗ 迁移失败: {rule.get('rule_id', 'unknown')} - {e}")
    
    # 更新规则版本号
    try:
        db.execute_update("UPDATE rule_version SET rule_version = rule_version + 1")
        print("\n✓ 规则版本号已更新")
    except Exception as e:
        print(f"\n⚠ 更新规则版本号失败: {e}")
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print(f"总计: {len(rules)}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    
    return failed_count == 0


if __name__ == "__main__":
    try:
        success = migrate_rules_to_database()
        if success:
            print("\n✓ 所有规则迁移成功！")
            sys.exit(0)
        else:
            print("\n⚠ 有部分规则迁移失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 迁移过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)








































