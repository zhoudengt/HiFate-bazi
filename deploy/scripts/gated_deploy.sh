#!/bin/bash
# ============================================
# HiFate 门控发布脚本（物理隔离部署）
# ============================================
# 核心原则：Node2 作为发布前哨，验证通过后才允许部署到 Node1
#
# 流程：
#   1. 部署前检查（本地）
#   2. 部署到 Node2（前哨节点）
#   3. Node2 全量回归测试（门控）
#   4. 门控判断：全部通过 → 部署 Node1；任意失败 → 停止
#   5. 部署到 Node1（生产节点）— 自动识别 Phase 1/2 模式
#      Phase 1: 直接 git pull（无 staging 目录时）
#      Phase 2: git pull → staging → rsync → live（零停机隔离）
#   6. Node1 生产验证
#   7. 记录部署历史
#
# Phase 2 初始化（一次性）：
#   bash deploy/scripts/init_staging.sh
#
# 使用方法：
#   bash deploy/scripts/gated_deploy.sh                    # 标准门控发布
#   bash deploy/scripts/gated_deploy.sh --dry-run          # 只部署 Node2 跑测试，不动 Node1
#   bash deploy/scripts/gated_deploy.sh --skip-node2       # 紧急模式：跳过 Node2 直接部署 Node1
#   bash deploy/scripts/gated_deploy.sh --test-only        # 只跑 Node2 测试（不部署）
#   bash deploy/scripts/gated_deploy.sh --rollback         # 回滚 Node1 到上一次成功的 commit
#
# 环境变量/配置文件：
#   与 incremental_deploy_production.sh 共享 deploy.conf
# ============================================

set -e

# ==================== 脚本初始化 ====================

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)

# 加载门控检查函数库
source "${SCRIPT_DIR}/lib/gate_check.sh"

# 颜色定义（如果 common.sh 未加载）
RED="${RED:-\033[0;31m}"
GREEN="${GREEN:-\033[0;32m}"
YELLOW="${YELLOW:-\033[1;33m}"
BLUE="${BLUE:-\033[0;34m}"
NC="${NC:-\033[0m}"

# ==================== 参数解析 ====================

DRY_RUN=false
SKIP_NODE2=false
TEST_ONLY=false
ROLLBACK_MODE=false
NON_INTERACTIVE=false
TEST_CATEGORIES="basic stream payment"

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-node2)
            SKIP_NODE2=true
            shift
            ;;
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --rollback)
            ROLLBACK_MODE=true
            shift
            ;;
        --non-interactive|-y)
            NON_INTERACTIVE=true
            shift
            ;;
        --categories)
            TEST_CATEGORIES="$2"
            shift 2
            ;;
        --help|-h)
            echo "HiFate 门控发布脚本"
            echo ""
            echo "用法:"
            echo "  $0                          标准门控发布（Node2 验证 → Node1 部署）"
            echo "  $0 --dry-run                只部署 Node2 跑测试，不动 Node1"
            echo "  $0 --skip-node2             紧急模式：跳过 Node2 直接部署 Node1"
            echo "  $0 --test-only              只跑 Node2 回归测试（不部署代码）"
            echo "  $0 --rollback               回滚 Node1 到上一次部署前的 commit"
            echo "  $0 --non-interactive / -y   非交互模式（自动确认）"
            echo "  $0 --categories \"basic\"     自定义测试类别（默认: basic stream payment）"
            exit 0
            ;;
        *)
            echo -e "${RED}未知参数: $1${NC}"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# ==================== 加载配置 ====================

# 自动加载 .env（敏感变量持久化在本地，已 gitignore）
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

CONFIG_FILE="${SCRIPT_DIR}/deploy.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# 必需配置
NODE1_PUBLIC_IP="${NODE1_PUBLIC_IP:-}"
NODE2_PUBLIC_IP="${NODE2_PUBLIC_IP:-}"
NODE2_PRIVATE_IP="${NODE2_PRIVATE_IP:-}"
SSH_PASSWORD="${SSH_PASSWORD:-}"
PROJECT_DIR="${PROJECT_DIR:-/opt/HiFate-bazi}"
STAGING_DIR="${PROJECT_DIR}-staging"
ROLLBACK_DIR="${PROJECT_DIR}-rollback"
GIT_BRANCH="${GIT_BRANCH:-master}"

