#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地 MySQL 同步表和数据到生产环境

功能：
1. 从本地 MySQL 导出所有表的结构和数据
2. 使用 mysqldump 导出（需要本地 MySQL 服务运行）
3. 生成使用 INSERT IGNORE 的 SQL（合并模式）
4. 直接导入到生产 Node1 Docker MySQL

使用方法：
    python3 scripts/db/sync_local_to_production.py                    # 同步所有表
    python3 scripts/db/sync_local_to_production.py --dry-run          # 预览模式
    python3 scripts/db/sync_local_to_production.py --tables "table1,table2"  # 同步指定表
"""

import sys
import os
import argparse
import subprocess
import tempfile
import re
from typing import List, Optional, Dict
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("❌ 错误: 缺少 pymysql 模块，请安装: pip install pymysql")
    sys.exit(1)


class LocalToProductionSyncer:
    """从本地 MySQL 同步到生产 MySQL 的同步器"""
    
    def __init__(self, local_config: Dict, production_config: Dict):
        """
        初始化同步器
        
        Args:
            local_config: 本地 MySQL 配置
            production_config: 生产 MySQL 配置
        """
        self.local_config = local_config
        self.production_config = production_config
        self.prod_conn = None
    
    def check_local_mysql(self) -> bool:
        """检查本地 MySQL 连接"""
        try:
            conn = pymysql.connect(**self.local_config, cursorclass=DictCursor)
            conn.close()
            print(f"✅ 本地 MySQL 连接成功: {self.local_config['host']}:{self.local_config['port']}")
            return True
        except Exception as e:
            print(f"❌ 本地 MySQL 连接失败: {e}")
            print(f"💡 提示: 请确保本地 MySQL 服务已启动")
            return False
    
    def check_production_mysql(self) -> bool:
        """检查生产 MySQL 连接"""
        try:
            self.prod_conn = pymysql.connect(**self.production_config, cursorclass=DictCursor)
            print(f"✅ 生产 MySQL 连接成功: {self.production_config['host']}:{self.production_config['port']}")
            return True
        except Exception as e:
            print(f"❌ 生产 MySQL 连接失败: {e}")
            return False
    
    def get_table_list(self) -> List[str]:
        """获取本地数据库的表列表"""
        conn = pymysql.connect(**self.local_config, cursorclass=DictCursor)
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                results = cursor.fetchall()
                if results and isinstance(results[0], dict):
                    return [row.get('table_name') or row.get('TABLE_NAME') for row in results]
                else:
                    return [row[0] for row in results]
        finally:
            conn.close()
    
    def export_table_structure(self, tables: Optional[List[str]] = None, output_file: str = None) -> str:
        """
        导出表结构
        
        Args:
            tables: 表列表（None 表示所有表）
            output_file: 输出文件路径（None 表示使用临时文件）
            
        Returns:
            导出的 SQL 文件路径
        """
        if output_file is None:
            fd, output_file = tempfile.mkstemp(suffix='.sql', prefix='table_structure_', text=True)
            os.close(fd)
        
        # 构建 mysqldump 命令
        cmd = [
            'mysqldump',
            f"--host={self.local_config['host']}",
            f"--port={self.local_config['port']}",
            f"--user={self.local_config['user']}",
            f"--password={self.local_config['password']}",
            '--default-character-set=utf8mb4',
            '--no-data',  # 只导出结构
            '--skip-lock-tables',
            '--single-transaction',
            '--routines',
            '--triggers',
            self.local_config['database']
        ]
        
        if tables:
            cmd.extend(tables)
        
        print(f"📤 导出表结构到: {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
            
            # 将 CREATE TABLE 替换为 CREATE TABLE IF NOT EXISTS
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 CREATE TABLE 为 CREATE TABLE IF NOT EXISTS
            content = re.sub(
                r'CREATE TABLE\s+',
                'CREATE TABLE IF NOT EXISTS ',
                content,
                flags=re.IGNORECASE
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 表结构导出成功")
            return output_file
        except subprocess.CalledProcessError as e:
            print(f"❌ 表结构导出失败: {e.stderr}")
            raise
        except Exception as e:
            print(f"❌ 表结构导出异常: {e}")
            raise
    
    def export_table_data(self, tables: Optional[List[str]] = None, output_file: str = None) -> str:
        """
        导出表数据（使用 INSERT IGNORE 模式）
        
        Args:
            tables: 表列表（None 表示所有表）
            output_file: 输出文件路径（None 表示使用临时文件）
            
        Returns:
            导出的 SQL 文件路径
        """
        if output_file is None:
            fd, output_file = tempfile.mkstemp(suffix='.sql', prefix='table_data_', text=True)
            os.close(fd)
        
        # 构建 mysqldump 命令
        cmd = [
            'mysqldump',
            f"--host={self.local_config['host']}",
            f"--port={self.local_config['port']}",
            f"--user={self.local_config['user']}",
            f"--password={self.local_config['password']}",
            '--default-character-set=utf8mb4',
            '--no-create-info',  # 不导出结构
            '--skip-lock-tables',
            '--single-transaction',
            '--skip-extended-insert',  # 不使用扩展 INSERT（逐行插入）
            '--complete-insert',  # 完整 INSERT 语句（包含列名）
            self.local_config['database']
        ]
        
        if tables:
            cmd.extend(tables)
        
        print(f"📤 导出表数据到: {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
            
            # 将 INSERT INTO 替换为 INSERT IGNORE INTO（合并模式）
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 INSERT INTO 为 INSERT IGNORE INTO
            content = re.sub(
                r'INSERT INTO\s+',
                'INSERT IGNORE INTO ',
                content,
                flags=re.IGNORECASE
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ 表数据导出成功（已转换为 INSERT IGNORE 模式）")
            return output_file
        except subprocess.CalledProcessError as e:
            print(f"❌ 表数据导出失败: {e.stderr}")
            raise
        except Exception as e:
            print(f"❌ 表数据导出异常: {e}")
            raise
    
    def import_sql_file(self, sql_file: str, dry_run: bool = False) -> bool:
        """
        导入 SQL 文件到生产数据库
        
        Args:
            sql_file: SQL 文件路径
            dry_run: 是否为预览模式
            
        Returns:
            是否成功
        """
        if dry_run:
            print(f"🔍 [预览模式] 将导入 SQL 文件: {sql_file}")
            # 读取文件并显示前几行
            with open(sql_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   文件总行数: {len(lines)}")
                print(f"   前 20 行预览:")
                for i, line in enumerate(lines[:20], 1):
                    print(f"   {i:4d}: {line.rstrip()}")
                if len(lines) > 20:
                    print(f"   ... (还有 {len(lines) - 20} 行)")
            return True
        
        if not self.prod_conn:
            if not self.check_production_mysql():
                return False
        
        print(f"📥 导入 SQL 文件到生产数据库...")
        
        try:
            # 读取 SQL 文件
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割 SQL 语句
            statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                line_stripped = line.strip()
                # 跳过注释和空行
                if not line_stripped or line_stripped.startswith('--') or line_stripped.startswith('/*'):
                    continue
                
                current_statement += line + '\n'
                
                # 如果行以分号结尾，说明是一个完整的语句
                if line_stripped.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # 执行 SQL 语句
            print(f"   执行 {len(statements)} 条 SQL 语句...")
            cursor = self.prod_conn.cursor()
            
            executed = 0
            failed = 0
            
            for i, statement in enumerate(statements):
                if not statement:
                    continue
                try:
                    cursor.execute(statement)
                    executed += 1
                    if (i + 1) % 100 == 0:
                        print(f"   已执行 {i + 1}/{len(statements)} 条语句...")
                except Exception as e:
                    failed += 1
                    error_msg = str(e)
                    # 忽略一些常见的错误（如表已存在等）
                    if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                        executed += 1  # 表已存在不算失败
                        failed -= 1
                    else:
                        print(f"   ⚠️  语句执行失败（跳过）: {error_msg[:100]}")
            
            self.prod_conn.commit()
            print(f"✅ 导入成功: 执行了 {executed} 条语句, 失败 {failed} 条")
            return True
            
        except Exception as e:
            if self.prod_conn:
                self.prod_conn.rollback()
            print(f"❌ 导入失败: {e}")
            raise
    
    def verify_sync(self, tables: Optional[List[str]] = None) -> Dict:
        """
        验证同步结果
        
        Args:
            tables: 要验证的表列表（None 表示所有表）
            
        Returns:
            验证结果字典
        """
        if not self.prod_conn:
            if not self.check_production_mysql():
                return {}
        
        print(f"\n🔍 验证同步结果...")
        print("=" * 80)
        
        # 获取本地表列表
        local_tables = set(self.get_table_list())
        if tables:
            local_tables = local_tables & set(tables)
        
        # 获取生产表列表
        with self.prod_conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            results = cursor.fetchall()
            if results and isinstance(results[0], dict):
                prod_tables = set([row.get('table_name') or row.get('TABLE_NAME') for row in results])
            else:
                prod_tables = set([row[0] for row in results])
        
        if tables:
            prod_tables = prod_tables & set(tables)
        
        verification_result = {
            'tables': {},
            'summary': {
                'total_tables': len(local_tables),
                'synced_tables': 0,
                'missing_tables': 0
            }
        }
        
        # 连接本地数据库获取记录数
        local_conn = pymysql.connect(**self.local_config, cursorclass=DictCursor)
        try:
            for table_name in sorted(local_tables):
                # 获取本地记录数
                with local_conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                    result = cursor.fetchone()
                    local_count = result.get('count', 0) if isinstance(result, dict) else result[0]
                
                # 获取生产记录数
                if table_name in prod_tables:
                    with self.prod_conn.cursor() as cursor:
                        cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                        result = cursor.fetchone()
                        prod_count = result.get('count', 0) if isinstance(result, dict) else result[0]
                    
                    verification_result['tables'][table_name] = {
                        'status': 'synced',
                        'local_count': local_count,
                        'prod_count': prod_count
                    }
                    verification_result['summary']['synced_tables'] += 1
                    
                    if local_count == prod_count:
                        print(f"✅ {table_name}: 同步成功 (本地: {local_count}, 生产: {prod_count})")
                    else:
                        print(f"⚠️  {table_name}: 记录数不一致 (本地: {local_count}, 生产: {prod_count})")
                else:
                    verification_result['tables'][table_name] = {
                        'status': 'missing',
                        'local_count': local_count,
                        'prod_count': 0
                    }
                    verification_result['summary']['missing_tables'] += 1
                    print(f"❌ {table_name}: 在生产环境不存在 (本地: {local_count})")
        finally:
            local_conn.close()
        
        print("=" * 80)
        print(f"\n📊 验证摘要:")
        print(f"  总表数: {verification_result['summary']['total_tables']}")
        print(f"  同步表数: {verification_result['summary']['synced_tables']}")
        print(f"  缺失表数: {verification_result['summary']['missing_tables']}")
        
        return verification_result
    
    def sync(self, tables: Optional[List[str]] = None, dry_run: bool = False, verify: bool = True) -> bool:
        """
        执行完整同步流程
        
        Args:
            tables: 要同步的表列表（None 表示所有表）
            dry_run: 是否为预览模式
            verify: 是否验证同步结果
            
        Returns:
            是否成功
        """
        print("=" * 80)
        print("从本地 MySQL 同步到生产环境")
        print("=" * 80)
        print(f"本地 MySQL: {self.local_config['host']}:{self.local_config['port']}/{self.local_config['database']}")
        print(f"生产 MySQL: {self.production_config['host']}:{self.production_config['port']}/{self.production_config['database']}")
        if tables:
            print(f"同步表: {', '.join(tables)}")
        else:
            print(f"同步所有表")
        print("=" * 80)
        print()
        
        # 1. 检查本地 MySQL 连接
        if not self.check_local_mysql():
            return False
        
        # 2. 检查生产 MySQL 连接（非预览模式）
        if not dry_run:
            if not self.check_production_mysql():
                return False
        
        # 3. 获取表列表
        if tables is None:
            tables = self.get_table_list()
            print(f"📋 找到 {len(tables)} 个表")
        else:
            print(f"📋 将同步 {len(tables)} 个指定表")
        
        try:
            # 4. 导出表结构
            structure_file = self.export_table_structure(tables)
            
            # 5. 导出表数据
            data_file = self.export_table_data(tables)
            
            # 6. 导入表结构
            print(f"\n📥 导入表结构...")
            self.import_sql_file(structure_file, dry_run=dry_run)
            
            # 7. 导入表数据
            print(f"\n📥 导入表数据...")
            self.import_sql_file(data_file, dry_run=dry_run)
            
            # 8. 验证同步结果
            if verify and not dry_run:
                self.verify_sync(tables)
            
            # 9. 清理临时文件
            if not dry_run:
                try:
                    os.unlink(structure_file)
                    os.unlink(data_file)
                except Exception:
                    pass
            
            print(f"\n✅ 同步完成！")
            return True
            
        except Exception as e:
            print(f"\n❌ 同步失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.prod_conn:
                self.prod_conn.close()


def get_local_config(args) -> Dict:
    """获取本地 MySQL 配置"""
    return {
        'host': args.local_host or os.getenv('LOCAL_MYSQL_HOST', '127.0.0.1'),
        'port': args.local_port or int(os.getenv('LOCAL_MYSQL_PORT', '3306')),
        'user': args.local_user or os.getenv('LOCAL_MYSQL_USER', 'root'),
        'password': args.local_password or os.getenv('LOCAL_MYSQL_PASSWORD', '123456'),
        'database': args.local_database or os.getenv('LOCAL_MYSQL_DATABASE', 'hifate_bazi'),
        'charset': 'utf8mb4'
    }


def get_production_config(args) -> Dict:
    """获取生产 MySQL 配置"""
    return {
        'host': args.prod_host or os.getenv('PROD_MYSQL_HOST', '8.210.52.217'),
        'port': args.prod_port or int(os.getenv('PROD_MYSQL_PORT', '3306')),
        'user': args.prod_user or os.getenv('PROD_MYSQL_USER', 'root'),
        'password': args.prod_password or os.getenv('PROD_MYSQL_PASSWORD', 'Yuanqizhan@163'),
        'database': args.prod_database or os.getenv('PROD_MYSQL_DATABASE', 'hifate_bazi'),
        'charset': 'utf8mb4'
    }


def main():
    parser = argparse.ArgumentParser(
        description='从本地 MySQL 同步表和数据到生产环境',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 同步所有表（使用环境变量）
  export LOCAL_MYSQL_PASSWORD="your_password"
  python3 scripts/db/sync_local_to_production.py

  # 预览模式（不实际导入）
  python3 scripts/db/sync_local_to_production.py --dry-run

  # 同步指定表
  python3 scripts/db/sync_local_to_production.py --tables "rizhu_liujiazi,config_elements"

  # 使用命令行参数指定配置
  python3 scripts/db/sync_local_to_production.py \\
      --local-password "your_password" \\
      --prod-host "8.210.52.217" \\
      --prod-password "Yuanqizhan@163"
        """
    )
    
    # 本地 MySQL 配置参数
    parser.add_argument('--local-host', help='本地 MySQL 主机（默认: 127.0.0.1）')
    parser.add_argument('--local-port', type=int, help='本地 MySQL 端口（默认: 3306）')
    parser.add_argument('--local-user', help='本地 MySQL 用户（默认: root）')
    parser.add_argument('--local-password', help='本地 MySQL 密码（默认: 从环境变量读取）')
    parser.add_argument('--local-database', help='本地 MySQL 数据库（默认: hifate_bazi）')
    
    # 生产 MySQL 配置参数
    parser.add_argument('--prod-host', help='生产 MySQL 主机（默认: 8.210.52.217）')
    parser.add_argument('--prod-port', type=int, help='生产 MySQL 端口（默认: 3306）')
    parser.add_argument('--prod-user', help='生产 MySQL 用户（默认: root）')
    parser.add_argument('--prod-password', help='生产 MySQL 密码（默认: Yuanqizhan@163）')
    parser.add_argument('--prod-database', help='生产 MySQL 数据库（默认: hifate_bazi）')
    
    # 其他参数
    parser.add_argument('--tables', help='要同步的表列表（逗号分隔），默认同步所有表')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际导入')
    parser.add_argument('--no-verify', action='store_true', help='不验证同步结果')
    
    args = parser.parse_args()
    
    # 解析表列表
    tables = None
    if args.tables:
        tables = [t.strip() for t in args.tables.split(',') if t.strip()]
    
    # 获取配置
    local_config = get_local_config(args)
    production_config = get_production_config(args)
    
    # 创建同步器并执行同步
    syncer = LocalToProductionSyncer(local_config, production_config)
    success = syncer.sync(
        tables=tables,
        dry_run=args.dry_run,
        verify=not args.no_verify
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

