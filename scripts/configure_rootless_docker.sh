#!/bin/bash
# 配置 Rootless Docker 环境
# 使用：bash scripts/configure_rootless_docker.sh

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

configure_node() {
    local host=$1
    local node_name=$2
    
    echo "=========================================="
    echo "在 $node_name ($host) 上配置 Rootless Docker"
    echo "=========================================="
    
    # 1. 配置环境变量
    echo ""
    echo "1. 配置环境变量..."
    
    # 检查 .bashrc 是否存在
    if ssh_exec $host "su - $FRONTEND_USER -c 'test -f ~/.bashrc' 2>/dev/null" 2>/dev/null; then
        # 检查是否已配置
        if ssh_exec $host "su - $FRONTEND_USER -c 'grep -q DOCKER_HOST ~/.bashrc' 2>/dev/null" 2>/dev/null; then
            echo "   ⚠️  环境变量已配置，跳过"
        else
            # 添加环境变量
            ssh_exec $host "su - $FRONTEND_USER -c 'cat >> ~/.bashrc << \"ENVEOF\"

# Docker Rootless 环境变量
export XDG_RUNTIME_DIR=\$HOME/.docker/run
export PATH=\$HOME/bin:\$PATH
export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock
ENVEOF
' 2>/dev/null" || {
                echo "   ❌ 配置环境变量失败"
                return 1
            }
            echo "   ✅ 环境变量已添加到 ~/.bashrc"
        fi
    else
        # 创建 .bashrc
        ssh_exec $host "su - $FRONTEND_USER -c 'cat > ~/.bashrc << \"ENVEOF\"
# Docker Rootless 环境变量
export XDG_RUNTIME_DIR=\$HOME/.docker/run
export PATH=\$HOME/bin:\$PATH
export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock
ENVEOF
' 2>/dev/null" || {
            echo "   ❌ 创建 .bashrc 失败"
            return 1
        }
        echo "   ✅ 已创建 ~/.bashrc 并配置环境变量"
    fi
    
    # 2. 配置 systemd user service
    echo ""
    echo "2. 配置 systemd user service..."
    
    # 创建 systemd user 目录
    ssh_exec $host "su - $FRONTEND_USER -c 'mkdir -p ~/.config/systemd/user' 2>/dev/null" || true
    
    # 创建 docker.service 文件
    ssh_exec $host "su - $FRONTEND_USER -c 'cat > ~/.config/systemd/user/docker.service << \"SERVICEEOF\"
[Unit]
Description=Docker Rootless Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=%h/bin/dockerd-rootless.sh
Restart=on-failure
RestartSec=5s
TimeoutStartSec=0
Delegate=yes
KillMode=mixed

[Install]
WantedBy=default.target
SERVICEEOF
' 2>/dev/null" || {
        echo "   ❌ 创建 systemd service 文件失败"
        return 1
    }
    echo "   ✅ systemd service 文件已创建"
    
    # 3. 启用 linger（允许用户服务在用户未登录时运行）
    echo ""
    echo "3. 启用 linger（允许用户服务在用户未登录时运行）..."
    ssh_exec $host "loginctl enable-linger $FRONTEND_USER" 2>/dev/null || {
        echo "   ⚠️  启用 linger 失败（可能需要手动执行）"
    }
    echo "   ✅ linger 已启用"
    
    # 4. 启用并启动服务
    echo ""
    echo "4. 启用并启动 Rootless Docker 服务..."
    
    # 重新加载 systemd user daemon
    ssh_exec $host "su - $FRONTEND_USER -c 'systemctl --user daemon-reload' 2>/dev/null" || {
        echo "   ⚠️  daemon-reload 失败，尝试手动启动"
    }
    
    # 启用服务
    ssh_exec $host "su - $FRONTEND_USER -c 'systemctl --user enable docker' 2>/dev/null" || {
        echo "   ⚠️  启用服务失败"
    }
    
    # 启动服务
    echo "   启动服务..."
    START_OUTPUT=$(ssh_exec $host "su - $FRONTEND_USER -c 'systemctl --user start docker' 2>&1" || echo "启动失败")
    
    if echo "$START_OUTPUT" | grep -q "error\|Error\|ERROR\|失败"; then
        echo "   ⚠️  启动失败，尝试手动启动"
        echo "   输出: $START_OUTPUT"
        # 尝试手动启动
        ssh_exec $host "su - $FRONTEND_USER -c 'nohup \$HOME/bin/dockerd-rootless.sh > /tmp/dockerd-rootless.log 2>&1 &' 2>/dev/null" || true
        sleep 3
    else
        echo "   ✅ 服务已启动"
    fi
    
    # 5. 验证服务状态
    echo ""
    echo "5. 验证服务状态..."
    sleep 2
    
    SERVICE_STATUS=$(ssh_exec $host "su - $FRONTEND_USER -c 'systemctl --user status docker 2>&1 | head -5' || echo '无法检查状态'" || echo "无法检查")
    echo "   $SERVICE_STATUS"
    
    # 6. 验证 Docker 可用性
    echo ""
    echo "6. 验证 Docker 可用性..."
    
    # 设置环境变量并测试
    DOCKER_TEST=$(ssh_exec $host "su - $FRONTEND_USER -c 'export XDG_RUNTIME_DIR=\$HOME/.docker/run && export PATH=\$HOME/bin:\$PATH && export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock && docker version --format \"{{.Server.Version}}\" 2>&1' 2>/dev/null" || echo "无法连接")
    
    if echo "$DOCKER_TEST" | grep -qE "^[0-9]+\.[0-9]+\.[0-9]+"; then
        echo "   ✅ Docker 可用，版本: $DOCKER_TEST"
    else
        echo "   ⚠️  Docker 可能未完全启动，等待几秒后重试..."
        sleep 5
        DOCKER_TEST2=$(ssh_exec $host "su - $FRONTEND_USER -c 'export XDG_RUNTIME_DIR=\$HOME/.docker/run && export PATH=\$HOME/bin:\$PATH && export DOCKER_HOST=unix://\$HOME/.docker/run/docker.sock && docker version --format \"{{.Server.Version}}\" 2>&1' 2>/dev/null" || echo "无法连接")
        if echo "$DOCKER_TEST2" | grep -qE "^[0-9]+\.[0-9]+\.[0-9]+"; then
            echo "   ✅ Docker 可用，版本: $DOCKER_TEST2"
        else
            echo "   ⚠️  Docker 可能未启动，请检查日志"
            echo "   日志: /tmp/dockerd-rootless.log"
        fi
    fi
    
    echo ""
    echo "✅ $node_name 配置完成"
    echo ""
}

echo "=========================================="
echo "配置 Rootless Docker 环境（双机）"
echo "=========================================="
echo ""
echo "功能："
echo "  - 配置环境变量（DOCKER_HOST, PATH）"
echo "  - 配置 systemd user service"
echo "  - 启动 Rootless Docker 服务"
echo ""

# 配置 Node1
configure_node $NODE1_PUBLIC_IP "Node1"

# 配置 Node2
configure_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "✅ 配置完成"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 清理旧配置: bash scripts/cleanup_old_docker_config.sh"
echo "  2. 配置网络: bash scripts/configure_rootless_network.sh"
echo ""

