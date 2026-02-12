#!/bin/bash
# 修复前端 Docker 容器内存限制问题
# 将 mem_limit/mem_reservation 改为 deploy.resources.limits/reservations
# 确保总内存控制在 4G 以内
# 使用：bash scripts/fix_frontend_docker_memory_limit.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_USER="frontend-user"
FRONTEND_DIR="/opt/hifate-frontend"
COMPOSE_FILE="$FRONTEND_DIR/docker-compose.yml"

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

fix_memory_config() {
    local host=$1
    local node_name=$2
    
    echo "🔧 修复 $node_name ($host) 上的前端容器内存限制配置..."
    echo "----------------------------------------"
    
    # 1. 检查配置文件是否存在
    echo "1. 检查配置文件是否存在..."
    if ssh_exec $host "test -f $COMPOSE_FILE"; then
        echo "   ✅ 配置文件存在: $COMPOSE_FILE"
    else
        echo "   ❌ 配置文件不存在: $COMPOSE_FILE"
        echo "   ⚠️  跳过此节点"
        return 1
    fi
    
    # 2. 备份配置文件
    echo ""
    echo "2. 备份配置文件..."
    BACKUP_FILE="${COMPOSE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    ssh_exec $host "cp $COMPOSE_FILE $BACKUP_FILE"
    echo "   ✅ 已备份到: $BACKUP_FILE"
    
    # 3. 检查是否使用了旧的内存限制方式
    echo ""
    echo "3. 检查当前配置..."
    HAS_MEM_LIMIT=$(ssh_exec $host "grep -c 'mem_limit:' $COMPOSE_FILE || echo '0'")
    HAS_MEM_RESERVATION=$(ssh_exec $host "grep -c 'mem_reservation:' $COMPOSE_FILE || echo '0'")
    
    if [ "$HAS_MEM_LIMIT" = "0" ] && [ "$HAS_MEM_RESERVATION" = "0" ]; then
        echo "   ✅ 配置已使用新方式（deploy.resources），无需修改"
        return 0
    fi
    
    echo "   ⚠️  发现旧的内存限制配置："
    echo "      mem_limit: $HAS_MEM_LIMIT 处"
    echo "      mem_reservation: $HAS_MEM_RESERVATION 处"
    
    # 4. 下载配置文件到临时文件
    echo ""
    echo "4. 下载配置文件进行修改..."
    TEMP_FILE=$(mktemp)
    ssh_exec $host "cat $COMPOSE_FILE" > "$TEMP_FILE"
    echo "   ✅ 已下载到临时文件: $TEMP_FILE"
    
    # 5. 修改配置文件
    echo ""
    echo "5. 修改配置文件..."
    
    # 使用 Python 脚本进行修改（更可靠）
    python3 - "$TEMP_FILE" << 'PYTHON_SCRIPT'
import sys
import re
import yaml

compose_file = sys.argv[1]

# 读取文件
with open(compose_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否有 mem_limit 或 mem_reservation
if 'mem_limit:' not in content and 'mem_reservation:' not in content:
    print("   ✅ 配置已使用新方式，无需修改")
    sys.exit(0)

# 解析 YAML
try:
    data = yaml.safe_load(content)
except Exception as e:
    print(f"   ❌ YAML 解析失败: {e}")
    sys.exit(1)

# 确保有 services 部分
if 'services' not in data:
    print("   ❌ 配置文件中没有 services 部分")
    sys.exit(1)

# 总内存限制（4G）
TOTAL_MEMORY_LIMIT = 4 * 1024  # 4G in MB
total_allocated = 0

# 遍历所有服务
for service_name, service_config in data['services'].items():
    if not isinstance(service_config, dict):
        continue
    
    # 检查是否有旧的内存限制
    mem_limit = service_config.pop('mem_limit', None)
    mem_reservation = service_config.pop('mem_reservation', None)
    
    if mem_limit or mem_reservation:
        print(f"   🔄 修改服务: {service_name}")
        
        # 确保有 deploy 部分
        if 'deploy' not in service_config:
            service_config['deploy'] = {}
        if 'resources' not in service_config['deploy']:
            service_config['deploy']['resources'] = {}
        if 'limits' not in service_config['deploy']['resources']:
            service_config['deploy']['resources']['limits'] = {}
        if 'reservations' not in service_config['deploy']['resources']:
            service_config['deploy']['resources']['reservations'] = {}
        
        # 转换内存限制
        if mem_limit:
            # 转换为 MB
            if isinstance(mem_limit, str):
                mem_limit_str = mem_limit.lower().strip()
                if mem_limit_str.endswith('g'):
                    mem_limit_mb = int(float(mem_limit_str[:-1]) * 1024)
                elif mem_limit_str.endswith('m'):
                    mem_limit_mb = int(float(mem_limit_str[:-1]))
                else:
                    mem_limit_mb = int(mem_limit_str)
            else:
                mem_limit_mb = int(mem_limit)
            
            service_config['deploy']['resources']['limits']['memory'] = f"{mem_limit_mb}M"
            total_allocated += mem_limit_mb
            print(f"      ✅ mem_limit: {mem_limit} -> {mem_limit_mb}M")
        
        if mem_reservation:
            # 转换为 MB
            if isinstance(mem_reservation, str):
                mem_reservation_str = mem_reservation.lower().strip()
                if mem_reservation_str.endswith('g'):
                    mem_reservation_mb = int(float(mem_reservation_str[:-1]) * 1024)
                elif mem_reservation_str.endswith('m'):
                    mem_reservation_mb = int(float(mem_reservation_str[:-1]))
                else:
                    mem_reservation_mb = int(mem_reservation_str)
            else:
                mem_reservation_mb = int(mem_reservation)
            
            service_config['deploy']['resources']['reservations']['memory'] = f"{mem_reservation_mb}M"
            print(f"      ✅ mem_reservation: {mem_reservation} -> {mem_reservation_mb}M")

# 检查总内存是否超过 4G
if total_allocated > TOTAL_MEMORY_LIMIT:
    print(f"   ⚠️  警告：总内存限制 {total_allocated}MB ({total_allocated/1024:.2f}G) 超过 4G")
    print(f"   ⚠️  建议调整各服务的内存限制，确保总和 ≤ 4G")
else:
    print(f"   ✅ 总内存限制: {total_allocated}MB ({total_allocated/1024:.2f}G) ≤ 4G")

# 确保版本为 3.8 或更高
if 'version' not in data or (data['version'] and float(data['version']) < 3.8):
    data['version'] = '3.8'
    print("   ✅ 设置版本为 3.8")

# 写回文件
with open(compose_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("   ✅ 配置文件修改完成")
PYTHON_SCRIPT
    
    if [ $? -ne 0 ]; then
        echo "   ❌ 配置文件修改失败"
        rm -f "$TEMP_FILE"
        return 1
    fi
    
    # 6. 上传修改后的配置文件
    echo ""
    echo "6. 上传修改后的配置文件..."
    ssh_exec $host "cat > $COMPOSE_FILE" < "$TEMP_FILE"
    rm -f "$TEMP_FILE"
    echo "   ✅ 配置文件已上传"
    
    # 7. 验证配置
    echo ""
    echo "7. 验证配置..."
    VALIDATION=$(ssh_exec $host "cd $FRONTEND_DIR && docker-compose config 2>&1" || echo "ERROR")
    if echo "$VALIDATION" | grep -q "ERROR\|error\|Error"; then
        echo "   ❌ 配置验证失败"
        echo "   错误信息: $(echo "$VALIDATION" | head -5)"
        echo "   ⚠️  已恢复备份文件"
        ssh_exec $host "cp $BACKUP_FILE $COMPOSE_FILE"
        return 1
    else
        echo "   ✅ 配置验证通过"
    fi
    
    # 8. 显示修改后的配置摘要
    echo ""
    echo "8. 配置摘要："
    ssh_exec $host "grep -A 3 'deploy:' $COMPOSE_FILE | grep -E 'memory:|limits:|reservations:' | head -10" || true
    
    echo ""
    echo "   ✅ $node_name 配置修复完成"
}

echo "=========================================="
echo "修复前端 Docker 容器内存限制配置"
echo "=========================================="
echo ""
echo "目标："
echo "  - 将 mem_limit/mem_reservation 改为 deploy.resources"
echo "  - 确保总内存控制在 4G 以内"
echo "  - 保持 frontend-user 权限不变"
echo ""

# 修复 Node1
fix_memory_config $NODE1_PUBLIC_IP "Node1"

# 修复 Node2
fix_memory_config $NODE2_PUBLIC_IP "Node2"

echo ""
echo "=========================================="
echo "完成"
echo "=========================================="
echo ""
echo "下一步操作（在服务器上执行）："
echo "  1. 切换到 frontend-user:"
echo "     su - frontend-user"
echo ""
echo "  2. 进入前端目录："
echo "     cd /opt/hifate-frontend"
echo ""
echo "  3. 停止现有容器："
echo "     docker-compose down"
echo ""
echo "  4. 启动容器（使用新配置）："
echo "     docker-compose up -d"
echo ""
echo "  5. 验证内存限制："
echo "     docker stats --no-stream"
echo ""
echo "  6. 检查容器状态："
echo "     docker-compose ps"
echo ""

