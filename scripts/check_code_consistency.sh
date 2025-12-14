#!/bin/bash
# 代码一致性检查脚本
# 检查本地、Node1、Node2 代码是否一致

set -e

NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
PROJECT_DIR="/opt/HiFate-bazi"

echo "========================================"
echo "🔍 代码一致性检查"
echo "========================================"
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查项列表
CHECKS=(
    "proto/generated/bazi_core_pb2_grpc.py:gRPC代码"
    "server/api/grpc_gateway.py:gRPC网关"
    "server/api/v2/desk_fengshui_api.py:办公桌风水API"
    "deploy/docker/docker-compose.prod.yml:Docker配置"
    "requirements.txt:依赖配置"
)

# 不一致文件列表
INCONSISTENT_FILES=()

# 检查单个文件
check_file() {
    local file_path=$1
    local file_desc=$2
    local node=$3
    
    echo "【检查】$file_desc ($file_path)"
    
    # 获取本地文件哈希
    if [ ! -f "$file_path" ]; then
        echo "  ⚠️  本地文件不存在: $file_path"
        return 1
    fi
    
    local local_hash=$(md5 -q "$file_path" 2>/dev/null || md5sum "$file_path" 2>/dev/null | cut -d' ' -f1)
    
    # 获取服务器文件哈希
    local server_hash=""
    if [ "$node" = "node1" ]; then
        server_hash=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE1_IP "md5sum $PROJECT_DIR/$file_path 2>/dev/null | cut -d' ' -f1" 2>/dev/null || echo "")
    elif [ "$node" = "node2" ]; then
        server_hash=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE2_IP "md5sum $PROJECT_DIR/$file_path 2>/dev/null | cut -d' ' -f1" 2>/dev/null || echo "")
    fi
    
    if [ -z "$server_hash" ]; then
        echo "  ${RED}❌ 服务器文件不存在或无法访问${NC}"
        INCONSISTENT_FILES+=("$file_path (服务器不存在)")
        return 1
    fi
    
    if [ "$local_hash" = "$server_hash" ]; then
        echo "  ${GREEN}✅ 一致${NC} (哈希: ${local_hash:0:8}...)${NC}"
        return 0
    else
        echo "  ${RED}❌ 不一致${NC}"
        echo "    本地: ${local_hash:0:8}..."
        echo "    服务器: ${server_hash:0:8}..."
        INCONSISTENT_FILES+=("$file_path")
        return 1
    fi
}

# 检查关键内容
check_content() {
    local file_path=$1
    local pattern=$2
    local desc=$3
    local node=$4
    
    echo "【检查】$desc"
    
    # 本地检查
    local local_count=$(grep -c "$pattern" "$file_path" 2>/dev/null || echo "0")
    
    # 服务器检查
    local server_count="0"
    if [ "$node" = "node1" ]; then
        server_count=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE1_IP "grep -c '$pattern' $PROJECT_DIR/$file_path 2>/dev/null || echo '0'" 2>/dev/null || echo "0")
    elif [ "$node" = "node2" ]; then
        server_count=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE2_IP "grep -c '$pattern' $PROJECT_DIR/$file_path 2>/dev/null || echo '0'" 2>/dev/null || echo "0")
    fi
    
    if [ "$local_count" = "$server_count" ]; then
        echo "  ${GREEN}✅ 一致${NC} (匹配数: $local_count)${NC}"
        return 0
    else
        echo "  ${RED}❌ 不一致${NC}"
        echo "    本地: $local_count 个匹配"
        echo "    服务器: $server_count 个匹配"
        INCONSISTENT_FILES+=("$file_path ($desc)")
        return 1
    fi
}

# 检查 Git 版本
check_git_version() {
    echo "【检查】Git 版本一致性"
    
    local local_commit=$(git rev-parse HEAD 2>/dev/null || echo "")
    local node1_commit=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE1_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" 2>/dev/null || echo "")
    local node2_commit=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE2_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" 2>/dev/null || echo "")
    
    if [ -z "$local_commit" ]; then
        echo "  ${YELLOW}⚠️  本地无法获取 Git 版本${NC}"
        return 1
    fi
    
    echo "  本地: ${local_commit:0:8}"
    echo "  Node1: ${node1_commit:0:8}"
    echo "  Node2: ${node2_commit:0:8}"
    
    if [ "$local_commit" = "$node1_commit" ] && [ "$local_commit" = "$node2_commit" ]; then
        echo "  ${GREEN}✅ Git 版本一致${NC}"
        return 0
    else
        echo "  ${RED}❌ Git 版本不一致${NC}"
        INCONSISTENT_FILES+=("Git版本")
        return 1
    fi
}

# 主检查流程
echo "【1/4】检查 Git 版本一致性"
check_git_version
echo ""

echo "【2/4】检查关键文件一致性（Node1）"
for check in "${CHECKS[@]}"; do
    file_path=$(echo $check | cut -d':' -f1)
    file_desc=$(echo $check | cut -d':' -f2)
    check_file "$file_path" "$file_desc" "node1"
done
echo ""

echo "【3/4】检查关键内容一致性（Node1）"
check_content "server/api/grpc_gateway.py" "/Users/zhoudt" "硬编码路径检查" "node1"
check_content "server/api/v2/desk_fengshui_api.py" "/Users/zhoudt" "硬编码路径检查" "node1"
check_content "proto/generated/bazi_core_pb2_grpc.py" "add_registered_method_handlers" "gRPC兼容性检查" "node1"
check_content "deploy/docker/docker-compose.prod.yml" "proto:/app/proto" "容器挂载检查" "node1"
echo ""

echo "【4/4】检查容器内代码一致性（Node1）"
echo "【检查】容器内 gRPC 代码"
container_count=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE1_IP "docker exec hifate-bazi-core grep -c 'add_registered_method_handlers' /app/proto/generated/bazi_core_pb2_grpc.py 2>/dev/null || echo '0'" 2>/dev/null || echo "0")
if [ "$container_count" = "0" ]; then
    echo "  ${GREEN}✅ 容器内代码已修复（0 个问题代码）${NC}"
else
    echo "  ${RED}❌ 容器内仍有 $container_count 个问题代码${NC}"
    INCONSISTENT_FILES+=("容器内gRPC代码")
fi

echo ""
echo "========================================"
echo "📊 检查结果汇总"
echo "========================================"

if [ ${#INCONSISTENT_FILES[@]} -eq 0 ]; then
    echo "${GREEN}✅ 所有检查通过，代码完全一致！${NC}"
    exit 0
else
    echo "${RED}❌ 发现 ${#INCONSISTENT_FILES[@]} 处不一致：${NC}"
    for file in "${INCONSISTENT_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "${YELLOW}💡 建议：${NC}"
    echo "  1. 检查本地代码是否已提交到 Git"
    echo "  2. 检查服务器代码是否已拉取最新版本"
    echo "  3. 运行修复脚本：bash scripts/grpc/fix_grpc_generated_code.py"
    echo "  4. 重启容器以应用新配置"
    exit 1
fi
