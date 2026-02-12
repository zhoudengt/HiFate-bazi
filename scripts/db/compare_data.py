#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据对比工具
对比本地和生产数据库的数据，生成详细的差异报告

使用方法：
    python3 scripts/db/compare_data.py [--node node1|node2] [--tables table1,table2]
"""

import sys
import os
import json
import argparse
from typing import Dict, List, Tuple, Optional
from datetime import datetime

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


class DataComparator:
    """数据对比器"""
    
    def __init__(self, local_config: Dict, production_config: Dict):
        """
        初始化对比器
        
        Args:
            local_config: 本地数据库配置
            production_config: 生产数据库配置
        """
        self.local_config = local_config
        self.production_config = production_config
        self.local_conn = None
        self.prod_conn = None
    
    def connect(self):
        """连接数据库"""
        try:
            self.local_conn = pymysql.connect(**self.local_config, cursorclass=DictCursor)
            print(f"✅ 本地数据库连接成功: {self.local_config['host']}:{self.local_config['port']}")
        except Exception as e:
            print(f"❌ 本地数据库连接失败: {e}")
            sys.exit(1)
        
        try:
            self.prod_conn = pymysql.connect(**self.production_config, cursorclass=DictCursor)
            print(f"✅ 生产数据库连接成功: {self.production_config['host']}:{self.production_config['port']}")
        except Exception as e:
            print(f"❌ 生产数据库连接失败: {e}")
            sys.exit(1)
    
    def close(self):
        """关闭数据库连接"""
        if self.local_conn:
            self.local_conn.close()
        if self.prod_conn:
            self.prod_conn.close()
    
    def get_table_list(self, conn) -> List[str]:
        """获取表列表"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            return [row['table_name'] for row in cursor.fetchall()]
    
    def get_table_primary_key(self, conn, table_name: str) -> List[str]:
        """获取表的主键列"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_schema = DATABASE()
                AND table_name = %s
                AND constraint_name = 'PRIMARY'
                ORDER BY ordinal_position
            """, (table_name,))
            return [row['column_name'] for row in cursor.fetchall()]
    
    def get_table_row_count(self, conn, table_name: str) -> int:
        """获取表的行数"""
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def get_table_checksum(self, conn, table_name: str) -> Optional[str]:
        """获取表的校验和"""
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CHECKSUM TABLE `{table_name}`")
                result = cursor.fetchone()
                return str(result['Checksum']) if result and 'Checksum' in result else None
        except Exception:
            return None
    
    def compare_table_data(self, table_name: str) -> Dict:
        """
        对比表数据（详细对比）
        
        Args:
            table_name: 表名
            
        Returns:
            对比结果字典
        """
        result = {
            'table_name': table_name,
            'local_count': 0,
            'prod_count': 0,
            'local_checksum': None,
            'prod_checksum': None,
            'is_identical': False,
            'differences': []
        }
        
        # 获取行数和校验和
        result['local_count'] = self.get_table_row_count(self.local_conn, table_name)
        result['prod_count'] = self.get_table_row_count(self.prod_conn, table_name)
        result['local_checksum'] = self.get_table_checksum(self.local_conn, table_name)
        result['prod_checksum'] = self.get_table_checksum(self.prod_conn, table_name)
        
        # 快速对比：如果行数和校验和都相同，认为数据一致
        if result['local_count'] == result['prod_count'] and result['local_checksum'] == result['prod_checksum']:
            result['is_identical'] = True
            return result
        
        # 详细对比：获取主键，对比每条记录
        primary_keys = self.get_table_primary_key(self.local_conn, table_name)
        if not primary_keys:
            # 没有主键，无法详细对比
            result['differences'].append({
                'type': 'no_primary_key',
                'message': '表没有主键，无法进行详细对比'
            })
            return result
        
        # 获取本地数据
        local_data = {}
        with self.local_conn.cursor() as cursor:
            pk_columns = ", ".join([f"`{pk}`" for pk in primary_keys])
            cursor.execute(f"SELECT * FROM `{table_name}`")
            for row in cursor.fetchall():
                pk_value = tuple(row[pk] for pk in primary_keys)
                local_data[pk_value] = row
        
        # 获取生产数据
        prod_data = {}
        with self.prod_conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}`")
            for row in cursor.fetchall():
                pk_value = tuple(row[pk] for pk in primary_keys)
                prod_data[pk_value] = row
        
        # 对比数据
        local_keys = set(local_data.keys())
        prod_keys = set(prod_data.keys())
        
        # 仅在本地存在的数据
        local_only = local_keys - prod_keys
        if local_only:
            result['differences'].append({
                'type': 'local_only',
                'count': len(local_only),
                'primary_keys': [str(pk) for pk in list(local_only)[:10]]  # 只显示前10个
            })
        
        # 仅在生产存在的数据
        prod_only = prod_keys - local_keys
        if prod_only:
            result['differences'].append({
                'type': 'prod_only',
                'count': len(prod_only),
                'primary_keys': [str(pk) for pk in list(prod_only)[:10]]  # 只显示前10个
            })
        
        # 共同存在但数据不同的记录
        common_keys = local_keys & prod_keys
        different_records = []
        for pk_value in common_keys:
            local_row = local_data[pk_value]
            prod_row = prod_data[pk_value]
            
            # 对比每个字段
            different_fields = []
            for key in local_row.keys():
                if local_row[key] != prod_row[key]:
                    different_fields.append({
                        'field': key,
                        'local_value': str(local_row[key])[:100],  # 限制长度
                        'prod_value': str(prod_row[key])[:100]
                    })
            
            if different_fields:
                different_records.append({
                    'primary_key': str(pk_value),
                    'different_fields': different_fields
                })
                
                # 限制记录数量
                if len(different_records) >= 10:
                    break
        
        if different_records:
            result['differences'].append({
                'type': 'different_data',
                'count': len(different_records),
                'records': different_records
            })
        
        result['is_identical'] = len(result['differences']) == 0
        return result
    
    def compare_all_tables(self, tables: Optional[List[str]] = None) -> Dict:
        """
        对比所有表
        
        Args:
            tables: 要对比的表列表（None表示所有表）
            
        Returns:
            对比结果字典
        """
        print("\n🔍 开始详细对比数据...")
        print("=" * 80)
        
        local_tables = set(self.get_table_list(self.local_conn))
        prod_tables = set(self.get_table_list(self.prod_conn))
        
        if tables:
            local_tables = local_tables & set(tables)
            prod_tables = prod_tables & set(tables)
        
        all_tables = local_tables | prod_tables
        comparison_result = {
            'timestamp': datetime.now().isoformat(),
            'tables': {},
            'summary': {
                'total_tables': len(all_tables),
                'identical_tables': 0,
                'different_tables': 0,
                'local_only_tables': 0,
                'prod_only_tables': 0
            }
        }
        
        for table_name in sorted(all_tables):
            print(f"\n📊 对比表: {table_name}...")
            
            if table_name not in local_tables:
                comparison_result['tables'][table_name] = {
                    'status': 'prod_only',
                    'local_count': 0,
                    'prod_count': self.get_table_row_count(self.prod_conn, table_name),
                    'is_identical': False
                }
                comparison_result['summary']['prod_only_tables'] += 1
                print(f"  ⚠️  仅在生产环境存在 ({comparison_result['tables'][table_name]['prod_count']} 行)")
                continue
            
            if table_name not in prod_tables:
                comparison_result['tables'][table_name] = {
                    'status': 'local_only',
                    'local_count': self.get_table_row_count(self.local_conn, table_name),
                    'prod_count': 0,
                    'is_identical': False
                }
                comparison_result['summary']['local_only_tables'] += 1
                print(f"  ⚠️  仅在本地存在 ({comparison_result['tables'][table_name]['local_count']} 行)")
                continue
            
            # 详细对比表数据
            table_result = self.compare_table_data(table_name)
            comparison_result['tables'][table_name] = table_result
            
            if table_result['is_identical']:
                comparison_result['summary']['identical_tables'] += 1
                print(f"  ✅ 数据一致 ({table_result['local_count']} 行)")
            else:
                comparison_result['summary']['different_tables'] += 1
                print(f"  ❌ 数据不一致 (本地: {table_result['local_count']}, 生产: {table_result['prod_count']})")
                
                # 显示差异详情
                for diff in table_result['differences']:
                    if diff['type'] == 'local_only':
                        print(f"    - 仅在本地存在: {diff['count']} 条记录")
                    elif diff['type'] == 'prod_only':
                        print(f"    - 仅在生产存在: {diff['count']} 条记录")
                    elif diff['type'] == 'different_data':
                        print(f"    - 数据不同: {diff['count']} 条记录")
        
        print("\n" + "=" * 80)
        print(f"\n📊 对比摘要:")
        print(f"  总表数: {comparison_result['summary']['total_tables']}")
        print(f"  一致表数: {comparison_result['summary']['identical_tables']}")
        print(f"  不一致表数: {comparison_result['summary']['different_tables']}")
        print(f"  仅本地表数: {comparison_result['summary']['local_only_tables']}")
        print(f"  仅生产表数: {comparison_result['summary']['prod_only_tables']}")
        
        return comparison_result


def get_database_config(env: str = 'local', node: Optional[str] = None) -> Dict:
    """获取数据库配置"""
    if env == 'local':
        return {
            'host': os.getenv('MYSQL_HOST', 'localhost'),
            'port': int(os.getenv('MYSQL_PORT', '3306')),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', '123456')),
            'database': os.getenv('MYSQL_DATABASE', 'hifate_bazi'),
            'charset': 'utf8mb4'
        }
    else:  # production
        node_ip = {
            'node1': os.getenv('NODE1_IP', '8.210.52.217'),
            'node2': os.getenv('NODE2_IP', '47.243.160.43')
        }.get(node or 'node1', '8.210.52.217')
        
        return {
            'host': os.getenv('PROD_MYSQL_HOST', node_ip),
            'port': int(os.getenv('PROD_MYSQL_PORT', '3306')),
            'user': os.getenv('PROD_MYSQL_USER', 'root'),
            'password': os.getenv('PROD_MYSQL_PASSWORD', os.getenv("MYSQL_PASSWORD", "")),
            'database': os.getenv('PROD_MYSQL_DATABASE', 'hifate_bazi'),
            'charset': 'utf8mb4'
        }


def main():
    parser = argparse.ArgumentParser(description='数据对比工具')
    parser.add_argument('--node', choices=['node1', 'node2'], default='node1', help='目标节点')
    parser.add_argument('--tables', help='要对比的表列表（逗号分隔）')
    parser.add_argument('--output', help='输出JSON文件路径')
    parser.add_argument('--prod-host', help='生产环境主机地址')
    parser.add_argument('--prod-port', type=int, help='生产环境端口')
    parser.add_argument('--prod-user', help='生产环境用户名')
    parser.add_argument('--prod-password', help='生产环境密码')
    parser.add_argument('--prod-database', help='生产环境数据库名')
    
    args = parser.parse_args()
    
    # 获取数据库配置
    local_config = get_database_config('local')
    
    if args.prod_host:
        prod_config = {
            'host': args.prod_host,
            'port': args.prod_port or 3306,
            'user': args.prod_user or 'root',
            'password': args.prod_password or os.getenv("MYSQL_PASSWORD", ""),
            'database': args.prod_database or 'hifate_bazi',
            'charset': 'utf8mb4'
        }
    else:
        prod_config = get_database_config('production', args.node)
    
    # 创建对比器
    comparator = DataComparator(local_config, prod_config)
    
    try:
        comparator.connect()
        
        # 解析表列表
        tables = None
        if args.tables:
            tables = [t.strip() for t in args.tables.split(',')]
        
        # 执行对比
        comparison_result = comparator.compare_all_tables(tables)
        
        # 保存对比结果
        if not args.output:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            args.output = f"/tmp/hifate_data_comparison_{timestamp}.json"
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(comparison_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 对比结果已保存: {args.output}")
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        comparator.close()


if __name__ == '__main__':
    main()

