#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在服务器上执行SQL文件，显示详细日志
"""
import sys
import subprocess
import re
import tempfile
import os
from datetime import datetime

if len(sys.argv) < 4:
    print("用法: python3 execute_sql_with_logs.py <mysql_container> <mysql_user> <mysql_password> <mysql_database> <sql_file>")
    sys.exit(1)

mysql_container = sys.argv[1]
mysql_user = sys.argv[2]
mysql_password = sys.argv[3]
mysql_database = sys.argv[4]
sql_file = sys.argv[5]

# 读取SQL文件
print("📖 读取SQL文件: " + sql_file, flush=True)
with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

# 解析SQL语句
statements = []
current_statement = ""
for line in sql_content.split('\n'):
    line_stripped = line.strip()
    if not line_stripped or line_stripped.startswith('--') or line_stripped.startswith('/*'):
        continue
    current_statement += line + '\n'
    if line_stripped.endswith(';'):
        statements.append(current_statement.strip())
        current_statement = ""

print("✅ 解析完成: 共 " + str(len(statements)) + " 条SQL语句", flush=True)

# 执行前清理阻塞的进程
print("🔧 检查并清理阻塞的MySQL进程...", flush=True)
try:
    # 检查长时间运行的查询和等待表锁的进程
    check_cmd = 'docker exec -i ' + mysql_container + ' mysql -u' + mysql_user + ' -p' + mysql_password + ' -e "SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO FROM information_schema.PROCESSLIST WHERE (STATE LIKE \\'%lock%\\' OR (COMMAND=\\'Query\\' AND TIME > 60) OR (COMMAND=\\'Sleep\\' AND TIME > 300)) AND ID != CONNECTION_ID();"'
    check_result = subprocess.run(check_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
    
    if check_result.returncode == 0 and check_result.stdout:
        lines = check_result.stdout.strip().split('\n')
        if len(lines) > 1:  # 有表头，所以>1表示有数据
            print("   ⚠️  发现阻塞进程，正在清理...", flush=True)
            # 提取进程ID并杀掉
            killed_count = 0
            for line in lines[1:]:  # 跳过表头
                parts = line.split('\t')
                if len(parts) > 0:
                    try:
                        process_id = int(parts[0])
                        if process_id > 0:
                            kill_cmd = 'docker exec -i ' + mysql_container + ' mysql -u' + mysql_user + ' -p' + mysql_password + ' -e "KILL ' + str(process_id) + ';"'
                            kill_result = subprocess.run(kill_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
                            if kill_result.returncode == 0:
                                killed_count += 1
                    except:
                        pass
            if killed_count > 0:
                print("   ✅ 已清理 " + str(killed_count) + " 个阻塞进程", flush=True)
                import time
                time.sleep(1)  # 等待1秒让锁释放
            else:
                print("   ✅ 无需清理", flush=True)
        else:
            print("   ✅ 无阻塞进程", flush=True)
    else:
        print("   ✅ 检查完成", flush=True)
except Exception as e:
    print("   ⚠️  清理检查失败（继续执行）: " + str(e)[:100], flush=True)

print("=" * 80, flush=True)

# 逐条执行SQL语句
executed = 0
failed = 0
start_time = datetime.now()

for i, statement in enumerate(statements):
    if not statement:
        continue
    
    # 提取表名
    table_match = re.search(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?', statement, re.IGNORECASE)
    if not table_match:
        table_match = re.search(r'INSERT\s+(?:IGNORE\s+)?INTO\s+`?(\w+)`?', statement, re.IGNORECASE)
    if not table_match:
        table_match = re.search(r'INSERT\s+INTO\s+`?(\w+)`?', statement, re.IGNORECASE)
    table_name = table_match.group(1) if table_match else "未知表"
    
    statement_preview = statement[:100].replace('\n', ' ').strip()
    if len(statement) > 100:
        statement_preview += "..."
    
    # 打印执行信息
    print("   [" + str(i + 1) + "/" + str(len(statements)) + "] 📋 表: " + table_name + " | 执行: " + statement_preview, flush=True)
    
    # 通过docker exec执行SQL
    # 使用临时文件方式执行，避免命令行转义问题
    try:
        # 创建临时SQL文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(statement)
            tmp_sql_file = tmp_file.name
        
        # 通过docker exec执行临时SQL文件
        cmd = 'docker exec -i ' + mysql_container + ' mysql -u' + mysql_user + ' -p' + mysql_password + ' --default-character-set=utf8mb4 ' + mysql_database + ' < ' + tmp_sql_file
        
        try:
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
            
            if result.returncode == 0:
                executed += 1
                print("      ✅ 成功", flush=True)
            else:
                failed += 1
                error_msg = result.stderr[:200] if result.stderr else "未知错误"
                if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                    executed += 1
                    failed -= 1
                    print("      ⚠️  已存在（跳过）", flush=True)
                else:
                    print("      ❌ 失败: " + error_msg, flush=True)
        except subprocess.TimeoutExpired:
            failed += 1
            print("      ⚠️  超时（跳过，继续执行下一条）", flush=True)
        except Exception as e:
            failed += 1
            print("      ❌ 异常: " + str(e)[:200], flush=True)
        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_sql_file)
            except:
                pass
                
    except Exception as e:
        failed += 1
        print("      ❌ 创建临时文件失败: " + str(e)[:200], flush=True)
    
    # 每10条显示一次进度
    if (i + 1) % 10 == 0 or (i + 1) == len(statements):
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remaining = (len(statements) - i - 1) / rate if rate > 0 else 0
        progress_pct = (i + 1) * 100 // len(statements) if len(statements) > 0 else 0
        print("   ⏳ 进度: " + str(i + 1) + "/" + str(len(statements)) + " (" + str(progress_pct) + "%) | 速度: " + "{:.1f}".format(rate) + " 条/秒 | 预计剩余: " + "{:.0f}".format(remaining) + "秒", flush=True)

print("=" * 80, flush=True)
elapsed = (datetime.now() - start_time).total_seconds()
print("✅ 执行完成: 成功 " + str(executed) + " 条, 失败 " + str(failed) + " 条, 耗时 " + "{:.2f}".format(elapsed) + " 秒", flush=True)
sys.exit(0 if failed == 0 else 1)

