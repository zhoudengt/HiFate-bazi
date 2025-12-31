#!/bin/bash
# 修复前端 Docker 容器内存限制问题（本地执行版本）
# 在服务器上由 frontend-user 直接执行
# 使用：bash fix_frontend_memory_limit_local.sh

set -e

FRONTEND_DIR="/opt/hifate-frontend"
COMPOSE_FILE="$FRONTEND_DIR/docker-compose.yml"

# 检查用户
if [ "$USER" != "frontend-user" ]; then
    echo "❌ 此脚本必须由 frontend-user 执行"
    echo "   当前用户: $USER"
    exit 1
fi

# 检查配置文件
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ 配置文件不存在: $COMPOSE_FILE"
    exit 1
fi

echo "=========================================="
echo "修复前端 Docker 容器内存限制配置"
echo "=========================================="
echo ""
echo "配置文件: $COMPOSE_FILE"
echo ""

# 备份配置文件
BACKUP_FILE="${COMPOSE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$COMPOSE_FILE" "$BACKUP_FILE"
echo "✅ 已备份到: $BACKUP_FILE"
echo ""

# 检查是否使用了旧的内存限制方式
HAS_MEM_LIMIT=$(grep -c 'mem_limit:' "$COMPOSE_FILE" || echo "0")
HAS_MEM_RESERVATION=$(grep -c 'mem_reservation:' "$COMPOSE_FILE" || echo "0")

if [ "$HAS_MEM_LIMIT" = "0" ] && [ "$HAS_MEM_RESERVATION" = "0" ]; then
    echo "✅ 配置已使用新方式（deploy.resources），无需修改"
    exit 0
fi

echo "⚠️  发现旧的内存限制配置："
echo "   mem_limit: $HAS_MEM_LIMIT 处"
echo "   mem_reservation: $HAS_MEM_RESERVATION 处"
echo ""

# 使用 Python 脚本进行修改
cd "$FRONTEND_DIR"

python3 << 'PYTHON_SCRIPT'
import sys
import re
import yaml
import os

compose_file = sys.argv[1]

# 读取文件
with open(compose_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否有 mem_limit 或 mem_reservation
if 'mem_limit:' not in content and 'mem_reservation:' not in content:
    print("✅ 配置已使用新方式，无需修改")
    sys.exit(0)

# 解析 YAML
try:
    data = yaml.safe_load(content)
except Exception as e:
    print(f"❌ YAML 解析失败: {e}")
    sys.exit(1)

# 确保有 services 部分
if 'services' not in data:
    print("❌ 配置文件中没有 services 部分")
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
        print(f"🔄 修改服务: {service_name}")
        
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
            print(f"   ✅ mem_limit: {mem_limit} -> {mem_limit_mb}M")
        
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
            print(f"   ✅ mem_reservation: {mem_reservation} -> {mem_reservation_mb}M")

# 检查总内存是否超过 4G
print("")
if total_allocated > TOTAL_MEMORY_LIMIT:
    print(f"⚠️  警告：总内存限制 {total_allocated}MB ({total_allocated/1024:.2f}G) 超过 4G")
    print(f"⚠️  建议调整各服务的内存限制，确保总和 ≤ 4G")
    response = input("是否继续？(y/N): ")
    if response.lower() != 'y':
        print("❌ 已取消")
        sys.exit(1)
else:
    print(f"✅ 总内存限制: {total_allocated}MB ({total_allocated/1024:.2f}G) ≤ 4G")

# 确保版本为 3.8 或更高
if 'version' not in data or (data['version'] and float(data['version']) < 3.8):
    data['version'] = '3.8'
    print("✅ 设置版本为 3.8")

# 写回文件
with open(compose_file, 'w', encoding='utf-8') as f:
    yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("")
print("✅ 配置文件修改完成")
PYTHON_SCRIPT
"$COMPOSE_FILE"

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 配置文件修改失败，已恢复备份"
    cp "$BACKUP_FILE" "$COMPOSE_FILE"
    exit 1
fi

# 验证配置
echo ""
echo "验证配置..."
if docker-compose config > /dev/null 2>&1; then
    echo "✅ 配置验证通过"
else
    echo "❌ 配置验证失败，已恢复备份"
    cp "$BACKUP_FILE" "$COMPOSE_FILE"
    exit 1
fi

echo ""
echo "=========================================="
echo "修复完成"
echo "=========================================="
echo ""
echo "下一步操作："
echo "  1. 停止现有容器："
echo "     docker-compose down"
echo ""
echo "  2. 启动容器（使用新配置）："
echo "     docker-compose up -d"
echo ""
echo "  3. 验证内存限制："
echo "     docker stats --no-stream"
echo ""
echo "  4. 检查容器状态："
echo "     docker-compose ps"
echo ""

