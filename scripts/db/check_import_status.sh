#!/bin/bash
# 检查 MySQL 导入状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "============================================================"
echo "  检查 MySQL 导入状态"
echo "============================================================"
echo ""

# 检测 Docker 环境
DOCKER_MYSQL_CONTAINER=""
if command -v docker >/dev/null 2>&1; then
    DOCKER_MYSQL_CONTAINER=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E "(hifate-mysql-master|hifate-mysql-slave)" | head -1)
    if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
        echo -e "${GREEN}✅ 检测到 Docker 环境${NC}"
        echo -e "  容器名称: ${DOCKER_MYSQL_CONTAINER}"
    else
        echo -e "${YELLOW}⚠️  未检测到 MySQL 容器${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker 未安装或未运行${NC}"
fi

echo ""
echo "============================================================"
echo "  1. 查看 MySQL 容器状态"
echo "============================================================"
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    echo -e "${BLUE}容器状态：${NC}"
    docker ps --filter "name=${DOCKER_MYSQL_CONTAINER}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo -e "${BLUE}容器资源使用：${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" "${DOCKER_MYSQL_CONTAINER}"
else
    echo -e "${YELLOW}未找到 MySQL 容器${NC}"
fi

echo ""
echo "============================================================"
echo "  2. 查看 MySQL 进程（容器内）"
echo "============================================================"
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    echo -e "${BLUE}MySQL 进程：${NC}"
    docker exec "${DOCKER_MYSQL_CONTAINER}" ps aux | grep -E "(mysql|mysqld)" | grep -v grep || echo "未找到 MySQL 进程"
    
    echo ""
    echo -e "${BLUE}正在执行的 MySQL 连接：${NC}"
    docker exec "${DOCKER_MYSQL_CONTAINER}" mysql -uroot -p$(grep MYSQL_PASSWORD /opt/HiFate-bazi/.env 2>/dev/null | cut -d'=' -f2 || echo "${MYSQL_PASSWORD:?MYSQL_PASSWORD required}") \
        -e "SHOW PROCESSLIST;" 2>/dev/null | grep -v "Sleep" || echo "无活跃连接"
else
    echo -e "${YELLOW}未找到 MySQL 容器${NC}"
fi

echo ""
echo "============================================================"
echo "  3. 查看 MySQL 日志（最近 50 行）"
echo "============================================================"
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    echo -e "${BLUE}容器日志：${NC}"
    docker logs --tail 50 "${DOCKER_MYSQL_CONTAINER}" 2>&1 | tail -20
else
    echo -e "${YELLOW}未找到 MySQL 容器${NC}"
fi

echo ""
echo "============================================================"
echo "  4. 查看数据库表数量（验证导入结果）"
echo "============================================================"
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    MYSQL_PASSWORD=$(grep MYSQL_PASSWORD /opt/HiFate-bazi/.env 2>/dev/null | cut -d'=' -f2 || echo "${MYSQL_PASSWORD:?MYSQL_PASSWORD required}")
    MYSQL_DATABASE=$(grep MYSQL_DATABASE /opt/HiFate-bazi/.env 2>/dev/null | cut -d'=' -f2 || echo "hifate_bazi")
    
    TABLE_COUNT=$(docker exec "${DOCKER_MYSQL_CONTAINER}" mysql -uroot -p"${MYSQL_PASSWORD}" \
        -e "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = '${MYSQL_DATABASE}'" -N 2>/dev/null | tail -1 || echo "0")
    
    echo -e "${BLUE}数据库: ${MYSQL_DATABASE}${NC}"
    echo "  表数量: ${TABLE_COUNT}"
    
    # 检查关键表
    echo ""
    echo -e "${BLUE}关键表检查：${NC}"
    KEY_TABLES=("bazi_rules" "daily_fortune_jianchu" "daily_fortune_zodiac" "rizhu_liujiazi")
    for table in "${KEY_TABLES[@]}"; do
        EXISTS=$(docker exec "${DOCKER_MYSQL_CONTAINER}" mysql -uroot -p"${MYSQL_PASSWORD}" \
            "${MYSQL_DATABASE}" -e "SHOW TABLES LIKE '${table}'" -N 2>/dev/null | grep -c "${table}" || echo "0")
        if [ "$EXISTS" -gt 0 ]; then
            ROW_COUNT=$(docker exec "${DOCKER_MYSQL_CONTAINER}" mysql -uroot -p"${MYSQL_PASSWORD}" \
                "${MYSQL_DATABASE}" -e "SELECT COUNT(*) FROM ${table}" -N 2>/dev/null | tail -1 || echo "0")
            echo -e "  ${GREEN}✅ ${table}${NC} - 行数: ${ROW_COUNT}"
        else
            echo -e "  ${RED}❌ ${table} 不存在${NC}"
        fi
    done
    
    # 检查 bazi_rules 数据量
    echo ""
    RULES_COUNT=$(docker exec "${DOCKER_MYSQL_CONTAINER}" mysql -uroot -p"${MYSQL_PASSWORD}" \
        "${MYSQL_DATABASE}" -e "SELECT COUNT(*) FROM bazi_rules WHERE enabled = 1" -N 2>/dev/null | tail -1 || echo "0")
    echo -e "${BLUE}bazi_rules 启用规则数: ${RULES_COUNT}${NC}"
else
    echo -e "${YELLOW}未找到 MySQL 容器${NC}"
fi

echo ""
echo "============================================================"
echo "  5. 实时监控 MySQL 进程（按 Ctrl+C 退出）"
echo "============================================================"
echo -e "${YELLOW}提示：如果要实时监控，可以运行：${NC}"
if [ -n "${DOCKER_MYSQL_CONTAINER}" ]; then
    echo "  watch -n 1 'docker exec ${DOCKER_MYSQL_CONTAINER} mysql -uroot -p\$(grep MYSQL_PASSWORD /opt/HiFate-bazi/.env | cut -d\"=\" -f2) -e \"SHOW PROCESSLIST;\"'"
    echo ""
    echo "  或者查看容器日志："
    echo "  docker logs -f ${DOCKER_MYSQL_CONTAINER}"
else
    echo "  docker logs -f <mysql-container-name>"
fi

echo ""

