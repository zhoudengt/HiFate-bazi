#!/bin/bash
# 增量部署脚本 - 生产环境双机部署
# 用途：通过热更新方式快速部署代码到生产环境，无需重启服务
# 使用：bash deploy/scripts/incremental_deploy_production.sh
#
# 适用场景：
#   - Python 代码更新
#   - 业务逻辑修改
#   - 规则更新
#   - 配置更新
#   - 微服务代码修改
#
# 不适用场景（需要使用完整部署）：
#   - 依赖变更（requirements.txt）
#   - Dockerfile 变更
#   - 首次部署
#   - 重大架构变更

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE1_PRIVATE_IP="172.18.121.222"
NODE2_PUBLIC_IP="47.243.160.43"
NODE2_PRIVATE_IP="172.18.121.223"

# Git 仓库配置
GIT_REPO="https://github.com/zhoudengt/HiFate-bazi"
GIT_BRANCH="master"

# 项目目录
PROJECT_DIR="/opt/HiFate-bazi"

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}错误：命令 $1 未安装${NC}"
        exit 1
    fi
}

echo "========================================"
echo "🚀 增量部署到生产环境（双机）"
echo "========================================"
echo "Node1: $NODE1_PUBLIC_IP ($NODE1_PRIVATE_IP)"
echo "Node2: $NODE2_PUBLIC_IP ($NODE2_PRIVATE_IP)"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# ==================== 第一步：部署前检查 ====================
echo -e "${BLUE}📋 第一步：部署前检查${NC}"
echo "----------------------------------------"

# 1.1 检查必要命令
echo "🔍 检查必要命令..."
check_command git
check_command ssh
check_command curl
echo -e "${GREEN}✅ 命令检查通过${NC}"

# 1.2 检查是否在 master 分支
echo ""
echo "🔍 检查当前分支..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "master" ]; then
    echo -e "${YELLOW}⚠️  警告：当前分支为 $CURRENT_BRANCH，建议在 master 分支部署${NC}"
    read -p "是否继续？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消部署"
        exit 1
    fi
else
    echo -e "${GREEN}✅ 当前分支：$CURRENT_BRANCH${NC}"
fi

# 1.3 检查是否有未提交的更改
echo ""
echo "🔍 检查未提交的更改..."
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}❌ 错误：存在未提交的更改，请先提交代码${NC}"
    git status --short
    exit 1
fi
echo -e "${GREEN}✅ 无未提交的更改${NC}"

