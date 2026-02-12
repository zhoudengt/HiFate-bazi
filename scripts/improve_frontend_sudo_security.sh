#!/bin/bash
# 改进 frontend-user sudo 权限安全性
# 将 (ALL) 改为 (root)，限制只能以 root 身份执行
# 使用：bash scripts/improve_frontend_sudo_security.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_USER="frontend-user"
SUDOERS_FILE="/etc/sudoers.d/frontend-docker"
DOCKER_WRAPPER="/usr/local/bin/docker-frontend"

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

improve_node() {
    local host=$1
    local node_name=$2
    
    echo "🔒 在 $node_name ($host) 上改进 sudo 权限安全性..."
    echo "=========================================="
    
    # 检查当前配置
    echo ""
    echo "📋 当前 sudo 配置："
    CURRENT_CONFIG=$(ssh_exec $host "cat $SUDOERS_FILE 2>/dev/null" || echo "")
    echo "$CURRENT_CONFIG"
    
    # 检查是否已经是 (root)
    if echo "$CURRENT_CONFIG" | grep -q "(root)"; then
        echo ""
        echo "✅ 已经是安全配置（(root)），无需修改"
        return 0
    fi
    
    # 备份当前配置
    echo ""
    echo "📦 备份当前配置..."
    ssh_exec $host "cp $SUDOERS_FILE ${SUDOERS_FILE}.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    
    # 创建改进后的配置
    echo ""
    echo "🔧 创建改进后的配置..."
    ssh_exec $host "cat > $SUDOERS_FILE << 'EOFSUDO'
# frontend-user Docker 受限权限配置（安全改进版）
# 只允许使用包装脚本 docker-frontend
# 限制只能以 root 身份执行（更安全）
frontend-user ALL=(root) NOPASSWD: $DOCKER_WRAPPER
Defaults:frontend-user !requiretty
EOFSUDO
" 2>/dev/null || {
        echo "      ❌ 创建 sudoers 文件失败"
        return 1
    }
    
    # 设置文件权限
    ssh_exec $host "chmod 0440 $SUDOERS_FILE" 2>/dev/null || true
    
    # 验证语法
    echo ""
    echo "✅ 验证 sudoers 文件语法..."
    SUDOERS_CHECK=$(ssh_exec $host "visudo -c -f $SUDOERS_FILE 2>&1" || echo "")
    if echo "$SUDOERS_CHECK" | grep -qE "(syntax OK|parsed OK)"; then
        echo "      ✅ sudoers 文件语法正确"
    else
        echo "      ❌ sudoers 文件语法错误"
        echo "      $SUDOERS_CHECK"
        # 恢复备份
        echo "      🔄 恢复备份配置..."
        ssh_exec $host "cp ${SUDOERS_FILE}.backup.* $SUDOERS_FILE" 2>/dev/null || true
        return 1
    fi
    
    # 验证新配置
    echo ""
    echo "✅ 验证新配置..."
    NEW_CONFIG=$(ssh_exec $host "sudo -l -U $FRONTEND_USER 2>/dev/null | grep docker-frontend" || echo "")
    if echo "$NEW_CONFIG" | grep -q "(root)"; then
        echo "      ✅ 新配置已生效：限制只能以 root 身份执行"
        echo "      $NEW_CONFIG"
    else
        echo "      ⚠️  配置可能未生效，请检查"
        echo "      $NEW_CONFIG"
    fi
    
    echo ""
    echo "✅ $node_name 配置完成"
    echo ""
}

echo "=========================================="
echo "改进 frontend-user sudo 权限安全性（双机）"
echo "=========================================="
echo ""
echo "改进内容："
echo "  - 将 sudo 配置从 (ALL) 改为 (root)"
echo "  - 限制只能以 root 身份执行 docker-frontend"
echo "  - 更符合最小权限原则"
echo ""
echo "⚠️  注意："
echo "  - 不会影响现有功能（脚本本身需要 root 权限）"
echo "  - 会自动备份当前配置"
echo ""

# 改进 Node1
improve_node $NODE1_PUBLIC_IP "Node1"

# 改进 Node2
improve_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 改进完成"
echo "=========================================="
echo ""
echo "改进内容："
echo "  ✅ sudo 配置从 (ALL) 改为 (root)"
echo "  ✅ 限制只能以 root 身份执行"
echo "  ✅ 更符合最小权限原则"
echo ""
echo "验证命令："
echo "  sudo -l -U frontend-user"
echo "  应该显示：(root) NOPASSWD: /usr/local/bin/docker-frontend"
echo ""

