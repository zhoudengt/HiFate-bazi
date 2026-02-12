#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无锁表增量数据同步脚本
使用 INSERT ... ON DUPLICATE KEY UPDATE 实现无锁增量同步

使用方法：
    python3 scripts/db/sync_incremental_data_no_lock.py --compare  # 对比数据
    python3 scripts/db/sync_incremental_data_no_lock.py --sync --node node1  # 同步到Node1
    python3 scripts/db/sync_incremental_data_no_lock.py --sync --node node2  # 同步到Node2
"""

import sys
import os
import json
import argparse
import subprocess
from typing import Dict, List, Tuple, Optional, Set
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


class IncrementalDataSyncer:
    """增量数据同步器（无锁表）"""
    
    def __init__(self, local_config: Dict, production_config: Optional[Dict] = None):
        """
        初始化同步器
        
        Args:
            local_config: 本地数据库配置
            production_config: 生产数据库配置（可选，用于对比）
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
        
        if self.production_config:
            try:
                self.prod_conn = pymysql.connect(**self.production_config, cursorclass=DictCursor)
                print(f"✅ 生产数据库连接成功: {self.production_config['host']}:{self.production_config['port']}")
            except Exception as e:
                print(f"⚠️  生产数据库连接失败: {e}")
                self.prod_conn = None
    
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
            results = cursor.fetchall()
            # 处理字典和元组两种格式
            if results and isinstance(results[0], dict):
                # information_schema返回的字段名可能是大写
                return [row.get('table_name') or row.get('TABLE_NAME') for row in results]
            else:
                return [row[0] for row in results]
    
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
            results = cursor.fetchall()
            # 处理字典和元组两种格式
            if results and isinstance(results[0], dict):
                # information_schema返回的字段名可能是大写
                return [row.get('column_name') or row.get('COLUMN_NAME') for row in results]
            else:
                return [row[0] for row in results]
    
    def get_table_columns(self, conn, table_name: str) -> List[str]:
        """获取表的列名"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            results = cursor.fetchall()
            # 处理字典和元组两种格式
            if results and isinstance(results[0], dict):
                # information_schema返回的字段名可能是大写
                return [row.get('column_name') or row.get('COLUMN_NAME') for row in results]
            else:
                return [row[0] for row in results]
    
    def get_table_row_count(self, conn, table_name: str) -> int:
        """获取表的行数"""
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            result = cursor.fetchone()
            if isinstance(result, dict):
                return result.get('count', 0) if result else 0
            else:
                return result[0] if result else 0
    
    def get_table_checksum(self, conn, table_name: str) -> Optional[str]:
        """获取表的校验和（用于快速对比）"""
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"CHECKSUM TABLE `{table_name}`")
                result = cursor.fetchone()
                if isinstance(result, dict):
                    return str(result.get('Checksum', '')) if result and 'Checksum' in result else None
                else:
                    # 元组格式：(table_name, checksum)
                    return str(result[1]) if result and len(result) > 1 else None
        except Exception:
            return None
    
    def compare_tables(self, tables: Optional[List[str]] = None) -> Dict:
        """
        对比本地和生产数据库的表数据
        
        Args:
            tables: 要对比的表列表（None表示所有表）
            
        Returns:
            对比结果字典
        """
        if not self.prod_conn:
            print("❌ 生产数据库未连接，无法对比")
            return {}
        
        print("\n🔍 开始对比数据...")
        print("=" * 80)
        
        local_tables = set(self.get_table_list(self.local_conn))
        prod_tables = set(self.get_table_list(self.prod_conn))
        
        if tables:
            local_tables = local_tables & set(tables)
            prod_tables = prod_tables & set(tables)
        
        all_tables = local_tables | prod_tables
        comparison_result = {
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
            if table_name not in local_tables:
                comparison_result['tables'][table_name] = {
                    'status': 'prod_only',
                    'local_count': 0,
                    'prod_count': self.get_table_row_count(self.prod_conn, table_name)
                }
                comparison_result['summary']['prod_only_tables'] += 1
                print(f"⚠️  {table_name}: 仅在生产环境存在 ({comparison_result['tables'][table_name]['prod_count']} 行)")
                continue
            
            if table_name not in prod_tables:
                comparison_result['tables'][table_name] = {
                    'status': 'local_only',
                    'local_count': self.get_table_row_count(self.local_conn, table_name),
                    'prod_count': 0
                }
                comparison_result['summary']['local_only_tables'] += 1
                print(f"⚠️  {table_name}: 仅在本地存在 ({comparison_result['tables'][table_name]['local_count']} 行)")
                continue
            
            # 对比表数据
            local_count = self.get_table_row_count(self.local_conn, table_name)
            prod_count = self.get_table_row_count(self.prod_conn, table_name)
            local_checksum = self.get_table_checksum(self.local_conn, table_name)
            prod_checksum = self.get_table_checksum(self.prod_conn, table_name)
            
            is_identical = (local_count == prod_count) and (local_checksum == prod_checksum)
            
            comparison_result['tables'][table_name] = {
                'status': 'identical' if is_identical else 'different',
                'local_count': local_count,
                'prod_count': prod_count,
                'local_checksum': local_checksum,
                'prod_checksum': prod_checksum
            }
            
            if is_identical:
                comparison_result['summary']['identical_tables'] += 1
                print(f"✅ {table_name}: 数据一致 ({local_count} 行)")
            else:
                comparison_result['summary']['different_tables'] += 1
                print(f"❌ {table_name}: 数据不一致 (本地: {local_count}, 生产: {prod_count})")
        
        print("=" * 80)
        print(f"\n📊 对比摘要:")
        print(f"  总表数: {comparison_result['summary']['total_tables']}")
        print(f"  一致表数: {comparison_result['summary']['identical_tables']}")
        print(f"  不一致表数: {comparison_result['summary']['different_tables']}")
        print(f"  仅本地表数: {comparison_result['summary']['local_only_tables']}")
        print(f"  仅生产表数: {comparison_result['summary']['prod_only_tables']}")
        
        return comparison_result
    
    def generate_incremental_sql(self, table_name: str, batch_size: int = 1000) -> str:
        """
        生成增量SQL（使用 INSERT ... ON DUPLICATE KEY UPDATE）
        
        Args:
            table_name: 表名
            batch_size: 批次大小
            
        Returns:
            SQL语句字符串
        """
        # 获取主键
        primary_keys = self.get_table_primary_key(self.local_conn, table_name)
        if not primary_keys:
            print(f"⚠️  表 {table_name} 没有主键，跳过")
            return ""
        
        # 获取列名
        columns = self.get_table_columns(self.local_conn, table_name)
        if not columns:
            return ""
        
        sql_lines = []
        sql_lines.append(f"-- 增量同步表: {table_name}")
        sql_lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_lines.append("START TRANSACTION;")
        sql_lines.append("")
        
        # 查询本地数据
        with self.local_conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM `{table_name}`")
            
            batch = []
            total_rows = 0
            
            for row in cursor.fetchall():
                batch.append(row)
                
                if len(batch) >= batch_size:
                    sql_lines.extend(self._generate_batch_insert_sql(table_name, columns, primary_keys, batch))
                    total_rows += len(batch)
                    batch = []
            
            # 处理剩余数据
            if batch:
                sql_lines.extend(self._generate_batch_insert_sql(table_name, columns, primary_keys, batch))
                total_rows += len(batch)
        
        sql_lines.append("")
        sql_lines.append("COMMIT;")
        sql_lines.append(f"-- 总计: {total_rows} 行")
        sql_lines.append("")
        
        return "\n".join(sql_lines)
    
    def _generate_batch_insert_sql(self, table_name: str, columns: List[str], 
                                   primary_keys: List[str], batch: List[Dict]) -> List[str]:
        """生成批量INSERT ... ON DUPLICATE KEY UPDATE SQL"""
        sql_lines = []
        
        # 构建列名列表
        columns_str = ", ".join([f"`{col}`" for col in columns])
        
        # 构建ON DUPLICATE KEY UPDATE子句
        update_clause = ", ".join([f"`{col}`=VALUES(`{col}`)" for col in columns])
        
        # 构建VALUES子句
        values_list = []
        for row in batch:
            values = []
            for col in columns:
                value = row.get(col)
                if value is None:
                    values.append("NULL")
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                elif isinstance(value, bool):
                    values.append("1" if value else "0")
                else:
                    # 转义字符串
                    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
                    values.append(f"'{escaped}'")
            values_list.append(f"({', '.join(values)})")
        
        # 生成INSERT语句
        sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES\n"
        sql += ",\n".join(values_list)
        sql += f"\nON DUPLICATE KEY UPDATE {update_clause};"
        
        sql_lines.append(sql)
        sql_lines.append("")
        
        return sql_lines
    
    def get_table_create_sql(self, table_name: str) -> str:
        """
        获取表的CREATE TABLE语句
        
        Args:
            table_name: 表名
            
        Returns:
            CREATE TABLE SQL语句
        """
        with self.local_conn.cursor() as cursor:
            cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
            result = cursor.fetchone()
            if isinstance(result, dict):
                # 尝试不同的字段名
                create_sql = (result.get('Create Table') or 
                             result.get('CREATE TABLE') or 
                             result.get('create table') or
                             result.get(list(result.keys())[1] if len(result.keys()) > 1 else ''))
            else:
                # 元组格式：(table_name, create_sql)
                create_sql = result[1] if result and len(result) > 1 else ''
            
            if create_sql:
                # 添加 IF NOT EXISTS（如果还没有）
                if "IF NOT EXISTS" not in create_sql.upper():
                    create_sql = create_sql.replace(f"CREATE TABLE `{table_name}`", f"CREATE TABLE IF NOT EXISTS `{table_name}`")
                
                # 移除AUTO_INCREMENT值（避免冲突）
                import re
                create_sql = re.sub(r'AUTO_INCREMENT=\d+', 'AUTO_INCREMENT=1', create_sql)
                
                # 确保语句以分号结尾
                create_sql = create_sql.strip()
                if not create_sql.endswith(';'):
                    create_sql = create_sql + ';'
                
                return create_sql
            return ""
    
    def generate_sync_sql(self, tables: Optional[List[str]] = None, output_file: Optional[str] = None, 
                         skip_missing_tables: bool = True, create_missing_tables: bool = True) -> str:
        """
        生成同步SQL文件
        
        Args:
            tables: 要同步的表列表（None表示所有表）
            output_file: 输出文件路径（可选）
            skip_missing_tables: 是否跳过不存在的表（在生产环境中）
            create_missing_tables: 是否为不存在的表创建表结构
            
        Returns:
            SQL文件路径
        """
        if not tables:
            tables = self.get_table_list(self.local_conn)
        
        print(f"\n📝 生成增量同步SQL...")
        print(f"   表数量: {len(tables)}")
        
        sql_lines = []
        sql_lines.append("-- 无锁表增量数据同步SQL")
        sql_lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_lines.append(f"-- 表数量: {len(tables)}")
        sql_lines.append("")
        sql_lines.append("SET NAMES utf8mb4;")
        sql_lines.append("SET FOREIGN_KEY_CHECKS=0;")
        sql_lines.append("")
        
        # 如果skip_missing_tables为True，检查生产环境中哪些表存在
        existing_tables = set()
        missing_tables = []
        
        # 方式1：如果能够连接生产数据库，直接查询
        if skip_missing_tables and self.prod_conn:
            try:
                existing_tables = set(self.get_table_list(self.prod_conn))
                missing_tables = [t for t in tables if t not in existing_tables]
            except Exception as e:
                print(f"   ⚠️  无法连接生产数据库检查表: {e}")
        
        # 方式2：如果无法连接，尝试从环境变量读取表列表（由Shell脚本提供）
        if not existing_tables:
            prod_tables_file = os.getenv('PROD_TABLES_FILE')
            if prod_tables_file and os.path.exists(prod_tables_file):
                try:
                    with open(prod_tables_file, 'r', encoding='utf-8') as f:
                        # 过滤掉错误信息、警告和空行
                        lines = []
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('ERROR') and not line.startswith('Warning') and not line.startswith('mysql:'):
                                lines.append(line)
                        existing_tables = set(lines)
                    missing_tables = [t for t in tables if t not in existing_tables]
                    print(f"   📋 从文件读取生产环境表列表: {len(existing_tables)} 个表")
                    if missing_tables:
                        print(f"   📋 检测到 {len(missing_tables)} 个表在生产环境不存在: {', '.join(missing_tables[:5])}{'...' if len(missing_tables) > 5 else ''}")
                except Exception as e:
                    print(f"   ⚠️  读取生产环境表列表失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 如果仍然无法获取且需要创建表，假设所有表都不存在（将创建所有表）
        if not existing_tables and create_missing_tables:
            print(f"   ⚠️  无法获取生产环境表列表，将尝试创建所有表")
            missing_tables = list(tables)
        
        # 强制创建模式：即使表列表匹配，也生成CREATE TABLE IF NOT EXISTS（确保表存在）
        # 这样可以处理表名匹配但表实际不存在的情况
        # 注意：由于无法直接连接生产数据库验证，我们总是生成CREATE TABLE IF NOT EXISTS
        if create_missing_tables:
            if not missing_tables:
                # 如果检测到所有表都存在，但仍然生成CREATE TABLE IF NOT EXISTS确保表结构正确
                print(f"   📋 虽然检测到所有表都存在，但仍将生成CREATE TABLE IF NOT EXISTS确保表结构正确")
            missing_tables = list(tables)  # 为所有表生成CREATE TABLE IF NOT EXISTS
        
        # 输出检测结果
        if existing_tables:
            print(f"   📊 生产环境已有 {len(existing_tables)} 个表")
            if missing_tables:
                print(f"   📋 需要创建 {len(missing_tables)} 个表: {', '.join(missing_tables[:5])}{'...' if len(missing_tables) > 5 else ''}")
            else:
                print(f"   ✅ 所有表都已存在，无需创建")
        
        processed_count = 0
        skipped_count = 0
        created_count = 0
        
        # 先创建不存在的表
        if create_missing_tables and missing_tables:
            print(f"\n   📋 检测到 {len(missing_tables)} 个表在生产环境不存在，将创建表结构...")
            sql_lines.append("-- ========================================")
            sql_lines.append("-- 创建不存在的表结构")
            sql_lines.append("-- ========================================")
            sql_lines.append("")
            
            for table_name in missing_tables:
                print(f"   📝 生成表结构: {table_name}...")
                create_sql = self.get_table_create_sql(table_name)
                if create_sql:
                    sql_lines.append(f"-- 创建表: {table_name}")
                    sql_lines.append(create_sql)
                    sql_lines.append("")
                    created_count += 1
                else:
                    print(f"   ⚠️  无法获取表结构: {table_name}")
            
            sql_lines.append("-- ========================================")
            sql_lines.append("-- 同步数据")
            sql_lines.append("-- ========================================")
            sql_lines.append("")
        
        # 然后同步数据（包括新创建的表）
        for table_name in tables:
            # 如果表在生产环境中不存在且不创建，跳过
            if skip_missing_tables and existing_tables and table_name not in existing_tables and not create_missing_tables:
                print(f"   ⚠️  跳过表（生产环境不存在）: {table_name}")
                skipped_count += 1
                continue
            
            print(f"   处理表数据: {table_name}...")
            table_sql = self.generate_incremental_sql(table_name)
            if table_sql:
                sql_lines.append(table_sql)
                processed_count += 1
        
        sql_lines.append("SET FOREIGN_KEY_CHECKS=1;")
        sql_lines.append("")
        sql_lines.append(f"-- 同步完成（创建: {created_count} 个表，处理: {processed_count} 个表，跳过: {skipped_count} 个表）")
        
        sql_content = "\n".join(sql_lines)
        
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"/tmp/hifate_incremental_sync_{timestamp}.sql"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sql_content)
        
        file_size = os.path.getsize(output_file)
        print(f"\n✅ SQL文件生成成功: {output_file}")
        print(f"   文件大小: {file_size / 1024:.2f} KB")
        print(f"   创建表数: {created_count}, 处理表数: {processed_count}, 跳过表数: {skipped_count}")
        
        return output_file


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
        # 从环境变量读取生产数据库配置
        # 注意：生产环境配置需要通过SSH获取，这里返回默认配置
        # 实际使用时，应该通过SSH执行获取配置
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
    parser = argparse.ArgumentParser(description='无锁表增量数据同步脚本')
    parser.add_argument('--compare', action='store_true', help='对比本地和生产数据')
    parser.add_argument('--sync', action='store_true', help='生成同步SQL')
    parser.add_argument('--node', choices=['node1', 'node2'], help='目标节点（用于对比）')
    parser.add_argument('--tables', help='要同步的表列表（逗号分隔）')
    parser.add_argument('--output', help='输出SQL文件路径')
    parser.add_argument('--create-missing-tables', action='store_true', default=True, help='为不存在的表创建表结构（默认：True）')
    parser.add_argument('--no-create-missing-tables', dest='create_missing_tables', action='store_false', help='不为不存在的表创建表结构')
    parser.add_argument('--prod-host', help='生产环境主机地址')
    parser.add_argument('--prod-port', type=int, help='生产环境端口')
    parser.add_argument('--prod-user', help='生产环境用户名')
    parser.add_argument('--prod-password', help='生产环境密码')
    parser.add_argument('--prod-database', help='生产环境数据库名')
    
    args = parser.parse_args()
    
    # 获取本地数据库配置
    local_config = get_database_config('local')
    
    # 获取生产数据库配置
    prod_config = None
    if args.compare or args.node:
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
    
    # 创建同步器
    syncer = IncrementalDataSyncer(local_config, prod_config)
    
    try:
        syncer.connect()
        
        # 解析表列表
        tables = None
        if args.tables:
            tables = [t.strip() for t in args.tables.split(',')]
        
        # 执行对比
        if args.compare:
            comparison_result = syncer.compare_tables(tables)
            
            # 保存对比结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = f"/tmp/hifate_data_comparison_{timestamp}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(comparison_result, f, indent=2, ensure_ascii=False)
            print(f"\n✅ 对比结果已保存: {result_file}")
        
        # 生成同步SQL
        if args.sync:
            sql_file = syncer.generate_sync_sql(tables, args.output, create_missing_tables=args.create_missing_tables)
            print(f"\n✅ 同步SQL已生成: {sql_file}")
            print(f"\n💡 下一步：使用 sync_incremental_data_no_lock.sh 脚本同步到生产环境")
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        syncer.close()


if __name__ == '__main__':
    main()

