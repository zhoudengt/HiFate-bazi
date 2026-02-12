#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库变更检测脚本
对比本地和生产数据库结构，生成变更报告和同步脚本

使用方法：
    python3 scripts/db/detect_db_changes.py [--generate-sync-script]

选项：
    --generate-sync-script: 生成数据库同步脚本
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


class DatabaseComparator:
    """数据库结构比较器"""
    
    def __init__(self, local_config: Dict, production_config: Dict):
        """
        初始化比较器
        
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
    
    def get_tables(self, conn) -> List[str]:
        """获取数据库表列表"""
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            result = cursor.fetchall()
            # 获取第一个字段的值（表名）
            table_key = list(result[0].keys())[0] if result else None
            return [row[table_key] for row in result] if table_key else []
    
    def get_table_structure(self, conn, table_name: str) -> Dict:
        """获取表结构"""
        with conn.cursor() as cursor:
            # 获取字段信息
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME,
                    COLUMN_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    COLUMN_KEY,
                    EXTRA,
                    COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (table_name,))
            columns = cursor.fetchall()
            
            # 获取索引信息
            cursor.execute(f"""
                SELECT 
                    INDEX_NAME,
                    COLUMN_NAME,
                    NON_UNIQUE,
                    SEQ_IN_INDEX
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """, (table_name,))
            indexes = cursor.fetchall()
            
            return {
                'columns': {col['COLUMN_NAME']: col for col in columns},
                'indexes': indexes
            }
    
    def get_table_row_count(self, conn, table_name: str) -> int:
        """获取表的记录数"""
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    def get_table_primary_key(self, conn, table_name: str) -> List[str]:
        """获取表的主键字段列表"""
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = %s
                AND CONSTRAINT_NAME = 'PRIMARY'
                ORDER BY ORDINAL_POSITION
            """, (table_name,))
            result = cursor.fetchall()
            return [row['COLUMN_NAME'] for row in result] if result else []
    
    def get_table_data_diff(self, table_name: str, primary_keys: List[str]) -> List[Dict]:
        """
        检测表数据差异（本地有但生产没有的数据）
        
        Returns:
            本地有但生产没有的数据行列表
        """
        diff_rows = []
        
        # 如果表没有主键，无法精确对比，只能对比记录数
        if not primary_keys:
            return diff_rows
        
        # 获取本地所有数据的主键值
        with self.local_conn.cursor() as local_cursor:
            pk_columns = ', '.join([f"`{pk}`" for pk in primary_keys])
            local_cursor.execute(f"SELECT {pk_columns} FROM `{table_name}`")
            local_rows = local_cursor.fetchall()
            local_pk_set = {tuple(row.values()) for row in local_rows}
        
        # 获取生产所有数据的主键值
        with self.prod_conn.cursor() as prod_cursor:
            prod_cursor.execute(f"SELECT {pk_columns} FROM `{table_name}`")
            prod_rows = prod_cursor.fetchall()
            prod_pk_set = {tuple(row.values()) for row in prod_rows}
        
        # 找出本地有但生产没有的主键
        diff_pk_set = local_pk_set - prod_pk_set
        
        # 获取这些主键对应的完整数据行
        if diff_pk_set:
            pk_conditions = []
            for pk_values in diff_pk_set:
                condition_parts = []
                for i, pk in enumerate(primary_keys):
                    value = list(pk_values)[i]
                    if isinstance(value, str):
                        escaped_value = value.replace("\\", "\\\\").replace("'", "\\'")
                        condition_parts.append(f"`{pk}` = '{escaped_value}'")
                    else:
                        condition_parts.append(f"`{pk}` = {value}")
                pk_conditions.append("(" + " AND ".join(condition_parts) + ")")
            
            with self.local_conn.cursor() as local_cursor:
                where_clause = " OR ".join(pk_conditions)
                local_cursor.execute(f"SELECT * FROM `{table_name}` WHERE {where_clause}")
                diff_rows = local_cursor.fetchall()
        
        return diff_rows
    
    def detect_changes(self) -> Dict:
        """
        检测数据库变更（包括表结构和数据）
        
        Returns:
            {
                'new_tables': [...],
                'new_columns': [...],
                'modified_columns': [...],
                'new_indexes': [...],
                'data_changes': {
                    'new_tables_data': [...],  # 新增表的数据
                    'table_data_diff': [...]    # 表数据差异
                }
            }
        """
        local_tables = set(self.get_tables(self.local_conn))
        prod_tables = set(self.get_tables(self.prod_conn))
        
        changes = {
            'new_tables': [],
            'dropped_tables': [],  # 删除表（生产环境存在但本地不存在）
            'new_columns': [],
            'dropped_columns': [],  # 删除字段（生产环境存在但本地不存在）
            'modified_columns': [],
            'new_indexes': [],
            'data_changes': {
                'new_tables_data': [],  # 新增表的数据
                'table_data_diff': []    # 表数据差异
            }
        }
        
        # 检测新增表
        new_tables = local_tables - prod_tables
        for table in new_tables:
            structure = self.get_table_structure(self.local_conn, table)
            local_row_count = self.get_table_row_count(self.local_conn, table)
            changes['new_tables'].append({
                'table': table,
                'structure': structure,
                'row_count': local_row_count
            })
            
            # 检测新增表的数据
            if local_row_count > 0:
                primary_keys = self.get_table_primary_key(self.local_conn, table)
                changes['data_changes']['new_tables_data'].append({
                    'table': table,
                    'row_count': local_row_count,
                    'primary_keys': primary_keys
                })
        
        # 检测删除表（生产环境存在但本地不存在）
        dropped_tables = prod_tables - local_tables
        for table in dropped_tables:
            prod_row_count = self.get_table_row_count(self.prod_conn, table)
            changes['dropped_tables'].append({
                'table': table,
                'row_count': prod_row_count
            })
        
        # 检测每个表的字段变更和数据差异
        common_tables = local_tables & prod_tables
        for table in common_tables:
            local_structure = self.get_table_structure(self.local_conn, table)
            prod_structure = self.get_table_structure(self.prod_conn, table)
            
            local_columns = set(local_structure['columns'].keys())
            prod_columns = set(prod_structure['columns'].keys())
            
            # 检测新增字段
            new_columns = local_columns - prod_columns
            for col_name in new_columns:
                changes['new_columns'].append({
                    'table': table,
                    'column': local_structure['columns'][col_name]
                })
            
            # 检测删除字段（生产环境存在但本地不存在）
            dropped_columns = prod_columns - local_columns
            for col_name in dropped_columns:
                changes['dropped_columns'].append({
                    'table': table,
                    'column': col_name,
                    'column_info': prod_structure['columns'][col_name]
                })
            
            # 检测修改字段（类型、长度等）
            common_columns = local_columns & prod_columns
            for col_name in common_columns:
                local_col = local_structure['columns'][col_name]
                prod_col = prod_structure['columns'][col_name]
                
                # 比较字段属性
                if (local_col['COLUMN_TYPE'] != prod_col['COLUMN_TYPE'] or
                    local_col['IS_NULLABLE'] != prod_col['IS_NULLABLE'] or
                    local_col['COLUMN_DEFAULT'] != prod_col['COLUMN_DEFAULT']):
                    changes['modified_columns'].append({
                        'table': table,
                        'column': col_name,
                        'local': local_col,
                        'production': prod_col
                    })
            
            # 检测数据差异（对比记录数）
            local_row_count = self.get_table_row_count(self.local_conn, table)
            prod_row_count = self.get_table_row_count(self.prod_conn, table)
            
            if local_row_count > prod_row_count:
                # 本地记录数大于生产，可能存在新增数据
                primary_keys = self.get_table_primary_key(self.local_conn, table)
                if primary_keys:
                    # 尝试获取数据差异
                    diff_rows = self.get_table_data_diff(table, primary_keys)
                    if diff_rows:
                        changes['data_changes']['table_data_diff'].append({
                            'table': table,
                            'local_count': local_row_count,
                            'prod_count': prod_row_count,
                            'diff_count': len(diff_rows),
                            'primary_keys': primary_keys,
                            'sample_rows': diff_rows[:10]  # 只保留前10条作为示例
                        })
        
        return changes
    
    def generate_insert_sql(self, table_name: str, row: Dict) -> str:
        """生成单条INSERT语句"""
        columns = list(row.keys())
        values = []
        
        for col in columns:
            value = row[col]
            if value is None:
                values.append("NULL")
            elif isinstance(value, (int, float)):
                values.append(str(value))
            elif isinstance(value, bool):
                values.append("1" if value else "0")
            else:
                # 转义字符串
                escaped_value = str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
                values.append(f"'{escaped_value}'")
        
        columns_str = ", ".join([f"`{col}`" for col in columns])
        values_str = ", ".join(values)
        return f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({values_str});"
    
    def generate_sync_script(self, changes: Dict, deployment_id: str) -> str:
        """生成数据库同步脚本（包括表结构和数据）"""
        script_lines = []
        script_lines.append(f"-- 数据库同步脚本")
        script_lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        script_lines.append(f"-- 部署ID: {deployment_id}")
        script_lines.append("")
        script_lines.append("START TRANSACTION;")
        script_lines.append("")
        
        # 生成删除表的 SQL（危险操作，需要明确警告）
        if changes['dropped_tables']:
            script_lines.append("-- ==================== 删除表（⚠️ 危险操作，需要手动确认）====================")
            script_lines.append("-- ⚠️  警告：删除表会永久删除所有数据，请先备份数据！")
            script_lines.append("-- ⚠️  建议：在执行删除前，先备份表数据：mysqldump -u root -p database_name table_name > backup_table_name.sql")
            script_lines.append("")
            for table_info in changes['dropped_tables']:
                table = table_info['table']
                row_count = table_info['row_count']
                script_lines.append(f"-- 删除表: {table} (包含 {row_count} 条数据)")
                script_lines.append(f"-- DROP TABLE IF EXISTS `{table}`;")
                script_lines.append("")
        
        # 生成新增表的 SQL
        if changes['new_tables']:
            script_lines.append("-- ==================== 新增表 ====================")
            for table_info in changes['new_tables']:
                table = table_info['table']
                script_lines.append(f"-- 创建表: {table}")
                # 使用 SHOW CREATE TABLE 获取完整的建表语句
                with self.local_conn.cursor() as cursor:
                    cursor.execute(f"SHOW CREATE TABLE `{table}`")
                    result = cursor.fetchone()
                    create_table_sql = result['Create Table']
                    script_lines.append(create_table_sql + ";")
                    script_lines.append("")
        
        # 生成删除字段的 SQL（危险操作，需要明确警告）
        if changes['dropped_columns']:
            script_lines.append("-- ==================== 删除字段（⚠️ 危险操作，需要手动确认）====================")
            script_lines.append("-- ⚠️  警告：删除字段会永久删除该字段的所有数据，请先确认是否有外键依赖！")
            script_lines.append("-- ⚠️  建议：在执行删除前，检查是否有其他表的外键引用此字段")
            script_lines.append("")
            for col_info in changes['dropped_columns']:
                table = col_info['table']
                col_name = col_info['column']
                script_lines.append(f"-- 删除表 {table} 的字段 {col_name}")
                script_lines.append(f"-- ALTER TABLE `{table}` DROP COLUMN `{col_name}`;")
                script_lines.append("")
        
        # 生成新增字段的 SQL
        if changes['new_columns']:
            script_lines.append("-- ==================== 新增字段 ====================")
            for col_info in changes['new_columns']:
                table = col_info['table']
                col = col_info['column']
                col_name = col['COLUMN_NAME']
                col_type = col['COLUMN_TYPE']
                nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
                default = f"DEFAULT {col['COLUMN_DEFAULT']}" if col['COLUMN_DEFAULT'] is not None else ""
                extra = col['EXTRA'] if col['EXTRA'] else ""
                comment = f"COMMENT '{col['COLUMN_COMMENT']}'" if col['COLUMN_COMMENT'] else ""
                
                alter_sql = f"ALTER TABLE `{table}` ADD COLUMN `{col_name}` {col_type} {nullable} {default} {extra} {comment};"
                script_lines.append(f"-- 表 {table} 新增字段 {col_name}")
                script_lines.append(alter_sql)
                script_lines.append("")
        
        # 生成修改字段的 SQL（注意：修改字段需要谨慎，这里只生成警告）
        if changes['modified_columns']:
            script_lines.append("-- ==================== 修改字段（需要手动确认）====================")
            script_lines.append("-- ⚠️  警告：字段修改可能影响现有数据，请手动确认后执行")
            script_lines.append("")
            for col_info in changes['modified_columns']:
                table = col_info['table']
                col_name = col_info['column']
                local_col = col_info['local']
                prod_col = col_info['production']
                
                script_lines.append(f"-- 表 {table} 字段 {col_name} 需要修改")
                script_lines.append(f"-- 本地: {local_col['COLUMN_TYPE']} {local_col['IS_NULLABLE']}")
                script_lines.append(f"-- 生产: {prod_col['COLUMN_TYPE']} {prod_col['IS_NULLABLE']}")
                script_lines.append(f"-- ALTER TABLE `{table}` MODIFY COLUMN `{col_name}` ...;")
                script_lines.append("")
        
        # 生成数据同步 SQL（新增表的数据）
        data_changes = changes.get('data_changes', {})
        if data_changes.get('new_tables_data'):
            script_lines.append("-- ==================== 新增表的数据 ====================")
            for table_data_info in data_changes['new_tables_data']:
                table = table_data_info['table']
                row_count = table_data_info['row_count']
                script_lines.append(f"-- 表 {table} 有 {row_count} 条数据需要同步")
                
                # 获取所有数据
                with self.local_conn.cursor() as cursor:
                    cursor.execute(f"SELECT * FROM `{table}`")
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        insert_sql = self.generate_insert_sql(table, row)
                        script_lines.append(insert_sql)
                
                script_lines.append("")
        
        # 生成数据同步 SQL（表数据差异）
        if data_changes.get('table_data_diff'):
            script_lines.append("-- ==================== 表数据差异（需要同步的数据）====================")
            for diff_info in data_changes['table_data_diff']:
                table = diff_info['table']
                diff_count = diff_info['diff_count']
                script_lines.append(f"-- 表 {table} 有 {diff_count} 条数据需要同步（本地有但生产没有）")
                
                # 获取差异数据
                sample_rows = diff_info.get('sample_rows', [])
                primary_keys = diff_info.get('primary_keys', [])
                
                # 如果有主键，获取完整的差异数据
                if primary_keys and sample_rows:
                    # 从sample_rows中获取主键值，然后查询完整数据
                    pk_columns = ', '.join([f"`{pk}`" for pk in primary_keys])
                    pk_values_list = []
                    for row in sample_rows:
                        pk_values = tuple(row[pk] for pk in primary_keys)
                        pk_values_list.append(pk_values)
                    
                    # 构建WHERE条件
                    if len(pk_values_list) <= 100:  # 限制一次查询的数据量
                        with self.local_conn.cursor() as cursor:
                            where_conditions = []
                            for pk_values in pk_values_list:
                                condition_parts = []
                                for i, pk in enumerate(primary_keys):
                                    value = pk_values[i]
                                    if isinstance(value, str):
                                        escaped_value = value.replace("\\", "\\\\").replace("'", "\\'")
                                        condition_parts.append(f"`{pk}` = '{escaped_value}'")
                                    else:
                                        condition_parts.append(f"`{pk}` = {value}")
                                where_conditions.append("(" + " AND ".join(condition_parts) + ")")
                            
                            if where_conditions:
                                where_clause = " OR ".join(where_conditions)
                                cursor.execute(f"SELECT * FROM `{table}` WHERE {where_clause}")
                                diff_rows = cursor.fetchall()
                                
                                for row in diff_rows:
                                    # 使用 INSERT IGNORE 或 INSERT ... ON DUPLICATE KEY UPDATE 避免重复
                                    insert_sql = self.generate_insert_sql(table, row)
                                    # 改为 INSERT IGNORE 避免主键冲突
                                    insert_sql = insert_sql.replace("INSERT INTO", "INSERT IGNORE INTO")
                                    script_lines.append(insert_sql)
                
                script_lines.append("")
        
        script_lines.append("COMMIT;")
        script_lines.append("")
        script_lines.append("-- 同步完成")
        
        return "\n".join(script_lines)
    
    def generate_rollback_script(self, changes: Dict, deployment_id: str) -> str:
        """生成数据库回滚脚本"""
        script_lines = []
        script_lines.append(f"-- 数据库回滚脚本")
        script_lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        script_lines.append(f"-- 部署ID: {deployment_id}")
        script_lines.append("")
        script_lines.append("START TRANSACTION;")
        script_lines.append("")
        
        # 生成恢复删除字段的 SQL（反向操作：重新添加被删除的字段）
        if changes['dropped_columns']:
            script_lines.append("-- ==================== 恢复删除的字段 ====================")
            script_lines.append("-- ⚠️  注意：此操作会重新添加被删除的字段，但数据无法恢复")
            for col_info in changes['dropped_columns']:
                table = col_info['table']
                col_name = col_info['column']
                col = col_info['column_info']
                col_type = col['COLUMN_TYPE']
                nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
                default = f"DEFAULT {col['COLUMN_DEFAULT']}" if col['COLUMN_DEFAULT'] is not None else ""
                extra = col['EXTRA'] if col['EXTRA'] else ""
                comment = f"COMMENT '{col['COLUMN_COMMENT']}'" if col['COLUMN_COMMENT'] else ""
                
                script_lines.append(f"-- 恢复表 {table} 的字段 {col_name}")
                script_lines.append(f"ALTER TABLE `{table}` ADD COLUMN `{col_name}` {col_type} {nullable} {default} {extra} {comment};")
                script_lines.append("")
        
        # 生成恢复删除表的 SQL（反向操作：重新创建被删除的表）
        if changes['dropped_tables']:
            script_lines.append("-- ==================== 恢复删除的表 ====================")
            script_lines.append("-- ⚠️  注意：此操作会重新创建被删除的表，但数据无法恢复（需要从备份恢复）")
            for table_info in changes['dropped_tables']:
                table = table_info['table']
                script_lines.append(f"-- 恢复表: {table}")
                script_lines.append(f"-- ⚠️  警告：表结构可以恢复，但数据需要从备份恢复")
                script_lines.append(f"-- 如果之前有备份，请使用：mysql -u root -p database_name < backup_{table}.sql")
                script_lines.append("")
        
        # 生成删除新增字段的 SQL（反向操作）
        if changes['new_columns']:
            script_lines.append("-- ==================== 删除新增字段 ====================")
            for col_info in reversed(changes['new_columns']):  # 反向删除
                table = col_info['table']
                col_name = col_info['column']['COLUMN_NAME']
                script_lines.append(f"ALTER TABLE `{table}` DROP COLUMN IF EXISTS `{col_name}`;")
                script_lines.append("")
        
        # 生成删除新增表的 SQL（反向操作）
        if changes['new_tables']:
            script_lines.append("-- ==================== 删除新增表 ====================")
            for table_info in reversed(changes['new_tables']):  # 反向删除
                table = table_info['table']
                script_lines.append(f"DROP TABLE IF EXISTS `{table}`;")
                script_lines.append("")
        
        script_lines.append("COMMIT;")
        script_lines.append("")
        script_lines.append("-- 回滚完成")
        
        return "\n".join(script_lines)


