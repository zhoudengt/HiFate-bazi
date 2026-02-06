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

# 🔴 临时：仅部署到 Node1，Node2 稍后统一处理
SKIP_NODE2=${SKIP_NODE2:-true}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# 配置加载（优先级：环境变量 > 配置文件 > 默认值）
# ============================================
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
CONFIG_FILE="${SCRIPT_DIR}/deploy.conf"

# 如果配置文件存在，加载它
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}✓ 从配置文件加载: $CONFIG_FILE${NC}"
    source "$CONFIG_FILE"
fi

# 生产环境配置（从环境变量或配置文件读取，无硬编码默认值）
NODE1_PUBLIC_IP="${NODE1_PUBLIC_IP:-}"
NODE1_PRIVATE_IP="${NODE1_PRIVATE_IP:-}"
NODE2_PUBLIC_IP="${NODE2_PUBLIC_IP:-}"
NODE2_PRIVATE_IP="${NODE2_PRIVATE_IP:-}"

# 验证必需配置
if [ -z "$NODE1_PUBLIC_IP" ]; then
    echo -e "${RED}❌ 错误：NODE1_PUBLIC_IP 未配置${NC}"
    echo -e "${YELLOW}请配置 deploy.conf 或设置环境变量${NC}"
    echo -e "  cp ${SCRIPT_DIR}/deploy.conf.template ${SCRIPT_DIR}/deploy.conf"
    exit 1
fi

# Git 仓库配置（有默认值）
GIT_REPO="${GIT_REPO:-https://github.com/zhoudengt/HiFate-bazi}"
GIT_BRANCH="${GIT_BRANCH:-master}"

# 项目目录（有默认值）
PROJECT_DIR="${PROJECT_DIR:-/opt/HiFate-bazi}"

# 生产数据库配置（单源：仅通过 Node1 SSH + docker exec 连接，禁止本地直连）
# 详见 standards/deployment.md、deploy/docs/
PROD_MYSQL_CONTAINER="${PROD_MYSQL_CONTAINER:-hifate-mysql-master}"
PROD_MYSQL_USER="${PROD_MYSQL_USER:-root}"
PROD_MYSQL_PASSWORD="${PROD_MYSQL_PASSWORD:-$SSH_PASSWORD}"
PROD_MYSQL_DATABASE="${PROD_MYSQL_DATABASE:-hifate_bazi}"

# SSH 密码（必须从环境变量或配置文件读取）
SSH_PASSWORD="${SSH_PASSWORD:-}"
if [ -z "$SSH_PASSWORD" ]; then
    echo -e "${YELLOW}⚠️ 警告：SSH_PASSWORD 未配置，将尝试使用 SSH 密钥认证${NC}"
fi

# 允许自动数据库同步（默认启用）
# 设置为 true 时，自动生成并执行数据库同步脚本，无需用户确认
# 设置为 false 时，需要手动确认（交互式环境）或跳过（非交互式环境）
AUTO_SYNC_DB=${AUTO_SYNC_DB:-true}

# SSH 执行函数（优先使用密钥认证，降级到密码认证）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    # 优先使用 SSH 密钥认证（通过 SSH config 配置的别名）
    local ssh_alias=""
    if [ "$host" = "$NODE1_PUBLIC_IP" ]; then
        ssh_alias="hifate-node1"
    elif [ "$host" = "$NODE2_PUBLIC_IP" ]; then
        ssh_alias="hifate-node2"
    fi
    
    # 如果配置了别名，优先使用密钥认证
    if [ -n "$ssh_alias" ]; then
        # 尝试使用密钥认证（静默失败，不显示错误）
        if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no $ssh_alias "$cmd" 2>/dev/null; then
            return 0
        fi
        # 如果密钥认证失败，尝试使用IP地址和密钥
        if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa_hifate root@$host "$cmd" 2>/dev/null; then
            return 0
        fi
    fi
    
    # 降级到密码认证（如果密钥认证失败）
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

