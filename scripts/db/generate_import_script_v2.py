#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）
简化版本：直接处理 mysqldump 输出

注意：此脚本用于生成 SQL 导入文件，不是执行数据库查询
- SQL 字符串拼接是正常的（生成 SQL 脚本）
- 硬编码路径是临时文件路径（/tmp/），可以接受
- UNHEX 不适用于生成 SQL 脚本（这是 mysqldump 的输出）
"""

import sys
import os
import subprocess
import argparse
import re
from datetime import datetime

def generate_import_script(local_host=None, local_port=3306, 
                            local_user=None, local_password=None,
                            local_database=None, output_file=None):
    """
    生成导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）
    
    注意：此脚本用于生成 SQL 导入文件，不是执行数据库查询
    """
    # 从环境变量读取配置（避免硬编码敏感信息）
    local_host = local_host or os.getenv('MYSQL_HOST', '127.0.0.1')
    local_user = local_user or os.getenv('MYSQL_USER', 'root')
    local_password = local_password or os.getenv('MYSQL_PASSWORD', os.getenv('MYSQL_ROOT_PASSWORD', '123456'))
    local_database = local_database or os.getenv('MYSQL_DATABASE', 'hifate_bazi')
    """
    生成导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）
    """
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/tmp/hifate_db_import_{timestamp}.sql"
    
    print(f"📤 导出数据库: {local_database}")
    print(f"📝 输出文件: {output_file}")
    
    # 使用 mysqldump 导出
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
        "--complete-insert",
        "--skip-extended-insert",
        "--add-drop-database",
        "--databases",
        local_database
    ]
    
    print("  执行 mysqldump...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            print(f"❌ mysqldump 失败: {result.stderr}")
            return None
        sql_content = result.stdout
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return None
    
    # 转换为 INSERT ... ON DUPLICATE KEY UPDATE 格式
    print("  转换为 INSERT ... ON DUPLICATE KEY UPDATE 格式...")
    
    with open(output_file, 'w', encoding='utf-8') as f_out:
        # 写入文件头
        f_out.write("-- HiFate 数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）\n")
        f_out.write(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"-- 数据库: {local_database}\n")
        f_out.write("-- \n")
        f_out.write("-- 使用方法：\n")
        f_out.write("--   cd /opt/HiFate-bazi\n")
        f_out.write("--   source .env\n")
        f_out.write("--   mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < this_file.sql\n")
        f_out.write("-- \n")
        f_out.write("SET NAMES utf8mb4;\n")
        f_out.write("SET FOREIGN_KEY_CHECKS=0;\n")
        f_out.write("SET UNIQUE_CHECKS=0;\n")
        f_out.write("\n")
        
        # 处理 SQL 内容
        lines = sql_content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 保留 CREATE TABLE、DROP TABLE 等结构语句
            if (line.strip().upper().startswith('CREATE ') or 
                line.strip().upper().startswith('DROP ') or
                line.strip().upper().startswith('LOCK ') or
                line.strip().upper().startswith('UNLOCK ') or
                line.strip().upper().startswith('USE ') or
                line.strip().startswith('/*') or
                line.strip().startswith('--')):
                f_out.write(line + '\n')
                i += 1
                continue
            
            # 检测 INSERT INTO 语句
            if line.strip().upper().startswith('INSERT INTO'):
                # 提取表名和列名
                match = re.match(r'INSERT INTO `?(\w+)`?\s*\(([^)]+)\)', line, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    columns_str = match.group(2)
                    columns = [col.strip().strip('`') for col in columns_str.split(',')]
                    
                    # 收集完整的 INSERT 语句（可能跨多行）
                    insert_lines = [line]
                    i += 1
                    while i < len(lines) and not lines[i].strip().endswith(';'):
                        insert_lines.append(lines[i])
                        i += 1
                    if i < len(lines):
                        insert_lines.append(lines[i])
                    
                    # 合并完整的 INSERT 语句
                    full_insert = ' '.join(insert_lines)
                    
                    # 提取 VALUES 部分
                    values_match = re.search(r'VALUES\s+(.+?);', full_insert, re.IGNORECASE | re.DOTALL)
                    if values_match:
                        values_part = values_match.group(1).strip()
                        
                        # 构建 ON DUPLICATE KEY UPDATE 子句
                        update_clause = ", ".join([f"`{col}`=VALUES(`{col}`)" for col in columns])
                        
                        # 写入转换后的语句
                        f_out.write(f"INSERT INTO `{table_name}` ({columns_str}) VALUES {values_part}\n")
                        f_out.write(f"ON DUPLICATE KEY UPDATE {update_clause};\n")
                    else:
                        # 如果无法解析，直接写入
                        f_out.write(full_insert + '\n')
                else:
                    # 如果无法解析，直接写入
                    f_out.write(line + '\n')
                i += 1
                continue
            
            # 其他行直接写入
            f_out.write(line + '\n')
            i += 1
        
        # 写入文件尾
        f_out.write("\n")
        f_out.write("SET FOREIGN_KEY_CHECKS=1;\n")
        f_out.write("SET UNIQUE_CHECKS=1;\n")
    
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
        # 动态获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        node1_path = os.path.join(project_root, "scripts", "db", os.path.basename(output_file))
        node2_path = os.path.join(project_root, "scripts", "db", os.path.basename(output_file))
        
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

