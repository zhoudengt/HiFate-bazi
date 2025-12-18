#!/bin/bash
# 安全监控设置脚本
# 用途：配置和启用安全监控功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=========================================="
echo "🔒 安全监控设置"
echo "=========================================="
echo ""

# 检查环境变量
echo -e "${BLUE}检查环境变量...${NC}"

if [ -f ".env" ]; then
    # 检查是否已配置安全监控
    if grep -q "SECURITY_MONITOR_ENABLED" .env; then
        echo -e "${GREEN}✓ 安全监控环境变量已配置${NC}"
    else
        echo -e "${YELLOW}⚠ 添加安全监控环境变量到 .env${NC}"
        cat >> .env << 'EOF'

# 安全监控配置
SECURITY_MONITOR_ENABLED=true
SECURITY_AUTO_BLOCK_ENABLED=true
SECURITY_RATE_LIMIT_ENABLED=true
SECURITY_RATE_LIMIT_THRESHOLD=100
EOF
        echo -e "${GREEN}✓ 已添加安全监控环境变量${NC}"
    fi
else
    echo -e "${YELLOW}⚠ .env 文件不存在，创建默认配置${NC}"
    cat > .env << 'EOF'
# 安全监控配置
SECURITY_MONITOR_ENABLED=true
SECURITY_AUTO_BLOCK_ENABLED=true
SECURITY_RATE_LIMIT_ENABLED=true
SECURITY_RATE_LIMIT_THRESHOLD=100
EOF
    echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
fi

echo ""
echo -e "${GREEN}✅ 安全监控设置完成${NC}"
echo ""
echo "下一步："
echo "  1. 重启服务以应用配置"
echo "  2. 访问 http://localhost:8001/api/v1/security/stats 查看安全统计"
echo "  3. 查看日志文件 logs/security_events.log（如果配置）"

