#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据一致性验证工具
对比本地和生产数据库的数据一致性

使用方法：
    python3 scripts/db/verify_data_consistency.py
"""

import sys
import os
import argparse
from typing import Dict, List, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("错误：需要安装 pymysql")
    print("安装命令：pip install pymysql")
    sys.exit(1)

# 导入数据库变更检测脚本中的工具类
# 需要将 scripts/db 添加到路径中
import sys
sys.path.insert(0, os.path.join(project_root, 'scripts', 'db'))
from detect_db_changes import DatabaseComparator, get_database_config


class DataConsistencyVerifier:
    """数据一致性验证器"""
    
    def __init__(self, local_config: Dict, production_config: Dict):
        """
        初始化验证器
        
        Args:
            local_config: 本地数据库配置
            production_config: 生产数据库配置
        """
        self.local_config = local_config
        self.production_config = production_config
        self.comparator = DatabaseComparator(local_config, production_config)
    
    def verify(self, key_tables: List[str] = None) -> Dict:
        """
        验证数据一致性
        
        Args:
            key_tables: 关键表列表（如果为None，则验证所有表）
        
        Returns:
            {
                'consistent': bool,
                'inconsistent_tables': [...],
                'details': {...}
            }
        """
        self.comparator.connect()
        
        try:
            # 获取所有表
            local_tables = set(self.comparator.get_tables(self.comparator.local_conn))
            prod_tables = set(self.comparator.get_tables(self.comparator.prod_conn))
            
            # 如果指定了关键表，只验证这些表
            if key_tables:
                local_tables = local_tables & set(key_tables)
                prod_tables = prod_tables & set(key_tables)
            
            # 只验证公共表
            common_tables = local_tables & prod_tables
            
            results = {
                'consistent': True,
                'inconsistent_tables': [],
                'details': {}
            }
            
            # 对比每个表的记录数
            for table in common_tables:
                local_count = self.comparator.get_table_row_count(self.comparator.local_conn, table)
                prod_count = self.comparator.get_table_row_count(self.comparator.prod_conn, table)
                
                details = {
                    'table': table,
                    'local_count': local_count,
                    'prod_count': prod_count,
                    'consistent': local_count == prod_count
                }
                
                if local_count != prod_count:
                    results['consistent'] = False
                    results['inconsistent_tables'].append(table)
                    details['diff'] = local_count - prod_count
                
                results['details'][table] = details
            
            return results
        
        finally:
            self.comparator.close()
    
    def print_report(self, results: Dict):
        """打印验证报告"""
        print("\n" + "=" * 80)
        print("数据一致性验证报告")
        print("=" * 80)
        print("")
        
        if results['consistent']:
            print("✅ 所有表数据一致")
        else:
            print(f"❌ 发现 {len(results['inconsistent_tables'])} 个表数据不一致")
        
        print("")
        print("详细对比：")
        print("-" * 80)
        print(f"{'表名':<30} {'本地记录数':<15} {'生产记录数':<15} {'状态':<10}")
        print("-" * 80)
        
        for table, details in results['details'].items():
            status = "✅ 一致" if details['consistent'] else "❌ 不一致"
            if not details['consistent']:
                status += f" (差异: {details['diff']})"
            print(f"{table:<30} {details['local_count']:<15} {details['prod_count']:<15} {status:<10}")
        
        print("-" * 80)
        print("")
        
        if not results['consistent']:
            print("⚠️  数据不一致的表：")
            for table in results['inconsistent_tables']:
                details = results['details'][table]
                print(f"  - {table}: 本地 {details['local_count']} 条，生产 {details['prod_count']} 条，差异 {details['diff']} 条")
            print("")
            print("建议：")
            print("  1. 运行数据库变更检测脚本：python3 scripts/db/detect_db_changes.py --generate-sync-script")
            print("  2. 执行数据同步：bash scripts/db/sync_production_db.sh --node node1 --deployment-id <ID>")
        
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='数据一致性验证工具')
    parser.add_argument('--key-tables', nargs='+', help='关键表列表（只验证这些表）')
    parser.add_argument('--local-host', help='本地数据库主机')
    parser.add_argument('--local-port', type=int, help='本地数据库端口')
    parser.add_argument('--local-user', help='本地数据库用户')
    parser.add_argument('--local-password', help='本地数据库密码')
    parser.add_argument('--local-database', help='本地数据库名')
    parser.add_argument('--prod-host', help='生产数据库主机')
    parser.add_argument('--prod-port', type=int, help='生产数据库端口')
    parser.add_argument('--prod-user', help='生产数据库用户')
    parser.add_argument('--prod-password', help='生产数据库密码')
    parser.add_argument('--prod-database', help='生产数据库名')
    args = parser.parse_args()
    
    # 获取数据库配置
    local_config = get_database_config('local')
    prod_config = get_database_config('production')
    
    # 命令行参数覆盖环境变量
    if args.local_host:
        local_config['host'] = args.local_host
    if args.local_port:
        local_config['port'] = args.local_port
    if args.local_user:
        local_config['user'] = args.local_user
    if args.local_password:
        local_config['password'] = args.local_password
    if args.local_database:
        local_config['database'] = args.local_database
    
    if args.prod_host:
        prod_config['host'] = args.prod_host
    if args.prod_port:
        prod_config['port'] = args.prod_port
    if args.prod_user:
        prod_config['user'] = args.prod_user
    if args.prod_password:
        prod_config['password'] = args.prod_password
    if args.prod_database:
        prod_config['database'] = args.prod_database
    
    # 创建验证器
    verifier = DataConsistencyVerifier(local_config, prod_config)
    
    try:
        # 执行验证
        print("\n🔍 验证数据一致性...")
        results = verifier.verify(key_tables=args.key_tables)
        
        # 打印报告
        verifier.print_report(results)
        
        # 如果有不一致，返回非零退出码
        return 0 if results['consistent'] else 1
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