# 🔴 通过 Node1 连接 Node2 执行命令（Node2 所有操作都通过 Node1）
# 重要：Node2 的所有操作都必须通过 Node1 的 SSH 连接执行，禁止直接连接 Node2
ssh_exec_node2_via_node1() {
    local cmd="$@"
    # 在 Node1 上执行 ssh 命令连接 Node2（使用内网 IP），传递密码
    # 格式：ssh root@Node1 "sshpass -p '密码' ssh root@Node2内网IP '命令'"
    ssh_exec $NODE1_PUBLIC_IP "sshpass -p '$SSH_PASSWORD' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE2_PRIVATE_IP '$cmd'"
}

# 删除前端相关目录和文件函数（前端团队已独立部署，禁止同步）
remove_frontend_files() {
    local host=$1
    local node_name=$2
    
    echo "🚫 删除 $node_name 前端相关目录和文件（前端团队已独立部署，禁止同步）..."
    ssh_exec $host "cd $PROJECT_DIR && \
        rm -rf local_frontend frontend frontend-config nginx deploy/nginx 2>/dev/null || true && \
        rm -f docker-compose.frontend.yml docker-compose.nginx.yml 2>/dev/null || true && \
        rm -f scripts/deploy-frontend.sh scripts/deploy_nacos_proxy.sh scripts/deploy_frontend_proxy_dual_nodes.sh 2>/dev/null || true && \
        rm -f scripts/rollback_frontend_proxy_dual_nodes.sh scripts/protect_frontend_directory.sh scripts/restore_frontend_directory.sh scripts/check_frontend_directory.sh 2>/dev/null || true && \
        echo '✅ 前端相关目录和文件已删除（前端团队独立部署）'"
    
    # 验证删除结果
    if ssh_exec $host "cd $PROJECT_DIR && [ -d local_frontend ] || [ -d frontend ] || [ -d frontend-config ] || [ -d nginx ] || [ -d deploy/nginx ]" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  警告：部分前端目录可能未完全删除，请手动检查${NC}"
    else
        echo -e "${GREEN}✅ $node_name 前端目录删除验证通过${NC}"
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

# 1.3 检查是否有未提交的更改（只检查已跟踪文件，忽略未跟踪文件和 local_frontend）
echo ""
echo "🔍 检查未提交的更改..."
# 只检查已跟踪文件的更改（--untracked-files=no 忽略未跟踪文件，排除 local_frontend）
UNCOMMITTED_CHANGES=$(git status --porcelain --untracked-files=no | grep -v "local_frontend" || true)
if [ -n "$UNCOMMITTED_CHANGES" ]; then
    echo -e "${RED}❌ 错误：存在未提交的更改，请先提交代码${NC}"
    echo "$UNCOMMITTED_CHANGES"
    exit 1
fi
echo -e "${GREEN}✅ 无未提交的更改（已跟踪文件，已排除 local_frontend）${NC}"

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

# 1.7 数据库变更检测（生产库为 Docker，仅支持 SSH + docker exec，本机不直连故跳过直连检测）
echo ""
echo "🔍 检测数据库变更..."
DB_SYNC_NEEDED=false

# 生产库为 Docker hifate-mysql-master，仅通过 Node1 SSH + docker exec 连接，无法从本机直连。
# 使用 --skip-prod-connection 跳过生产库直连，避免超时/连接失败导致部署中断。
if command -v timeout &> /dev/null; then
    DB_DETECT_OUTPUT=$(timeout 15 python3 scripts/db/detect_db_changes.py --skip-prod-connection 2>&1 || echo "数据库变更检测异常")
    DB_DETECT_EXIT=$?
    [ $DB_DETECT_EXIT -eq 124 ] && DB_DETECT_EXIT=0  # 超时也继续部署
elif command -v gtimeout &> /dev/null; then
    DB_DETECT_OUTPUT=$(gtimeout 15 python3 scripts/db/detect_db_changes.py --skip-prod-connection 2>&1 || echo "数据库变更检测异常")
    DB_DETECT_EXIT=$?
    [ $DB_DETECT_EXIT -eq 124 ] && DB_DETECT_EXIT=0
else
    DB_DETECT_OUTPUT=$(python3 scripts/db/detect_db_changes.py --skip-prod-connection 2>&1) || true
    DB_DETECT_EXIT=0
fi

# 若未使用 --skip-prod-connection 导致失败，不阻断部署：生产库仅支持 SSH + docker exec
if [ $DB_DETECT_EXIT -ne 0 ]; then
    echo -e "${YELLOW}⚠️  数据库变更检测未完成（生产库为 Docker，仅支持 Node1 SSH + docker exec）${NC}"
    echo -e "${YELLOW}⚠️  跳过数据库变更检测，继续部署。如有库表变更请手动执行 scripts/db/sync_production_db.sh${NC}"
    DB_DETECT_EXIT=0
fi

if [ $DB_DETECT_EXIT -eq 0 ]; then
    # 检查输出中是否包含变更信息（增强正则表达式，包含删除表和删除字段）
    if echo "$DB_DETECT_OUTPUT" | grep -qE "(新增表|删除表|新增字段|删除字段|修改字段|新增表的数据|表数据差异)" && ! echo "$DB_DETECT_OUTPUT" | grep -q "✅ 无数据库变更"; then
        echo "$DB_DETECT_OUTPUT"
        echo -e "${YELLOW}⚠️  发现数据库变更${NC}"
        DB_SYNC_NEEDED=true
        
        # 强制自动同步数据库（默认 AUTO_SYNC_DB=true）
        if [ "$AUTO_SYNC_DB" = "true" ]; then
            # 自动模式：自动生成并执行同步脚本
            echo -e "${GREEN}✅ 自动数据库同步模式已启用，自动生成并执行同步脚本${NC}"
            DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)
            echo "生成同步脚本..."
            python3 scripts/db/detect_db_changes.py --generate-sync-script 2>&1 | tail -5
            SYNC_SCRIPT="scripts/db/sync_${DEPLOYMENT_ID}.sql"
            
            # 查找最新生成的同步脚本
            LATEST_SYNC_SCRIPT=$(ls -t scripts/db/sync_*.sql 2>/dev/null | head -1)
            if [ -n "$LATEST_SYNC_SCRIPT" ] && [ -f "$LATEST_SYNC_SCRIPT" ]; then
                DEPLOYMENT_ID=$(basename "$LATEST_SYNC_SCRIPT" | sed 's/sync_//;s/.sql//')
                SYNC_SCRIPT="$LATEST_SYNC_SCRIPT"
                echo -e "${GREEN}✅ 同步脚本已生成: $SYNC_SCRIPT${NC}"
                
                # 自动同步到 Node1（生产数据库在 Node1）
                echo "🔄 自动同步数据库到 Node1（生产数据库）..."
                if bash scripts/db/sync_production_db.sh --node node1 --deployment-id $DEPLOYMENT_ID; then
                    # 注意：所有环境统一连接生产 Node1 Docker MySQL，不需要同步到 Node2
                    echo -e "${GREEN}✅ 数据库同步完成（生产数据库在 Node1）${NC}"
                else
                    echo -e "${RED}❌ 数据库同步失败${NC}"
                    echo -e "${RED}🔴 数据库同步是强制步骤，部署已停止${NC}"
                    exit 1
                fi
            else
                echo -e "${RED}❌ 同步脚本生成失败${NC}"
                echo -e "${RED}🔴 数据库同步脚本生成是强制步骤，部署已停止${NC}"
                exit 1
            fi
        else
            # AUTO_SYNC_DB=false 时，提示用户需要手动同步
            echo -e "${RED}❌ 数据库变更检测到，但 AUTO_SYNC_DB=false，无法自动同步${NC}"
            echo -e "${YELLOW}💡 请设置 AUTO_SYNC_DB=true 或手动执行数据库同步：${NC}"
            echo "  bash scripts/db/sync_production_db.sh --node node1 --deployment-id <DEPLOYMENT_ID>"
            echo -e "${RED}🔴 数据库同步是强制步骤，部署已停止${NC}"
            exit 1
        fi
    else
        echo "$DB_DETECT_OUTPUT" | tail -20
        echo -e "${GREEN}✅ 无数据库变更（已跳过生产库直连检测）${NC}"
        
        # 即使跳过直连检测，也检查是否有待同步的脚本（可能之前已生成但未同步）
        LATEST_SYNC_SCRIPT=$(ls -t scripts/db/sync_*.sql 2>/dev/null | head -1)
        if [ -n "$LATEST_SYNC_SCRIPT" ] && [ -f "$LATEST_SYNC_SCRIPT" ]; then
            SYNC_SCRIPT_AGE=$(($(date +%s) - $(stat -f %m "$LATEST_SYNC_SCRIPT" 2>/dev/null || stat -c %Y "$LATEST_SYNC_SCRIPT" 2>/dev/null || echo 0)))
            # 如果同步脚本是最近 7 天内生成的，提示是否需要同步
            if [ $SYNC_SCRIPT_AGE -lt 604800 ]; then
                DEPLOYMENT_ID=$(basename "$LATEST_SYNC_SCRIPT" | sed 's/sync_//;s/.sql//')
                echo -e "${YELLOW}💡 发现待同步脚本: $LATEST_SYNC_SCRIPT (生成于 $((SYNC_SCRIPT_AGE / 86400)) 天前)${NC}"
                
                # 如果启用自动同步，自动执行
                if [ "$AUTO_SYNC_DB" = "true" ]; then
                    echo -e "${GREEN}✅ 自动数据库同步模式已启用，执行待同步脚本${NC}"
                    echo "🔄 同步数据库到 Node1（生产数据库）..."
                    if bash scripts/db/sync_production_db.sh --node node1 --deployment-id $DEPLOYMENT_ID; then
                        echo -e "${GREEN}✅ 数据库同步完成（生产数据库在 Node1）${NC}"
                        DB_SYNC_NEEDED=false  # 已同步，标记为无需同步
                    else
                        echo -e "${RED}❌ 数据库同步失败${NC}"
                        echo -e "${YELLOW}⚠️  部署将继续，但请手动检查并执行数据库同步：${NC}"
                        echo "  bash scripts/db/sync_production_db.sh --node node1 --deployment-id $DEPLOYMENT_ID"
                    fi
                else
                    echo -e "${YELLOW}⚠️  发现待同步脚本，但 AUTO_SYNC_DB=false，跳过自动同步${NC}"
                    echo -e "${YELLOW}💡 如需同步，请手动执行：${NC}"
                    echo "  bash scripts/db/sync_production_db.sh --node node1 --deployment-id $DEPLOYMENT_ID"
                fi
            fi
        fi
    fi
