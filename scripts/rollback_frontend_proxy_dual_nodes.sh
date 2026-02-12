#!/bin/bash
# scripts/rollback_frontend_proxy_dual_nodes.sh - 撤回前端代理配置（双机）
# 用途：在 Node1 和 Node2 上撤回 Nacos 和 Destiny 代理配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"

# SSH 密码（从环境变量读取）
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"

# SSH 执行函数（使用 root 用户）
ssh_exec_root() {
    local host=$1
    shift
    local cmd="$@"
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "$cmd"
    fi
}

# 在单机上撤回配置
rollback_node() {
    local node_name=$1
    local node_ip=$2
    
    echo ""
    echo "=========================================="
    echo -e "${BLUE}撤回 ${node_name} (${node_ip})${NC}"
    echo "=========================================="
    echo ""
    
    # 1. 检查项目目录
    echo "[1/4] 检查项目目录..."
    if ssh_exec_root $node_ip "test -d $PROJECT_DIR"; then
        echo -e "  ${GREEN}✅ 项目目录存在${NC}"
    else
        echo -e "  ${RED}❌ 项目目录不存在：$PROJECT_DIR${NC}"
        return 1
    fi
    
    # 2. 拉取最新代码（移除配置后的版本）
    echo ""
    echo "[2/4] 拉取最新代码（包含撤回的配置）..."
    if ssh_exec_root $node_ip "cd $PROJECT_DIR && git pull origin master"; then
        echo -e "  ${GREEN}✅ 代码更新完成${NC}"
    else
        echo -e "  ${YELLOW}⚠️  代码更新失败，继续使用现有配置${NC}"
    fi
    
    # 3. 检查配置文件是否已移除配置
    echo ""
    echo "[3/4] 检查配置文件..."
    if ssh_exec_root $node_ip "test -f $PROJECT_DIR/frontend-config/nginx.conf"; then
        echo -e "  ${GREEN}✅ Nginx 配置文件存在${NC}"
        
        # 检查是否还包含旧配置
        if ssh_exec_root $node_ip "grep -q '/nacos' $PROJECT_DIR/frontend-config/nginx.conf || grep -q '/destiny/api/grpc-web' $PROJECT_DIR/frontend-config/nginx.conf"; then
            echo -e "  ${YELLOW}⚠️  配置文件中仍包含旧配置，需要手动移除${NC}"
            echo "  正在手动移除配置..."
            
            # 使用 sed 移除配置块
            ssh_exec_root $node_ip "cd $PROJECT_DIR && \
                sed -i '/# ============================================/,/# ============================================/d' frontend-config/nginx.conf && \
                sed -i '/location \/nacos/,/^[[:space:]]*}/d' frontend-config/nginx.conf && \
                sed -i '/location \/destiny\/api\/grpc-web/,/^[[:space:]]*}/d' frontend-config/nginx.conf"
            
            echo -e "  ${GREEN}✅ 配置已移除${NC}"
        else
            echo -e "  ${GREEN}✅ 配置文件中已不包含旧配置${NC}"
        fi
    else
        echo -e "  ${RED}❌ Nginx 配置文件不存在${NC}"
        return 1
    fi
    
    # 4. 重启 Nginx 服务
    echo ""
    echo "[4/4] 重启前端 Nginx 服务..."
    if ssh_exec_root $node_ip "cd $PROJECT_DIR && docker-compose -f docker-compose.frontend.yml restart nginx-frontend"; then
        echo -e "  ${GREEN}✅ Nginx 服务重启成功${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Nginx 服务重启失败，尝试重新创建${NC}"
        if ssh_exec_root $node_ip "cd $PROJECT_DIR && docker-compose -f docker-compose.frontend.yml up -d --force-recreate nginx-frontend"; then
            echo -e "  ${GREEN}✅ Nginx 服务重新创建成功${NC}"
        else
            echo -e "  ${RED}❌ Nginx 服务重新创建失败${NC}"
            return 1
        fi
    fi
    
    # 5. 验证配置
    echo ""
    echo "验证 Nginx 配置..."
    if ssh_exec_root $node_ip "docker exec hifate-frontend-nginx nginx -t 2>&1"; then
        echo -e "  ${GREEN}✅ Nginx 配置验证通过${NC}"
    else
        echo -e "  ${RED}❌ Nginx 配置验证失败${NC}"
        return 1
    fi
    
    # 6. 验证配置已移除
    echo ""
    echo "验证配置已移除..."
    if ssh_exec_root $node_ip "grep -q '/nacos' $PROJECT_DIR/frontend-config/nginx.conf || grep -q '/destiny/api/grpc-web' $PROJECT_DIR/frontend-config/nginx.conf"; then
        echo -e "  ${YELLOW}⚠️  配置文件中仍包含旧配置${NC}"
        return 1
    else
        echo -e "  ${GREEN}✅ 配置已成功移除${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}✅ ${node_name} 撤回完成${NC}"
    return 0
}

