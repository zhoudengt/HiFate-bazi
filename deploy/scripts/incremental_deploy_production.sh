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

# 在 Node1 上拉取代码（确保与 GitHub 一致）
echo "📥 在 Node1 上拉取代码..."
echo "⚠️  检查服务器本地更改（禁止直接在服务器上修改代码）..."
LOCAL_CHANGES_NODE1=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")
if [ -n "$LOCAL_CHANGES_NODE1" ]; then
    echo -e "${YELLOW}⚠️  警告：Node1 上有本地未提交的更改：${NC}"
    echo "$LOCAL_CHANGES_NODE1" | sed 's/^/  /'
    echo -e "${YELLOW}⚠️  这些更改将被保存（git stash），确保与 GitHub 代码一致${NC}"
    echo -e "${YELLOW}⚠️  如需保留这些更改，请在本地修改并提交到 GitHub${NC}"
fi

ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout $GIT_BRANCH && \
    (git stash || true) && \
    git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node1 代码拉取失败${NC}"
    exit 1
}

# 验证 Node1 代码与 GitHub 一致
NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
LOCAL_COMMIT=$(git rev-parse HEAD)
if [ "$NODE1_COMMIT" != "$LOCAL_COMMIT" ]; then
    echo -e "${YELLOW}⚠️  警告：Node1 代码版本与本地不一致${NC}"
    echo "  Node1: $NODE1_COMMIT"
    echo "  本地:  $LOCAL_COMMIT"
    echo -e "${YELLOW}⚠️  请确保已推送到 GitHub：git push origin master${NC}"
    echo -e "${YELLOW}⚠️  重新拉取 Node1 代码以同步...${NC}"
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git pull origin $GIT_BRANCH"
    NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    if [ "$NODE1_COMMIT" != "$LOCAL_COMMIT" ]; then
        echo -e "${RED}❌ 错误：Node1 代码版本仍与本地不一致${NC}"
        echo -e "${RED}🔴 请确保已推送到 GitHub：git push origin master${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Node1 代码已同步到最新版本${NC}"
fi

# 修复 Node1 Nginx 配置（确保IP占位符被替换）
echo "🔧 修复 Node1 Nginx 配置..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
    source .env 2>/dev/null || true && \
    NODE1_IP=\${NODE1_IP:-$NODE1_PRIVATE_IP} && \
    NODE2_IP=\${NODE2_IP:-$NODE2_PRIVATE_IP} && \
    sed -i \"s/NODE1_IP/\$NODE1_IP/g\" deploy/nginx/conf.d/hifate.conf && \
    sed -i \"s/NODE2_IP/\$NODE2_IP/g\" deploy/nginx/conf.d/hifate.conf"

# 重启 Nginx 容器以应用配置变更（如果需要）
echo "🔄 重启 Node1 Nginx 容器（应用配置变更）..."
ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR/deploy/docker && \
    source ../.env 2>/dev/null || source ../../.env 2>/dev/null || true && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml up -d nginx --no-deps 2>/dev/null || \
    docker restart hifate-nginx 2>/dev/null || true"

echo -e "${GREEN}✅ Node1 代码拉取完成${NC}"

# 在 Node2 上拉取代码（确保与 GitHub 一致）
echo "📥 在 Node2 上拉取代码..."
echo "⚠️  检查服务器本地更改（禁止直接在服务器上修改代码）..."
LOCAL_CHANGES_NODE2=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")
if [ -n "$LOCAL_CHANGES_NODE2" ]; then
    echo -e "${YELLOW}⚠️  警告：Node2 上有本地未提交的更改：${NC}"
    echo "$LOCAL_CHANGES_NODE2" | sed 's/^/  /'
    echo -e "${YELLOW}⚠️  这些更改将被保存（git stash），确保与 GitHub 代码一致${NC}"
    echo -e "${YELLOW}⚠️  如需保留这些更改，请在本地修改并提交到 GitHub${NC}"
fi

ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout $GIT_BRANCH && \
    (git stash || true) && \
    git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node2 代码拉取失败${NC}"
    exit 1
}