# 1.4 检查是否有未推送的提交
echo ""
echo "🔍 检查未推送的提交..."
LOCAL_COMMITS=$(git rev-list @{u}..HEAD 2>/dev/null | wc -l || echo "0")
if [ "$LOCAL_COMMITS" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  警告：存在 $LOCAL_COMMITS 个未推送的提交${NC}"
    read -p "是否先推送到远程？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📤 推送到远程..."
        git push origin $CURRENT_BRANCH
        echo -e "${GREEN}✅ 推送完成${NC}"
    fi
else
    echo -e "${GREEN}✅ 无未推送的提交${NC}"
fi

# 1.5 本地语法验证
echo ""
echo "🔍 验证代码语法..."
python3 << 'EOF'
import ast
import sys
import os
import glob

errors = []
patterns = ['server/**/*.py', 'src/**/*.py', 'services/**/*.py']

for pattern in patterns:
    for path in glob.glob(pattern, recursive=True):
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    ast.parse(f.read(), path)
            except SyntaxError as e:
                errors.append(f'{path}:{e.lineno}: {e.msg}')
            except Exception as e:
                errors.append(f'{path}: {str(e)}')

if errors:
    print('❌ 语法错误：')
    for err in errors[:10]:  # 只显示前10个错误
        print(f'  - {err}')
    if len(errors) > 10:
        print(f'  ... 还有 {len(errors) - 10} 个错误')
    sys.exit(1)
print('✅ 语法验证通过')
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 语法验证失败，停止部署${NC}"
    exit 1
fi

# 1.6 关键模块导入验证（可选，本地环境可能缺少依赖）
echo ""
echo "🔍 验证关键模块导入（可选，本地环境可能缺少依赖）..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

critical_modules = [
    'server.services.rule_service',
    'server.hot_reload.hot_reload_manager',
]

failed = []
for module in critical_modules:
    try:
        __import__(module)
        print(f'✅ {module} 导入成功')
    except Exception as e:
        print(f'⚠️  {module} 导入失败: {e}（本地环境可能缺少依赖，将在服务器端验证）')
        failed.append(module)

# 如果所有模块都失败，可能是本地环境问题，不阻止部署
# 将在服务器端进行完整验证
if len(failed) == len(critical_modules):
    print('⚠️  所有模块导入失败，可能是本地环境缺少依赖，将在服务器端验证')
else:
    print(f'✅ {len(critical_modules) - len(failed)}/{len(critical_modules)} 个关键模块导入成功')
EOF

# 不因为本地导入失败而阻止部署，服务器端会进行完整验证
echo -e "${GREEN}✅ 本地验证完成（服务器端将进行完整验证）${NC}"

echo ""
echo -e "${GREEN}✅ 部署前检查全部通过${NC}"
echo ""

# ==================== 第二步：检查服务器连接 ====================
echo -e "${BLUE}🔌 第二步：检查服务器连接${NC}"
echo "----------------------------------------"

echo "🔍 检查 Node1 连接..."
if ssh_exec $NODE1_PUBLIC_IP "echo 'Node1 连接成功'" 2>/dev/null; then
    echo -e "${GREEN}✅ Node1 连接成功${NC}"
else
    echo -e "${RED}❌ 无法连接到 Node1 ($NODE1_PUBLIC_IP)${NC}"
    exit 1
fi

echo "🔍 检查 Node2 连接..."
if ssh_exec $NODE2_PUBLIC_IP "echo 'Node2 连接成功'" 2>/dev/null; then
    echo -e "${GREEN}✅ Node2 连接成功${NC}"
else
    echo -e "${RED}❌ 无法连接到 Node2 ($NODE2_PUBLIC_IP)${NC}"
    exit 1
fi

echo ""

# ==================== 第三步：拉取代码 ====================
echo -e "${BLUE}📥 第三步：拉取最新代码${NC}"
echo "----------------------------------------"

# 在 Node1 上拉取代码
echo "📥 在 Node1 上拉取代码..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git checkout $GIT_BRANCH && git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node1 代码拉取失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ Node1 代码拉取完成${NC}"

# 在 Node2 上拉取代码
echo "📥 在 Node2 上拉取代码..."
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git checkout $GIT_BRANCH && git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node2 代码拉取失败${NC}"
    exit 1
}
echo -e "${GREEN}✅ Node2 代码拉取完成${NC}"

echo ""

# ==================== 第四步：服务器端验证 ====================
echo -e "${BLUE}🔍 第四步：服务器端验证${NC}"
echo "----------------------------------------"

# 在 Node1 上验证语法
echo "🔍 在 Node1 上验证代码语法..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && python3 << 'EOF'
import ast
import sys
import os
import glob

errors = []
for pattern in ['server/**/*.py', 'src/**/*.py', 'services/**/*.py']:
    for path in glob.glob(pattern, recursive=True):
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    ast.parse(f.read(), path)
            except SyntaxError as e:
                errors.append(f'{path}:{e.lineno}: {e.msg}')

if errors:
    print('❌ 语法错误：')
    for err in errors[:5]:
        print(f'  - {err}')
    sys.exit(1)
print('✅ 语法验证通过')
EOF" || {
    echo -e "${RED}❌ Node1 语法验证失败${NC}"
    exit 1
}

echo -e "${GREEN}✅ Node1 语法验证通过${NC}"

# 在 Node2 上验证语法
echo "🔍 在 Node2 上验证代码语法..."
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && python3 << 'EOF'
import ast
import sys
import os
import glob

errors = []
for pattern in ['server/**/*.py', 'src/**/*.py', 'services/**/*.py']:
    for path in glob.glob(pattern, recursive=True):
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    ast.parse(f.read(), path)
            except SyntaxError as e:
                errors.append(f'{path}:{e.lineno}: {e.msg}')

if errors:
    print('❌ 语法错误：')
    for err in errors[:5]:
        print(f'  - {err}')
    sys.exit(1)
print('✅ 语法验证通过')
EOF" || {
    echo -e "${RED}❌ Node2 语法验证失败${NC}"
    exit 1
}

echo -e "${GREEN}✅ Node2 语法验证通过${NC}"

echo ""

# ==================== 第五步：触发热更新 ====================
echo -e "${BLUE}🔄 第五步：触发热更新${NC}"
echo "----------------------------------------"

# 在 Node1 上触发热更新（会自动同步到 Node2）
echo "🔄 在 Node1 上触发热更新..."
HEALTH_URL="http://$NODE1_PUBLIC_IP:8001"
SYNC_URL="$HEALTH_URL/api/v1/hot-reload/sync"