# Phase 2: 代码目录隔离 - 需要同步的目录列表
# 这些是容器 volume 挂载的代码目录
SYNC_DIRS="core shared server services proto src"

# 部署日志目录（相对于项目根目录）
DEPLOY_LOG_DIR="${PROJECT_ROOT}/deploy/logs"
mkdir -p "$DEPLOY_LOG_DIR"

# 部署 ID
DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)
DEPLOY_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# ==================== 验证配置 ====================

validate_config() {
    local errors=0
    
    if [ -z "$NODE1_PUBLIC_IP" ]; then
        echo -e "${RED}NODE1_PUBLIC_IP 未配置${NC}"
        ((errors++))
    fi
    
    if [ "$SKIP_NODE2" = "false" ] && [ -z "$NODE2_PUBLIC_IP" ]; then
        echo -e "${RED}NODE2_PUBLIC_IP 未配置（如需跳过 Node2 请使用 --skip-node2）${NC}"
        ((errors++))
    fi
    
    if [ $errors -gt 0 ]; then
        echo -e "${YELLOW}请配置 deploy.conf 或设置环境变量${NC}"
        exit 1
    fi
}

# ==================== SSH 函数（复用现有逻辑） ====================

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
    
    if [ -n "$ssh_alias" ]; then
        if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no $ssh_alias "$cmd" 2>/dev/null; then
            return 0
        fi
        if ssh -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa_hifate root@$host "$cmd" 2>/dev/null; then
            return 0
        fi
    fi
    
    # 降级到密码认证
    if [ -n "$SSH_PASSWORD" ] && command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    fi
}

ssh_exec_node2_via_node1() {
    local cmd="$@"
    if [ -n "$NODE2_PRIVATE_IP" ]; then
        ssh_exec $NODE1_PUBLIC_IP "sshpass -p '$SSH_PASSWORD' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE2_PRIVATE_IP '$cmd'"
    else
        ssh_exec $NODE2_PUBLIC_IP "$cmd"
    fi
}

# ==================== 回滚模式 ====================

if [ "$ROLLBACK_MODE" = "true" ]; then
    echo "========================================"
    echo -e "${YELLOW}回滚模式${NC}"
    echo "========================================"
    
    # 读取上次成功部署的 commit
    LAST_SUCCESS_FILE="${DEPLOY_LOG_DIR}/last_success_commit.txt"
    if [ ! -f "$LAST_SUCCESS_FILE" ]; then
        echo -e "${RED}未找到上次成功部署的 commit 记录${NC}"
        echo "文件不存在: $LAST_SUCCESS_FILE"
        exit 1
    fi
    
    ROLLBACK_COMMIT=$(cat "$LAST_SUCCESS_FILE")
    CURRENT_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    
    echo "当前版本:   ${CURRENT_COMMIT:0:8}"
    echo "回滚目标:   ${ROLLBACK_COMMIT:0:8}"
    
    if [ "$CURRENT_COMMIT" = "$ROLLBACK_COMMIT" ]; then
        echo -e "${YELLOW}当前版本即为上次成功版本，无需回滚${NC}"
        exit 0
    fi
    
    # 确认
    if [ "$NON_INTERACTIVE" != "true" ] && [ -t 0 ]; then
        read -p "确认回滚到 ${ROLLBACK_COMMIT:0:8}？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "已取消"
            exit 0
        fi
    fi
    
    # 执行回滚（优先使用 rollback 目录，否则 git checkout）
    echo "回滚 Node1..."
    NODE1_HAS_ROLLBACK=$(ssh_exec $NODE1_PUBLIC_IP "[ -d ${PROJECT_DIR}-rollback/server ] && echo 'yes' || echo 'no'" 2>/dev/null)
    if [ "$NODE1_HAS_ROLLBACK" = "yes" ]; then
        echo "使用 rollback 目录恢复（秒级回滚）..."
        for dir in core shared server services proto src; do
            ssh_exec $NODE1_PUBLIC_IP "[ -d ${PROJECT_DIR}-rollback/$dir ] && rsync -a --delete ${PROJECT_DIR}-rollback/$dir/ $PROJECT_DIR/$dir/" 2>/dev/null || true
        done
    else
        echo "使用 git checkout 回滚..."
        ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git checkout $ROLLBACK_COMMIT"
    fi
    gate_hot_reload "$NODE1_PUBLIC_IP" "Node1" 2
    gate_health_check "$NODE1_PUBLIC_IP" "Node1"
    
    record_deploy_history "$DEPLOYMENT_ID" "rollback" "node1_rollback" "回滚到 ${ROLLBACK_COMMIT:0:8}" "$ROLLBACK_COMMIT"
    echo -e "${GREEN}回滚完成${NC}"
    exit 0