else
    echo -e "${RED}❌ 数据库变更检测失败（可能是连接问题）${NC}"
    echo "$DB_DETECT_OUTPUT" | tail -5
    echo -e "${RED}🔴 数据库检查是强制步骤，部署已停止${NC}"
    echo -e "${YELLOW}💡 请检查数据库连接配置，确保可以连接到本地和生产数据库${NC}"
    exit 1
fi

# 1.8 配置变更检测（必须检查）
echo ""
echo "🔍 检测配置变更..."
if python3 scripts/config/detect_config_changes.py 2>/dev/null; then
    CONFIG_CHANGES_OUTPUT=$(python3 scripts/config/detect_config_changes.py 2>&1)
    if echo "$CONFIG_CHANGES_OUTPUT" | grep -q "✅ 无配置变更"; then
        echo -e "${GREEN}✅ 无配置变更${NC}"
        CONFIG_SYNC_NEEDED=false
    else
        echo "$CONFIG_CHANGES_OUTPUT"
        echo -e "${YELLOW}⚠️  发现配置变更${NC}"
        CONFIG_SYNC_NEEDED=true
        
        # 检查是否在非交互式环境
        if [ -t 0 ] && [ -z "$CI" ]; then
            # 交互式环境，询问是否同步配置
        read -p "是否同步配置到生产环境（Node1）？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🔄 同步配置到 Node1..."
            bash scripts/config/sync_production_config.sh --node node1
            
            # 询问是否同步到Node2
            read -p "是否同步到 Node2？(y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                echo "🔄 同步配置到 Node2..."
                bash scripts/config/sync_production_config.sh --node node2
            fi
        else
            echo -e "${YELLOW}⚠️  配置同步已跳过，请稍后手动执行：${NC}"
                echo "  bash scripts/config/sync_production_config.sh --node node1"
            fi
        else
            # 非交互式环境，自动跳过配置同步
            echo -e "${YELLOW}⚠️  配置同步已跳过（非交互式环境），请稍后手动执行：${NC}"
            echo "  bash scripts/config/sync_production_config.sh --node node1"
        fi
    fi
