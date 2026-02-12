#!/bin/bash
# 恢复服务器上的 frontend 目录
# 注意：如果 frontend 目录有重要数据，需要先从备份或 Git 历史中恢复

set -e

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
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

echo "=========================================="
echo "恢复服务器 frontend 目录"
echo "=========================================="
echo ""
echo "⚠️  警告：此操作将从 Git 历史中恢复 frontend 目录"
echo "⚠️  如果服务器上的 frontend 目录有本地修改，这些修改可能会丢失"
echo ""

read -p "是否继续？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 1
fi

# 恢复方案: 从 local_frontend 复制创建 frontend 目录
echo ""
echo "从 local_frontend 复制创建 frontend 目录"
echo "--------------------------------------------------------"

# 在 Node1 上恢复
echo ""
echo "📥 在 Node1 上从 local_frontend 复制创建 frontend 目录..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
    if [ -d local_frontend ]; then \
        if [ -d frontend ]; then \
            echo '⚠️  Node1: frontend 目录已存在，备份为 frontend.backup.$(date +%s)' && \
            mv frontend frontend.backup.\$(date +%s); \
        fi && \
        cp -r local_frontend frontend && \
        echo '✅ Node1: frontend 目录已从 local_frontend 复制' && \
        echo '   文件数量: \$(find frontend -type f | wc -l)'; \
    else \
        echo '❌ Node1: local_frontend 目录不存在，无法复制'; \
        exit 1; \
    fi"

# 在 Node2 上恢复（如果目录为空或不存在）
echo ""
echo "📥 在 Node2 上检查并恢复 frontend 目录..."
FRONTEND_FILE_COUNT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && find frontend -type f 2>/dev/null | wc -l" 2>/dev/null || echo "0")
if [ "$FRONTEND_FILE_COUNT" -lt 10 ]; then
    echo "⚠️  Node2: frontend 目录存在但文件较少（$FRONTEND_FILE_COUNT 个文件），从 local_frontend 复制..."
    ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
        if [ -d local_frontend ]; then \
            if [ -d frontend ]; then \
                echo '⚠️  Node2: frontend 目录已存在，备份为 frontend.backup.$(date +%s)' && \
                mv frontend frontend.backup.\$(date +%s); \
            fi && \
            cp -r local_frontend frontend && \
            echo '✅ Node2: frontend 目录已从 local_frontend 复制' && \
            echo '   文件数量: \$(find frontend -type f | wc -l)'; \
        else \
            echo '❌ Node2: local_frontend 目录不存在，无法复制'; \
        fi"
else
    echo "✅ Node2: frontend 目录已存在且有文件（$FRONTEND_FILE_COUNT 个文件），跳过恢复"
fi

echo ""
echo "=========================================="
echo "验证恢复结果"
echo "=========================================="

# 验证 Node1
if ssh_exec $NODE1_PUBLIC_IP "test -d $PROJECT_DIR/frontend" 2>/dev/null; then
    echo "✅ Node1: frontend 目录已恢复"
    echo "   文件数量: $(ssh_exec $NODE1_PUBLIC_IP "find $PROJECT_DIR/frontend -type f | wc -l" 2>/dev/null)"
else
    echo "❌ Node1: frontend 目录恢复失败"
fi

# 验证 Node2
if ssh_exec $NODE2_PUBLIC_IP "test -d $PROJECT_DIR/frontend" 2>/dev/null; then
    echo "✅ Node2: frontend 目录已恢复"
    echo "   文件数量: $(ssh_exec $NODE2_PUBLIC_IP "find $PROJECT_DIR/frontend -type f | wc -l" 2>/dev/null)"
else
    echo "❌ Node2: frontend 目录恢复失败"
fi

echo ""
echo "=========================================="
echo "重要提示"
echo "=========================================="
echo "⚠️  如果 frontend 目录需要保留，建议："
echo "   1. 将 frontend 目录添加到 .gitignore（防止被 Git 删除）"
echo "   2. 或者将 frontend 目录添加到 Git 仓库（如果需要版本控制）"
echo "   3. 或者创建一个符号链接：ln -s local_frontend frontend"
echo ""

