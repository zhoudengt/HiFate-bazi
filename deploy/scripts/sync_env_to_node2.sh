#!/bin/bash
# -*- coding: utf-8 -*-
"""
同步 Node1 的 .env 配置文件到 Node2
用途：确保双机配置一致，特别是 Bot ID 等配置
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
ENV_FILE="$PROJECT_DIR/.env"

# SSH 密码（从环境变量或默认值读取）
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# SSH 执行函数（支持密码登录）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        # 如果没有 sshpass，尝试使用 expect（如果可用）
        if command -v expect &> /dev/null; then
            expect << EOF
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
        else
            # 如果都没有，尝试直接 SSH（可能需要手动输入密码或已配置密钥）
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
        fi
    fi
}

# SCP 上传函数
scp_upload() {
    local host=$1
    local local_file=$2
    local remote_file=$3
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$local_file" root@$host:"$remote_file"
    else
        # 如果没有 sshpass，尝试使用 expect
        if command -v expect &> /dev/null; then
            expect << EOF
spawn scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$local_file" root@$host:"$remote_file"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
        else
            # 如果都没有，尝试直接 SCP
            scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$local_file" root@$host:"$remote_file"
        fi
    fi
}

echo "========================================"
echo "🔄 同步 Node1 配置到 Node2"
echo "========================================"
echo ""

# 步骤 1: 检查 Node1 的 .env 文件是否存在
echo "步骤 1: 检查 Node1 的 .env 文件..."
if ! ssh_exec $NODE1_PUBLIC_IP "test -f $ENV_FILE"; then
    echo -e "${RED}错误：Node1 的 .env 文件不存在: $ENV_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node1 的 .env 文件存在${NC}"
echo ""

# 步骤 2: 从 Node1 下载 .env 文件到本地临时文件
echo "步骤 2: 从 Node1 下载 .env 文件..."
TEMP_ENV_FILE="/tmp/node1_env_$(date +%s).env"
if command -v sshpass &> /dev/null; then
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE1_PUBLIC_IP:$ENV_FILE "$TEMP_ENV_FILE"
elif command -v expect &> /dev/null; then
    expect << EOF
spawn scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE1_PUBLIC_IP:$ENV_FILE "$TEMP_ENV_FILE"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
else
    scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE1_PUBLIC_IP:$ENV_FILE "$TEMP_ENV_FILE"
fi

if [ ! -f "$TEMP_ENV_FILE" ]; then
    echo -e "${RED}错误：下载 .env 文件失败${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 已下载 .env 文件到本地${NC}"
echo ""

# 步骤 3: 备份 Node2 的现有 .env 文件（如果存在）
echo "步骤 3: 备份 Node2 的现有 .env 文件..."
if ssh_exec $NODE2_PUBLIC_IP "test -f $ENV_FILE"; then
    BACKUP_FILE="${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    ssh_exec $NODE2_PUBLIC_IP "cp $ENV_FILE $BACKUP_FILE"
    echo -e "${GREEN}✓ 已备份到: $BACKUP_FILE${NC}"
else
    echo -e "${YELLOW}⚠ Node2 的 .env 文件不存在，将创建新文件${NC}"
fi
echo ""

# 步骤 4: 上传 .env 文件到 Node2
echo "步骤 4: 上传 .env 文件到 Node2..."
scp_upload $NODE2_PUBLIC_IP "$TEMP_ENV_FILE" "$ENV_FILE"
echo -e "${GREEN}✓ 已上传 .env 文件到 Node2${NC}"
echo ""

# 步骤 5: 验证 Node2 的 .env 文件
echo "步骤 5: 验证 Node2 的 .env 文件..."
if ssh_exec $NODE2_PUBLIC_IP "test -f $ENV_FILE"; then
    echo -e "${GREEN}✓ Node2 的 .env 文件存在${NC}"
    
    # 显示关键配置项（不显示敏感信息）
    echo ""
    echo "关键配置项（Node2）："
    ssh_exec $NODE2_PUBLIC_IP "grep -E '^[A-Z_]+.*BOT_ID|^COZE_ACCESS_TOKEN' $ENV_FILE | sed 's/=.*/=***/' || true"
else
    echo -e "${RED}错误：Node2 的 .env 文件不存在${NC}"
    exit 1
fi
echo ""

# 步骤 6: 清理临时文件
echo "步骤 6: 清理临时文件..."
rm -f "$TEMP_ENV_FILE"
echo -e "${GREEN}✓ 临时文件已清理${NC}"
echo ""

# 步骤 7: 提示是否需要重启服务
echo "========================================"
echo -e "${GREEN}配置同步完成！${NC}"
echo "========================================"
echo ""
echo "⚠️  重要提示："
echo "1. 如果修改了 Bot ID 等配置，需要重启相关服务才能生效"
echo "2. 重启命令："
echo "   ssh root@$NODE2_PUBLIC_IP \"cd $PROJECT_DIR/deploy/docker && \\"
echo "       docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \\"
echo "       --env-file $ENV_FILE up -d --force-recreate web intent-service\""
echo ""
echo "3. 或者重启所有服务："
echo "   ssh root@$NODE2_PUBLIC_IP \"cd $PROJECT_DIR/deploy/docker && \\"
echo "       docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \\"
echo "       --env-file $ENV_FILE restart\""
echo ""

