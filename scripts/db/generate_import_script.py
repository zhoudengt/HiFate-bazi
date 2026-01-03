#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）
将本地数据库导出为可导入的 SQL 脚本
"""

import sys
import os
import subprocess
import argparse
import re
from datetime import datetime

def generate_import_script(local_host="127.0.0.1", local_port=3306, 
                            local_user="root", local_password="123456",
                            local_database="hifate_bazi", output_file=None):
    """
    生成导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）
    
    Args:
        local_host: 本地 MySQL 主机
        local_port: 本地 MySQL 端口
        local_user: 本地 MySQL 用户
        local_password: 本地 MySQL 密码
        local_database: 本地数据库名
        output_file: 输出文件路径
    """
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/tmp/hifate_db_import_{timestamp}.sql"
    
    print(f"📤 导出数据库: {local_database}")
    print(f"📝 输出文件: {output_file}")
    
    # 使用 mysqldump 导出（包含表结构和数据）
    temp_file = f"{output_file}.tmp"
    cmd = [
        "mysqldump",
        f"-h{local_host}",
        f"-P{local_port}",
        f"-u{local_user}",
        f"-p{local_password}",
        "--default-character-set=utf8mb4",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--complete-insert",  # 完整的 INSERT 语句（包含列名）
        "--skip-extended-insert",  # 每行一个 INSERT（便于转换）
        "--add-drop-database",
        "--databases",
        local_database
    ]
    
    print("  执行 mysqldump...")
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"❌ mysqldump 失败: {result.stderr}")
                return None
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return None
    
    # 转换为 INSERT ... ON DUPLICATE KEY UPDATE 格式
    print("  转换为 INSERT ... ON DUPLICATE KEY UPDATE 格式...")
    
    with open(temp_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        # 写入文件头
        f_out.write("-- HiFate 数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）\n")
        f_out.write(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"-- 数据库: {local_database}\n")
        f_out.write("-- \n")
        f_out.write("-- 使用方法：\n")
        f_out.write("--   mysql -h<host> -P<port> -u<user> -p<password> <database> < this_file.sql\n")
        f_out.write("-- \n")
        f_out.write("SET NAMES utf8mb4;\n")
        f_out.write("SET FOREIGN_KEY_CHECKS=0;\n")
        f_out.write("SET UNIQUE_CHECKS=0;\n")
        f_out.write("\n")
        
        current_table = None
        table_columns = {}
        in_insert = False
        insert_buffer = []
        
        for line in f_in:
            original_line = line
            line = line.rstrip()
            
            # 保留 CREATE TABLE 等结构语句
            if line.upper().startswith('CREATE ') or \
               line.upper().startswith('DROP ') or \
               line.upper().startswith('LOCK ') or \
               line.upper().startswith('UNLOCK ') or \
               line.upper().startswith('USE ') or \
               line.startswith('/*') or \
               (line.startswith('--') and not in_insert):
                f_out.write(original_line)
                continue
            
            # 检测 INSERT INTO 语句
            if line.upper().startswith('INSERT INTO'):
                in_insert = True
                insert_buffer = [line]
                
                # 提取表名和列名
                # 格式：INSERT INTO `table_name` (`col1`, `col2`, ...) VALUES
                match = re.match(r"INSERT INTO `?(\w+)`?\s*\(([^)]+)\)", line, re.IGNORECASE)
                if match:
                    current_table = match.group(1)
                    columns_str = match.group(2)
                    columns = [col.strip().strip('`') for col in columns_str.split(',')]
                    table_columns[current_table] = columns
                continue
            
            # 如果是 INSERT 语句的一部分
            if in_insert:
                insert_buffer.append(line)
                
                # 检测 INSERT 语句结束（以分号结尾，且不在字符串中）
                if line.endswith(';'):
                    # 合并所有 INSERT 行
                    full_insert = ' '.join(insert_buffer)
                    
                    # 提取 VALUES 部分
                    values_match = re.search(r'VALUES\s+(.+)', full_insert, re.IGNORECASE | re.DOTALL)
                    if values_match and current_table and current_table in table_columns:
                        values_part = values_match.group(1).rstrip(';').strip()
                        columns = table_columns[current_table]
                        
                        # 构建 ON DUPLICATE KEY UPDATE 子句
                        update_clause = ", ".join([f"`{col}`=VALUES(`{col}`)" for col in columns])
                        
                        # 写入转换后的语句
                        insert_match = re.match(r"(INSERT INTO `?\w+`?\s*\([^)]+\))", full_insert, re.IGNORECASE)
                        if insert_match:
                            insert_part = insert_match.group(1)
                            f_out.write(f"{insert_part} VALUES {values_part}\n")
                            f_out.write(f"ON DUPLICATE KEY UPDATE {update_clause};\n")
                    else:
                        # 如果无法解析，直接写入（可能是格式问题）
                        f_out.write(original_line)
                    
                    in_insert = False
                    insert_buffer = []
                    current_table = None
                continue
            
            # 其他行直接写入
            f_out.write(original_line)
        
        # 写入文件尾
        f_out.write("\n")
        f_out.write("SET FOREIGN_KEY_CHECKS=1;\n")
        f_out.write("SET UNIQUE_CHECKS=1;\n")
    
    # 删除临时文件
    os.remove(temp_file)
    
    file_size = os.path.getsize(output_file)
    file_size_mb = file_size / (1024 * 1024)
    
    print(f"✅ 生成成功")
    print(f"  文件: {output_file}")
    print(f"  大小: {file_size_mb:.2f} MB")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description='生成数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）')
    parser.add_argument('--host', default='127.0.0.1', help='本地 MySQL 主机')
    parser.add_argument('--port', type=int, default=3306, help='本地 MySQL 端口')
    parser.add_argument('--user', default='root', help='本地 MySQL 用户')
    parser.add_argument('--password', default='123456', help='本地 MySQL 密码')
    parser.add_argument('--database', default='hifate_bazi', help='本地数据库名')
    parser.add_argument('--output', help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    # 从环境变量读取配置（如果未指定）
    host = os.getenv('MYSQL_HOST', args.host)
    port = int(os.getenv('MYSQL_PORT', args.port))
    user = os.getenv('MYSQL_USER', args.user)
    password = os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', args.password))
    database = os.getenv('MYSQL_DATABASE', args.database)
    
    output_file = generate_import_script(
        local_host=host,
        local_port=port,
        local_user=user,
        local_password=password,
        local_database=database,
        output_file=args.output
    )
    
    if output_file:
        print(f"\n✅ 导入脚本已生成: {output_file}")
        print(f"\n💡 使用方法：")
        print(f"  1. 上传到生产环境：")
        print(f"     scp {output_file} root@8.210.52.217:/opt/HiFate-bazi/scripts/db/")
        print(f"     scp {output_file} root@47.243.160.43:/opt/HiFate-bazi/scripts/db/")
        print(f"  2. 在生产环境执行（Node1 和 Node2）：")
        print(f"     cd /opt/HiFate-bazi")
        print(f"     source .env")
        print(f"     mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < scripts/db/{os.path.basename(output_file)}")
    else:
        print("❌ 生成失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
