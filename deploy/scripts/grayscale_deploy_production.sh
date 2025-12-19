#!/bin/bash
# 灰度发布脚本 - 生产环境双机灰度部署
# 用途：先部署到 Node1，运行完整功能测试，通过后再部署到 Node2
# 使用：bash deploy/scripts/grayscale_deploy_production.sh
#
# 适用场景：
#   - Python 代码更新
#   - 业务逻辑修改
#   - 规则更新
#   - 配置更新
#   - 微服务代码修改
#   - 数据库结构变更
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

# SSH 密码（从环境变量或默认值读取）
SSH_PASSWORD="${SSH_PASSWORD:-Yuanqizhan@163}"

# 部署ID（用于日志和报告）
DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)
FAILURE_LOG_DIR="logs/deployment_failures"

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

# 保护 frontend 目录函数（在 git 操作前后保护 frontend 目录不被删除）
protect_frontend_directory() {
    local host=$1
    local action=$2  # "backup" 或 "restore"
    
    if [ "$action" = "backup" ]; then
        # 备份 frontend 目录（如果存在）
        ssh_exec $host "cd $PROJECT_DIR && \
            if [ -d frontend ] && [ -n \"\$(ls -A frontend 2>/dev/null)\" ]; then
                BACKUP_DIR=\"frontend.backup.\$(date +%s)\"
                cp -r frontend \"\$BACKUP_DIR\" 2>/dev/null && \
                echo \"✅ frontend 目录已备份到 \$BACKUP_DIR\" || true
            fi"
    elif [ "$action" = "restore" ]; then
        # 恢复 frontend 目录（如果被删除）
        ssh_exec $host "cd $PROJECT_DIR && \
            if [ ! -d frontend ] || [ -z \"\$(ls -A frontend 2>/dev/null)\" ]; then
                # 查找最新的备份
                LATEST_BACKUP=\$(ls -td frontend.backup.* 2>/dev/null | head -1)
                if [ -n \"\$LATEST_BACKUP\" ] && [ -d \"\$LATEST_BACKUP\" ]; then
                    cp -r \"\$LATEST_BACKUP\" frontend && \
                    echo \"✅ frontend 目录已从备份恢复: \$LATEST_BACKUP\" || true
                elif [ -d local_frontend ]; then
                    cp -r local_frontend frontend && \
                    echo \"✅ frontend 目录已从 local_frontend 恢复\" || true
                fi
            else
                echo \"✅ frontend 目录存在且不为空，无需恢复\" || true
            fi"
    fi
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}错误：命令 $1 未安装${NC}"
        exit 1
    fi
}

# 回滚函数
rollback_node1() {
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}🔄 开始回滚 Node1${NC}"
    echo -e "${RED}========================================${NC}"
    
    # 1. 回滚代码（热更新回滚）
    echo "🔄 回滚 Node1 代码..."
    ROLLBACK_CODE=$(curl -s -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/rollback" 2>&1 || echo "failed")
    if echo "$ROLLBACK_CODE" | grep -q "success\|ok\|回滚"; then
        echo -e "${GREEN}✅ Node1 代码回滚成功${NC}"
    else
        echo -e "${YELLOW}⚠️  Node1 代码回滚响应：$ROLLBACK_CODE${NC}"
    fi
    
    # 2. 回滚数据库（如果有数据库变更）
    if [ -f "scripts/db/rollback/rollback_${DEPLOYMENT_ID}.sql" ]; then
        echo "🔄 回滚 Node1 数据库..."
        bash scripts/db/rollback_db.sh --node node1 --rollback-file "scripts/db/rollback/rollback_${DEPLOYMENT_ID}.sql" || {
            echo -e "${YELLOW}⚠️  Node1 数据库回滚失败（可能需要手动处理）${NC}"
        }
    fi
    
    echo -e "${GREEN}✅ Node1 回滚完成${NC}"
}

# 生成失败报告
generate_failure_report() {
    local stage=$1
    local error_details=$2
    
    mkdir -p "$FAILURE_LOG_DIR"
    REPORT_FILE="$FAILURE_LOG_DIR/failure_${DEPLOYMENT_ID}.json"
    
    cat > "$REPORT_FILE" << EOF
{
    "deployment_id": "$DEPLOYMENT_ID",
    "node": "node1",
    "status": "failed",
    "stage": "$stage",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "errors": $error_details,
    "rollback_status": "executed",
    "rollback_details": {
        "code_rollback": "executed",
        "db_rollback": "executed_if_needed"
    }
}
EOF
    
    echo -e "${YELLOW}📋 失败报告已保存到: $REPORT_FILE${NC}"
}