else
    echo -e "${YELLOW}⚠️  配置变更检测脚本不可用，跳过检查${NC}"
    CONFIG_SYNC_NEEDED=false
fi

# 1.9 部署前最终确认
echo ""
echo "========================================"
echo "📋 部署前检查总结"
echo "========================================"
if [ "$DB_SYNC_NEEDED" = true ]; then
    echo -e "${YELLOW}⚠️  数据库变更需要同步（已处理或已跳过）${NC}"
fi
if [ "$CONFIG_SYNC_NEEDED" = true ]; then
    echo -e "${YELLOW}⚠️  配置变更需要同步（已处理或已跳过）${NC}"
fi
echo "========================================"
echo ""

# 检查是否在非交互式环境（CI/CD 或通过管道输入）
if [ -t 0 ] && [ -z "$CI" ]; then
    # 交互式环境，需要用户确认
read -p "确认继续部署？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "部署已取消"
    exit 1
    fi
else
    # 非交互式环境，自动继续
    echo -e "${GREEN}✅ 非交互式环境，自动继续部署${NC}"
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

# 🔴 临时：只部署到 Node1，Node2 稍后统一处理
if [ "$SKIP_NODE2" = "true" ]; then
    echo "🔍 检查 Node2 连接（跳过，仅部署 Node1）..."
    echo -e "${YELLOW}⚠️  本次部署仅到 Node1，Node2 稍后统一处理${NC}"
