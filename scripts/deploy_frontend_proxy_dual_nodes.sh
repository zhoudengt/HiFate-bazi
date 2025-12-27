#!/bin/bash
# scripts/deploy_frontend_proxy_dual_nodes.sh - 双机部署前端代理配置
# 用途：在 Node1 和 Node2 上部署前端 Nginx 代理配置（Nacos 和 Destiny）

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
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"

# SSH 执行函数（支持密码登录）
# 使用 root 用户连接，然后切换到 frontend-user 执行命令（因为 frontend-user 可能无法访问 /opt/HiFate-bazi）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        # 使用 root 用户连接，然后切换到 frontend-user 执行
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "su - frontend-user -c '$cmd'"
    else
        # 如果没有 sshpass，尝试使用 SSH 密钥
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$host "su - frontend-user -c '$cmd'"
    fi
}

# SSH 执行函数（使用 root 用户，用于需要 root 权限的操作）
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

# 在单机上部署
deploy_node() {
    local node_name=$1
    local node_ip=$2
    
    echo ""
    echo "=========================================="
    echo -e "${BLUE}部署 ${node_name} (${node_ip})${NC}"
    echo "=========================================="
    echo ""
    
    # 1. 检查项目目录（使用 root 用户）
    echo "[1/5] 检查项目目录..."
    if ssh_exec_root $node_ip "test -d $PROJECT_DIR"; then
        echo -e "  ${GREEN}✅ 项目目录存在${NC}"
    else
        echo -e "  ${RED}❌ 项目目录不存在：$PROJECT_DIR${NC}"
        return 1
    fi
    
    # 2. 拉取最新代码（使用 root 用户，因为需要访问 /opt/HiFate-bazi）
    echo ""
    echo "[2/5] 拉取最新代码..."
    if ssh_exec_root $node_ip "cd $PROJECT_DIR && git pull origin master"; then
        echo -e "  ${GREEN}✅ 代码更新完成${NC}"
    else
        echo -e "  ${YELLOW}⚠️  代码更新失败，继续使用现有配置${NC}"
    fi
    
    # 3. 检查配置文件（使用 root 用户）
    echo ""
    echo "[3/5] 检查配置文件..."
    if ssh_exec_root $node_ip "test -f $PROJECT_DIR/frontend-config/nginx.conf"; then
        echo -e "  ${GREEN}✅ Nginx 配置文件存在${NC}"
        
        # 检查是否包含新配置
        if ssh_exec_root $node_ip "grep -q '/nacos' $PROJECT_DIR/frontend-config/nginx.conf && grep -q '/destiny/api/grpc-web' $PROJECT_DIR/frontend-config/nginx.conf"; then
            echo -e "  ${GREEN}✅ 新代理配置已存在${NC}"
        else
            echo -e "  ${YELLOW}⚠️  新代理配置不存在，需要更新${NC}"
        fi
    else
        echo -e "  ${RED}❌ Nginx 配置文件不存在${NC}"
        return 1
    fi
    
    # 4. 检查 Docker Compose 配置（使用 root 用户）
    echo ""
    echo "[4/5] 检查 Docker Compose 配置..."
    if ssh_exec_root $node_ip "test -f $PROJECT_DIR/docker-compose.frontend.yml"; then
        echo -e "  ${GREEN}✅ Docker Compose 配置文件存在${NC}"
    else
        echo -e "  ${RED}❌ Docker Compose 配置文件不存在${NC}"
        return 1
    fi
    
    # 5. 重启 Nginx 服务（使用 root 用户，因为需要访问项目目录）
    echo ""
    echo "[5/5] 重启前端 Nginx 服务..."
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
    
    # 6. 验证配置（使用 root 用户执行 docker exec）
    echo ""
    echo "验证 Nginx 配置..."
    if ssh_exec_root $node_ip "docker exec hifate-frontend-nginx nginx -t 2>&1"; then
        echo -e "  ${GREEN}✅ Nginx 配置验证通过${NC}"
    else
        echo -e "  ${RED}❌ Nginx 配置验证失败${NC}"
        return 1
    fi
    
    echo ""
    echo -e "${GREEN}✅ ${node_name} 部署完成${NC}"
    return 0
}

# 主函数
main() {
    echo "=========================================="
    echo "  前端代理配置双机部署工具"
    echo "=========================================="
    echo ""
    echo "将部署以下配置："
    echo "  1. Nacos 代理：/nacos -> localhost:9060"
    echo "  2. Destiny gRPC-Web 代理：/destiny/api/grpc-web/ -> localhost:9070"
    echo ""
    echo "目标节点："
    echo "  - Node1: $NODE1_PUBLIC_IP"
    echo "  - Node2: $NODE2_PUBLIC_IP"
    echo ""
    
    # 检查 SSH 连接（使用 root 用户）
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
    
    # 部署 Node1
    NODE1_SUCCESS=false
    if deploy_node "Node1" "$NODE1_PUBLIC_IP"; then
        NODE1_SUCCESS=true
    fi
    
    # 部署 Node2
    NODE2_SUCCESS=false
    if deploy_node "Node2" "$NODE2_PUBLIC_IP"; then
        NODE2_SUCCESS=true
    fi
    
    # 总结
    echo ""
    echo "=========================================="
    echo "  部署结果总结"
    echo "=========================================="
    echo ""
    
    if [ "$NODE1_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Node1 部署成功${NC}"
    else
        echo -e "${RED}❌ Node1 部署失败${NC}"
    fi
    
    if [ "$NODE2_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ Node2 部署成功${NC}"
    else
        echo -e "${RED}❌ Node2 部署失败${NC}"
    fi
    
    echo ""
    
    if [ "$NODE1_SUCCESS" = true ] && [ "$NODE2_SUCCESS" = true ]; then
        echo -e "${GREEN}✅ 双机部署完成！${NC}"
        echo ""
        echo "下一步："
        echo "  1. 验证 Nacos 代理：curl http://服务器IP/nacos/"
        echo "  2. 验证 Destiny 代理：curl http://服务器IP/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call"
        echo "  3. 确保 Nacos 服务运行在 9060 端口"
        echo "  4. 确保 Destiny 服务运行在 9070 端口"
        exit 0
    else
        echo -e "${RED}❌ 部分节点部署失败，请检查错误信息${NC}"
        exit 1
    fi
}

# 执行主函数
main "$@"

