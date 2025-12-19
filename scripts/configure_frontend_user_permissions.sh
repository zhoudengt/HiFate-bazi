#!/bin/bash
# 配置 frontend-user 权限：只能访问 /opt/hifate-frontend
# 使用：bash scripts/configure_frontend_user_permissions.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
FRONTEND_USER="frontend-user"
FRONTEND_DIR="/opt/hifate-frontend"
PROJECT_DIR="/opt/HiFate-bazi"

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

configure_node() {
    local host=$1
    local node_name=$2
    
    echo "🔧 配置 $node_name ($host) 的 frontend-user 权限..."
    echo "----------------------------------------"
    
    # 1. 检查 frontend-user 是否存在
    if ! ssh_exec $host "id $FRONTEND_USER" 2>/dev/null; then
        echo "⚠️  frontend-user 用户不存在，创建用户..."
        ssh_exec $host "useradd -m -s /bin/bash $FRONTEND_USER" 2>/dev/null || echo "   用户可能已存在"
    else
        echo "✅ frontend-user 用户已存在"
    fi
    
    # 2. 创建 /opt/hifate-frontend 目录（如果不存在）
    echo ""
    echo "1. 创建/检查 $FRONTEND_DIR 目录..."
    ssh_exec $host "mkdir -p $FRONTEND_DIR"
    echo "   ✅ 目录已创建/存在"
    
    # 3. 设置 /opt/hifate-frontend 目录权限（775: rwxrwxr-x）
    echo ""
    echo "2. 设置 $FRONTEND_DIR 目录权限..."
    ssh_exec $host "chmod 775 $FRONTEND_DIR"
    ssh_exec $host "chown root:root $FRONTEND_DIR"
    
    # 使用 ACL 给 frontend-user 完整权限（推荐方案）
    echo ""
    echo "3. 使用 ACL 给 frontend-user 完整权限..."
    if ssh_exec $host "which setfacl" 2>/dev/null; then
        ssh_exec $host "setfacl -R -m u:$FRONTEND_USER:rwx $FRONTEND_DIR" 2>/dev/null || true
        ssh_exec $host "setfacl -R -d -m u:$FRONTEND_USER:rwx $FRONTEND_DIR" 2>/dev/null || true
        echo "   ✅ ACL 权限已设置"
    else
        echo "   ⚠️  setfacl 不可用，使用组权限方案..."
        ssh_exec $host "groupadd -f hifate-frontend-group" 2>/dev/null || true
        ssh_exec $host "usermod -a -G hifate-frontend-group $FRONTEND_USER" 2>/dev/null || true
        ssh_exec $host "chgrp -R hifate-frontend-group $FRONTEND_DIR" 2>/dev/null || true
        ssh_exec $host "chmod -R 775 $FRONTEND_DIR"
        echo "   ✅ 组权限已设置"
    fi
    
    # 4. 设置 /opt 目录权限（751: drwxr-x--x）
    # 允许执行（进入）但不允许列出内容
    echo ""
    echo "4. 设置 /opt 目录权限（751: 允许执行但不允许列出）..."
    ssh_exec $host "chmod 751 /opt"
    ssh_exec $host "chown root:root /opt"
    echo "   ✅ /opt 权限已设置为 751"
    
    # 5. 设置 /opt/HiFate-bazi 目录权限（750: drwxr-x---）
    # 完全禁止其他用户访问
    echo ""
    echo "5. 禁止 frontend-user 访问 $PROJECT_DIR..."
    if ssh_exec $host "test -d $PROJECT_DIR" 2>/dev/null; then
        ssh_exec $host "chmod 750 $PROJECT_DIR"
        ssh_exec $host "chown root:root $PROJECT_DIR"
        
        # 递归设置子目录权限（只设置目录，不改变文件权限，避免影响服务）
        ssh_exec $host "find $PROJECT_DIR -type d -exec chmod 750 {} \\; 2>/dev/null || true"
        echo "   ✅ $PROJECT_DIR 权限已设置为 750"
    else
        echo "   ⚠️  $PROJECT_DIR 不存在，跳过"
    fi
    
    # 6. 禁止访问 /opt 下的其他目录
    echo ""
    echo "6. 设置 /opt 下其他目录的权限..."
    ssh_exec $host "find /opt -maxdepth 1 -type d ! -path /opt ! -path $FRONTEND_DIR -exec chmod 750 {} \\; 2>/dev/null || true"
    ssh_exec $host "find /opt -maxdepth 1 -type d ! -path /opt ! -path $FRONTEND_DIR -exec chown root:root {} \\; 2>/dev/null || true"
    echo "   ✅ 其他目录权限已设置"
    
    # 7. 验证权限
    echo ""
    echo "7. 验证权限设置..."
    
    # 验证 /opt/hifate-frontend 权限
    PERM=$(ssh_exec $host "stat -c '%a' $FRONTEND_DIR" 2>/dev/null || echo "")
    echo "   $FRONTEND_DIR 权限: $PERM"
    
    # 验证 frontend-user 可以访问 /opt/hifate-frontend
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -r $FRONTEND_DIR && test -w $FRONTEND_DIR && test -x $FRONTEND_DIR'" 2>/dev/null; then
        echo "   ✅ frontend-user 可以读写执行 $FRONTEND_DIR"
    else
        echo "   ❌ frontend-user 无法访问 $FRONTEND_DIR"
    fi
    
    # 验证 frontend-user 无法访问 /opt/HiFate-bazi
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -r $PROJECT_DIR'" 2>/dev/null; then
        echo "   ❌ frontend-user 仍然可以访问 $PROJECT_DIR（需要修复）"
    else
        echo "   ✅ frontend-user 无法访问 $PROJECT_DIR"
    fi
    
    echo ""
}

echo "=========================================="
echo "配置 frontend-user 权限"
echo "=========================================="
echo ""
echo "目标："
echo "  - frontend-user 只能访问 $FRONTEND_DIR（读写执行）"
echo "  - frontend-user 无法访问 $PROJECT_DIR"
echo "  - frontend-user 无法看到 /opt 下的其他目录"
echo ""

# 配置 Node1
configure_node $NODE1_PUBLIC_IP "Node1"

# 配置 Node2
configure_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "完成"
echo "=========================================="
echo "✅ frontend-user 权限配置完成"
echo ""
echo "权限总结："
echo "  - /opt/hifate-frontend: 775 (rwxrwxr-x) + ACL/组权限"
echo "  - /opt: 751 (drwxr-x--x) - 允许执行但不允许列出"
echo "  - /opt/HiFate-bazi: 750 (drwxr-x---) - 完全禁止其他用户访问"
echo "  - /opt 下其他目录: 750 - 禁止其他用户访问"
echo ""