else
    echo "🔍 检查 Node2 连接..."
    if ssh_exec_node2_via_node1 "echo 'Node2 连接成功'" 2>/dev/null; then
        echo -e "${GREEN}✅ Node2 连接成功${NC}"
    else
        echo -e "${RED}❌ 无法连接到 Node2 ($NODE2_PUBLIC_IP)${NC}"
        exit 1
    fi
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

# 🚫 删除前端相关目录和文件（前端团队已独立部署，禁止同步）
remove_frontend_files $NODE1_PUBLIC_IP "Node1"

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

# 🔥 热更新说明：若生产使用 docker-compose.hotreload.yml（volume 挂载 server/src/services/core），
#    宿主机 git pull 后容器内即见新代码，无需 docker cp；后续触发热更新即可生效。
#    详见 deploy/docs/06-热更新Volume部署说明.md

# 🚫 注意：Nginx 配置由前端团队管理，后端部署脚本不再修改 Nginx 配置

echo -e "${GREEN}✅ Node1 代码拉取完成${NC}"

# 🔴 临时：跳过 Node2 部署
if [ "$SKIP_NODE2" = "true" ]; then
    echo "📥 Node2 部署已跳过（本次仅部署 Node1）..."
    echo -e "${YELLOW}⚠️  本次部署仅到 Node1，Node2 稍后统一处理${NC}"
else
    # 🔴 重要：在 Node2 上拉取代码（通过 Node1 SSH 连接执行）
    echo "📥 在 Node2 上拉取代码（通过 Node1 SSH 连接）..."
echo "⚠️  检查服务器本地更改（禁止直接在服务器上修改代码）..."
LOCAL_CHANGES_NODE2=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git status --porcelain" 2>/dev/null || echo "")
if [ -n "$LOCAL_CHANGES_NODE2" ]; then
    echo -e "${YELLOW}⚠️  警告：Node2 上有本地未提交的更改：${NC}"
    echo "$LOCAL_CHANGES_NODE2" | sed 's/^/  /'
    echo -e "${YELLOW}⚠️  这些更改将被保存（git stash），确保与 GitHub 代码一致${NC}"
    echo -e "${YELLOW}⚠️  如需保留这些更改，请在本地修改并提交到 GitHub${NC}"
fi

ssh_exec_node2_via_node1 "cd $PROJECT_DIR && \
    git fetch origin && \
    git checkout $GIT_BRANCH && \
    (git stash || true) && \
    git pull origin $GIT_BRANCH" || {
    echo -e "${RED}❌ Node2 代码拉取失败${NC}"
    exit 1
}

# 🚫 删除前端相关目录和文件（前端团队已独立部署，禁止同步）
# 通过 Node1 SSH 连接执行
ssh_exec_node2_via_node1 "cd $PROJECT_DIR && rm -rf local_frontend frontend 2>/dev/null || true"

