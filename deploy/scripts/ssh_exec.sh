#!/bin/bash
# SSH 执行脚本（支持密码认证）
# 使用：bash ssh_exec.sh <host> <command>

set -e

HOST=$1
COMMAND=$2
SSH_PASSWORD="Yuanqizhan@163"

if [ -z "$HOST" ] || [ -z "$COMMAND" ]; then
    echo "用法: $0 <host> <command>"
    exit 1
fi

# 尝试使用 sshpass
if command -v sshpass &> /dev/null; then
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$HOST "$COMMAND"
# 尝试使用 expect
elif command -v expect &> /dev/null; then
    expect << EOF
set timeout 30
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$HOST "$COMMAND"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    "Password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
else
    echo "错误: 需要安装 sshpass 或 expect"
    echo "macOS: brew install hudochenkov/sshpass/sshpass"
    echo "或: brew install expect"
    exit 1
fi
