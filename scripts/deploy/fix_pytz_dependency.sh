#!/bin/bash
# 彻底修复pytz依赖问题
# 方案1：等待GitHub Actions构建完成后拉取新镜像（推荐）
# 方案2：在服务器上手动重建镜像（快速方案）

set -e

NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
}

echo "=========================================="
echo "   彻底修复pytz依赖问题"
echo "=========================================="
echo ""
echo "请选择修复方案："
echo "1. 等待GitHub Actions构建完成后拉取新镜像（推荐，标准流程）"
echo "2. 在服务器上手动重建镜像（快速方案，需要10-15分钟）"
echo ""
read -p "请选择 (1/2): " choice

case $choice in
    1)
        echo ""
        echo "📋 方案1：等待GitHub Actions构建"
        echo "----------------------------------------"
        echo "1. GitHub Actions会自动构建新镜像（包含pytz验证）"
        echo "2. 构建完成后，执行以下命令拉取新镜像："
        echo ""
        echo "   # Node1"
        echo "   ssh root@$NODE1_IP 'cd /opt/HiFate-bazi/deploy/docker && \\"
        echo "     source /opt/HiFate-bazi/.env && \\"
        echo "     docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \\"
        echo "     --env-file /opt/HiFate-bazi/.env pull && \\"
        echo "     docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \\"
        echo "     --env-file /opt/HiFate-bazi/.env up -d --force-recreate'"
        echo ""
        echo "   # Node2"
        echo "   ssh root@$NODE2_IP 'cd /opt/HiFate-bazi/deploy/docker && \\"
        echo "     source /opt/HiFate-bazi/.env && \\"
        echo "     docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \\"
        echo "     --env-file /opt/HiFate-bazi/.env pull && \\"
        echo "     docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \\"
        echo "     --env-file /opt/HiFate-bazi/.env up -d --force-recreate'"
        echo ""
        echo "💡 提示："
        echo "   - 查看构建状态：https://github.com/zhoudengt/HiFate-bazi/actions"
        echo "   - 构建通常需要5-10分钟"
        echo "   - 构建完成后，镜像会自动推送到ACR"
        ;;
    2)
        echo ""
        echo "📋 方案2：在服务器上手动重建镜像"
        echo "----------------------------------------"
        echo "⚠️  此方案需要10-15分钟，会占用服务器资源"
        echo ""
        read -p "确认在服务器上重建镜像？(y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            echo "已取消"
            exit 0
        fi
        
        echo ""
        echo "🔨 在Node1上重建镜像..."
        ssh_exec $NODE1_IP "cd /opt/HiFate-bazi && \
            docker build --platform linux/amd64 -t registry.cn-hangzhou.aliyuncs.com/hifate/hifate-bazi:latest . && \
            echo '✅ Node1 镜像重建完成'"
        
        echo ""
        echo "🔨 在Node2上重建镜像..."
        ssh_exec $NODE2_IP "cd /opt/HiFate-bazi && \
            docker build --platform linux/amd64 -t registry.cn-hangzhou.aliyuncs.com/hifate/hifate-bazi:latest . && \
            echo '✅ Node2 镜像重建完成'"
        
        echo ""
        echo "🔄 重启容器应用新镜像..."
        echo "Node1..."
        ssh_exec $NODE1_IP "cd /opt/HiFate-bazi/deploy/docker && \
            source /opt/HiFate-bazi/.env && \
            docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \
            --env-file /opt/HiFate-bazi/.env up -d --force-recreate"
        
        echo "Node2..."
        ssh_exec $NODE2_IP "cd /opt/HiFate-bazi/deploy/docker && \
            source /opt/HiFate-bazi/.env && \
            docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \
            --env-file /opt/HiFate-bazi/.env up -d --force-recreate"
        
        echo ""
        echo "✅ 镜像重建和容器重启完成"
        echo ""
        echo "🔍 验证服务状态..."
        sleep 10
        curl -s http://$NODE1_IP:8001/health | python3 -m json.tool | head -5 || echo "⚠️  服务可能还在启动中"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "   修复完成"
echo "=========================================="