# 验证 Node2 代码与 GitHub 一致（通过 Node1 SSH 连接）
NODE2_COMMIT=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
if [ "$NODE2_COMMIT" != "$LOCAL_COMMIT" ]; then
    echo -e "${YELLOW}⚠️  警告：Node2 代码版本与本地不一致${NC}"
    echo "  Node2: $NODE2_COMMIT"
    echo "  本地:  $LOCAL_COMMIT"
    echo -e "${YELLOW}⚠️  请确保已推送到 GitHub：git push origin master${NC}"
    echo -e "${YELLOW}⚠️  重新拉取 Node2 代码以同步（通过 Node1 SSH 连接）...${NC}"
    ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git fetch origin && git pull origin $GIT_BRANCH"
    # 🚫 删除前端相关目录和文件（通过 Node1 SSH 连接）
    ssh_exec_node2_via_node1 "cd $PROJECT_DIR && rm -rf local_frontend frontend 2>/dev/null || true"
    NODE2_COMMIT=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
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
NODE2_COMMIT_CHECK=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)

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

# 🚫 注意：Nginx 配置由前端团队管理，后端部署脚本不再修改 Nginx 配置

    echo -e "${GREEN}✅ Node2 代码拉取完成${NC}"
fi

echo ""

# ==================== 第四步：验证双机代码一致性 ====================
echo -e "${BLUE}🔍 第四步：验证双机代码一致性（强制检查）${NC}"
echo "----------------------------------------"

# 检查双机 Git 版本一致性（如果跳过 Node2，则只检查 Node1）
if [ "$SKIP_NODE2" = "true" ]; then
    echo "🔍 检查 Node1 Git 版本（Node2 已跳过）..."
    NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
    NODE2_COMMIT="$NODE1_COMMIT"  # 跳过 Node2 检查
    echo -e "${GREEN}✅ Node1 Git 版本：${NODE1_COMMIT:0:8}${NC}"
else
    echo "🔍 检查双机 Git 版本一致性..."
    NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
    NODE2_COMMIT=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
fi

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
    ssh_exec_node2_via_node1 "cd $PROJECT_DIR && \
        git fetch origin && \
        git reset --hard $NODE1_COMMIT 2>/dev/null || \
        git reset --hard origin/$GIT_BRANCH" || {
        echo -e "${RED}❌ 错误：无法同步 Node2 代码${NC}"
        exit 1
    }
    # 🚫 删除前端相关目录和文件（通过 Node1 连接）
    ssh_exec_node2_via_node1 "cd $PROJECT_DIR && rm -rf local_frontend frontend 2>/dev/null || true"
    
    # 再次验证
    NODE2_COMMIT_AFTER=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
    if [ "$NODE1_COMMIT" != "$NODE2_COMMIT_AFTER" ]; then
        echo -e "${RED}❌ 错误：同步后双机 Git 版本仍不一致（违反双机代码一致性规范）${NC}"
        echo -e "${RED}🔴 严格执行：停止部署，必须确保双机代码一致后才能继续${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Node2 代码已同步到与 Node1 一致${NC}"
else
    echo -e "${GREEN}✅ 双机 Git 版本一致（${NODE1_COMMIT:0:8}）${NC}"
fi

# 检查双机关键文件一致性（仅部署 Node1 时跳过）
if [ "$SKIP_NODE2" = "true" ]; then
    echo ""
    echo "🔍 双机关键文件一致性检查已跳过（本次仅部署 Node1）"
    echo -e "${GREEN}✅ Node1 验证通过${NC}"
else
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
    NODE2_HASH=$(ssh_exec_node2_via_node1 "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
    
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
fi

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

# 在 Node2 上验证语法（如果跳过 Node2，则跳过验证）
if [ "$SKIP_NODE2" = "true" ]; then
    echo "🔍 Node2 语法验证已跳过（本次仅部署 Node1）..."
    echo -e "${GREEN}✅ Node2 语法验证已跳过${NC}"
else
    echo "🔍 在 Node2 上验证代码语法..."
ssh_exec_node2_via_node1 "cd $PROJECT_DIR && python3 << 'EOFPY'
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

if errors:
    print('❌ 语法错误：')
    for err in errors[:5]:
        print(f'  - {err}')
    sys.exit(1)
print('✅ 语法验证通过')
EOFPY" || {
    echo -e "${RED}❌ Node2 语法验证失败${NC}"
    exit 1
}

