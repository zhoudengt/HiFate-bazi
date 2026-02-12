#!/bin/bash
# 生产环境 FrontendGateway 服务测试脚本
# 用途：在双机生产环境测试 FrontendGateway 服务可用性

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"

# SSH 密码（从环境变量或默认值读取）
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

echo ""
echo "============================================================"
echo "FrontendGateway 服务生产环境测试"
echo "============================================================"
echo "Node1: $NODE1_PUBLIC_IP"
echo "Node2: $NODE2_PUBLIC_IP"
echo ""

# 测试函数
test_node() {
    local node_ip=$1
    local node_name=$2
    
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}测试 ${node_name} (${node_ip})${NC}"
    echo -e "${BLUE}============================================================${NC}"
    
    # 检查测试脚本是否存在
    if ! ssh_exec $node_ip "test -f $PROJECT_DIR/scripts/test_frontend_gateway.py"; then
        echo -e "${RED}❌ 错误：测试脚本不存在${NC}"
        return 1
    fi
    
    # 运行测试脚本
    echo "运行测试脚本..."
    ssh_exec $node_ip "cd $PROJECT_DIR && python3 scripts/test_frontend_gateway.py" || {
        echo -e "${RED}❌ ${node_name} 测试失败${NC}"
        return 1
    }
    
    echo -e "${GREEN}✅ ${node_name} 测试完成${NC}"
    echo ""
    return 0
}

# 测试 Node1
test_node $NODE1_PUBLIC_IP "Node1"

# 测试 Node2
test_node $NODE2_PUBLIC_IP "Node2"

echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ 所有测试完成！${NC}"
echo -e "${GREEN}============================================================${NC}"