fi

# ==================== 主流程开始 ====================

echo "========================================"
echo "HiFate 门控发布"
echo "========================================"
echo "部署ID:     $DEPLOYMENT_ID"
echo "时间:       $DEPLOY_START_TIME"
echo "Node1 (生产): $NODE1_PUBLIC_IP"
if [ "$SKIP_NODE2" = "false" ]; then
    echo "Node2 (前哨): $NODE2_PUBLIC_IP"
fi
echo ""
if [ "$DRY_RUN" = "true" ]; then
    echo -e "${YELLOW}模式: DRY-RUN（只部署 Node2 测试，不动 Node1）${NC}"
elif [ "$SKIP_NODE2" = "true" ]; then
    echo -e "${YELLOW}模式: 紧急（跳过 Node2，直接部署 Node1）${NC}"
elif [ "$TEST_ONLY" = "true" ]; then
    echo -e "${YELLOW}模式: 仅测试（只跑 Node2 回归测试，不部署）${NC}"
else
    echo "模式: 标准门控发布（Node2 验证 → Node1 部署）"
fi
echo "========================================"
echo ""

validate_config

# ==================== Step 1: 部署前检查 ====================

echo -e "${BLUE}[Step 1/7] 部署前检查${NC}"
echo "----------------------------------------"

# 1.1 检查本地 Git 状态
echo "检查 Git 状态..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "$GIT_BRANCH" ]; then
    echo -e "${YELLOW}警告：当前分支为 $CURRENT_BRANCH，建议在 $GIT_BRANCH 分支部署${NC}"
    if [ "$NON_INTERACTIVE" != "true" ] && [ -t 0 ]; then
        read -p "是否继续？(y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
fi

# 1.2 检查未提交更改
UNCOMMITTED=$(git status --porcelain --untracked-files=no | grep -v "local_frontend" | grep -v "deploy/logs" || true)
if [ -n "$UNCOMMITTED" ]; then
    echo -e "${RED}存在未提交的更改，请先提交:${NC}"
    echo "$UNCOMMITTED"
    exit 1
fi
echo -e "${GREEN}Git 状态正常${NC}"

