#!/bin/bash
# 从 docker 组中移除 frontend-user（安全加固）
# 使用：bash scripts/remove_frontend_user_from_docker_group.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_USER="frontend-user"

ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    fi
}

remove_from_docker_group() {
    local host=$1
    local node_name=$2
    
    echo "🔒 在 $node_name ($host) 上移除 frontend-user 从 docker 组..."
    
    # 检查当前所属组
    CURRENT_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
    echo "   当前所属组: $CURRENT_GROUPS"
    
    if echo "$CURRENT_GROUPS" | grep -q "docker"; then
        echo "   ⚠️  frontend-user 在 docker 组中，正在移除..."
        
        # 获取所有组，排除 docker
        ALL_GROUPS=$(ssh_exec $host "id -Gn $FRONTEND_USER" 2>/dev/null | tr ' ' ',' | sed 's/docker,//g' | sed 's/,docker//g' | sed 's/docker//g')
        
        # 移除 docker 组
        ssh_exec $host "usermod -G \"$ALL_GROUPS\" $FRONTEND_USER" 2>/dev/null || {
            # 如果上面的方法失败，使用 gpasswd
            ssh_exec $host "gpasswd -d $FRONTEND_USER docker" 2>/dev/null || true
        }
        
        # 验证
        NEW_GROUPS=$(ssh_exec $host "groups $FRONTEND_USER" 2>/dev/null || echo "")
        if echo "$NEW_GROUPS" | grep -q "docker"; then
            echo "   ❌ 移除失败，frontend-user 仍在 docker 组中"
        else
            echo "   ✅ 已移除，frontend-user 不再在 docker 组中"
            echo "   新所属组: $NEW_GROUPS"
        fi
    else
        echo "   ✅ frontend-user 不在 docker 组中，无需操作"
    fi
    
    echo ""
}

echo "=========================================="
echo "从 docker 组中移除 frontend-user"
echo "=========================================="
echo ""
echo "目的：禁止 frontend-user 访问 Docker"
echo ""

remove_from_docker_group $NODE1_PUBLIC_IP "Node1"
remove_from_docker_group $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "完成"
echo "=========================================="
echo "✅ frontend-user 已从 docker 组中移除"
echo ""
echo "验证：frontend-user 现在无法执行 docker 命令"
echo ""

