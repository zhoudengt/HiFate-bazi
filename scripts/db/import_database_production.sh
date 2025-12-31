#!/bin/bash
# 在生产环境执行数据库导入脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/opt/HiFate-bazi"
SQL_FILE="${1:-scripts/db/hifate_db_import_20251231_182038.sql}"

echo "============================================================"
echo "  生产环境数据库导入脚本"
echo "============================================================"
echo ""
echo "📝 SQL 文件: ${SQL_FILE}"
echo ""

# 检查文件是否存在
if [ ! -f "${PROJECT_DIR}/${SQL_FILE}" ]; then
    echo -e "${RED}❌ SQL 文件不存在: ${PROJECT_DIR}/${SQL_FILE}${NC}"
    exit 1
fi

# 加载环境变量
if [ -f "${PROJECT_DIR}/.env" ]; then
    source "${PROJECT_DIR}/.env"
    echo -e "${GREEN}✅ 已加载环境变量${NC}"
else
    echo -e "${YELLOW}⚠️  .env 文件不存在，使用默认配置${NC}"
fi

# 获取 MySQL 配置（从 .env 文件）
MYSQL_HOST="${MYSQL_HOST:-localhost}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-Yuanqizhan@163}"
MYSQL_DATABASE="${MYSQL_DATABASE:-hifate_bazi}"

# 检测 Docker 环境
DOCKER_MYSQL_CONTAINER=""
if command -v docker >/dev/null 2>&1; then
    # 查找 MySQL 容器（可能是 hifate-mysql-master 或 hifate-mysql-slave）
    DOCKER_MYSQL_CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E "(hifate-mysql-master|hifate-mysql-slave)" | head -1)
    if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
        echo -e "${YELLOW}检测到 Docker 环境，使用容器: ${DOCKER_MYSQL_CONTAINER}${NC}"
        # Docker 环境：MySQL 在容器内，使用 localhost
        MYSQL_HOST="localhost"
    fi
fi

echo ""
echo -e "${BLUE}数据库配置：${NC}"
echo "  主机: ${MYSQL_HOST}:${MYSQL_PORT}"
echo "  用户: ${MYSQL_USER}"
echo "  数据库: ${MYSQL_DATABASE}"
echo ""

# 确认执行
read -p "确认执行导入？(y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 执行导入
echo ""
echo -e "${BLUE}📥 开始导入数据库...${NC}"
echo "----------------------------------------"

cd "${PROJECT_DIR}"

# 确定 MySQL 执行方式
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    # Docker 环境：使用 docker exec
    echo -e "${BLUE}使用 Docker 容器执行导入...${NC}"
    
    # 将 SQL 文件复制到容器中（如果文件不在容器内）
    SQL_FILE_BASENAME=$(basename "${SQL_FILE}")
    CONTAINER_SQL_PATH="/tmp/${SQL_FILE_BASENAME}"
    
    # 检查文件是否在容器内可访问（通过挂载）
    # 如果文件在 /opt/HiFate-bazi 目录下，容器应该可以访问
    if [ -f "${PROJECT_DIR}/${SQL_FILE}" ]; then
        # 文件在项目目录下，容器应该可以通过挂载访问
        CONTAINER_SQL_PATH="${PROJECT_DIR}/${SQL_FILE}"
    else
        # 复制文件到容器
        echo -e "${YELLOW}复制 SQL 文件到容器...${NC}"
        docker cp "${PROJECT_DIR}/${SQL_FILE}" "${DOCKER_MYSQL_CONTAINER}:${CONTAINER_SQL_PATH}" 2>/dev/null || {
            echo -e "${RED}❌ 无法复制文件到容器${NC}"
            exit 1
        }
    fi
    
    # 执行导入（在容器内执行 mysql 命令）
    if docker exec -i "${DOCKER_MYSQL_CONTAINER}" mysql \
        -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} \
        --default-character-set=utf8mb4 \
        ${MYSQL_DATABASE} < "${PROJECT_DIR}/${SQL_FILE}" 2>&1; then
        echo -e "${GREEN}✅ 导入成功${NC}"
    else
        echo -e "${RED}❌ 导入失败${NC}"
        echo ""
        echo -e "${YELLOW}请尝试手动执行：${NC}"
        echo "  docker exec -i ${DOCKER_MYSQL_CONTAINER} mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} < ${PROJECT_DIR}/${SQL_FILE}"
        exit 1
    fi