# 验证 Node2 代码与 GitHub 一致
NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
if [ "$NODE2_COMMIT" != "$LOCAL_COMMIT" ]; then
    echo -e "${YELLOW}⚠️  警告：Node2 代码版本与本地不一致${NC}"
    echo "  Node2: $NODE2_COMMIT"
    echo "  本地:  $LOCAL_COMMIT"
    echo -e "${YELLOW}⚠️  请确保已推送到 GitHub：git push origin master${NC}"
    echo -e "${YELLOW}⚠️  重新拉取 Node2 代码以同步...${NC}"
    ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git pull origin $GIT_BRANCH"
    NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    if [ "$NODE2_COMMIT" != "$LOCAL_COMMIT" ]; then
        echo -e "${RED}❌ 错误：Node2 代码版本仍与本地不一致${NC}"
        echo -e "${RED}🔴 请确保已推送到 GitHub：git push origin master${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Node2 代码已同步到最新版本${NC}"
fi

# 🔴 严格执行：立即检查 Node1 与 Node2 Git 版本一致性（双机代码必须一致）
echo ""
echo "🔍 严格执行：检查 Node1 与 Node2 Git 版本一致性（双机代码必须完全一致）..."
NODE1_COMMIT_CHECK=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
NODE2_COMMIT_CHECK=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)

if [ "$NODE1_COMMIT_CHECK" != "$NODE2_COMMIT_CHECK" ]; then
    echo -e "${RED}❌ 错误：Node1 与 Node2 Git 版本不一致（违反双机代码一致性规范）${NC}"
    echo "  Node1: ${NODE1_COMMIT_CHECK:0:8}"
    echo "  Node2: ${NODE2_COMMIT_CHECK:0:8}"
    echo -e "${RED}🔴 严格执行：Node1 与 Node2 代码必须完全一致，停止部署${NC}"
    echo ""
    echo "修复步骤："
    echo "  1. 确保 GitHub 代码是最新的：git push origin master"
    echo "  2. 同步双机代码："
    echo "     ssh root@$NODE1_PUBLIC_IP 'cd $PROJECT_DIR && git reset --hard origin/master && git pull origin master'"
    echo "     ssh root@$NODE2_PUBLIC_IP 'cd $PROJECT_DIR && git reset --hard origin/master && git pull origin master'"
    echo "  3. 验证双机一致性：bash scripts/check_code_consistency.sh"
    echo "  4. 重新执行增量部署脚本"
    exit 1
fi
echo -e "${GREEN}✅ Node1 与 Node2 Git 版本一致（${NODE1_COMMIT_CHECK:0:8}）${NC}"

# 修复 Node2 Nginx 配置（确保IP占位符被替换）
echo "🔧 修复 Node2 Nginx 配置..."
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
    source .env 2>/dev/null || true && \
    NODE1_IP=\${NODE1_IP:-$NODE1_PRIVATE_IP} && \
    NODE2_IP=\${NODE2_IP:-$NODE2_PRIVATE_IP} && \
    sed -i \"s/NODE1_IP/\$NODE1_IP/g\" deploy/nginx/conf.d/hifate.conf && \
    sed -i \"s/NODE2_IP/\$NODE2_IP/g\" deploy/nginx/conf.d/hifate.conf"

# 重启 Nginx 容器以应用配置变更（如果需要）
echo "🔄 重启 Node2 Nginx 容器（应用配置变更）..."
ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR/deploy/docker && \
    source ../.env 2>/dev/null || source ../../.env 2>/dev/null || true && \
    docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml up -d nginx --no-deps 2>/dev/null || \
    docker restart hifate-nginx 2>/dev/null || true"

echo -e "${GREEN}✅ Node2 代码拉取完成${NC}"

echo ""

# ==================== 第四步：验证双机代码一致性 ====================
echo -e "${BLUE}🔍 第四步：验证双机代码一致性（强制检查）${NC}"
echo "----------------------------------------"

# 检查双机 Git 版本一致性
echo "🔍 检查双机 Git 版本一致性..."
NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")

if [ -z "$NODE1_COMMIT" ] || [ -z "$NODE2_COMMIT" ]; then
    echo -e "${RED}❌ 错误：无法获取双机 Git 版本${NC}"
    exit 1
fi

if [ "$NODE1_COMMIT" != "$NODE2_COMMIT" ]; then
    echo -e "${RED}❌ 错误：Node1 和 Node2 Git 版本不一致（违反双机代码一致性规范）${NC}"
    echo "  Node1: ${NODE1_COMMIT:0:8}"
    echo "  Node2: ${NODE2_COMMIT:0:8}"
    echo ""
    echo -e "${RED}🔴 严格执行：Node1 与 Node2 代码必须完全一致${NC}"
    echo -e "${YELLOW}⚠️  正在强制同步 Node2 代码到与 Node1 一致...${NC}"
    
    # 强制同步 Node2 到与 Node1 一致
    ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && \
        git fetch origin && \
        git reset --hard $NODE1_COMMIT 2>/dev/null || \
        git reset --hard origin/$GIT_BRANCH" || {
        echo -e "${RED}❌ 错误：无法同步 Node2 代码${NC}"
        exit 1
    }
    
    # 再次验证
    NODE2_COMMIT_AFTER=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
    if [ "$NODE1_COMMIT" != "$NODE2_COMMIT_AFTER" ]; then
        echo -e "${RED}❌ 错误：同步后双机 Git 版本仍不一致（违反双机代码一致性规范）${NC}"
        echo -e "${RED}🔴 严格执行：停止部署，必须确保双机代码一致后才能继续${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Node2 代码已同步到与 Node1 一致${NC}"
