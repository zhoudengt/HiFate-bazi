#!/bin/bash
# 重启 Node1 Docker MySQL 服务脚本
# 使用方法：
#   1. 在 Node1 服务器上直接执行：bash scripts/restart_node1_mysql.sh
#   2. 从本地通过 SSH 执行：bash scripts/restart_node1_mysql.sh --ssh root@8.210.52.217

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否通过 SSH 执行
SSH_TARGET=""
if [ "$1" == "--ssh" ] && [ -n "$2" ]; then
    SSH_TARGET="$2"
    echo -e "${YELLOW}⚠️  将通过 SSH 连接到: $SSH_TARGET${NC}"
fi

# 执行命令的函数
exec_cmd() {
    if [ -n "$SSH_TARGET" ]; then
        ssh "$SSH_TARGET" "$1"
    else
        eval "$1"
    fi
}

echo "========================================"
echo "重启 Node1 Docker MySQL 服务"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# 检查 MySQL 容器状态
echo "[1/4] 检查 MySQL 容器状态..."
MYSQL_STATUS=$(exec_cmd "docker ps -a --filter 'name=hifate-mysql-master' --format '{{.Status}}'" 2>/dev/null || echo "")

if [ -z "$MYSQL_STATUS" ]; then
    echo -e "${RED}❌ 错误：未找到 MySQL 容器 'hifate-mysql-master'${NC}"
    echo "请检查容器是否存在："
    echo "  docker ps -a | grep mysql"
    exit 1
fi

echo -e "${GREEN}✅ MySQL 容器状态: $MYSQL_STATUS${NC}"
echo ""

# 检查是否有应用连接
echo "[2/4] 检查数据库连接..."
CONNECTION_COUNT=$(exec_cmd "docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 -e 'SHOW PROCESSLIST;' 2>/dev/null | wc -l" 2>/dev/null || echo "0")

if [ "$CONNECTION_COUNT" -gt 5 ]; then
    echo -e "${YELLOW}⚠️  警告：当前有 $((CONNECTION_COUNT - 2)) 个数据库连接${NC}"
    echo -e "${YELLOW}⚠️  重启 MySQL 可能会中断这些连接${NC}"
    read -p "是否继续重启？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消重启操作"
        exit 0
    fi
else
    echo -e "${GREEN}✅ 当前连接数较少，可以安全重启${NC}"
fi
echo ""

# 重启 MySQL 容器
echo "[3/4] 重启 MySQL 容器..."
if exec_cmd "docker restart hifate-mysql-master" 2>/dev/null; then
    echo -e "${GREEN}✅ MySQL 容器重启命令已执行${NC}"
else
    echo -e "${RED}❌ MySQL 容器重启失败${NC}"
    exit 1
fi
echo ""

# 等待 MySQL 启动
echo "[4/4] 等待 MySQL 启动..."
MAX_WAIT=60
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if exec_cmd "docker exec hifate-mysql-master mysqladmin ping -h localhost -uroot -pYuanqizhan@163 --silent" 2>/dev/null; then
        echo -e "${GREEN}✅ MySQL 已成功启动${NC}"
        break
    fi
    WAIT_TIME=$((WAIT_TIME + 2))
    echo "等待 MySQL 启动... ($WAIT_TIME/$MAX_WAIT 秒)"
    sleep 2
done

if [ $WAIT_TIME -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ MySQL 启动超时，请检查日志${NC}"
    echo "查看日志命令："
    echo "  docker logs hifate-mysql-master --tail 50"
    exit 1
fi

# 验证 MySQL 状态
echo ""
echo "验证 MySQL 状态..."
MYSQL_VERSION=$(exec_cmd "docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 -e 'SELECT VERSION();' 2>/dev/null | tail -n 1" 2>/dev/null || echo "未知")
MYSQL_UPTIME=$(exec_cmd "docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 -e 'SHOW STATUS LIKE \"Uptime\";' 2>/dev/null | tail -n 1" 2>/dev/null || echo "未知")

echo -e "${GREEN}✅ MySQL 版本: $MYSQL_VERSION${NC}"
echo -e "${GREEN}✅ MySQL 运行时间: $MYSQL_UPTIME${NC}"

echo ""
echo "========================================"
echo -e "${GREEN}MySQL 重启成功！${NC}"
echo "========================================"
echo ""
echo "后续操作建议："
echo "  1. 检查应用连接是否正常"
echo "  2. 检查主从复制状态（如果有从库）"
echo "  3. 监控 MySQL 日志：docker logs hifate-mysql-master -f"
echo ""






