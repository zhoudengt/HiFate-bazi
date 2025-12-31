#!/bin/bash
# scripts/fix_frontend_mem_limit.sh - 修复前端容器内存限制（使用 mem_limit）

set -e

SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"
NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
COMPOSE_FILE="/opt/hifate-frontend/docker-compose.yml"
FRONTEND_USER="frontend-user"

echo "=========================================="
echo "修复前端容器内存限制（使用 mem_limit）"
echo "=========================================="
echo ""

fix_node() {
    local NODE_IP=$1
    local NODE_NAME=$2
    
    echo "=========================================="
    echo "处理 $NODE_NAME ($NODE_IP)"
    echo "=========================================="
    echo ""
    
    # 1. 备份配置
    echo "1. 备份当前配置..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE_IP \
        "su - $FRONTEND_USER -c 'cd /opt/hifate-frontend && cp docker-compose.yml docker-compose.yml.backup.\$(date +%Y%m%d_%H%M%S)'"
    echo "   ✅ 备份完成"
    echo ""
    
    # 2. 下载配置文件
    echo "2. 下载配置文件..."
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no root@$NODE_IP:$COMPOSE_FILE /tmp/docker-compose.yml.$NODE_NAME
    echo "   ✅ 下载完成"
    echo ""
    
    # 3. 修改配置（使用 Python 脚本）
    echo "3. 修改配置（移除 deploy.resources，添加 mem_limit）..."
    python3 <<PYEOF
import yaml
import sys

compose_file = "/tmp/docker-compose.yml.$NODE_NAME"

with open(compose_file, 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

if 'services' not in data:
    print("   ❌ 配置文件中没有 services 部分")
    sys.exit(1)

# 内存限制映射
mem_limits = {
    "frontend-nacos": "1408M",
    "frontend-gateway": "1024M",
    "frontend-mysql": "512M",
    "frontend-modules-system": "384M",
    "frontend-modules-destiny": "384M",
    "frontend-redis": "256M",
    "frontend-nginx": "128M",
}

total_mb = 0

for service_name, service_config in data['services'].items():
    if not isinstance(service_config, dict):
        continue
    
    print(f"   🔄 处理服务: {service_name}")
    
    # 移除 deploy.resources
    if 'deploy' in service_config:
        deploy = service_config['deploy']
        if 'resources' in deploy:
            print(f"      ✅ 移除 deploy.resources")
            del deploy['resources']
        if not deploy:  # 如果 deploy 为空，删除整个 deploy
            del service_config['deploy']
    
    # 添加 mem_limit
    if service_name in mem_limits:
        mem_limit = mem_limits[service_name]
        service_config['mem_limit'] = mem_limit
        
        # 计算总内存（转换为 MB）
        mem_str = mem_limit.upper().strip()
        if mem_str.endswith('M'):
            mem_mb = int(mem_str[:-1])
        elif mem_str.endswith('G'):
            mem_mb = int(float(mem_str[:-1]) * 1024)
        else:
            mem_mb = int(mem_str)
        
        total_mb += mem_mb
        print(f"      ✅ 设置 mem_limit: {mem_limit}")
    else:
        print(f"      ⚠️  未找到内存限制配置，跳过")

print(f"\n   ✅ 总内存限制: {total_mb}MB ({total_mb/1024:.2f}G)")

# 确保版本 >= 2.0（mem_limit 需要）
if 'version' not in data or (data['version'] and float(data['version']) < 2.0):
    data['version'] = '3.8'
    print("   ✅ 设置版本为 3.8")

# 保存文件
with open(compose_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("   ✅ 配置文件修改完成")
PYEOF

    if [ $? -ne 0 ]; then
        echo "   ❌ 修改失败"
        exit 1
    fi
    echo ""
    
    # 4. 上传配置文件
    echo "4. 上传配置文件..."
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no /tmp/docker-compose.yml.$NODE_NAME root@$NODE_IP:$COMPOSE_FILE
    echo "   ✅ 上传完成"
    echo ""
    
    # 5. 验证配置
    echo "5. 验证配置..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE_IP \
        "su - $FRONTEND_USER -c 'cd /opt/hifate-frontend && docker-compose config > /dev/null 2>&1'"
    if [ $? -eq 0 ]; then
        echo "   ✅ 配置验证通过"
    else
        echo "   ❌ 配置验证失败"
        exit 1
    fi
    echo ""
    
    # 6. 重启容器
    echo "6. 重启所有容器..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE_IP \
        "su - $FRONTEND_USER -c 'cd /opt/hifate-frontend && docker-compose down && docker-compose up -d'"
    echo "   ✅ 容器已重启"
    echo ""
    
    # 7. 等待容器启动
    echo "7. 等待容器启动..."
    sleep 15
    echo ""
    
    # 8. 验证内存限制
    echo "8. 验证内存限制是否生效..."
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$NODE_IP \
        "su - $FRONTEND_USER -c 'docker stats --no-stream --format \"table {{.Name}}\\t{{.MemUsage}}\\t{{.MemPerc}}\" \$(docker ps --filter name=frontend --format \"{{.Names}}\") 2>/dev/null | head -10'"
    echo ""
    
    echo "✅ $NODE_NAME 修复完成"
    echo ""
}

# 修复 Node1
fix_node "$NODE1_IP" "Node1"

# 修复 Node2
fix_node "$NODE2_IP" "Node2"

echo "=========================================="
echo "✅ 所有节点修复完成"
echo "=========================================="
echo ""
echo "请观察容器运行情况，确保稳定运行 5 分钟以上"