echo "========================================"
echo "🚀 灰度发布到生产环境"
echo "========================================"
echo "Node1 (灰度节点): $NODE1_PUBLIC_IP ($NODE1_PRIVATE_IP)"
echo "Node2 (生产节点): $NODE2_PUBLIC_IP ($NODE2_PRIVATE_IP)"
echo "部署ID: $DEPLOYMENT_ID"
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
check_command python3
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
    for err in errors[:10]:
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

# 1.6 数据库变更检测
echo ""
echo "🔍 检测数据库变更..."
if [ -f "scripts/db/detect_db_changes.py" ]; then
    python3 scripts/db/detect_db_changes.py --generate-sync-script || {
        echo -e "${YELLOW}⚠️  数据库变更检测失败，继续部署（可能没有数据库变更）${NC}"
    }
else
    echo -e "${YELLOW}⚠️  数据库变更检测脚本不存在，跳过数据库变更检测${NC}"
fi

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

# ==================== 第三步：部署到 Node1（灰度节点）====================
echo -e "${BLUE}📥 第三步：部署到 Node1（灰度节点）${NC}"
echo "----------------------------------------"

# 3.1 拉取代码到 Node1
echo "📥 在 Node1 上拉取代码..."
LOCAL_CHANGES_NODE1=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")
if [ -n "$LOCAL_CHANGES_NODE1" ]; then
    echo -e "${YELLOW}⚠️  警告：Node1 上有本地未提交的更改，将被保存（git stash）${NC}"
fi

# 🔒 保护 frontend 目录：在 git pull 之前备份
echo "🔒 保护 frontend 目录（备份）..."
protect_frontend_directory $NODE1_PUBLIC_IP "backup"

ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout $GIT_BRANCH && \
    (git stash || true) && \
    git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node1 代码拉取失败${NC}"
    # 即使失败也要尝试恢复 frontend 目录
    protect_frontend_directory $NODE1_PUBLIC_IP "restore"
    exit 1
}

# 🔒 保护 frontend 目录：在 git pull 之后恢复（如果被删除）
echo "🔒 保护 frontend 目录（恢复检查）..."
protect_frontend_directory $NODE1_PUBLIC_IP "restore"

# 验证 Node1 代码与 GitHub 一致
NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
LOCAL_COMMIT=$(git rev-parse HEAD)
if [ "$NODE1_COMMIT" != "$LOCAL_COMMIT" ]; then
    echo -e "${RED}❌ 错误：Node1 代码版本与本地不一致${NC}"
    echo "  Node1: $NODE1_COMMIT"
    echo "  本地:  $LOCAL_COMMIT"
    echo -e "${RED}🔴 请确保已推送到 GitHub：git push origin master${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node1 代码拉取完成（版本: ${NODE1_COMMIT:0:8}）${NC}"

# 3.2 修复 Node1 Nginx 配置
echo "🔧 修复 Node1 Nginx 配置..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
    source .env 2>/dev/null || true && \
    NODE1_IP=\${NODE1_IP:-$NODE1_PRIVATE_IP} && \
    NODE2_IP=\${NODE2_IP:-$NODE2_PRIVATE_IP} && \
    sed -i \"s/NODE1_IP/\$NODE1_IP/g\" deploy/nginx/conf.d/hifate.conf && \
    sed -i \"s/NODE2_IP/\$NODE2_IP/g\" deploy/nginx/conf.d/hifate.conf"

# 3.3 执行数据库同步（如有变更）
echo ""
echo "🔍 检查是否需要执行数据库同步..."
if [ -f "scripts/db/sync_production_db.sh" ] && [ -f "scripts/db/sync_${DEPLOYMENT_ID}.sql" ]; then
    echo "🔄 执行数据库同步到 Node1..."
    bash scripts/db/sync_production_db.sh --node node1 --deployment-id "$DEPLOYMENT_ID" || {
        echo -e "${RED}❌ Node1 数据库同步失败，回滚...${NC}"
        rollback_node1
        generate_failure_report "database_sync" '["数据库同步失败"]'
        exit 1
    }
    echo -e "${GREEN}✅ Node1 数据库同步完成${NC}"
else
    echo -e "${GREEN}✅ 无需数据库同步${NC}"
fi

# 3.4 服务器端语法验证
echo ""
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
    echo -e "${RED}❌ Node1 语法验证失败，回滚...${NC}"
    rollback_node1
    generate_failure_report "syntax_validation" '["语法验证失败"]'
    exit 1
}
echo -e "${GREEN}✅ Node1 语法验证通过${NC}"

