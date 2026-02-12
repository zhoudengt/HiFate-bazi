#!/bin/bash
# 保护服务器上的 frontend 目录不被 Git 删除
# 通过将 frontend 目录添加到 .gitignore 实现

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
echo "保护服务器 frontend 目录"
echo "=========================================="
echo ""

# 在 .gitignore 中添加 frontend/（如果还没有）
if grep -q "^frontend/$" .gitignore 2>/dev/null; then
    echo "✅ 本地 .gitignore 已包含 frontend/"
else
    echo "📝 在本地 .gitignore 中添加 frontend/..."
    echo "" >> .gitignore
    echo "# Frontend directories" >> .gitignore
    echo "# 注意：frontend 目录已重命名为 local_frontend" >> .gitignore
    echo "# 但为了保护服务器上可能存在的 frontend 目录不被 Git 删除，添加到 .gitignore" >> .gitignore
    echo "frontend/" >> .gitignore
    echo "✅ 已添加到本地 .gitignore"
fi

# 在服务器上也添加 frontend/ 到 .gitignore
echo ""
echo "📝 在 Node1 的 .gitignore 中添加 frontend/..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
    if ! grep -q '^frontend/$' .gitignore 2>/dev/null; then
        echo '' >> .gitignore && \
        echo '# Frontend directories' >> .gitignore && \
        echo '# 注意：frontend 目录已重命名为 local_frontend' >> .gitignore && \
        echo '# 但为了保护服务器上可能存在的 frontend 目录不被 Git 删除，添加到 .gitignore' >> .gitignore && \
        echo 'frontend/' >> .gitignore && \
        echo '✅ Node1: 已添加到 .gitignore'
    else
        echo '✅ Node1: .gitignore 已包含 frontend/'
    fi"

echo ""
echo "📝 在 Node2 的 .gitignore 中添加 frontend/..."
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
    if ! grep -q '^frontend/$' .gitignore 2>/dev/null; then
        echo '' >> .gitignore && \
        echo '# Frontend directories' >> .gitignore && \
        echo '# 注意：frontend 目录已重命名为 local_frontend' >> .gitignore && \
        echo '# 但为了保护服务器上可能存在的 frontend 目录不被 Git 删除，添加到 .gitignore' >> .gitignore && \
        echo 'frontend/' >> .gitignore && \
        echo '✅ Node2: 已添加到 .gitignore'
    else
        echo '✅ Node2: .gitignore 已包含 frontend/'
    fi"

echo ""
echo "=========================================="
echo "验证 frontend 目录保护"
echo "=========================================="

# 验证 Node1
if ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git check-ignore frontend/" 2>/dev/null; then
    echo "✅ Node1: frontend 目录已被 Git 忽略（不会被删除）"
else
    echo "⚠️  Node1: frontend 目录未被 Git 忽略（如果目录不存在，可能无法检查）"
fi

# 验证 Node2
if ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git check-ignore frontend/" 2>/dev/null; then
    echo "✅ Node2: frontend 目录已被 Git 忽略（不会被删除）"
else
    echo "⚠️  Node2: frontend 目录未被 Git 忽略（如果目录不存在，可能无法检查）"
fi

echo ""
echo "=========================================="
echo "完成"
echo "=========================================="
echo "✅ frontend 目录已被添加到 .gitignore"
echo "⚠️  注意：如果 frontend 目录已经在 Git 跟踪中，需要先从 Git 中移除："
echo "   git rm -r --cached frontend/"
echo "   然后提交更改"
echo ""

