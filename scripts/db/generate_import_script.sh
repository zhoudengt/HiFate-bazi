#!/bin/bash
# 生成数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）

set -e

# 配置
LOCAL_MYSQL_HOST="${MYSQL_HOST:-127.0.0.1}"
LOCAL_MYSQL_PORT="${MYSQL_PORT:-3306}"
LOCAL_MYSQL_USER="${MYSQL_USER:-root}"
LOCAL_MYSQL_PASS="${MYSQL_PASSWORD:-${MYSQL_ROOT_PASSWORD:-123456}}"
LOCAL_DB="${MYSQL_DATABASE:-hifate_bazi}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="/tmp/hifate_db_import_${TIMESTAMP}.sql"
TEMP_FILE="/tmp/hifate_db_import_${TIMESTAMP}.tmp"

echo "============================================================"
echo "  生成数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE）"
echo "============================================================"
echo ""
echo "📤 导出数据库: $LOCAL_DB"
echo "📝 输出文件: $OUTPUT_FILE"
echo ""

# 第一步：使用 mysqldump 导出
echo "  执行 mysqldump..."
mysqldump -h${LOCAL_MYSQL_HOST} -P${LOCAL_MYSQL_PORT} -u${LOCAL_MYSQL_USER} -p${LOCAL_MYSQL_PASS} \
    --default-character-set=utf8mb4 \
    --single-transaction \
    --routines \
    --triggers \
    --complete-insert \
    --skip-extended-insert \
    --add-drop-database \
    --databases ${LOCAL_DB} > "${TEMP_FILE}" 2>&1

if [ $? -ne 0 ]; then
    echo "❌ mysqldump 失败"
    exit 1
fi

# 第二步：转换为 INSERT ... ON DUPLICATE KEY UPDATE 格式
echo "  转换为 INSERT ... ON DUPLICATE KEY UPDATE 格式..."

# 写入文件头
cat > "${OUTPUT_FILE}" << 'EOF'
-- HiFate 数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式）
-- 生成时间: TIMESTAMP_PLACEHOLDER
-- 数据库: DATABASE_PLACEHOLDER
-- 
-- 使用方法：
--   cd /opt/HiFate-bazi
--   source .env
--   mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < this_file.sql
-- 
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS=0;
SET UNIQUE_CHECKS=0;

EOF

# 替换占位符
sed -i '' "s/TIMESTAMP_PLACEHOLDER/$(date '+%Y-%m-%d %H:%M:%S')/g" "${OUTPUT_FILE}"
sed -i '' "s/DATABASE_PLACEHOLDER/${LOCAL_DB}/g" "${OUTPUT_FILE}"

# 处理 SQL 文件：为每个 INSERT 语句添加 ON DUPLICATE KEY UPDATE
python3 << PYTHON_SCRIPT
import re
import sys

def convert_insert_to_upsert(content):
    """将 INSERT 语句转换为 INSERT ... ON DUPLICATE KEY UPDATE"""
    lines = content.split('\n')
    output = []
    current_insert = []
    in_insert = False
    
    for line in lines:
        # 保留 CREATE TABLE、DROP TABLE 等结构语句
        if (line.strip().upper().startswith('CREATE ') or 
            line.strip().upper().startswith('DROP ') or
            line.strip().upper().startswith('LOCK ') or
            line.strip().upper().startswith('UNLOCK ') or
            line.strip().upper().startswith('USE ') or
            line.strip().startswith('/*') or
            (line.strip().startswith('--') and not in_insert)):
            output.append(line)
            continue
        
        # 检测 INSERT INTO 语句
        if line.strip().upper().startswith('INSERT INTO'):
            in_insert = True
            current_insert = [line]
            continue
        
        # 收集 INSERT 语句的所有行
        if in_insert:
            current_insert.append(line)
            
            # 检测 INSERT 语句结束（以分号结尾）
            if line.rstrip().endswith(';'):
                # 合并完整的 INSERT 语句
                full_insert = ' '.join(current_insert)
                
                # 提取表名和列名
                match = re.match(r'INSERT INTO `?(\w+)`?\s*\(([^)]+)\)', full_insert, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
                    columns_str = match.group(2)
                    columns = [col.strip().strip('`') for col in columns_str.split(',')]
                    
                    # 构建 ON DUPLICATE KEY UPDATE 子句
                    update_clause = ", ".join([f"`{col}`=VALUES(`{col}`)" for col in columns])
                    
                    # 写入转换后的语句
                    insert_part = f"INSERT INTO `{table_name}` ({columns_str})"
                    values_part = re.search(r'VALUES\s+(.+);', full_insert, re.IGNORECASE | re.DOTALL)
                    if values_part:
                        values = values_part.group(1).strip()
                        output.append(f"{insert_part} VALUES {values}")
                        output.append(f"ON DUPLICATE KEY UPDATE {update_clause};")
                    else:
                        # 如果无法解析，直接写入
                        output.append(full_insert)
                else:
                    # 如果无法解析，直接写入
                    output.append(full_insert)
                
                in_insert = False
                current_insert = []
            continue
        
        # 其他行直接写入
        output.append(line)
    
    return '\n'.join(output)

# 读取临时文件
with open('${TEMP_FILE}', 'r', encoding='utf-8') as f:
    content = f.read()

# 转换
converted = convert_insert_to_upsert(content)

# 追加到输出文件
with open('${OUTPUT_FILE}', 'a', encoding='utf-8') as f:
    f.write(converted)
    f.write('\n\n')
    f.write('SET FOREIGN_KEY_CHECKS=1;\n')
    f.write('SET UNIQUE_CHECKS=1;\n')

PYTHON_SCRIPT

# 删除临时文件
rm -f "${TEMP_FILE}"

# 显示结果
FILE_SIZE=$(ls -lh "${OUTPUT_FILE}" | awk '{print $5}')
echo "✅ 生成成功"
echo "  文件: ${OUTPUT_FILE}"
echo "  大小: ${FILE_SIZE}"
echo ""
echo "💡 使用方法："
echo "  1. 上传到生产环境："
echo "     scp ${OUTPUT_FILE} root@8.210.52.217:/opt/HiFate-bazi/scripts/db/"
echo "     scp ${OUTPUT_FILE} root@47.243.160.43:/opt/HiFate-bazi/scripts/db/"
echo "  2. 在生产环境执行（Node1 和 Node2）："
echo "     cd /opt/HiFate-bazi"
echo "     source .env"
echo "     mysql -h\$MYSQL_HOST -P\$MYSQL_PORT -u\$MYSQL_USER -p\$MYSQL_PASSWORD \$MYSQL_DATABASE < scripts/db/$(basename ${OUTPUT_FILE})"