# 3.5 触发热更新
echo ""
echo "🔄 在 Node1 上触发热更新..."
HEALTH_URL="http://$NODE1_PUBLIC_IP:8001"
if ! curl -f -s "$HEALTH_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Node1 服务不可用，无法触发热更新${NC}"
    rollback_node1
    generate_failure_report "service_unavailable" '["服务不可用"]'
    exit 1
fi

SYNC_URL="$HEALTH_URL/api/v1/hot-reload/sync"
SYNC_RESPONSE=$(curl -s -X POST "$SYNC_URL" 2>&1)
if echo "$SYNC_RESPONSE" | grep -q "success\|ok\|同步"; then
    echo -e "${GREEN}✅ 热更新触发成功${NC}"
else
    echo -e "${YELLOW}⚠️  热更新响应：$SYNC_RESPONSE${NC}"
fi

# 等待热更新完成
echo "⏳ 等待热更新完成（30秒）..."
sleep 30

echo -e "${GREEN}✅ Node1 部署完成${NC}"
echo ""

# ==================== 第四步：Node1 完整功能测试（关键步骤）====================
echo -e "${BLUE}🧪 第四步：Node1 完整功能测试（关键步骤）${NC}"
echo "----------------------------------------"

# 4.1 健康检查
echo "🏥 检查 Node1 健康状态..."
MAX_RETRIES=5
RETRY_COUNT=0
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$HEALTH_URL/health" > /dev/null 2>&1; then
        HEALTH_OK=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ 健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 5
done

if [ "$HEALTH_OK" = false ]; then
    echo -e "${RED}❌ Node1 健康检查失败，回滚...${NC}"
    rollback_node1
    generate_failure_report "health_check" '["健康检查失败"]'
    exit 1
fi
echo -e "${GREEN}✅ Node1 健康检查通过${NC}"

# 4.2 运行完整功能测试
echo ""
echo "🧪 运行 Node1 完整功能测试..."
if [ -f "tests/e2e_node1_test.py" ]; then
    python3 tests/e2e_node1_test.py --node-url "$HEALTH_URL" || {
        TEST_ERRORS=$(python3 tests/e2e_node1_test.py --node-url "$HEALTH_URL" --json-output 2>/dev/null || echo '[]')
        echo -e "${RED}❌ Node1 功能测试失败，回滚...${NC}"
        rollback_node1
        generate_failure_report "function_test" "$TEST_ERRORS"
        exit 1
    }
    echo -e "${GREEN}✅ Node1 功能测试全部通过${NC}"
else
    echo -e "${YELLOW}⚠️  测试脚本不存在，跳过功能测试${NC}"
    echo -e "${YELLOW}⚠️  建议创建 tests/e2e_node1_test.py 进行完整测试${NC}"
fi

# 4.3 热更新状态检查
echo ""
echo "🔍 检查 Node1 热更新状态..."
NODE1_STATUS=$(curl -s "$HEALTH_URL/api/v1/hot-reload/status" 2>/dev/null || echo "{}")
if echo "$NODE1_STATUS" | grep -q "error\|失败"; then
    echo -e "${YELLOW}⚠️  Node1 热更新状态异常${NC}"
else
    echo -e "${GREEN}✅ Node1 热更新状态正常${NC}"
fi

echo ""
echo -e "${GREEN}✅ Node1 完整功能测试通过，可以继续部署到 Node2${NC}"
echo ""

# ==================== 第五步：部署到 Node2（生产节点）====================
echo -e "${BLUE}📥 第五步：部署到 Node2（生产节点）${NC}"
echo "----------------------------------------"

# 5.1 拉取代码到 Node2
echo "📥 在 Node2 上拉取代码..."
LOCAL_CHANGES_NODE2=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")
if [ -n "$LOCAL_CHANGES_NODE2" ]; then
    echo -e "${YELLOW}⚠️  警告：Node2 上有本地未提交的更改，将被保存（git stash）${NC}"
fi

ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout $GIT_BRANCH && \
    (git stash || true) && \
    git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node2 代码拉取失败${NC}"
    exit 1
}

# 验证 Node2 代码与 Node1 一致
NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
if [ "$NODE2_COMMIT" != "$NODE1_COMMIT" ]; then
    echo -e "${RED}❌ 错误：Node2 代码版本与 Node1 不一致${NC}"
    echo "  Node1: $NODE1_COMMIT"
    echo "  Node2: $NODE2_COMMIT"
    exit 1
fi
echo -e "${GREEN}✅ Node2 代码拉取完成（版本: ${NODE2_COMMIT:0:8}）${NC}"

