#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 QA 对话系统数据库表结构
检查表是否存在、结构是否正确、索引是否存在
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from shared.config.database import get_mysql_connection, return_mysql_connection

def verify_table_exists(cursor, table_name):
    """验证表是否存在"""
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = %s",
        (table_name,)
    )
    result = cursor.fetchone()
    return result[0] > 0

def verify_table_structure(cursor, table_name, expected_columns):
    """验证表结构是否正确"""
    cursor.execute(
        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
        "FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s "
        "ORDER BY ORDINAL_POSITION",
        (table_name,)
    )
    actual_columns = {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]} 
                      for row in cursor.fetchall()}
    
    missing_columns = []
    wrong_type_columns = []
    
    for col_name, col_info in expected_columns.items():
        if col_name not in actual_columns:
            missing_columns.append(col_name)
        else:
            # 简单的类型检查（可以根据需要扩展）
            actual_type = actual_columns[col_name]['type'].upper()
            expected_type = col_info.get('type', '').upper()
            if expected_type and expected_type not in actual_type:
                wrong_type_columns.append(f"{col_name} (期望: {expected_type}, 实际: {actual_type})")
    
    return {
        'missing': missing_columns,
        'wrong_type': wrong_type_columns,
        'actual_columns': actual_columns
    }

def verify_indexes(cursor, table_name, expected_indexes):
    """验证索引是否存在"""
    cursor.execute(
        "SELECT INDEX_NAME, COLUMN_NAME "
        "FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = %s "
        "AND INDEX_NAME != 'PRIMARY'",
        (table_name,)
    )
    actual_indexes = {}
    for row in cursor.fetchall():
        index_name = row[0]
        column_name = row[1]
        if index_name not in actual_indexes:
            actual_indexes[index_name] = []
        actual_indexes[index_name].append(column_name)
    
    missing_indexes = []
    for index_name, columns in expected_indexes.items():
        if index_name not in actual_indexes:
            missing_indexes.append(f"{index_name} ({', '.join(columns)})")
        else:
            # 检查索引列是否匹配
            actual_cols = set(actual_indexes[index_name])
            expected_cols = set(columns)
            if actual_cols != expected_cols:
                missing_indexes.append(
                    f"{index_name} (期望: {', '.join(columns)}, 实际: {', '.join(actual_cols)})"
                )
    
    return {
        'missing': missing_indexes,
        'actual_indexes': actual_indexes
    }