else
    # 非 Docker 环境：使用本地 mysql 命令
    echo -e "${BLUE}使用本地 MySQL 客户端执行导入...${NC}"
    
    # 尝试使用 mysql 命令
    if command -v mysql >/dev/null 2>&1; then
        MYSQL_CMD="mysql"
    elif [ -f "/usr/bin/mysql" ]; then
        MYSQL_CMD="/usr/bin/mysql"
    elif [ -f "/usr/local/bin/mysql" ]; then
        MYSQL_CMD="/usr/local/bin/mysql"
    else
        echo -e "${RED}❌ 未找到 mysql 命令${NC}"
        echo "请手动执行："
        echo "  mysql -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} ${MYSQL_DATABASE} < ${PROJECT_DIR}/${SQL_FILE}"
        exit 1
    fi
    
    # 执行导入
    if ${MYSQL_CMD} -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} \
        --default-character-set=utf8mb4 \
        ${MYSQL_DATABASE} < "${PROJECT_DIR}/${SQL_FILE}" 2>&1; then
        echo -e "${GREEN}✅ 导入成功${NC}"
    else
        echo -e "${RED}❌ 导入失败${NC}"
        exit 1
    fi
fi

# 验证导入结果
echo ""
echo -e "${BLUE}🔍 验证导入结果...${NC}"
echo "----------------------------------------"

# 确定验证命令
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    VERIFY_CMD="docker exec ${DOCKER_MYSQL_CONTAINER} mysql"
else
    VERIFY_CMD="${MYSQL_CMD}"
fi

TABLE_COUNT=$(${VERIFY_CMD} -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} \
    ${MYSQL_DATABASE} -e "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = DATABASE()" -N 2>/dev/null | tail -1)

echo "  表数量: ${TABLE_COUNT}"

# 检查关键表
KEY_TABLES=("bazi_rules" "daily_fortune_jianchu" "daily_fortune_zodiac" "rizhu_liujiazi")
for table in "${KEY_TABLES[@]}"; do
    EXISTS=$(${VERIFY_CMD} -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} \
        ${MYSQL_DATABASE} -e "SHOW TABLES LIKE '${table}'" -N 2>/dev/null | grep -c "${table}" || echo "0")
    if [ "$EXISTS" -gt 0 ]; then
        echo -e "  ${GREEN}✅ 表 ${table} 存在${NC}"
    else
        echo -e "  ${YELLOW}⚠️  表 ${table} 不存在${NC}"
    fi
done

# 检查 bazi_rules 数据量
RULES_COUNT=$(${VERIFY_CMD} -h${MYSQL_HOST} -P${MYSQL_PORT} -u${MYSQL_USER} -p${MYSQL_PASSWORD} \
    ${MYSQL_DATABASE} -e "SELECT COUNT(*) FROM bazi_rules WHERE enabled = 1" -N 2>/dev/null | tail -1 || echo "0")
echo "  bazi_rules 启用规则数: ${RULES_COUNT}"

echo ""
echo "============================================================"
echo -e "${GREEN}✅ 数据库导入完成！${NC}"
echo "============================================================"
echo ""
echo -e "${YELLOW}💡 建议：${NC}"
echo "  1. 测试接口是否正常："
echo "     curl -X POST http://localhost:8001/api/v1/children-study/stream \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"solar_date\": \"1990-01-15\", \"solar_time\": \"12:00\", \"gender\": \"male\"}'"
echo ""