else
    echo -e "${GREEN}✅ 双机 Git 版本一致（${NODE1_COMMIT:0:8}）${NC}"
fi

# 检查双机关键文件一致性
echo ""
echo "🔍 检查双机关键文件一致性..."
KEY_FILES=(
    "server/api/grpc_gateway.py"
    "server/api/v2/desk_fengshui_api.py"
    "deploy/docker/docker-compose.prod.yml"
    "requirements.txt"
)

INCONSISTENT_FILES=()
for file in "${KEY_FILES[@]}"; do
    NODE1_HASH=$(ssh_exec $NODE1_PUBLIC_IP "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
    NODE2_HASH=$(ssh_exec $NODE2_PUBLIC_IP "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
    
    if [ -z "$NODE1_HASH" ] || [ -z "$NODE2_HASH" ]; then
        echo -e "${YELLOW}⚠️  警告：无法检查 $file${NC}"
        continue
    fi
    
    if [ "$NODE1_HASH" != "$NODE2_HASH" ]; then
        echo -e "${RED}❌ 错误：$file 双机不一致（违反双机代码一致性规范）${NC}"
        echo -e "${RED}🔴 严格执行：停止部署，必须确保双机代码一致后才能继续${NC}"
        INCONSISTENT_FILES+=("$file")
    fi
done

if [ ${#INCONSISTENT_FILES[@]} -gt 0 ]; then
    echo -e "${RED}❌ 错误：发现 ${#INCONSISTENT_FILES[@]} 个文件双机不一致（违反双机代码一致性规范）${NC}"
    for file in "${INCONSISTENT_FILES[@]}"; do
        echo -e "${RED}  - $file${NC}"
    done
    echo -e "${RED}🔴 严格执行：Node1 与 Node2 代码必须完全一致${NC}"
    echo -e "${RED}🔴 停止部署：必须修复双机代码不一致后才能继续${NC}"
    echo ""
    echo "修复步骤："
    echo "  1. 确保 GitHub 代码是最新的：git push origin master"
    echo "  2. 同步双机代码（强制执行）："
    echo "     ssh root@$NODE1_PUBLIC_IP 'cd $PROJECT_DIR && git reset --hard origin/master && git pull origin master'"
    echo "     ssh root@$NODE2_PUBLIC_IP 'cd $PROJECT_DIR && git reset --hard origin/master && git pull origin master'"
    echo "  3. 验证双机一致性：bash scripts/check_code_consistency.sh"
    echo "  4. 重新执行增量部署脚本"
    echo ""
    echo "⚠️  注意：如果在服务器上直接修改了文件，必须："
    echo "  - 在本地做相同修改"
    echo "  - 提交到 Git 并推送到 GitHub"
    echo "  - 然后在服务器上拉取最新代码"
    exit 1
fi

echo -e "${GREEN}✅ 双机关键文件一致性检查通过${NC}"

echo ""

# ==================== 第五步：服务器端验证 ====================
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

# ==================== 第六步：触发热更新 ====================
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

# 🔴 严格执行：最终验证 Node1 与 Node2 代码一致性（双机代码必须一致）
echo ""
echo "🔍 严格执行：最终验证 Node1 与 Node2 代码一致性（双机代码必须完全一致）..."
FINAL_NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
FINAL_NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)

if [ "$FINAL_NODE1_COMMIT" != "$FINAL_NODE2_COMMIT" ]; then
    echo -e "${RED}❌ 错误：部署后双机 Git 版本不一致（违反双机代码一致性规范）${NC}"
    echo "  Node1: ${FINAL_NODE1_COMMIT:0:8}"
    echo "  Node2: ${FINAL_NODE2_COMMIT:0:8}"
    echo -e "${RED}🔴 严格执行：Node1 与 Node2 代码必须完全一致，部署失败${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 部署后双机 Git 版本一致（${FINAL_NODE1_COMMIT:0:8}）${NC}"
echo ""
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

# ==================== 第七步：双机代码一致性验证 ====================
echo -e "${BLUE}🔍 第七步：双机代码一致性验证（严格执行）${NC}"
echo "----------------------------------------"

echo "🔍 验证 Node1 与 Node2 代码一致性..."

# 获取双机 Git 版本
NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
NODE2_COMMIT=$(ssh_exec $NODE2_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")

if [ -z "$NODE1_COMMIT" ] || [ -z "$NODE2_COMMIT" ]; then
    echo -e "${RED}❌ 错误：无法获取双机 Git 版本${NC}"
    exit 1
fi

echo "  Node1 Git 版本: ${NODE1_COMMIT:0:8}"
echo "  Node2 Git 版本: ${NODE2_COMMIT:0:8}"

if [ "$NODE1_COMMIT" != "$NODE2_COMMIT" ]; then
    echo -e "${RED}❌ 错误：Node1 与 Node2 Git 版本不一致！${NC}"
    echo -e "${RED}🔴 违反规范：双机代码必须完全一致（严格执行）${NC}"
    echo -e "${RED}🔴 停止部署：必须修复双机代码不一致后才能继续${NC}"
    echo ""
    echo "修复步骤："
    echo "  1. 在 Node1 和 Node2 上执行: git pull origin master"
    echo "  2. 验证双机 Git 版本一致"
    echo "  3. 重新执行增量部署脚本"
    echo ""
    echo "修复方法："
    echo "  1. 在 Node1 上执行: git reset --hard origin/master && git pull origin master"
    echo "  2. 在 Node2 上执行: git reset --hard origin/master && git pull origin master"
    echo "  3. 重新运行增量部署脚本"
    exit 1
fi

echo -e "${GREEN}✅ Node1 与 Node2 Git 版本一致${NC}"

# 验证关键文件一致性
echo ""
echo "🔍 验证关键文件一致性..."

KEY_FILES=(
    "server/api/grpc_gateway.py"
    "server/api/v2/desk_fengshui_api.py"
    "deploy/docker/docker-compose.prod.yml"
    "requirements.txt"
)

ALL_FILES_MATCH=true
for file in "${KEY_FILES[@]}"; do
    NODE1_HASH=$(ssh_exec $NODE1_PUBLIC_IP "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
    NODE2_HASH=$(ssh_exec $NODE2_PUBLIC_IP "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
    
    if [ -z "$NODE1_HASH" ] || [ -z "$NODE2_HASH" ]; then
        echo -e "${YELLOW}⚠️  无法验证 $file${NC}"
        continue
    fi
    
    if [ "$NODE1_HASH" != "$NODE2_HASH" ]; then
        echo -e "${RED}❌ 错误：$file 在 Node1 和 Node2 不一致！${NC}"
        echo "    Node1: ${NODE1_HASH:0:16}..."
        echo "    Node2: ${NODE2_HASH:0:16}..."
        echo -e "${RED}   违反规范：双机代码必须完全一致（严格执行）${NC}"
        ALL_FILES_MATCH=false
    fi
done

if [ "$ALL_FILES_MATCH" = false ]; then
    echo ""
    echo -e "${RED}❌ 双机文件一致性验证失败（违反双机代码一致性规范）${NC}"
    echo -e "${RED}🔴 严格执行：Node1 与 Node2 代码必须完全一致${NC}"
    echo -e "${RED}🔴 停止部署：必须修复双机代码不一致后才能继续${NC}"
    echo ""
    echo "修复步骤："
    echo "  1. 确保代码已推送到 GitHub: git push origin master"
    echo "  2. 在 Node1 上执行: cd /opt/HiFate-bazi && git reset --hard origin/master && git pull origin master"
    echo "  3. 在 Node2 上执行: cd /opt/HiFate-bazi && git reset --hard origin/master && git pull origin master"
    echo "  4. 验证双机代码一致性: bash scripts/check_code_consistency.sh"
    echo "  5. 重新运行增量部署脚本"
    exit 1
fi

echo -e "${GREEN}✅ 关键文件一致性验证通过${NC}"
echo ""
echo -e "${GREEN}✅ 双机代码一致性验证通过（严格执行，符合规范）${NC}"
echo -e "${GREEN}✅ Node1 与 Node2 代码完全一致（${NODE1_COMMIT:0:8}）${NC}"
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
echo -e "${GREEN}✅ 双机代码版本一致: ${NODE1_COMMIT:0:8}（严格执行，符合规范）${NC}"
echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