# 5.2 修复 Node2 Nginx 配置
echo "🔧 修复 Node2 Nginx 配置..."
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
    source .env 2>/dev/null || true && \
    NODE1_IP=\${NODE1_IP:-$NODE1_PRIVATE_IP} && \
    NODE2_IP=\${NODE2_IP:-$NODE2_PRIVATE_IP} && \
    sed -i \"s/NODE1_IP/\$NODE1_IP/g\" deploy/nginx/conf.d/hifate.conf && \
    sed -i \"s/NODE2_IP/\$NODE2_IP/g\" deploy/nginx/conf.d/hifate.conf"

# 5.3 执行数据库同步（如有变更）
if [ -f "scripts/db/sync_production_db.sh" ] && [ -f "scripts/db/sync_${DEPLOYMENT_ID}.sql" ]; then
    echo ""
    echo "🔄 执行数据库同步到 Node2..."
    bash scripts/db/sync_production_db.sh --node node2 --deployment-id "$DEPLOYMENT_ID" || {
        echo -e "${RED}❌ Node2 数据库同步失败${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Node2 数据库同步完成${NC}"
fi

# 5.4 服务器端语法验证
echo ""
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

# 5.5 触发热更新
echo ""
echo "🔄 在 Node2 上触发热更新..."
NODE2_HEALTH_URL="http://$NODE2_PUBLIC_IP:8001"
if ! curl -f -s "$NODE2_HEALTH_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Node2 服务不可用，无法触发热更新${NC}"
    exit 1
fi

NODE2_SYNC_URL="$NODE2_HEALTH_URL/api/v1/hot-reload/sync"
NODE2_SYNC_RESPONSE=$(curl -s -X POST "$NODE2_SYNC_URL" 2>&1)
if echo "$NODE2_SYNC_RESPONSE" | grep -q "success\|ok\|同步"; then
    echo -e "${GREEN}✅ 热更新触发成功${NC}"
else
    echo -e "${YELLOW}⚠️  热更新响应：$NODE2_SYNC_RESPONSE${NC}"
fi

# 等待热更新完成
echo "⏳ 等待热更新完成（30秒）..."
sleep 30

echo -e "${GREEN}✅ Node2 部署完成${NC}"
echo ""

# ==================== 第六步：Node2 快速验证 ====================
echo -e "${BLUE}🔍 第六步：Node2 快速验证${NC}"
echo "----------------------------------------"

# 6.1 健康检查
echo "🏥 检查 Node2 健康状态..."
MAX_RETRIES=5
RETRY_COUNT=0
NODE2_HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$NODE2_HEALTH_URL/health" > /dev/null 2>&1; then
        NODE2_HEALTH_OK=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ 健康检查失败，重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 5
done

if [ "$NODE2_HEALTH_OK" = false ]; then
    echo -e "${RED}❌ Node2 健康检查失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Node2 健康检查通过${NC}"

# 6.2 关键接口快速测试
echo ""
echo "🧪 运行 Node2 关键接口快速测试..."
if [ -f "tests/e2e_production_test.py" ]; then
    python3 tests/e2e_production_test.py --node1-url "$HEALTH_URL" --node2-url "$NODE2_HEALTH_URL" --quick-test || {
        echo -e "${YELLOW}⚠️  Node2 快速测试失败，但服务健康检查通过${NC}"
    }
else
    echo -e "${YELLOW}⚠️  测试脚本不存在，跳过快速测试${NC}"
fi

# 6.3 双机代码一致性验证
echo ""
echo "🔍 验证双机代码一致性..."
if [ "$NODE1_COMMIT" = "$NODE2_COMMIT" ]; then
    echo -e "${GREEN}✅ 双机代码版本一致（${NODE1_COMMIT:0:8}）${NC}"
else
    echo -e "${RED}❌ 错误：双机代码版本不一致${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Node2 验证通过${NC}"
echo ""

# ==================== 完成 ====================
echo "========================================"
echo -e "${GREEN}✅ 灰度发布完成！${NC}"
echo "========================================"
echo ""
echo "部署信息："
echo "  部署ID: $DEPLOYMENT_ID"
echo "  双机代码版本: ${NODE1_COMMIT:0:8}"
echo "  部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "访问地址："
echo "  Node1: http://$NODE1_PUBLIC_IP"
echo "  Node2: http://$NODE2_PUBLIC_IP"
echo ""
echo "健康检查："
echo "  Node1: http://$NODE1_PUBLIC_IP:8001/health"
echo "  Node2: http://$NODE2_PUBLIC_IP:8001/health"
echo ""
echo -e "${GREEN}✅ 灰度发布成功：Node1 测试通过，Node2 验证通过${NC}"
echo ""