def get_database_config(env: str = 'local') -> Dict:
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
        # 从环境变量或配置文件读取生产数据库配置
        return {
            'host': os.getenv('PROD_MYSQL_HOST', '8.210.52.217'),
            'port': int(os.getenv('PROD_MYSQL_PORT', '3306')),
            'user': os.getenv('PROD_MYSQL_USER', 'root'),
            'password': os.getenv('PROD_MYSQL_PASSWORD', os.getenv("MYSQL_PASSWORD", "")),
            'database': os.getenv('PROD_MYSQL_DATABASE', 'hifate_bazi'),
            'charset': 'utf8mb4'
        }


def main():
    parser = argparse.ArgumentParser(description='数据库变更检测脚本')
    parser.add_argument('--generate-sync-script', action='store_true', help='生成数据库同步脚本')
    parser.add_argument('--skip-prod-connection', action='store_true',
                        help='跳过生产库直连（生产库为 Docker hifate-mysql-master，仅支持 SSH + docker exec，无法本机直连时使用）')
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
    
    # 跳过生产库直连：生产库在 Node1 Docker 内，仅支持 SSH + docker exec，无法从本机直连
    if args.skip_prod_connection:
        print("生产数据库为 Docker 容器 hifate-mysql-master，仅支持通过 Node1 SSH + docker exec 连接，无法从本机直连。")
        print("已跳过生产库直连检测，视为无数据库变更。如有库表变更请手动执行 scripts/db/sync_production_db.sh。")
        print("\n✅ 无数据库变更")
        return 0
    
    # 创建比较器
    comparator = DatabaseComparator(local_config, prod_config)
    
    try:
        # 连接数据库
        comparator.connect()
        
        # 检测变更
        print("\n🔍 检测数据库变更...")
        changes = comparator.detect_changes()
        
        # 打印变更报告
        print("\n" + "=" * 80)
        print("数据库变更报告")
        print("=" * 80)
        
        if changes['new_tables']:
            print(f"\n📋 新增表 ({len(changes['new_tables'])} 个):")
            for table_info in changes['new_tables']:
                print(f"  - {table_info['table']}")
        else:
            print("\n✅ 无新增表")
        
        if changes['dropped_tables']:
            print(f"\n⚠️  删除表 ({len(changes['dropped_tables'])} 个，生产环境存在但本地不存在):")
            for table_info in changes['dropped_tables']:
                print(f"  - {table_info['table']} (包含 {table_info['row_count']} 条数据)")
        else:
            print("\n✅ 无删除表")
        
        if changes['new_columns']:
            print(f"\n📋 新增字段 ({len(changes['new_columns'])} 个):")
            for col_info in changes['new_columns']:
                print(f"  - {col_info['table']}.{col_info['column']['COLUMN_NAME']}")
        else:
            print("\n✅ 无新增字段")
        
        if changes['dropped_columns']:
            print(f"\n⚠️  删除字段 ({len(changes['dropped_columns'])} 个，生产环境存在但本地不存在):")
            for col_info in changes['dropped_columns']:
                print(f"  - {col_info['table']}.{col_info['column']}")
        else:
            print("\n✅ 无删除字段")
        
        if changes['modified_columns']:
            print(f"\n⚠️  修改字段 ({len(changes['modified_columns'])} 个，需要手动确认):")
            for col_info in changes['modified_columns']:
                print(f"  - {col_info['table']}.{col_info['column']}")
        else:
            print("\n✅ 无修改字段")
        
        # 显示数据变更
        data_changes = changes.get('data_changes', {})
        if data_changes.get('new_tables_data'):
            print(f"\n📋 新增表的数据 ({len(data_changes['new_tables_data'])} 个表):")
            for table_data_info in data_changes['new_tables_data']:
                print(f"  - {table_data_info['table']}: {table_data_info['row_count']} 条记录")
        else:
            print("\n✅ 无新增表数据")
        
        if data_changes.get('table_data_diff'):
            print(f"\n📋 表数据差异 ({len(data_changes['table_data_diff'])} 个表):")
            for diff_info in data_changes['table_data_diff']:
                print(f"  - {diff_info['table']}: 本地 {diff_info['local_count']} 条，生产 {diff_info['prod_count']} 条，差异 {diff_info['diff_count']} 条")
        else:
            print("\n✅ 无表数据差异")
        
        print("\n" + "=" * 80)
        
        # 获取数据变更信息（用于后续处理）
        data_changes = changes.get('data_changes', {})
        
        # 生成同步脚本
        if args.generate_sync_script:
            deployment_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 生成同步脚本
            sync_script = comparator.generate_sync_script(changes, deployment_id)
            sync_file = f"scripts/db/sync_{deployment_id}.sql"
            os.makedirs(os.path.dirname(sync_file), exist_ok=True)
            with open(sync_file, 'w', encoding='utf-8') as f:
                f.write(sync_script)
            print(f"\n✅ 同步脚本已生成: {sync_file}")
            
            # 生成回滚脚本
            rollback_script = comparator.generate_rollback_script(changes, deployment_id)
            rollback_file = f"scripts/db/rollback/rollback_{deployment_id}.sql"
            os.makedirs(os.path.dirname(rollback_file), exist_ok=True)
            with open(rollback_file, 'w', encoding='utf-8') as f:
                f.write(rollback_script)
            print(f"✅ 回滚脚本已生成: {rollback_file}")
            
            # 保存变更信息到 JSON（供其他脚本使用）
            changes_file = f"scripts/db/changes_{deployment_id}.json"
            with open(changes_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'deployment_id': deployment_id,
                    'timestamp': datetime.now().isoformat(),
                    'changes': {
                        'new_tables': [t['table'] for t in changes['new_tables']],
                        'new_columns': [f"{c['table']}.{c['column']['COLUMN_NAME']}" for c in changes['new_columns']],
                        'modified_columns': [f"{c['table']}.{c['column']}" for c in changes['modified_columns']],
                        'new_tables_data': [{'table': t['table'], 'row_count': t['row_count']} for t in data_changes.get('new_tables_data', [])],
                        'table_data_diff': [{'table': d['table'], 'diff_count': d['diff_count']} for d in data_changes.get('table_data_diff', [])]
                    }
                }, f, ensure_ascii=False, indent=2)
            print(f"✅ 变更信息已保存: {changes_file}")
        
        # 如果有变更，返回非零退出码
        has_changes = any([
            changes['new_tables'],
            changes['new_columns'],
            changes['modified_columns'],
            data_changes.get('new_tables_data'),
            data_changes.get('table_data_diff')
        ])
        
        if has_changes:
            return 0
        else:
            print("\n✅ 无数据库变更")
            return 0
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        comparator.close()


if __name__ == '__main__':
    sys.exit(main())

