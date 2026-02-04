#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断生产环境和测试环境规则匹配差异

检查项：
1. 数据库规则数量对比
2. 代码版本对比
3. 缓存影响检查
4. 规则 enabled 状态检查
"""

import sys
import os
import json
from typing import Dict, List, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.mysql_config import get_mysql_connection, return_mysql_connection
from server.services.rule_service import RuleService


def check_database_rules(env_name: str = "本地") -> Dict:
    """检查数据库规则"""
    print(f"\n{'='*60}")
    print(f"📊 检查 {env_name} 环境数据库规则")
    print(f"{'='*60}")
    
    try:
        import pymysql.cursors
        conn = get_mysql_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # 1. 检查总规则数
        cursor.execute("SELECT COUNT(*) as total FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%'")
        total_rules = cursor.fetchone()['total']
        
        # 2. 检查启用的规则数
        cursor.execute("SELECT COUNT(*) as total FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1")
        enabled_rules = cursor.fetchone()['total']
        
        # 3. 按类型统计
        cursor.execute("""
            SELECT rule_type, COUNT(*) as count, 
                   SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) as enabled_count
            FROM bazi_rules 
            WHERE rule_code LIKE 'FORMULA_%'
            GROUP BY rule_type
            ORDER BY rule_type
        """)
        type_stats = cursor.fetchall()
        
        # 4. 检查特定八字匹配的规则数（1987-01-07 09:00 男）
        # 先计算八字
        from server.services.bazi_service import BaziService
        bazi_result = BaziService.calculate_bazi_full(
            solar_date="1987-01-07",
            solar_time="09:00",
            gender="male"
        )
        bazi_data = bazi_result.get('bazi', {})
        
        # 构建规则匹配数据
        rule_data = {
            'basic_info': bazi_data.get('basic_info', {}),
            'bazi_pillars': bazi_data.get('bazi_pillars', {}),
            'details': bazi_data.get('details', {}),
            'ten_gods_stats': bazi_data.get('ten_gods_stats', {}),
            'elements': bazi_data.get('elements', {}),
            'element_counts': bazi_data.get('element_counts', {}),
            'relationships': bazi_data.get('relationships', {})
        }
        
        # 匹配规则
        rule_types = ['wealth', 'marriage', 'career', 'children', 'character', 'summary', 'health', 'peach_blossom', 'shishen', 'parents']
        matched_rules = RuleService.match_rules(rule_data, rule_types=rule_types, use_cache=False)
        
        # 只统计 FORMULA_ 前缀的规则
        formula_rules = [r for r in matched_rules if r.get('rule_id', '').startswith('FORMULA_')]
        
        # 按类型统计匹配的规则
        matched_by_type = {}
        for rule in formula_rules:
            rule_type = rule.get('rule_type', '')
            if rule_type not in matched_by_type:
                matched_by_type[rule_type] = 0
            matched_by_type[rule_type] += 1
        
        result = {
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'type_stats': type_stats,
            'matched_rules_count': len(formula_rules),
            'matched_by_type': matched_by_type
        }
        
        print(f"✅ 总规则数: {total_rules}")
        print(f"✅ 启用规则数: {enabled_rules}")
        print(f"\n📋 按类型统计:")
        for stat in type_stats:
            print(f"  - {stat['rule_type']}: 总计 {stat['count']}, 启用 {stat['enabled_count']}")
        
        print(f"\n🎯 测试八字 (1987-01-07 09:00 男) 匹配结果:")
        print(f"  - 总匹配数: {len(formula_rules)}")
        for rule_type, count in matched_by_type.items():
            print(f"  - {rule_type}: {count}")
        
        cursor.close()
        return_mysql_connection(conn)
        
        return result
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def check_code_version(env_name: str = "本地") -> Dict:
    """检查代码版本"""
    print(f"\n{'='*60}")
    print(f"📝 检查 {env_name} 环境代码版本")
    print(f"{'='*60}")
    
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        commit_hash = result.stdout.strip() if result.returncode == 0 else "未知"
        
        result2 = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd=project_root,
            capture_output=True,
            text=True
        )
        last_commit = result2.stdout.strip() if result2.returncode == 0 else "未知"
        
        print(f"✅ Git Commit: {commit_hash}")
        print(f"✅ 最后提交: {last_commit}")
        
        return {
            'commit_hash': commit_hash,
            'last_commit': last_commit
        }
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return {}


def check_cache_status() -> Dict:
    """检查缓存状态"""
    print(f"\n{'='*60}")
    print(f"💾 检查缓存状态")
    print(f"{'='*60}")
    
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        
        # 检查缓存键数量（估算）
        print(f"✅ 缓存系统: 已初始化")
        print(f"⚠️  注意: 缓存可能影响规则匹配结果，建议清除缓存后重新测试")
        
        return {
            'cache_enabled': True
        }
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return {}


def clear_cache():
    """清除缓存"""
    print(f"\n{'='*60}")
    print(f"🧹 清除缓存")
    print(f"{'='*60}")
    
    try:
        from server.utils.cache_multi_level import get_multi_cache
        cache = get_multi_cache()
        cache.l1.clear()
        print(f"✅ L1 缓存已清除")
        
        from shared.config.redis import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            # 清除规则相关的缓存键
            pattern = "rule:*"
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    redis_client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            print(f"✅ Redis 缓存已清除 (删除了 {deleted} 个键)")
        else:
            print(f"⚠️  Redis 不可用，跳过")
        
        # 重置规则引擎缓存
        RuleService._engine = None
        print(f"✅ 规则引擎缓存已重置")
        
    except Exception as e:
        print(f"❌ 清除缓存失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("="*60)
    print("🔍 规则匹配差异诊断工具")
    print("="*60)
    
    # 1. 检查本地环境
    local_db = check_database_rules("本地")
    local_code = check_code_version("本地")
    cache_status = check_cache_status()
    
    # 2. 询问是否清除缓存（非交互式模式自动清除）
    print(f"\n{'='*60}")
    print("🧹 自动清除缓存并重新测试...")
    clear_cache()
    print(f"\n🔄 重新测试规则匹配...")
    local_db_after = check_database_rules("本地(清除缓存后)")
    
    # 3. 生成报告
    print(f"\n{'='*60}")
    print("📊 诊断报告")
    print(f"{'='*60}")
    print(f"\n本地环境:")
    print(f"  - 总规则数: {local_db.get('total_rules', 'N/A')}")
    print(f"  - 启用规则数: {local_db.get('enabled_rules', 'N/A')}")
    print(f"  - 测试八字匹配数: {local_db.get('matched_rules_count', 'N/A')}")
    print(f"  - Git Commit: {local_code.get('commit_hash', 'N/A')[:8]}")
    
    print(f"\n💡 建议:")
    print(f"  1. 检查生产环境数据库规则数量是否与本地一致")
    print(f"  2. 检查生产环境代码版本是否与本地一致")
    print(f"  3. 清除生产环境缓存后重新测试")
    print(f"  4. 检查生产环境规则 enabled 状态")
    
    print(f"\n📋 下一步操作:")
    print(f"  1. SSH 到生产环境检查数据库: ssh root@8.210.52.217")
    print(f"  2. 运行 SQL 查询规则数量:")
    print(f"     SELECT COUNT(*) FROM bazi_rules WHERE rule_code LIKE 'FORMULA_%' AND enabled = 1;")
    print(f"  3. 检查生产环境代码版本:")
    print(f"     cd /opt/HiFate-bazi && git log --oneline -1")
    print(f"  4. 清除生产环境缓存（通过 API）:")
    print(f"     curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/check")


if __name__ == '__main__':
    main()

