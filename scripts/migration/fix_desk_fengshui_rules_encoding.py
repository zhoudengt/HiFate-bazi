#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复办公桌风水规则数据库中的乱码问题
读取现有规则，修复编码，更新数据库
"""

import sys
import os
import json

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

try:
    from server.config.mysql_config import get_mysql_connection, return_mysql_connection
    import pymysql
except ImportError:
    print("❌ 无法导入MySQL配置模块")
    sys.exit(1)


def safe_decode(text):
    """
    安全解码字符串，处理可能的编码问题
    增强版：支持多种编码修复策略
    """
    if not text:
        return text
    
    if isinstance(text, bytes):
        try:
            return text.decode('utf-8')
        except UnicodeDecodeError:
            try:
                # 尝试latin1 -> utf-8的修复（pymysql常见问题）
                fixed = text.decode('latin1').encode('latin1').decode('utf-8')
                # 验证修复后的文本是否包含中文字符或常见标点
                if any('\u4e00' <= c <= '\u9fff' or c in '，。！？；：' for c in fixed[:50]):
                    return fixed
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            try:
                # 尝试gbk编码
                fixed = text.decode('gbk')
                if any('\u4e00' <= c <= '\u9fff' or c in '，。！？；：' for c in fixed[:50]):
                    return fixed
            except:
                pass
            return str(text, errors='ignore')
    
    if isinstance(text, str):
        try:
            # 先尝试正常编码解码验证
            text.encode('utf-8').decode('utf-8')
            
            # 检查是否有常见的乱码模式
            has_suspicious_chars = False
            for c in text[:200]:  # 检查前200个字符
                if 0x80 <= ord(c) <= 0xFF:
                    has_suspicious_chars = True
                    break
            
            if has_suspicious_chars:
                # 可能是latin1编码的中文，尝试修复
                try:
                    fixed = text.encode('latin1').decode('utf-8')
                    # 验证修复后的文本是否包含中文字符
                    if any('\u4e00' <= c <= '\u9fff' or c in '，。！？；：' for c in fixed[:100]):
                        return fixed
                except (UnicodeEncodeError, UnicodeDecodeError):
                    pass
            
            return text
        except UnicodeEncodeError:
            # 如果无法编码，尝试修复
            try:
                fixed = text.encode('latin1').decode('utf-8')
                if any('\u4e00' <= c <= '\u9fff' or c in '，。！？；：' for c in fixed[:100]):
                    return fixed
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            return text
    
    return str(text)


def fix_rules_encoding(dry_run=True):
    """
    修复规则编码
    
    Args:
        dry_run: 是否为预览模式（不实际修改数据库）
    """
    conn = get_mysql_connection()
    try:
        # 确保连接使用utf8mb4字符集
        conn.set_charset('utf8mb4')
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # 执行SET NAMES确保会话级别字符集
        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
        
        # 查询所有规则
        sql = "SELECT * FROM desk_fengshui_rules"
        cursor.execute(sql)
        rules = cursor.fetchall()
        
        print(f"📊 找到 {len(rules)} 条规则")
        print("=" * 80)
        
        fixed_count = 0
        error_count = 0
        
        for rule in rules:
            rule_id = rule.get('id')
            rule_code = rule.get('rule_code')
            needs_fix = False
            updates = {}
            
            # 检查并修复各个字段
            fields_to_check = ['item_label', 'reason', 'suggestion']
            for field in fields_to_check:
                original_value = rule.get(field)
                if original_value:
                    fixed_value = safe_decode(original_value)
                    if fixed_value != original_value:
                        needs_fix = True
                        updates[field] = fixed_value
                        print(f"  [{rule_code}] {field}:")
                        print(f"    原文: {original_value[:50]}...")
                        print(f"    修复: {fixed_value[:50]}...")
            
            # 检查JSON字段
            json_fields = ['ideal_position', 'conditions']
            for field in json_fields:
                value = rule.get(field)
                if value:
                    if isinstance(value, str):
                        try:
                            # 先修复编码
                            fixed_str = safe_decode(value)
                            parsed = json.loads(fixed_str)
                            # 检查JSON内部是否有乱码
                            json_str = json.dumps(parsed, ensure_ascii=False)
                            if json_str != value:
                                needs_fix = True
                                updates[field] = json_str
                                print(f"  [{rule_code}] {field} (JSON): 需要修复")
                        except:
                            pass
            
            if needs_fix:
                if not dry_run:
                    # 构建UPDATE语句
                    set_clauses = []
                    values = []
                    for field, value in updates.items():
                        set_clauses.append(f"{field} = %s")
                        values.append(value)
                    
                    values.append(rule_id)
                    update_sql = f"""
                        UPDATE desk_fengshui_rules 
                        SET {', '.join(set_clauses)}
                        WHERE id = %s
                    """
                    try:
                        cursor.execute(update_sql, values)
                        conn.commit()
                        fixed_count += 1
                        print(f"  ✅ [{rule_code}] 修复成功")
                    except Exception as e:
                        error_count += 1
                        print(f"  ❌ [{rule_code}] 修复失败: {e}")
                else:
                    fixed_count += 1
                    print(f"  📝 [{rule_code}] 将修复 {len(updates)} 个字段")
        
        print("=" * 80)
        if dry_run:
            print(f"📊 预览结果: 将修复 {fixed_count} 条规则")
            print("💡 使用 --execute 参数执行实际修复")
        else:
            print(f"✅ 修复完成: {fixed_count} 条规则已修复")
            if error_count > 0:
                print(f"⚠️  修复失败: {error_count} 条规则")
        
        cursor.close()
        
    except Exception as e:
        print(f"❌ 修复过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        return_mysql_connection(conn)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='修复办公桌风水规则编码问题')
    parser.add_argument('--execute', action='store_true', help='执行实际修复（默认是预览模式）')
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("🔍 预览模式：不会修改数据库")
    else:
        print("⚠️  执行模式：将修改数据库")
        response = input("确认继续？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消")
            return
    
    print("\n开始修复规则编码...")
    fix_rules_encoding(dry_run=dry_run)


if __name__ == '__main__':
    main()