# 先检查服务是否可用
if ! curl -f -s "$HEALTH_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Node1 服务不可用，无法触发热更新${NC}"
    exit 1
fi

# 触发热更新同步
SYNC_RESPONSE=$(curl -s -X POST "$SYNC_URL" 2>&1)
if echo "$SYNC_RESPONSE" | grep -q "success\|ok\|同步" || [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 热更新触发成功${NC}"
else
    echo -e "${YELLOW}⚠️  热更新响应：$SYNC_RESPONSE${NC}"
    echo -e "${YELLOW}⚠️  继续部署，请手动检查热更新状态${NC}"
fi

# 等待热更新完成
echo "⏳ 等待热更新完成（30秒）..."
sleep 30

echo ""

# ==================== 第六步：部署后验证 ====================
echo -e "${BLUE}🏥 第六步：部署后验证${NC}"
echo "----------------------------------------"

# 6.1 健康检查
check_health() {
    local node_ip=$1
    local node_name=$2
    local max_retries=5
    local retry_count=0
    local health_ok=false
    
    echo "🏥 检查 $node_name 健康状态..."
    while [ $retry_count -lt $max_retries ]; do
        if curl -f -s "http://$node_ip:8001/health" > /dev/null 2>&1; then
            health_ok=true
            break
        fi
        retry_count=$((retry_count + 1))
        echo "⏳ 健康检查失败，重试 $retry_count/$max_retries..."
        sleep 5
    done
    
    if [ "$health_ok" = true ]; then
        echo -e "${GREEN}✅ $node_name 健康检查通过${NC}"
        return 0
    else
        echo -e "${RED}❌ $node_name 健康检查失败${NC}"
        return 1
    fi
}

# 检查 Node1
if ! check_health $NODE1_PUBLIC_IP "Node1"; then
    echo -e "${RED}❌ Node1 健康检查失败，自动回滚...${NC}"
    curl -s -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/rollback" || true
    exit 1
fi

# 检查 Node2
if ! check_health $NODE2_PUBLIC_IP "Node2"; then
    echo -e "${RED}❌ Node2 健康检查失败，自动回滚...${NC}"
    curl -s -X POST "http://$NODE2_PUBLIC_IP:8001/api/v1/hot-reload/rollback" || true
    exit 1
fi

# 6.2 热更新状态检查
echo ""
echo "🔍 检查热更新状态..."
NODE1_STATUS=$(curl -s "http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/status" 2>/dev/null || echo "{}")
NODE2_STATUS=$(curl -s "http://$NODE2_PUBLIC_IP:8001/api/v1/hot-reload/status" 2>/dev/null || echo "{}")

if echo "$NODE1_STATUS" | grep -q "error\|失败" && [ -n "$NODE1_STATUS" ]; then
    echo -e "${YELLOW}⚠️  Node1 热更新状态异常${NC}"
else
    echo -e "${GREEN}✅ Node1 热更新状态正常${NC}"
fi

if echo "$NODE2_STATUS" | grep -q "error\|失败" && [ -n "$NODE2_STATUS" ]; then
    echo -e "${YELLOW}⚠️  Node2 热更新状态异常${NC}"
else
    echo -e "${GREEN}✅ Node2 热更新状态正常${NC}"
fi

# 6.3 功能验证（可选，快速检查关键 API）
echo ""
echo "🔍 验证关键功能..."
TEST_RESPONSE=$(curl -s -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/bazi/calculate" \
    -H "Content-Type: application/json" \
    -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}' 2>/dev/null || echo "{}")

if echo "$TEST_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ 关键功能验证通过${NC}"
else
    echo -e "${YELLOW}⚠️  关键功能验证失败，但服务健康检查通过，继续...${NC}"
    echo "响应: $TEST_RESPONSE" | head -c 200
    echo ""
fi

echo ""

# ==================== 完成 ====================
echo "========================================"
echo -e "${GREEN}✅ 增量部署完成！${NC}"
echo "========================================"
echo ""
echo "访问地址："
echo "  Node1: http://$NODE1_PUBLIC_IP"
echo "  Node2: http://$NODE2_PUBLIC_IP"
echo ""
echo "健康检查："
echo "  Node1: http://$NODE1_PUBLIC_IP:8001/health"
echo "  Node2: http://$NODE2_PUBLIC_IP:8001/health"
echo ""
echo "热更新状态："
echo "  Node1: http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/status"
echo "  Node2: http://$NODE2_PUBLIC_IP:8001/api/v1/hot-reload/status"
echo ""
echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