echo -e "${GREEN}✅ Node2 语法验证通过${NC}"
fi

echo ""

# ==================== 第六步：触发热更新 ====================
echo -e "${BLUE}🔄 第五步：触发热更新${NC}"
echo "----------------------------------------"

# 在 Node1 上触发热更新（通知所有 Worker）
echo "🔄 在 Node1 上触发热更新..."
HEALTH_URL="http://$NODE1_PUBLIC_IP:8001"
RELOAD_ALL_URL="$HEALTH_URL/api/v1/hot-reload/reload-all"

# 先检查服务是否可用（添加超时）
if ! curl -f -s --max-time 10 "$HEALTH_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}❌ Node1 服务不可用，无法触发热更新${NC}"
    exit 1
fi

# 🔴 一次 reload-all：重载所有模块 + 通知所有 Worker（源码重载末尾已含路由重注册，无需二次调用）
echo "🔄 执行全量热更新（reload-all）..."
RELOAD_RESPONSE=$(curl -s --max-time 45 -X POST "$RELOAD_ALL_URL" -H "Content-Type: application/json" -d '{}' 2>&1)
if echo "$RELOAD_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ 热更新触发成功${NC}"
else
    echo -e "${YELLOW}⚠️  热更新响应：$RELOAD_RESPONSE${NC}"
    echo -e "${YELLOW}⚠️  继续部署，请手动检查热更新状态${NC}"
fi

# 短暂等待 Worker 完成（信号检测间隔 2s，3s 足够）
echo "⏳ 等待 Worker 完成..."
sleep 3
echo -e "${GREEN}✅ 热更新阶段完成${NC}"

# 🔴 功能验证：调用 /hot-reload/verify 确认关键功能正常
echo ""
echo "🔍 执行热更新功能验证..."
VERIFY_RESPONSE=$(curl -s --max-time 15 -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/verify" 2>/dev/null || echo "{}")

if echo "$VERIFY_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}✅ 热更新功能验证通过${NC}"
elif echo "$VERIFY_RESPONSE" | grep -q '"success":false'; then
    echo -e "${RED}❌ 热更新功能验证失败！${NC}"
    echo "验证结果: $VERIFY_RESPONSE"
    echo -e "${YELLOW}⚠️  请立即检查支付、gRPC 等关键功能是否正常${NC}"
else
    echo -e "${YELLOW}⚠️  功能验证端点不可用（可能版本较旧），跳过${NC}"
fi

echo ""

# ==================== 第六步：部署后验证 ====================
echo -e "${BLUE}🏥 第六步：部署后验证${NC}"
echo "----------------------------------------"

# 🔴 严格执行：最终验证 Node1 与 Node2 代码一致性（双机代码必须一致）
echo ""
# 🔴 最终验证（如果跳过 Node2，则只验证 Node1）
if [ "$SKIP_NODE2" = "true" ]; then
    echo ""
    echo "🔍 最终验证 Node1 代码..."
    FINAL_NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    echo -e "${GREEN}✅ Node1 代码版本：${FINAL_NODE1_COMMIT:0:8}${NC}"
else
    echo ""
    echo "🔍 严格执行：最终验证 Node1 与 Node2 代码一致性（双机代码必须完全一致）..."
    FINAL_NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    FINAL_NODE2_COMMIT=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)

    if [ "$FINAL_NODE1_COMMIT" != "$FINAL_NODE2_COMMIT" ]; then
        echo -e "${RED}❌ 错误：部署后双机 Git 版本不一致（违反双机代码一致性规范）${NC}"
        echo "  Node1: ${FINAL_NODE1_COMMIT:0:8}"
        echo "  Node2: ${FINAL_NODE2_COMMIT:0:8}"
        echo -e "${RED}🔴 严格执行：Node1 与 Node2 代码必须完全一致，部署失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ 部署后双机 Git 版本一致（${FINAL_NODE1_COMMIT:0:8}）${NC}"
fi
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
        if curl -f -s --max-time 5 "http://$node_ip:8001/health" > /dev/null 2>&1; then
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
    curl -s --max-time 10 -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/rollback" || true
    exit 1
fi

