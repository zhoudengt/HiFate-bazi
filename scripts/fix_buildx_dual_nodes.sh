#!/bin/bash
# scripts/fix_buildx_dual_nodes.sh - 双机 buildx 版本修复脚本
# 用途：在 Node1 和 Node2 上同时修复 buildx 版本问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE1_PRIVATE_IP="172.18.121.222"
NODE2_PUBLIC_IP="47.243.160.43"
NODE2_PRIVATE_IP="172.18.121.223"

# SSH 密码（从环境变量读取）
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# SSH 执行函数（支持密码登录）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "$cmd"
    else
        # 如果没有 sshpass，尝试使用 SSH 密钥
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "$cmd"
    fi
}

# 在单机上执行修复
fix_node() {
    local node_name=$1
    local node_ip=$2
    
    echo ""
    echo "=========================================="
    echo -e "${BLUE}修复 ${node_name} (${node_ip})${NC}"
    echo "=========================================="
    echo ""
    
    # 1. 检查修复脚本是否存在
    echo "[1/4] 检查修复脚本..."
    if ssh_exec $node_ip "test -f /opt/HiFate-bazi/scripts/fix_buildx_version.sh"; then
        echo -e "  ${GREEN}✅ 修复脚本存在${NC}"
    else
        echo -e "  ${YELLOW}⚠️  修复脚本不存在，需要先上传${NC}"
        echo "  请先执行：git pull 或手动上传脚本"
        return 1
    fi
    
    # 2. 检查当前 buildx 版本
    echo ""
    echo "[2/4] 检查当前 buildx 版本..."
    BUILDX_VERSION=$(ssh_exec $node_ip "docker buildx version 2>/dev/null | head -n1" || echo "")
    if [ -n "$BUILDX_VERSION" ]; then
        echo "  当前版本: $BUILDX_VERSION"
        VERSION_NUM=$(echo "$BUILDX_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "")
        if [ -n "$VERSION_NUM" ]; then
            MAJOR=$(echo "$VERSION_NUM" | cut -d. -f1)
            MINOR=$(echo "$VERSION_NUM" | cut -d. -f2)
            if [ "$MAJOR" -lt 0 ] || ([ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 17 ]); then
                echo -e "  ${RED}❌ 版本 $VERSION_NUM 低于 0.17.0，需要升级${NC}"
                NEED_FIX=true
            else
                echo -e "  ${GREEN}✅ 版本 $VERSION_NUM 满足要求${NC}"
                NEED_FIX=false
            fi
        else
            echo -e "  ${YELLOW}⚠️  无法解析版本号${NC}"
            NEED_FIX=true
        fi
    else
        echo -e "  ${YELLOW}⚠️  buildx 未安装或无法访问${NC}"
        NEED_FIX=true
    fi
    
    # 3. 执行修复（如果需要）
    if [ "$NEED_FIX" = true ]; then
        echo ""
        echo "[3/4] 执行修复..."
        if ssh_exec $node_ip "cd /opt/HiFate-bazi && bash scripts/fix_buildx_version.sh"; then
            echo -e "  ${GREEN}✅ 修复脚本执行完成${NC}"
        else
            echo -e "  ${RED}❌ 修复脚本执行失败${NC}"
            return 1
        fi
    else
        echo ""
        echo "[3/4] 跳过修复（版本已满足要求）"
    fi
    
    # 4. 验证修复结果
    echo ""
    echo "[4/4] 验证修复结果..."
    FINAL_VERSION=$(ssh_exec $node_ip "docker buildx version 2>/dev/null | head -n1" || echo "")
    if [ -n "$FINAL_VERSION" ]; then
        echo "  最终版本: $FINAL_VERSION"
        VERSION_NUM=$(echo "$FINAL_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "")
        if [ -n "$VERSION_NUM" ]; then
            MAJOR=$(echo "$VERSION_NUM" | cut -d. -f1)
            MINOR=$(echo "$VERSION_NUM" | cut -d. -f2)
            if [ "$MAJOR" -lt 0 ] || ([ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 17 ]); then
                echo -e "  ${RED}❌ 版本仍然低于 0.17.0${NC}"
                return 1
            else
                echo -e "  ${GREEN}✅ 版本 $VERSION_NUM 满足要求${NC}"
            fi
        else
            echo -e "  ${YELLOW}⚠️  无法验证版本，但 buildx 已安装${NC}"
        fi
    else
        echo -e "  ${RED}❌ buildx 未安装或无法访问${NC}"
        return 1
    fi
    
    echo ""
    echo -e "${GREEN}✅ ${node_name} 修复完成${NC}"
    return 0
}

# 主函数
main() {
    echo "=========================================="
    echo "  Docker Compose buildx 双机修复工具"
    echo "=========================================="
    echo ""
    echo "将修复以下节点："
    echo "  - Node1: $NODE1_PUBLIC_IP"
    echo "  - Node2: $NODE2_PUBLIC_IP"
    echo ""
    
    # 检查 SSH 连接
    echo "检查 SSH 连接..."
    if ! ssh_exec $NODE1_PUBLIC_IP "echo 'Node1 连接成功'" &>/dev/null; then
        echo -e "${RED}❌ 无法连接到 Node1${NC}"
        echo "请检查："
        echo "  1. SSH 密码是否正确（环境变量 SSH_PASSWORD）"
        echo "  2. 网络连接是否正常"
        exit 1
    fi
    
    if ! ssh_exec $NODE2_PUBLIC_IP "echo 'Node2 连接成功'" &>/dev/null; then
        echo -e "${RED}❌ 无法连接到 Node2${NC}"
        echo "请检查："
        echo "  1. SSH 密码是否正确（环境变量 SSH_PASSWORD）"
        echo "  2. 网络连接是否正常"
        exit 1
    fi
    
    echo -e "${GREEN}✅ SSH 连接正常${NC}"
    echo ""
    
    # 修复 Node1
    NODE1_SUCCESS=false
    if fix_node "Node1" "$NODE1_PUBLIC_IP"; then
        NODE1_SUCCESS=true
    fi
    
    # 修复 Node2
    NODE2_SUCCESS=false
    if fix_node "Node2" "$NODE2_PUBLIC_IP"; then
        NODE2_SUCCESS=true
    fi
    
    # 总结
    echo ""
    echo "=========================================="
    echo "  修复结果总结"
    echo "=========================================="
    echo ""
    
    if [ "$NODE1_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Node1 修复成功${NC}"
    else
        echo -e "${RED}❌ Node1 修复失败${NC}"
    fi
    
    if [ "$NODE2_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Node2 修复成功${NC}"
    else
        echo -e "${RED}❌ Node2 修复失败${NC}"
    fi
    
    echo ""
    
    if [ "$NODE1_SUCCESS" = true ] && [ "$NODE2_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ 双机修复完成！${NC}"
        echo ""
        echo "下一步："
        echo "  1. 在 Node1 上测试：docker-compose up -d frontend-gateway"
        echo "  2. 在 Node2 上测试：docker-compose up -d frontend-gateway"
        exit 0
    else
        echo -e "${RED}❌ 部分节点修复失败，请检查错误信息${NC}"
        exit 1
    fi
}

# 执行主函数
main "$@"

