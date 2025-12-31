#!/bin/bash
# 在服务器上重建Docker镜像（包含pytz依赖）
# 使用方式：bash scripts/deploy/rebuild_image_with_pytz.sh [node1|node2|both]

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

NODE=${1:-both}

echo "=========================================="
echo "   重建Docker镜像（包含pytz依赖）"
echo "=========================================="
echo ""

if [ "$NODE" = "node1" ] || [ "$NODE" = "both" ]; then
    echo "🔨 在Node1上重建镜像..."
    echo "   这需要10-15分钟，请耐心等待..."
    ssh_exec $NODE1_IP "cd /opt/HiFate-bazi && \
        git pull origin master && \
        docker build --platform linux/amd64 \
        -t registry.cn-hangzhou.aliyuncs.com/hifate/hifate-bazi:latest . 2>&1 | \
        tee /tmp/docker_build_node1.log | \
        grep -E '(Step|ERROR|✅|❌|pytz)' || true"
    
    if ssh_exec $NODE1_IP "docker images | grep -q 'hifate-bazi.*latest'"; then
        echo "✅ Node1 镜像重建完成"
    else
        echo "❌ Node1 镜像重建失败，请检查日志：ssh root@$NODE1_IP 'tail -50 /tmp/docker_build_node1.log'"
        exit 1
    fi
fi

if [ "$NODE" = "node2" ] || [ "$NODE" = "both" ]; then
    echo ""
    echo "🔨 在Node2上重建镜像..."
    echo "   这需要10-15分钟，请耐心等待..."
    ssh_exec $NODE2_IP "cd /opt/HiFate-bazi && \
        git pull origin master && \
        docker build --platform linux/amd64 \
        -t registry.cn-hangzhou.aliyuncs.com/hifate/hifate-bazi:latest . 2>&1 | \
        tee /tmp/docker_build_node2.log | \
        grep -E '(Step|ERROR|✅|❌|pytz)' || true"
    
    if ssh_exec $NODE2_IP "docker images | grep -q 'hifate-bazi.*latest'"; then
        echo "✅ Node2 镜像重建完成"
    else
        echo "❌ Node2 镜像重建失败，请检查日志：ssh root@$NODE2_IP 'tail -50 /tmp/docker_build_node2.log'"
        exit 1
    fi
fi

echo ""
echo "🔄 重启容器应用新镜像..."
if [ "$NODE" = "node1" ] || [ "$NODE" = "both" ]; then
    echo "Node1..."
    ssh_exec $NODE1_IP "cd /opt/HiFate-bazi/deploy/docker && \
        source /opt/HiFate-bazi/.env && \
        docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml \
        --env-file /opt/HiFate-bazi/.env up -d --force-recreate 2>&1 | tail -10"
fi

if [ "$NODE" = "node2" ] || [ "$NODE" = "both" ]; then
    echo "Node2..."
    ssh_exec $NODE2_IP "cd /opt/HiFate-bazi/deploy/docker && \
        source /opt/HiFate-bazi/.env && \
        docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml \
        --env-file /opt/HiFate-bazi/.env up -d --force-recreate 2>&1 | tail -10"
fi

echo ""
echo "⏳ 等待服务启动（30秒）..."
sleep 30

echo ""
echo "🔍 验证服务状态..."
if [ "$NODE" = "node1" ] || [ "$NODE" = "both" ]; then
    echo "Node1健康检查："
    curl -s http://$NODE1_IP:8001/health | python3 -m json.tool | head -5 || echo "⚠️  服务可能还在启动中"
fi

if [ "$NODE" = "node2" ] || [ "$NODE" = "both" ]; then
    echo "Node2健康检查："
    curl -s http://$NODE2_IP:8001/health | python3 -m json.tool | head -5 || echo "⚠️  服务可能还在启动中"
fi

echo ""
echo "✅ 镜像重建和容器重启完成"
echo ""
echo "📋 验证pytz依赖："
if [ "$NODE" = "node1" ] || [ "$NODE" = "both" ]; then
    ssh_exec $NODE1_IP "docker exec hifate-web python -c 'import pytz; print(\"✅ Node1: pytz可用，版本:\", pytz.__version__)'" || echo "❌ Node1: pytz不可用"
fi
if [ "$NODE" = "node2" ] || [ "$NODE" = "both" ]; then
    ssh_exec $NODE2_IP "docker exec hifate-web python -c 'import pytz; print(\"✅ Node2: pytz可用，版本:\", pytz.__version__)'" || echo "❌ Node2: pytz不可用"
fi