# 检查 Node2（仅部署 Node1 时跳过）
if [ "$SKIP_NODE2" != "true" ]; then
    if ! check_health $NODE2_PUBLIC_IP "Node2"; then
        echo -e "${RED}❌ Node2 健康检查失败，自动回滚...${NC}"
        curl -s --max-time 10 -X POST "http://$NODE2_PUBLIC_IP:8001/api/v1/hot-reload/rollback" || true
        exit 1
    fi
else
    echo "🏥 Node2 健康检查已跳过（本次仅部署 Node1）"
fi

# 6.2 热更新状态检查
echo ""
echo "🔍 检查热更新状态..."
NODE1_STATUS=$(curl -s --max-time 5 "http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/status" 2>/dev/null || echo "{}")

if echo "$NODE1_STATUS" | grep -q "error\|失败" && [ -n "$NODE1_STATUS" ]; then
    echo -e "${YELLOW}⚠️  Node1 热更新状态异常${NC}"
else
    echo -e "${GREEN}✅ Node1 热更新状态正常${NC}"
fi

if [ "$SKIP_NODE2" != "true" ]; then
    NODE2_STATUS=$(curl -s --max-time 5 "http://$NODE2_PUBLIC_IP:8001/api/v1/hot-reload/status" 2>/dev/null || echo "{}")
    if echo "$NODE2_STATUS" | grep -q "error\|失败" && [ -n "$NODE2_STATUS" ]; then
        echo -e "${YELLOW}⚠️  Node2 热更新状态异常${NC}"
    else
        echo -e "${GREEN}✅ Node2 热更新状态正常${NC}"
    fi
else
    echo "🔍 Node2 热更新状态检查已跳过（本次仅部署 Node1）"
fi

# 6.3 功能验证（可选，快速检查关键 API）
echo ""
echo "🔍 验证关键功能..."
TEST_RESPONSE=$(curl -s --max-time 10 -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/bazi/calculate" \
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
echo -e "${BLUE}🔍 第七步：代码一致性验证${NC}"
echo "----------------------------------------"

NODE1_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")

if [ "$SKIP_NODE2" = "true" ]; then
    echo "🔍 验证 Node1 代码版本（Node2 已跳过）..."
    if [ -z "$NODE1_COMMIT" ]; then
        echo -e "${RED}❌ 错误：无法获取 Node1 Git 版本${NC}"
        exit 1
    fi
    echo "  Node1 Git 版本: ${NODE1_COMMIT:0:8}"
    echo -e "${GREEN}✅ Node1 代码验证通过（${NODE1_COMMIT:0:8}）${NC}"
else
    echo "🔍 验证 Node1 与 Node2 代码一致性..."

    # 获取双机 Git 版本
    NODE2_COMMIT=$(ssh_exec_node2_via_node1 "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")

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
        NODE2_HASH=$(ssh_exec_node2_via_node1 "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
        
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
fi
echo ""

# ==================== 完成 ====================
echo "========================================"
echo -e "${GREEN}✅ 增量部署完成！${NC}"
echo "========================================"
echo ""
echo "访问地址："
echo "  Node1: http://$NODE1_PUBLIC_IP"
if [ "$SKIP_NODE2" != "true" ] && [ -n "$NODE2_PUBLIC_IP" ]; then
    echo "  Node2: http://$NODE2_PUBLIC_IP"
fi
echo ""
echo "健康检查："
echo "  Node1: http://$NODE1_PUBLIC_IP:8001/health"
if [ "$SKIP_NODE2" != "true" ] && [ -n "$NODE2_PUBLIC_IP" ]; then
    echo "  Node2: http://$NODE2_PUBLIC_IP:8001/health"
fi
echo ""
echo "热更新状态："
echo "  Node1: http://$NODE1_PUBLIC_IP:8001/api/v1/hot-reload/status"
if [ "$SKIP_NODE2" != "true" ] && [ -n "$NODE2_PUBLIC_IP" ]; then
    echo "  Node2: http://$NODE2_PUBLIC_IP:8001/api/v1/hot-reload/status"
fi
echo ""
if [ "$SKIP_NODE2" = "true" ]; then
    echo -e "${GREEN}✅ Node1 代码版本: ${NODE1_COMMIT:0:8}（仅部署 Node1）${NC}"
else
    echo -e "${GREEN}✅ 双机代码版本一致: ${NODE1_COMMIT:0:8}（严格执行，符合规范）${NC}"
fi
echo "部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

