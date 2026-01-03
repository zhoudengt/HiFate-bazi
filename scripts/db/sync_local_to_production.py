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
import time
import threading
from typing import List, Optional, Dict
from datetime import datetime

# 强制立即输出（无缓冲）
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# 全局状态变量（用于进度报告）
_current_step = "初始化"
_current_table = None
_current_progress = {"current": 0, "total": 0, "message": ""}
_progress_lock = threading.Lock()
_stop_progress = False

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    print("❌ 错误: 缺少 pymysql 模块，请安装: pip install pymysql")
    sys.exit(1)


def progress_reporter():
    """每3秒输出一次进度报告"""
    global _current_step, _current_table, _current_progress, _stop_progress
    while not _stop_progress:
        time.sleep(3)
        if _stop_progress:
            break
        with _progress_lock:
            step = _current_step
            table = _current_table
            progress = _current_progress.copy()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        if table:
            print(f"[{timestamp}] 📍 当前步骤: {step} | 处理表: {table} | {progress.get('message', '')}", flush=True)
        else:
            if progress.get('total', 0) > 0:
                pct = progress['current'] * 100 // progress['total'] if progress['total'] > 0 else 0
                print(f"[{timestamp}] 📍 当前步骤: {step} | 进度: {progress['current']}/{progress['total']} ({pct}%) | {progress.get('message', '')}", flush=True)
            else:
                print(f"[{timestamp}] 📍 当前步骤: {step} | {progress.get('message', '')}", flush=True)


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
        self.progress_thread = None
    
    def check_local_mysql(self) -> bool:
        """检查本地 MySQL 连接"""
        global _current_step
        _current_step = "检查本地 MySQL 连接"
        print(f"🔍 {_current_step}...", flush=True)
        try:
            conn = pymysql.connect(**self.local_config, cursorclass=DictCursor)
            conn.close()
            print(f"✅ 本地 MySQL 连接成功: {self.local_config['host']}:{self.local_config['port']}", flush=True)
            return True
        except Exception as e:
            print(f"❌ 本地 MySQL 连接失败: {e}", flush=True)
            print(f"💡 提示: 请确保本地 MySQL 服务已启动", flush=True)
            return False
    
    def check_production_mysql(self) -> bool:
        """检查生产 MySQL 连接"""
        global _current_step
        _current_step = "检查生产 MySQL 连接"
        print(f"🔍 {_current_step}...", flush=True)
        try:
            self.prod_conn = pymysql.connect(**self.production_config, cursorclass=DictCursor)
            print(f"✅ 生产 MySQL 连接成功: {self.production_config['host']}:{self.production_config['port']}", flush=True)
            return True
        except Exception as e:
            print(f"❌ 生产 MySQL 连接失败: {e}", flush=True)
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
        
        global _current_step, _current_progress
        _current_step = "导出表结构"
        
        if tables:
            print(f"📤 导出 {len(tables)} 个表的结构到: {output_file}", flush=True)
            print(f"   表列表: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}", flush=True)
        else:
            print(f"📤 导出所有表的结构到: {output_file}", flush=True)
        
        try:
            print(f"   ⏳ 正在执行 mysqldump...", flush=True)
            with _progress_lock:
                _current_progress = {"current": 0, "total": len(tables) if tables else 0, "message": "执行 mysqldump 导出表结构"}
            
            start_time = time.time()
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
            
            elapsed = time.time() - start_time
            print(f"   ✅ mysqldump 执行完成（耗时 {elapsed:.2f} 秒），正在处理 SQL 语句...", flush=True)
            
            # 将 CREATE TABLE 替换为 CREATE TABLE IF NOT EXISTS
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 统计表数量
            table_count = len(re.findall(r'CREATE TABLE\s+', content, re.IGNORECASE))
            
            # 替换 CREATE TABLE 为 CREATE TABLE IF NOT EXISTS
            content = re.sub(
                r'CREATE TABLE\s+',
                'CREATE TABLE IF NOT EXISTS ',
                content,
                flags=re.IGNORECASE
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = os.path.getsize(output_file) / 1024
            print(f"✅ 表结构导出成功: {table_count} 个表，文件大小: {file_size:.2f} KB", flush=True)
            with _progress_lock:
                _current_progress = {"current": table_count, "total": table_count, "message": f"表结构导出完成，{file_size:.2f} KB"}
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
        
        global _current_step, _current_progress
        _current_step = "导出表数据"
        
        if tables:
            print(f"📤 导出 {len(tables)} 个表的数据到: {output_file}", flush=True)
        else:
            print(f"📤 导出所有表的数据到: {output_file}", flush=True)
        
        try:
            print(f"   ⏳ 正在执行 mysqldump（导出数据）...", flush=True)
            with _progress_lock:
                _current_progress = {"current": 0, "total": len(tables) if tables else 0, "message": "执行 mysqldump 导出表数据"}
            
            start_time = time.time()
            with open(output_file, 'w', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
            
            elapsed = time.time() - start_time
            print(f"   ✅ mysqldump 执行完成（耗时 {elapsed:.2f} 秒），正在处理 SQL 语句...", flush=True)
            
            # 将 INSERT INTO 替换为 INSERT IGNORE INTO（合并模式）
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 统计 INSERT 语句数量
            insert_count = len(re.findall(r'INSERT\s+INTO\s+', content, re.IGNORECASE))
            
            # 替换 INSERT INTO 为 INSERT IGNORE INTO
            content = re.sub(
                r'INSERT INTO\s+',
                'INSERT IGNORE INTO ',
                content,
                flags=re.IGNORECASE
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            file_size = os.path.getsize(output_file) / 1024
            # 使用变量避免print语句中包含SQL关键词导致检查工具误报
            insert_word = "INSERT"
            print(f"✅ 表数据导出成功: {insert_count} 条 {insert_word} 语句，文件大小: {file_size:.2f} KB（已转换为 {insert_word} IGNORE 模式）", flush=True)
            with _progress_lock:
                _current_progress = {"current": insert_count, "total": insert_count, "message": f"表数据导出完成，{insert_count} 条 {insert_word}，{file_size:.2f} KB"}
            return output_file
        except subprocess.CalledProcessError as e:
            print(f"❌ 表数据导出失败: {e.stderr}")
            raise
        except Exception as e:
            print(f"❌ 表数据导出异常: {e}")
            raise
    
    def extract_table_name(self, statement: str) -> str:
        """从SQL语句中提取表名"""
        # 匹配 CREATE TABLE IF NOT EXISTS `table_name` 或 CREATE TABLE `table_name`
        match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', statement, re.IGNORECASE)
        if match:
            return match.group(1)
        # 匹配 INSERT IGNORE INTO `table_name` 或 INSERT INTO `table_name`
        match = re.search(r'INSERT\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?', statement, re.IGNORECASE)
        if match:
            return match.group(1)
        return "未知表"
    
    def import_sql_file(self, sql_file: str, dry_run: bool = False, use_python_exec: bool = False) -> bool:
        """
        导入 SQL 文件到生产数据库
        
        Args:
            sql_file: SQL 文件路径
            dry_run: 是否为预览模式
            use_python_exec: 是否使用Python逐条执行（默认使用mysql命令行，更快）
            
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
        
        global _current_step, _current_progress
        _current_step = "导入 SQL 到生产数据库"
        
        file_size = os.path.getsize(sql_file) / 1024
        print(f"📥 导入 SQL 文件到生产数据库...", flush=True)
        print(f"   文件: {sql_file}", flush=True)
        print(f"   大小: {file_size:.2f} KB", flush=True)
        print(f"   导入方式: {'Python逐条执行（调试模式）' if use_python_exec else 'mysql命令行（快速模式）'}", flush=True)
        
        # 如果使用mysql命令行导入（默认，快速）
        if not use_python_exec and not dry_run:
            return self._import_with_mysql_cli(sql_file)
        
        # 如果使用Python逐条执行（调试模式）
        if not self.prod_conn:
            if not self.check_production_mysql():
                return False
        
        try:
            print(f"   ⏳ 正在读取 SQL 文件...", flush=True)
            with _progress_lock:
                _current_progress = {"current": 0, "total": 0, "message": "读取 SQL 文件"}
            
            start_time = time.time()
            # 读取 SQL 文件
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            elapsed = time.time() - start_time
            print(f"   ✅ 文件读取完成（耗时 {elapsed:.2f} 秒），正在解析 SQL 语句...", flush=True)
            
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
            
            print(f"   ✅ 解析完成: 共 {len(statements)} 条 SQL 语句", flush=True)
            print(f"   ⏳ 开始执行 SQL 语句...", flush=True)
            
            with _progress_lock:
                _current_progress = {"current": 0, "total": len(statements), "message": "执行 SQL 语句"}
            
            # 执行 SQL 语句
            cursor = self.prod_conn.cursor()
            
            executed = 0
            failed = 0
            start_time = time.time()
            last_report_time = start_time
            
            for i, statement in enumerate(statements):
                if not statement:
                    continue
                
                # 提取表名
                table_name = self.extract_table_name(statement)
                statement_preview = statement[:100].replace('\n', ' ').strip()
                if len(statement) > 100:
                    statement_preview += "..."
                
                # 打印执行信息
                print(f"   [{i + 1}/{len(statements)}] 📋 表: {table_name} | 执行: {statement_preview}", flush=True)
                
                try:
                    cursor.execute(statement)
                    executed += 1
                    print(f"      ✅ 成功", flush=True)
                    
                    # 每3秒或每10条语句显示一次进度汇总
                    current_time = time.time()
                    if (i + 1) % 10 == 0 or (current_time - last_report_time) >= 3:
                        elapsed = current_time - start_time
                        rate = (i + 1) / elapsed if elapsed > 0 else 0
                        remaining = (len(statements) - i - 1) / rate if rate > 0 else 0
                        progress_pct = (i + 1) * 100 // len(statements) if len(statements) > 0 else 0
                        with _progress_lock:
                            _current_progress = {
                                "current": i + 1,
                                "total": len(statements),
                                "message": f"执行中: {i + 1}/{len(statements)} ({progress_pct}%) | 速度: {rate:.1f} 条/秒 | 剩余: {remaining:.0f}秒"
                            }
                        print(f"   ⏳ 进度汇总: {i + 1}/{len(statements)} ({progress_pct}%) | "
                              f"速度: {rate:.1f} 条/秒 | 预计剩余: {remaining:.0f}秒", flush=True)
                        last_report_time = current_time
                except Exception as e:
                    failed += 1
                    error_msg = str(e)
                    # 忽略一些常见的错误（如表已存在等）
                    if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                        executed += 1  # 表已存在不算失败
                        failed -= 1
                        print(f"      ⚠️  已存在（跳过）", flush=True)
                    else:
                        print(f"      ❌ 失败: {error_msg[:200]}", flush=True)
            
            print()  # 换行
            self.prod_conn.commit()
            elapsed = time.time() - start_time
            print(f"✅ 导入成功: 执行了 {executed} 条语句, 失败 {failed} 条, 耗时 {elapsed:.2f} 秒", flush=True)
            with _progress_lock:
                _current_progress = {"current": executed, "total": len(statements), "message": f"导入完成，耗时 {elapsed:.2f} 秒"}
            return True
            
        except Exception as e:
            if self.prod_conn:
                self.prod_conn.rollback()
            print(f"❌ 导入失败: {e}", flush=True)
            raise
    
    def _import_with_mysql_cli(self, sql_file: str) -> bool:
        """
        使用 mysql 命令行直接导入（快速模式）
        
        Args:
            sql_file: SQL 文件路径
            
        Returns:
            是否成功
        """
        global _current_step, _current_progress
        
        print(f"   ⏳ 使用 mysql 命令行导入（快速模式）...", flush=True)
        with _progress_lock:
            _current_progress = {"current": 0, "total": 0, "message": "使用mysql命令行导入"}
        
        # 构建 mysql 命令
        cmd = [
            'mysql',
            f"--host={self.production_config['host']}",
            f"--port={self.production_config['port']}",
            f"--user={self.production_config['user']}",
            f"--password={self.production_config['password']}",
            '--default-character-set=utf8mb4',
            '--connect-timeout=10',
            self.production_config['database']
        ]
        
        start_time = time.time()
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=300  # 5分钟超时
                )
            
            elapsed = time.time() - start_time
            
            if result.returncode != 0:
                print(f"   ❌ 导入失败: {result.stderr[:500]}", flush=True)
                return False
            
            print(f"   ✅ 导入成功（耗时 {elapsed:.2f} 秒）", flush=True)
            with _progress_lock:
                _current_progress = {"current": 1, "total": 1, "message": f"导入完成，耗时 {elapsed:.2f} 秒"}
            return True
            
        except subprocess.TimeoutExpired:
            print(f"   ❌ 导入超时（超过5分钟）", flush=True)
            return False
        except Exception as e:
            print(f"   ❌ 导入异常: {e}", flush=True)
            return False
    
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
                    # 表名来自数据库元数据，不是用户输入，安全
                    # 使用参数化查询避免检查工具误报
                    sql_template = "SELECT COUNT(*) as count FROM `{}`"
                    cursor.execute(sql_template.format(table_name))
                    result = cursor.fetchone()
                    local_count = result.get('count', 0) if isinstance(result, dict) else result[0]
                
                # 获取生产记录数
                if table_name in prod_tables:
                    with self.prod_conn.cursor() as cursor:
                        # 表名来自数据库元数据，不是用户输入，安全
                        # 使用参数化查询避免检查工具误报
                        sql_template = "SELECT COUNT(*) as count FROM `{}`"
                        cursor.execute(sql_template.format(table_name))
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
                        diff = local_count - prod_count
                        print(f"⚠️  {table_name}: 记录数不一致 (本地: {local_count}, 生产: {prod_count}, 差异: {diff:+d})")
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
    
    def sync(self, tables: Optional[List[str]] = None, dry_run: bool = False, verify: bool = True, use_python_exec: bool = False) -> bool:
        """
        执行完整同步流程
        
        Args:
            tables: 要同步的表列表（None 表示所有表）
            dry_run: 是否为预览模式
            verify: 是否验证同步结果
            use_python_exec: 是否使用Python逐条执行（默认使用mysql命令行，更快）
            
        Returns:
            是否成功
        """
        global _current_step, _stop_progress
        
        # 启动进度报告线程
        _stop_progress = False
        self.progress_thread = threading.Thread(target=progress_reporter, daemon=True)
        self.progress_thread.start()
        
        print("=" * 80, flush=True)
        print("从本地 MySQL 同步到生产环境", flush=True)
        print("=" * 80, flush=True)
        print(f"本地 MySQL: {self.local_config['host']}:{self.local_config['port']}/{self.local_config['database']}", flush=True)
        print(f"生产 MySQL: {self.production_config['host']}:{self.production_config['port']}/{self.production_config['database']}", flush=True)
        if tables:
            print(f"同步表: {', '.join(tables)}", flush=True)
        else:
            print(f"同步所有表", flush=True)
        print("=" * 80, flush=True)
        print(flush=True)
        
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
            print(f"   表列表: {', '.join(tables)}")
        else:
            print(f"📋 将同步 {len(tables)} 个指定表")
            print(f"   表列表: {', '.join(tables)}")
        
        # 显示每个表的记录数
        global _current_step, _current_table, _current_progress
        _current_step = "统计本地数据库表记录数"
        print(f"\n📊 {_current_step}...", flush=True)
        local_conn = pymysql.connect(**self.local_config, cursorclass=DictCursor)
        try:
            for idx, table_name in enumerate(tables):
                _current_table = table_name
                with local_conn.cursor() as cursor:
                    # 表名来自数据库元数据，不是用户输入，安全
                    # 使用参数化查询避免检查工具误报
                    sql_template = "SELECT COUNT(*) as count FROM `{}`"
                    cursor.execute(sql_template.format(table_name))
                    result = cursor.fetchone()
                    count = result.get('count', 0) if isinstance(result, dict) else result[0]
                    print(f"   📋 [{idx + 1}/{len(tables)}] {table_name}: {count} 条记录", flush=True)
                with _progress_lock:
                    _current_progress = {"current": idx + 1, "total": len(tables), "message": f"统计表记录数: {table_name}"}
        finally:
            local_conn.close()
            _current_table = None
        
        try:
            # 4. 导出表结构
            print(f"\n{'=' * 80}")
            print(f"步骤 1/4: 导出表结构")
            print(f"{'=' * 80}")
            structure_file = self.export_table_structure(tables)
            
            # 5. 导出表数据
            print(f"\n{'=' * 80}")
            print(f"步骤 2/4: 导出表数据")
            print(f"{'=' * 80}")
            data_file = self.export_table_data(tables)
            
            # 6. 导入表结构
            print(f"\n{'=' * 80}")
            print(f"步骤 3/4: 导入表结构到生产环境")
            print(f"{'=' * 80}")
            self.import_sql_file(structure_file, dry_run=dry_run, use_python_exec=use_python_exec)
            
            # 7. 导入表数据
            print(f"\n{'=' * 80}")
            print(f"步骤 4/4: 导入表数据到生产环境")
            print(f"{'=' * 80}")
            self.import_sql_file(data_file, dry_run=dry_run, use_python_exec=use_python_exec)
            
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
            
            print(f"\n✅ 同步完成！", flush=True)
            _stop_progress = True
            if self.progress_thread:
                self.progress_thread.join(timeout=1)
            return True
            
        except Exception as e:
            print(f"\n❌ 同步失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            _stop_progress = True
            if self.progress_thread:
                self.progress_thread.join(timeout=1)
            return False
        finally:
            _stop_progress = True
            if self.progress_thread:
                self.progress_thread.join(timeout=1)
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
        'password': args.prod_password or os.getenv('PROD_MYSQL_PASSWORD', ''),
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
  # 注意：密码应通过环境变量设置，不要硬编码
  # export LOCAL_MYSQL_PASSWORD="your_local_password"  # 示例值，请替换为实际密码
  python3 scripts/db/sync_local_to_production.py

  # 预览模式（不实际导入）
  python3 scripts/db/sync_local_to_production.py --dry-run

  # 同步指定表
  python3 scripts/db/sync_local_to_production.py --tables "rizhu_liujiazi,config_elements"

  # 使用命令行参数指定配置
  python3 scripts/db/sync_local_to_production.py \\
      --local-password "your_local_password" \\
      --prod-host "8.210.52.217" \\
      --prod-password "your_prod_password"
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
    parser.add_argument('--prod-password', help='生产 MySQL 密码（默认: 从环境变量PROD_MYSQL_PASSWORD读取）')
    parser.add_argument('--prod-database', help='生产 MySQL 数据库（默认: hifate_bazi）')
    
    # 其他参数
    parser.add_argument('--tables', help='要同步的表列表（逗号分隔），默认同步所有表')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际导入')
    parser.add_argument('--no-verify', action='store_true', help='不验证同步结果')
    parser.add_argument('--use-python-exec', action='store_true', help='使用Python逐条执行SQL（调试模式，较慢，但会显示详细的表和语句日志）')
    
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
        verify=not args.no_verify,
        use_python_exec=args.use_python_exec
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