def verify_qa_tables():
    """验证 QA 对话系统相关表"""
    print("=" * 80)
    print("QA 对话系统数据库表验证")
    print("=" * 80)
    
    conn = None
    try:
        conn = get_mysql_connection()
        cursor = conn.cursor()
        
        # 1. 验证 qa_conversation_sessions 表
        print("\n[1] 验证 qa_conversation_sessions 表")
        print("-" * 80)
        
        if not verify_table_exists(cursor, 'qa_conversation_sessions'):
            print("❌ 表不存在: qa_conversation_sessions")
            print("\n修复建议:")
            print("  执行 SQL 脚本创建表:")
            print("  mysql -u root -p hifate_bazi < server/db/migrations/create_qa_tables.sql")
            return False
        
        print("✅ 表存在: qa_conversation_sessions")
        
        # 验证表结构
        expected_columns = {
            'id': {'type': 'INT'},
            'user_id': {'type': 'VARCHAR'},
            'session_id': {'type': 'VARCHAR'},
            'solar_date': {'type': 'VARCHAR'},
            'solar_time': {'type': 'VARCHAR'},
            'gender': {'type': 'VARCHAR'},
            'current_category': {'type': 'VARCHAR'},
            'created_at': {'type': 'TIMESTAMP'},
            'updated_at': {'type': 'TIMESTAMP'}
        }
        
        structure_result = verify_table_structure(cursor, 'qa_conversation_sessions', expected_columns)
        if structure_result['missing']:
            print(f"❌ 缺少列: {', '.join(structure_result['missing'])}")
        if structure_result['wrong_type']:
            print(f"⚠️  类型不匹配: {', '.join(structure_result['wrong_type'])}")
        if not structure_result['missing'] and not structure_result['wrong_type']:
            print("✅ 表结构正确")
        
        # 验证索引
        expected_indexes = {
            'idx_user_id': ['user_id'],
            'idx_session_id': ['session_id'],
            'idx_created_at': ['created_at']
        }
        
        index_result = verify_indexes(cursor, 'qa_conversation_sessions', expected_indexes)
        if index_result['missing']:
            print(f"⚠️  缺少索引: {', '.join(index_result['missing'])}")
        else:
            print("✅ 索引正确")
        
        # 2. 验证 qa_conversation_history 表
        print("\n[2] 验证 qa_conversation_history 表")
        print("-" * 80)
        
        if not verify_table_exists(cursor, 'qa_conversation_history'):
            print("❌ 表不存在: qa_conversation_history")
            print("\n修复建议:")
            print("  执行 SQL 脚本创建表:")
            print("  mysql -u root -p hifate_bazi < server/db/migrations/create_qa_tables.sql")
            return False
        
        print("✅ 表存在: qa_conversation_history")
        
        # 验证表结构
        expected_columns = {
            'id': {'type': 'INT'},
            'session_id': {'type': 'VARCHAR'},
            'turn_number': {'type': 'INT'},
            'question': {'type': 'TEXT'},
            'answer': {'type': 'TEXT'},
            'generated_questions_before': {'type': 'JSON'},
            'generated_questions_after': {'type': 'JSON'},
            'intent_result': {'type': 'JSON'},
            'category': {'type': 'VARCHAR'},
            'created_at': {'type': 'TIMESTAMP'}
        }
        
        structure_result = verify_table_structure(cursor, 'qa_conversation_history', expected_columns)
        if structure_result['missing']:
            print(f"❌ 缺少列: {', '.join(structure_result['missing'])}")
        if structure_result['wrong_type']:
            print(f"⚠️  类型不匹配: {', '.join(structure_result['wrong_type'])}")
        if not structure_result['missing'] and not structure_result['wrong_type']:
            print("✅ 表结构正确")
        
        # 验证索引
        expected_indexes = {
            'idx_session_id': ['session_id'],
            'idx_turn_number': ['session_id', 'turn_number'],
            'idx_created_at': ['created_at']
        }
        
        index_result = verify_indexes(cursor, 'qa_conversation_history', expected_indexes)
        if index_result['missing']:
            print(f"⚠️  缺少索引: {', '.join(index_result['missing'])}")
        else:
            print("✅ 索引正确")
        
        # 3. 验证 qa_question_templates 表
        print("\n[3] 验证 qa_question_templates 表")
        print("-" * 80)
        
        if not verify_table_exists(cursor, 'qa_question_templates'):
            print("❌ 表不存在: qa_question_templates")
            print("\n修复建议:")
            print("  执行 SQL 脚本创建表:")
            print("  mysql -u root -p hifate_bazi < server/db/migrations/create_qa_tables.sql")
            return False
        
        print("✅ 表存在: qa_question_templates")
        
        # 验证表结构
        expected_columns = {
            'id': {'type': 'INT'},
            'category': {'type': 'VARCHAR'},
            'question_text': {'type': 'TEXT'},
            'question_type': {'type': 'VARCHAR'},
            'priority': {'type': 'INT'},
            'enabled': {'type': 'TINYINT'},
            'created_at': {'type': 'TIMESTAMP'},
            'updated_at': {'type': 'TIMESTAMP'}
        }
        
        structure_result = verify_table_structure(cursor, 'qa_question_templates', expected_columns)
        if structure_result['missing']:
            print(f"❌ 缺少列: {', '.join(structure_result['missing'])}")
        if structure_result['wrong_type']:
            print(f"⚠️  类型不匹配: {', '.join(structure_result['wrong_type'])}")
        if not structure_result['missing'] and not structure_result['wrong_type']:
            print("✅ 表结构正确")
        
        # 验证索引
        expected_indexes = {
            'idx_category': ['category'],
            'idx_enabled': ['enabled'],
            'idx_priority': ['priority']
        }
        
        index_result = verify_indexes(cursor, 'qa_question_templates', expected_indexes)
        if index_result['missing']:
            print(f"⚠️  缺少索引: {', '.join(index_result['missing'])}")
        else:
            print("✅ 索引正确")
        
        # 4. 检查数据完整性
        print("\n[4] 检查数据完整性")
        print("-" * 80)
        
        # 检查是否有会话记录
        cursor.execute("SELECT COUNT(*) FROM qa_conversation_sessions")
        session_count = cursor.fetchone()[0]
        print(f"会话记录数: {session_count}")
        
        # 检查是否有对话历史
        cursor.execute("SELECT COUNT(*) FROM qa_conversation_history")
        history_count = cursor.fetchone()[0]
        print(f"对话历史记录数: {history_count}")
        
        # 检查是否有问题模板
        cursor.execute("SELECT COUNT(*) FROM qa_question_templates WHERE enabled = 1")
        template_count = cursor.fetchone()[0]
        print(f"启用的问题模板数: {template_count}")
        
        if template_count == 0:
            print("⚠️  没有启用的问题模板，建议导入初始数据")
        
        print("\n" + "=" * 80)
        print("✅ 验证完成")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 验证过程发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            return_mysql_connection(conn)

if __name__ == '__main__':
    success = verify_qa_tables()
    sys.exit(0 if success else 1)