# 1.3 检查未推送提交
LOCAL_COMMITS=$(git rev-list @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')
if [ "$LOCAL_COMMITS" -gt 0 ]; then
    echo -e "${YELLOW}存在 $LOCAL_COMMITS 个未推送的提交${NC}"
    if [ "$NON_INTERACTIVE" != "true" ] && [ -t 0 ]; then
        read -p "是否先推送？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push origin $CURRENT_BRANCH
            echo -e "${GREEN}推送完成${NC}"
        fi
    else
        echo -e "${RED}非交互模式下存在未推送提交，请先推送${NC}"
        exit 1
    fi
fi

LOCAL_COMMIT=$(git rev-parse HEAD)
echo "本地 commit: ${LOCAL_COMMIT:0:8}"

# 1.4 本地语法验证
echo ""
echo "本地语法验证..."
python3 << 'PYEOF'
import ast, sys, os, glob
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
    print('语法错误：')
    for err in errors[:10]:
        print(f'  - {err}')
    sys.exit(1)
print('语法验证通过')
PYEOF

if [ $? -ne 0 ]; then
    echo -e "${RED}本地语法验证失败，停止部署${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}[Step 1] 部署前检查通过${NC}"
echo ""

# ==================== Step 2: 检查服务器连接 ====================

echo -e "${BLUE}[Step 2/7] 检查服务器连接${NC}"
echo "----------------------------------------"

echo "检查 Node1 连接..."
if ! ssh_exec $NODE1_PUBLIC_IP "echo 'ok'" > /dev/null 2>&1; then
    echo -e "${RED}无法连接到 Node1 ($NODE1_PUBLIC_IP)${NC}"
    exit 1
fi
echo -e "${GREEN}Node1 连接正常${NC}"

# 记录 Node1 当前 commit（用于回滚）
NODE1_BEFORE_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
echo "Node1 当前版本: ${NODE1_BEFORE_COMMIT:0:8}"

if [ "$SKIP_NODE2" = "false" ]; then
    echo "检查 Node2 连接..."
    # 优先直接连接 Node2，降级走 Node1 跳转
    if ssh_exec $NODE2_PUBLIC_IP "echo 'ok'" > /dev/null 2>&1; then
        NODE2_SSH_MODE="direct"
        echo -e "${GREEN}Node2 直连正常${NC}"
    elif ssh_exec_node2_via_node1 "echo 'ok'" > /dev/null 2>&1; then
        NODE2_SSH_MODE="via_node1"
        echo -e "${GREEN}Node2 通过 Node1 连接正常${NC}"
    else
        echo -e "${RED}无法连接到 Node2${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}[Step 2] 服务器连接正常${NC}"
echo ""

# ==================== 辅助函数：Node2 SSH 执行 ====================

node2_ssh() {
    local cmd="$@"
    if [ "$NODE2_SSH_MODE" = "direct" ]; then
        ssh_exec $NODE2_PUBLIC_IP "$cmd"
    else
        ssh_exec_node2_via_node1 "$cmd"
    fi
}

# ==================== 辅助函数：compose 文件 hash 与同步 ====================

gate_compose_hash() {
    local ssh_func="$1"
    local project_dir="$2"
    local node_label="$3"
    local hash
    hash=$($ssh_func "cd $project_dir && md5sum docker-compose*.yml 2>/dev/null | md5sum | awk '{print \$1}'" 2>/dev/null) || hash="unknown"
    echo "$hash"
}

gate_compose_sync() {
    local ssh_func="$1"
    local project_dir="$2"
    local node_label="$3"
    local hash_before="$4"
    local display_name="$5"

    local hash_after
    hash_after=$($ssh_func "cd $project_dir && md5sum docker-compose*.yml 2>/dev/null | md5sum | awk '{print \$1}'" 2>/dev/null) || hash_after="unknown"

    if [ "$hash_before" != "$hash_after" ] && [ "$hash_before" != "unknown" ] && [ "$hash_after" != "unknown" ]; then
        echo -e "${YELLOW}检测到 $display_name compose 文件变更，执行容器重建...${NC}"
        $ssh_func "cd $project_dir && docker compose up -d --build" || {
            echo -e "${RED}$display_name 容器重建失败${NC}"
            return 1
        }
        echo -e "${GREEN}$display_name 容器重建完成${NC}"
    else
        echo "$display_name compose 文件无变更，跳过容器重建"
    fi
}

# ==================== Step 3: 部署到 Node2（前哨） ====================

if [ "$SKIP_NODE2" = "false" ] && [ "$TEST_ONLY" = "false" ]; then
    echo -e "${BLUE}[Step 3/7] 部署到 Node2（前哨节点）${NC}"
    echo "----------------------------------------"
    
    # 3.0 记录 compose 文件 hash（pull 前，用于检测基础设施变更）
    NODE2_COMPOSE_HASH_BEFORE=$(gate_compose_hash node2_ssh "$PROJECT_DIR" "node2")
    
    # 3.1 Git pull on Node2（pull 失败时尝试 reset --hard 解决分叉）
    echo "在 Node2 上拉取代码..."
    if ! node2_ssh "cd $PROJECT_DIR && \
        git fetch origin && \
        git checkout $GIT_BRANCH && \
        (git stash || true) && \
        git pull origin $GIT_BRANCH" 2>/dev/null; then
        echo -e "${YELLOW}Node2 git pull 失败，尝试 reset --hard origin/$GIT_BRANCH 解决分叉...${NC}"
        node2_ssh "cd $PROJECT_DIR && git fetch origin && git reset --hard origin/$GIT_BRANCH" || {
            echo -e "${RED}Node2 代码拉取失败${NC}"
            record_deploy_history "$DEPLOYMENT_ID" "failed" "node2_deploy" "代码拉取失败" "$LOCAL_COMMIT"
            exit 1
        }
    fi
    
    # 3.2 验证 Node2 代码版本
    NODE2_COMMIT=$(node2_ssh "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    if [ "$NODE2_COMMIT" != "$LOCAL_COMMIT" ]; then
        echo -e "${YELLOW}警告：Node2 版本 (${NODE2_COMMIT:0:8}) 与本地 (${LOCAL_COMMIT:0:8}) 不一致${NC}"
        echo -e "${YELLOW}请确保已推送到 GitHub${NC}"
    fi
    echo "Node2 版本: ${NODE2_COMMIT:0:8}"
    
    # 3.3 Node2 语法验证
    echo ""
    echo "Node2 语法验证..."
    node2_ssh "cd $PROJECT_DIR && python3 -c \"
import ast, sys, os, glob
errors = []
for p in ['server/**/*.py', 'src/**/*.py', 'services/**/*.py']:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    ast.parse(fh.read(), f)
            except SyntaxError as e:
                errors.append(f'{f}:{e.lineno}: {e.msg}')
if errors:
    [print(e) for e in errors[:5]]
    sys.exit(1)
print('OK')
\"" || {
        echo -e "${RED}Node2 语法验证失败，停止部署${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node2_syntax" "语法错误" "$LOCAL_COMMIT"
        exit 1
    }
    echo -e "${GREEN}Node2 语法验证通过${NC}"
    
    # 3.4 Compose 同步（若 compose 文件变更则重建容器，防止基础设施漂移）
    echo ""
    gate_compose_sync node2_ssh "$PROJECT_DIR" "node2" "$NODE2_COMPOSE_HASH_BEFORE" "Node2"
    
    # 3.5 Node2 热更新（失败不阻断，代码已落盘，后续请求或重启会加载）
    echo ""
    gate_hot_reload "$NODE2_PUBLIC_IP" "Node2" 2 || echo -e "${YELLOW}Node2 热更新超时，继续部署（代码已落盘）${NC}"

    echo ""
    echo -e "${GREEN}[Step 3] Node2 部署完成${NC}"
    echo ""
    
elif [ "$TEST_ONLY" = "true" ]; then
    echo -e "${BLUE}[Step 3/7] 跳过部署（仅测试模式）${NC}"
    echo ""
elif [ "$SKIP_NODE2" = "true" ]; then
    echo -e "${BLUE}[Step 3/7] 跳过 Node2（紧急模式）${NC}"
    echo ""
fi

# ==================== Step 4: Node2 全量回归测试（门控） ====================

if [ "$SKIP_NODE2" = "false" ]; then
    echo -e "${BLUE}[Step 4/7] Node2 全量回归测试（门控关卡）${NC}"
    echo "========================================"
    echo -e "${YELLOW}这是门控关卡：测试不通过则 Node1 不会被部署${NC}"
    echo "========================================"
    echo ""
    
    # 4.1 健康检查
    if ! gate_health_check "$NODE2_PUBLIC_IP" "Node2" 5 5; then
        print_gate_decision "Node2 前哨验证" "false" "Node2 健康检查失败，Node1 未被影响"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node2_health" "健康检查失败" "$LOCAL_COMMIT"
        exit 1
    fi
    
    # 4.2 全量回归测试
    echo ""
    echo "运行 Node2 全量回归测试..."
    echo "测试类别: $TEST_CATEGORIES"
    echo ""
    
    if gate_regression_test "node2" "$TEST_CATEGORIES" "true" "$PROJECT_ROOT"; then
        GATE_NODE2_RESULT="PASS"
    else
        GATE_NODE2_RESULT="FAIL"
    fi
    
    # 4.3 门控判断
    if [ "$GATE_NODE2_RESULT" = "PASS" ]; then
        print_gate_decision "Node2 前哨验证" "true" "全部测试通过，允许部署到 Node1"
        record_deploy_history "$DEPLOYMENT_ID" "gate_pass" "node2_test" "Node2 测试全部通过" "$LOCAL_COMMIT"
    else
        print_gate_decision "Node2 前哨验证" "false" "存在失败测试，Node1 不会被部署。请修复后重试。"
        record_deploy_history "$DEPLOYMENT_ID" "gate_fail" "node2_test" "Node2 测试存在失败" "$LOCAL_COMMIT"
        
        echo -e "${YELLOW}Node1 当前版本未受影响: ${NODE1_BEFORE_COMMIT:0:8}${NC}"
        echo ""
        echo "下一步操作:"
        echo "  1. 查看失败的测试用例，修复代码"
        echo "  2. git commit && git push"
        echo "  3. 重新运行: bash deploy/scripts/gated_deploy.sh"
        echo ""
        echo "如需只重跑 Node2 测试:"
        echo "  bash deploy/scripts/gated_deploy.sh --test-only"
        exit 1
    fi
    
    # DRY-RUN 模式到此结束
    if [ "$DRY_RUN" = "true" ]; then
        echo -e "${GREEN}DRY-RUN 完成：Node2 验证通过，Node1 未被修改${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "dry_run" "complete" "DRY-RUN 完成" "$LOCAL_COMMIT"
        exit 0
    fi
    
    # TEST-ONLY 模式到此结束
    if [ "$TEST_ONLY" = "true" ]; then
        echo -e "${GREEN}测试完成${NC}"
        exit 0
    fi

else
    echo -e "${BLUE}[Step 4/7] 跳过 Node2 测试（紧急模式）${NC}"
    echo -e "${YELLOW}警告：紧急模式跳过了 Node2 前哨验证，风险较高${NC}"
    echo ""
    
    if [ "$NON_INTERACTIVE" != "true" ] && [ -t 0 ]; then
        read -p "确认以紧急模式直接部署 Node1？(y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
fi

# ==================== Step 5: 部署到 Node1（生产） ====================

echo -e "${BLUE}[Step 5/7] 部署到 Node1（生产节点）${NC}"
echo "----------------------------------------"

# Node1 SSH 包装（用于 gate_compose_sync）
run_on_node1() { ssh_exec $NODE1_PUBLIC_IP "$@"; }

# 记录 Node1 compose hash（pull 前，用于检测基础设施变更）
NODE1_COMPOSE_HASH_BEFORE=$(gate_compose_hash run_on_node1 "$PROJECT_DIR" "node1")

# 保存回滚点
echo "$NODE1_BEFORE_COMMIT" > "${DEPLOY_LOG_DIR}/last_success_commit.txt"
echo "回滚点已保存: ${NODE1_BEFORE_COMMIT:0:8}"

# 检测是否启用 Phase 2 staging 隔离
NODE1_HAS_STAGING=$(ssh_exec $NODE1_PUBLIC_IP "[ -d $STAGING_DIR ] && echo 'yes' || echo 'no'" 2>/dev/null)

if [ "$NODE1_HAS_STAGING" = "yes" ]; then
    # ====== Phase 2 模式：staging 目录隔离 ======
    echo -e "${GREEN}[Phase 2] 检测到 staging 目录，使用隔离部署模式${NC}"
    echo ""
    
    # 5.1 Git pull 到 staging 目录（不影响运行中的容器）
    echo "在 staging 目录拉取代码（容器不受影响）..."
    ssh_exec $NODE1_PUBLIC_IP "cd $STAGING_DIR && \
        git fetch origin && \
        git checkout $GIT_BRANCH && \
        (git stash || true) && \
        git pull origin $GIT_BRANCH" || {
        echo -e "${RED}Node1 staging 代码拉取失败${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node1_staging_pull" "staging 代码拉取失败" "$LOCAL_COMMIT"
        exit 1
    }
    
    NODE1_STAGING_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $STAGING_DIR && git rev-parse HEAD" 2>/dev/null)
    echo "staging 版本: ${NODE1_STAGING_COMMIT:0:8}"
    
    # 5.2 在 staging 目录做语法验证（代码还没进 live）
    echo ""
    echo "staging 语法验证..."
    ssh_exec $NODE1_PUBLIC_IP "cd $STAGING_DIR && python3 -c \"
import ast, sys, os, glob
errors = []
for p in ['server/**/*.py', 'src/**/*.py', 'services/**/*.py']:
    for f in glob.glob(p, recursive=True):
        if os.path.isfile(f):
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    ast.parse(fh.read(), f)
            except SyntaxError as e:
                errors.append(f'{f}:{e.lineno}: {e.msg}')
if errors:
    [print(e) for e in errors[:5]]
    sys.exit(1)
print('OK')
\"" || {
        echo -e "${RED}staging 语法验证失败，live 目录未被修改${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node1_staging_syntax" "staging 语法验证失败" "$LOCAL_COMMIT"
        exit 1
    }
    echo -e "${GREEN}staging 语法验证通过${NC}"
    
    # 5.3 备份当前 live 目录（硬链接拷贝，瞬间完成，不额外占空间）
    echo ""
    echo "备份当前 live 目录..."
    ssh_exec $NODE1_PUBLIC_IP "rm -rf $ROLLBACK_DIR && cp -al $PROJECT_DIR $ROLLBACK_DIR" || {
        echo -e "${YELLOW}备份失败（可能是首次部署），继续...${NC}"
    }
    echo -e "${GREEN}备份完成${NC}"
    
    # 5.4 rsync 同步 staging → live（只同步代码目录，增量同步，通常 <3s）
    echo ""
    echo "同步代码到 live 目录..."
    for dir in $SYNC_DIRS; do
        ssh_exec $NODE1_PUBLIC_IP "[ -d $STAGING_DIR/$dir ] && rsync -a --delete $STAGING_DIR/$dir/ $PROJECT_DIR/$dir/" 2>/dev/null || true
    done
    echo -e "${GREEN}代码同步完成${NC}"
    
    # 5.5 同步 staging 的 git 信息到 live（让 live 目录知道当前版本）
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git checkout $GIT_BRANCH && (git stash || true) && git pull origin $GIT_BRANCH" 2>/dev/null || true
    
    NODE1_AFTER_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    echo "live 版本: ${NODE1_AFTER_COMMIT:0:8}"
    
    # 5.5b Compose 同步（若 compose 文件变更则重建容器）
    echo ""
    gate_compose_sync run_on_node1 "$PROJECT_DIR" "node1" "$NODE1_COMPOSE_HASH_BEFORE" "Node1"

else
    # ====== Phase 1 模式：直接 git pull（向后兼容） ======
    echo -e "${YELLOW}[Phase 1] 未检测到 staging 目录，使用直接部署模式${NC}"
    echo "提示: 运行 'bash deploy/scripts/init_staging.sh' 启用 Phase 2 隔离模式"
    echo ""
    
    # 5.1 Git pull on Node1（直接影响容器）
    echo "在 Node1 上拉取代码..."
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && \
        git fetch origin && \
        git checkout $GIT_BRANCH && \
        (git stash || true) && \
        git pull origin $GIT_BRANCH" || {
        echo -e "${RED}Node1 代码拉取失败${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node1_deploy" "代码拉取失败" "$LOCAL_COMMIT"
        exit 1
    }
    
    NODE1_AFTER_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    echo "Node1 版本: ${NODE1_AFTER_COMMIT:0:8}"
    
    # 5.1b Compose 同步（若 compose 文件变更则重建容器）
    echo ""
    gate_compose_sync run_on_node1 "$PROJECT_DIR" "node1" "$NODE1_COMPOSE_HASH_BEFORE" "Node1"
fi

# 5.6 Node1 热更新（两种模式共用）
echo ""
gate_hot_reload "$NODE1_PUBLIC_IP" "Node1" 2

echo ""
echo -e "${GREEN}[Step 5] Node1 部署完成${NC}"
echo ""

# ==================== Step 6: Node1 生产验证 ====================

echo -e "${BLUE}[Step 6/7] Node1 生产验证${NC}"
echo "----------------------------------------"

# 6.1 健康检查
if ! gate_health_check "$NODE1_PUBLIC_IP" "Node1" 5 5; then
    echo -e "${RED}Node1 健康检查失败！${NC}"
    echo -e "${YELLOW}尝试自动回滚...${NC}"
    
    # 回滚 Node1（优先使用 rollback 目录，否则 git checkout）
    NODE1_HAS_ROLLBACK=$(ssh_exec $NODE1_PUBLIC_IP "[ -d $ROLLBACK_DIR/server ] && echo 'yes' || echo 'no'" 2>/dev/null)
    if [ "$NODE1_HAS_ROLLBACK" = "yes" ]; then
        echo "使用 rollback 目录恢复..."
        for dir in $SYNC_DIRS; do
            ssh_exec $NODE1_PUBLIC_IP "[ -d $ROLLBACK_DIR/$dir ] && rsync -a --delete $ROLLBACK_DIR/$dir/ $PROJECT_DIR/$dir/" 2>/dev/null || true
        done
    else
        echo "使用 git checkout 回滚..."
        ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git checkout $NODE1_BEFORE_COMMIT" 2>/dev/null
    fi
    gate_hot_reload "$NODE1_PUBLIC_IP" "Node1" 2
    
    record_deploy_history "$DEPLOYMENT_ID" "rollback" "node1_health_fail" "健康检查失败，已回滚" "$LOCAL_COMMIT"
    echo -e "${YELLOW}Node1 已回滚到 ${NODE1_BEFORE_COMMIT:0:8}${NC}"
    exit 1
fi

# 6.2 关键接口快速验证
echo ""
echo "关键接口验证..."
BAZI_RESPONSE=$(curl -s --max-time 15 -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/bazi/interface" \
    -H "Content-Type: application/json" \
    -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}' 2>/dev/null || echo "{}")

if echo "$BAZI_RESPONSE" | grep -q '"success":true'; then
    echo -e "${GREEN}关键接口验证通过${NC}"
    NODE1_VERIFY="PASS"
else
    echo -e "${YELLOW}关键接口验证异常（但服务健康）${NC}"
    NODE1_VERIFY="WARN"
fi

echo ""
echo -e "${GREEN}[Step 6] Node1 验证完成${NC}"
echo ""

# ==================== Step 7: 记录部署历史 ====================

echo -e "${BLUE}[Step 7/7] 记录部署历史${NC}"
echo "----------------------------------------"

DEPLOY_END_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# 更新上次成功 commit
echo "$NODE1_AFTER_COMMIT" > "${DEPLOY_LOG_DIR}/last_success_commit.txt"

# 记录完整历史
record_deploy_history "$DEPLOYMENT_ID" "success" "complete" "门控发布成功" "$NODE1_AFTER_COMMIT"

# 生成部署报告
generate_deploy_report "$DEPLOYMENT_ID" "success" "${GATE_NODE2_RESULT:-skipped}" "$NODE1_VERIFY" \
    "$NODE1_AFTER_COMMIT" "$DEPLOY_START_TIME" "$DEPLOY_END_TIME"

echo ""

# ==================== 完成 ====================

echo "========================================"
echo -e "${GREEN}门控发布成功${NC}"
echo "========================================"
echo ""
echo "部署信息："
echo "  部署ID:     $DEPLOYMENT_ID"
echo "  Git Commit: ${NODE1_AFTER_COMMIT:0:8}"
echo "  部署前版本: ${NODE1_BEFORE_COMMIT:0:8}"
echo "  开始时间:   $DEPLOY_START_TIME"
echo "  完成时间:   $DEPLOY_END_TIME"
if [ "$SKIP_NODE2" = "false" ]; then
    echo "  Node2 测试: ${GATE_NODE2_RESULT}"
fi
echo "  Node1 验证: ${NODE1_VERIFY}"
if [ "${NODE1_HAS_STAGING:-no}" = "yes" ]; then
    echo "  部署模式:   Phase 2（staging 隔离）"
else
    echo "  部署模式:   Phase 1（直接 git pull）"
fi
echo ""
echo "健康检查："
echo "  Node1: http://$NODE1_PUBLIC_IP:8001/health"
if [ "$SKIP_NODE2" = "false" ]; then
    echo "  Node2: http://$NODE2_PUBLIC_IP:8001/health"
fi
echo ""
echo "回滚命令（如需要）："
echo "  bash deploy/scripts/gated_deploy.sh --rollback"
echo ""
echo "部署报告："
echo "  ${DEPLOY_LOG_DIR}/deploy_${DEPLOYMENT_ID}.json"
echo ""