# 主函数
main() {
    echo "=========================================="
    echo "  前端代理配置撤回工具（双机）"
    echo "=========================================="
    echo ""
    echo "将撤回以下配置："
    echo "  1. Nacos 代理：/nacos -> localhost:9060"
    echo "  2. Destiny gRPC-Web 代理：/destiny/api/grpc-web/ -> localhost:9070"
    echo ""
    echo "目标节点："
    echo "  - Node1: $NODE1_PUBLIC_IP"
    echo "  - Node2: $NODE2_PUBLIC_IP"
    echo ""
    
    # 确认操作（支持 --yes 参数跳过确认）
    if [ "$1" != "--yes" ] && [ "$1" != "-y" ]; then
        read -p "确认要撤回这些配置吗？(y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo "已取消撤回操作"
            exit 0
        fi
    else
        echo "使用 --yes 参数，跳过确认"
    fi
    
    # 检查 SSH 连接
    echo ""
    echo "检查 SSH 连接..."
    if ! ssh_exec_root $NODE1_PUBLIC_IP "echo 'Node1 连接成功'" &>/dev/null; then
        echo -e "${RED}❌ 无法连接到 Node1${NC}"
        echo "请检查："
        echo "  1. SSH 密码是否正确（环境变量 SSH_PASSWORD）"
        echo "  2. root 用户是否可以 SSH 登录"
        echo "  3. 网络连接是否正常"
        exit 1
    fi
    
    if ! ssh_exec_root $NODE2_PUBLIC_IP "echo 'Node2 连接成功'" &>/dev/null; then
        echo -e "${RED}❌ 无法连接到 Node2${NC}"
        echo "请检查："
        echo "  1. SSH 密码是否正确（环境变量 SSH_PASSWORD）"
        echo "  2. root 用户是否可以 SSH 登录"
        echo "  3. 网络连接是否正常"
        exit 1
    fi
    
    echo -e "${GREEN}✅ SSH 连接正常${NC}"
    echo ""
    
    # 撤回 Node1
    NODE1_SUCCESS=false
    if rollback_node "Node1" "$NODE1_PUBLIC_IP"; then
        NODE1_SUCCESS=true
    fi
    
    # 撤回 Node2
    NODE2_SUCCESS=false
    if rollback_node "Node2" "$NODE2_PUBLIC_IP"; then
        NODE2_SUCCESS=true
    fi
    
    # 总结
    echo ""
    echo "=========================================="
    echo "  撤回结果总结"
    echo "=========================================="
    echo ""
    
    if [ "$NODE1_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Node1 撤回成功${NC}"
    else
        echo -e "${RED}❌ Node1 撤回失败${NC}"
    fi
    
    if [ "$NODE2_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Node2 撤回成功${NC}"
    else
        echo -e "${RED}❌ Node2 撤回失败${NC}"
    fi
    
    echo ""
    
    if [ "$NODE1_SUCCESS" = true ] && [ "$NODE2_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ 双机撤回完成！${NC}"
        echo ""
        echo "配置已从以下位置移除："
        echo "  - /nacos 代理配置"
        echo "  - /destiny/api/grpc-web/ 代理配置"
        exit 0
    else
        echo -e "${RED}❌ 部分节点撤回失败，请检查错误信息${NC}"
        exit 1
    fi
}

# 执行主函数
main "$@"

