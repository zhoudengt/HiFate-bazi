#!/bin/bash
# ============================================
# HiFate 增量发布脚本（门控发布）v2
# ============================================
# 流程：
#   1. 部署前检查（本地 Git + 语法）
#   2. 检查服务器连接
#   3. 部署到 Node2（前哨）+ 健康检查 + 回归测试（basic+payment 阻断，stream 仅警告）
#   4. 部署到 Node1（生产）— Phase 1/2 自动识别
#   5. Node1 热更新 + 21 端点并发验证（带步骤级重试）
#   6. 记录部署历史
#
# 使用方法：
#   bash deploy/scripts/gated_deploy.sh                    # 标准门控发布
#   bash deploy/scripts/gated_deploy.sh --dry-run          # 只部署 Node2 跑测试，不动 Node1
#   bash deploy/scripts/gated_deploy.sh --skip-node2       # 紧急模式：跳过 Node2 直接部署 Node1
#   bash deploy/scripts/gated_deploy.sh --test-only        # 只跑 Node2 测试（不部署）
#   bash deploy/scripts/gated_deploy.sh --rollback         # 回滚 Node1 到上一次成功的 commit
# ============================================

# 不使用 set -e，防止 ((var++)) 等表达式误杀脚本

# ==================== 脚本初始化 ====================

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)

# 并发锁
LOCK_DIR="/tmp/hifate_gated_deploy.lock"
_cleanup_lock() { rmdir "$LOCK_DIR" 2>/dev/null || true; }
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_OWNER=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "unknown")
    echo -e "\033[0;31m另一个发布进程正在运行 (PID: $LOCK_OWNER)，请等待完成后重试\033[0m"
    exit 1
fi
echo $$ > "$LOCK_DIR/pid"
trap _cleanup_lock EXIT

source "${SCRIPT_DIR}/lib/gate_check.sh"

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
NO_VERIFY=false
TEST_CATEGORIES="basic stream payment"

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)       DRY_RUN=true; shift ;;
        --skip-node2)    SKIP_NODE2=true; shift ;;
        --no-verify)     NO_VERIFY=true; shift ;;
        --test-only)     TEST_ONLY=true; shift ;;
        --rollback)      ROLLBACK_MODE=true; shift ;;
        --non-interactive|-y) NON_INTERACTIVE=true; shift ;;
        --categories)    TEST_CATEGORIES="$2"; shift 2 ;;
        --help|-h)
            echo "HiFate 门控发布脚本 v2"
            echo ""
            echo "用法:"
            echo "  $0                          增量发布（Node2 验证 → Node1 部署）"
            echo "  $0 --dry-run                只部署 Node2 跑测试，不动 Node1"
            echo "  $0 --skip-node2             紧急模式：跳过 Node2 直接部署 Node1"
            echo "  $0 --no-verify              跳过 Node1 验证，部署后重启 web"
            echo "  $0 --test-only              只跑 Node2 回归测试（不部署代码）"
            echo "  $0 --rollback               回滚 Node1 到上一次部署前的 commit"
            echo "  $0 --non-interactive / -y   非交互模式（自动确认）"
            echo "  $0 --categories \"basic\"     自定义测试类别"
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

if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a; source "${PROJECT_ROOT}/.env"; set +a
fi

CONFIG_FILE="${SCRIPT_DIR}/deploy.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

NODE1_PUBLIC_IP="${NODE1_PUBLIC_IP:-}"
NODE2_PUBLIC_IP="${NODE2_PUBLIC_IP:-}"
NODE2_PRIVATE_IP="${NODE2_PRIVATE_IP:-}"
SSH_PASSWORD="${SSH_PASSWORD:-}"
PROJECT_DIR="${PROJECT_DIR:-/opt/HiFate-bazi}"
STAGING_DIR="${PROJECT_DIR}-staging"
ROLLBACK_DIR="${PROJECT_DIR}-rollback"
GIT_BRANCH="${GIT_BRANCH:-master}"
SYNC_DIRS="core shared server services proto src"

DEPLOY_LOG_DIR="${PROJECT_ROOT}/deploy/logs"
mkdir -p "$DEPLOY_LOG_DIR"

DEPLOYMENT_ID=$(date +%Y%m%d_%H%M%S)
DEPLOY_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

# ==================== 验证配置 ====================

validate_config() {
    local errors=0

    if [ -z "$NODE1_PUBLIC_IP" ]; then
        echo -e "${RED}NODE1_PUBLIC_IP 未配置${NC}"
        errors=1
    fi

    if [ "$SKIP_NODE2" = "false" ] && [ -z "$NODE2_PUBLIC_IP" ]; then
        echo -e "${RED}NODE2_PUBLIC_IP 未配置（如需跳过 Node2 请使用 --skip-node2）${NC}"
        errors=1
    fi

    if [ $errors -gt 0 ]; then
        echo -e "${YELLOW}请配置 deploy.conf 或设置环境变量${NC}"
        exit 1
    fi
}

# ==================== SSH 函数 ====================

ssh_exec() {
    local host=$1
    shift
    local cmd="$@"

    local ssh_alias=""
    if [ "$host" = "$NODE1_PUBLIC_IP" ]; then
        ssh_alias="hifate-node1"
    elif [ "$host" = "$NODE2_PUBLIC_IP" ]; then
        ssh_alias="hifate-node2"
    fi

    if [ -n "$ssh_alias" ]; then
        if ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no $ssh_alias "$cmd" 2>/dev/null; then
            return 0
        fi
        if ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=no -i ~/.ssh/id_rsa_hifate root@$host "$cmd" 2>/dev/null; then
            return 0
        fi
    fi

    if [ -n "$SSH_PASSWORD" ] && command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 root@$host "$cmd"
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

run_on_node1() { ssh_exec $NODE1_PUBLIC_IP "$@"; }

node2_ssh() {
    local cmd="$@"
    if [ "$NODE2_SSH_MODE" = "direct" ]; then
        ssh_exec $NODE2_PUBLIC_IP "$cmd"
    else
        ssh_exec_node2_via_node1 "$cmd"
    fi
}

# ==================== compose 辅助 ====================

gate_compose_hash() {
    local ssh_func="$1"
    local project_dir="$2"
    local node_label="$3"
    local hash
    hash=$($ssh_func "cd $project_dir/deploy/docker && md5sum docker-compose*.yml 2>/dev/null | md5sum | awk '{print \$1}'" 2>/dev/null) || hash="unknown"
    echo "$hash"
}

gate_compose_sync() {
    local ssh_func="$1"
    local project_dir="$2"
    local node_label="$3"
    local hash_before="$4"
    local display_name="$5"

    local hash_after
    hash_after=$($ssh_func "cd $project_dir/deploy/docker && md5sum docker-compose*.yml 2>/dev/null | md5sum | awk '{print \$1}'" 2>/dev/null) || hash_after="unknown"

    if [ "$hash_before" != "$hash_after" ] && [ "$hash_before" != "unknown" ] && [ "$hash_after" != "unknown" ]; then
        echo -e "${YELLOW}检测到 $display_name compose 文件变更，执行容器重建...${NC}"
        $ssh_func "cd $project_dir/deploy/docker && docker compose -f docker-compose.prod.yml -f docker-compose.${node_label}.yml --env-file $project_dir/.env up -d --no-deps web" || {
            echo -e "${RED}$display_name 容器重建失败${NC}"
            return 1
        }
        echo -e "${GREEN}$display_name 容器重建完成${NC}"
    else
        echo "$display_name compose 文件无变更，跳过容器重建"
    fi
}

# ==================== 回滚模式 ====================

if [ "$ROLLBACK_MODE" = "true" ]; then
    echo "========================================"
    echo -e "${YELLOW}回滚模式${NC}"
    echo "========================================"

    validate_config

    LAST_SUCCESS_FILE="${DEPLOY_LOG_DIR}/last_success_commit.txt"
    if [ ! -f "$LAST_SUCCESS_FILE" ]; then
        echo -e "${RED}未找到上次成功部署的 commit 记录${NC}"
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

    if [ "$NON_INTERACTIVE" != "true" ] && [ -t 0 ]; then
        read -p "确认回滚到 ${ROLLBACK_COMMIT:0:8}？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "已取消"
            exit 0
        fi
    fi

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
    gate_reload_endpoints_multi "$NODE1_PUBLIC_IP" "Node1" 4
    gate_health_check "$NODE1_PUBLIC_IP" "Node1"

    record_deploy_history "$DEPLOYMENT_ID" "rollback" "node1_rollback" "回滚到 ${ROLLBACK_COMMIT:0:8}" "$ROLLBACK_COMMIT"
    echo -e "${GREEN}回滚完成${NC}"
    exit 0
fi

# ==================== 主流程开始 ====================

echo "========================================"
echo "HiFate 门控发布 v2"
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
    if [ "$NO_VERIFY" = "true" ]; then
        echo -e "${YELLOW}模式: 快速（跳过 Node2 + 跳过验证，部署后重启 web）${NC}"
    else
        echo -e "${YELLOW}模式: 紧急（跳过 Node2，直接部署 Node1）${NC}"
    fi
elif [ "$TEST_ONLY" = "true" ]; then
    echo -e "${YELLOW}模式: 仅测试（只跑 Node2 回归测试，不部署）${NC}"
else
    echo "模式: 标准门控发布（Node2 验证 → Node1 部署）"
fi
echo "========================================"
echo ""

validate_config

# ==================== Step 1: 部署前检查 ====================

echo -e "${BLUE}[Step 1/6] 部署前检查${NC}"
echo "----------------------------------------"

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

UNCOMMITTED=$(git status --porcelain --untracked-files=no | grep -v "local_frontend" | grep -v "deploy/logs" || true)
if [ -n "$UNCOMMITTED" ]; then
    echo -e "${RED}存在未提交的更改，请先提交:${NC}"
    echo "$UNCOMMITTED"
    exit 1
fi
echo -e "${GREEN}Git 状态正常${NC}"

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

echo ""
echo "本地语法验证..."
if ! python3 << 'PYEOF'
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
then
    echo -e "${RED}本地语法验证失败，停止部署${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}[Step 1] 部署前检查通过${NC}"
echo ""

# ==================== Step 2: 检查服务器连接 ====================

echo -e "${BLUE}[Step 2/6] 检查服务器连接${NC}"
echo "----------------------------------------"

echo "检查 Node1 连接..."
if ! ssh_exec $NODE1_PUBLIC_IP "echo 'ok'" > /dev/null 2>&1; then
    echo -e "${RED}无法连接到 Node1 ($NODE1_PUBLIC_IP)${NC}"
    exit 1
fi
echo -e "${GREEN}Node1 连接正常${NC}"

NODE1_BEFORE_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
echo "Node1 当前版本: ${NODE1_BEFORE_COMMIT:0:8}"

if [ "$SKIP_NODE2" = "false" ]; then
    echo "检查 Node2 连接..."
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

# ==================== Step 3: Node2 前哨部署 + 门控测试 ====================

if [ "$SKIP_NODE2" = "false" ]; then

    if [ "$TEST_ONLY" = "false" ]; then
        echo -e "${BLUE}[Step 3/6] Node2 前哨部署 + 门控测试${NC}"
        echo "----------------------------------------"

        # 3.0 compose hash
        NODE2_COMPOSE_HASH_BEFORE=$(gate_compose_hash node2_ssh "$PROJECT_DIR" "node2")

        # 3.1 Git pull（合并为一次 SSH：fetch + checkout + stash + pull + 取 commit）
        echo "在 Node2 上拉取代码..."
        NODE2_PULL_RESULT=$(node2_ssh "cd $PROJECT_DIR && git fetch origin && git checkout $GIT_BRANCH && (git stash || true) && git pull origin $GIT_BRANCH && git rev-parse HEAD" 2>/dev/null) || {
            echo -e "${YELLOW}Node2 git pull 失败，尝试 reset --hard...${NC}"
            NODE2_PULL_RESULT=$(node2_ssh "cd $PROJECT_DIR && git fetch origin && git reset --hard origin/$GIT_BRANCH && git rev-parse HEAD" 2>/dev/null) || {
                echo -e "${RED}Node2 代码拉取失败${NC}"
                record_deploy_history "$DEPLOYMENT_ID" "failed" "node2_deploy" "代码拉取失败" "$LOCAL_COMMIT"
                exit 1
            }
        }
        NODE2_COMMIT=$(echo "$NODE2_PULL_RESULT" | tail -1)
        echo "Node2 版本: ${NODE2_COMMIT:0:8}"

        if [ "$NODE2_COMMIT" != "$LOCAL_COMMIT" ]; then
            echo -e "${RED}Node2 版本 (${NODE2_COMMIT:0:8}) 与本地 (${LOCAL_COMMIT:0:8}) 不一致${NC}"
            echo -e "${RED}请先确保 git push 完成，再重新运行发布${NC}"
            record_deploy_history "$DEPLOYMENT_ID" "failed" "node2_version_mismatch" "版本不一致" "$LOCAL_COMMIT"
            exit 1
        fi

        # 3.2 Compose 同步
        echo ""
        gate_compose_sync node2_ssh "$PROJECT_DIR" "node2" "$NODE2_COMPOSE_HASH_BEFORE" "Node2"

        # 3.3 Node2 热更新 + 端点恢复（不做 21 端点验证）
        echo ""
        gate_hot_reload "$NODE2_PUBLIC_IP" "Node2" 2 "${NODE2_PORT:-8001}" "$NODE2_PUBLIC_IP" "$SSH_PASSWORD" || echo -e "${YELLOW}Node2 热更新超时，继续（代码已落盘）${NC}"
        echo ""
        gate_reload_endpoints_multi "$NODE2_PUBLIC_IP" "Node2" 4 "${NODE2_PORT:-8001}"

        # 3.4 清理缓存
        echo ""
        gate_clear_business_cache node2_ssh "hifate-redis-slave" "Node2"

        echo ""
        echo -e "${GREEN}Node2 部署完成${NC}"
        echo ""
    else
        echo -e "${BLUE}[Step 3/6] 跳过部署（仅测试模式）${NC}"
        echo ""
    fi

    # ---- 门控测试 ----

    echo -e "${BLUE}[门控关卡] Node2 回归测试${NC}"
    echo "========================================"
    echo -e "${YELLOW}basic + payment 必须通过；stream 仅警告不阻断${NC}"
    echo "========================================"
    echo ""

    # 健康检查
    if ! gate_health_check "$NODE2_PUBLIC_IP" "Node2" 5 5 "${NODE2_PORT:-8001}" "$NODE2_PUBLIC_IP" "$SSH_PASSWORD"; then
        print_gate_decision "Node2 前哨验证" "false" "Node2 健康检查失败，Node1 未被影响"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node2_health" "健康检查失败" "$LOCAL_COMMIT"
        exit 1
    fi

    # 阻断级测试：basic + payment
    echo ""
    echo "运行阻断级测试（basic + payment）..."
    GATE_BLOCKING_PASS=true
    if ! gate_regression_test "node2" "basic payment" "true" "$PROJECT_DIR" "$NODE2_PUBLIC_IP" "$SSH_PASSWORD"; then
        GATE_BLOCKING_PASS=false
    fi

    if [ "$GATE_BLOCKING_PASS" = "false" ]; then
        # 重试一次
        echo ""
        echo -e "${YELLOW}阻断级测试失败，自动重试一次...${NC}"
        if gate_regression_test "node2" "basic payment" "true" "$PROJECT_DIR" "$NODE2_PUBLIC_IP" "$SSH_PASSWORD"; then
            GATE_BLOCKING_PASS=true
        fi
    fi

    if [ "$GATE_BLOCKING_PASS" = "false" ]; then
        print_gate_decision "Node2 前哨验证" "false" "basic/payment 测试失败，Node1 不会被部署"
        record_deploy_history "$DEPLOYMENT_ID" "gate_fail" "node2_test" "阻断级测试失败" "$LOCAL_COMMIT"
        echo -e "${YELLOW}Node1 当前版本未受影响: ${NODE1_BEFORE_COMMIT:0:8}${NC}"
        exit 1
    fi

    # 警告级测试：stream（失败不阻断）
    echo ""
    echo "运行警告级测试（stream）..."
    if gate_regression_test "node2" "stream" "true" "$PROJECT_DIR" "$NODE2_PUBLIC_IP" "$SSH_PASSWORD"; then
        GATE_NODE2_RESULT="PASS"
    else
        GATE_NODE2_RESULT="PASS_WITH_WARN"
        echo -e "${YELLOW}stream 测试存在失败，但不阻断发布（LLM 依赖可能波动）${NC}"
    fi

    print_gate_decision "Node2 前哨验证" "true" "阻断级测试全部通过，允许部署到 Node1（stream: ${GATE_NODE2_RESULT}）"
    record_deploy_history "$DEPLOYMENT_ID" "gate_pass" "node2_test" "门控通过 (${GATE_NODE2_RESULT})" "$LOCAL_COMMIT"

    # DRY-RUN / TEST-ONLY 到此结束
    if [ "$DRY_RUN" = "true" ]; then
        echo -e "${GREEN}DRY-RUN 完成：Node2 验证通过，Node1 未被修改${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "dry_run" "complete" "DRY-RUN 完成" "$LOCAL_COMMIT"
        exit 0
    fi
    if [ "$TEST_ONLY" = "true" ]; then
        echo -e "${GREEN}测试完成${NC}"
        exit 0
    fi

else
    echo -e "${BLUE}[Step 3/6] 跳过 Node2（紧急/快速模式）${NC}"
    echo ""

    if [ "$NON_INTERACTIVE" != "true" ] && [ -t 0 ] && [ "$NO_VERIFY" != "true" ]; then
        read -p "确认以紧急模式直接部署 Node1？(y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
fi

# ==================== Step 4: 部署到 Node1（生产） ====================

echo -e "${BLUE}[Step 4/6] 部署到 Node1（生产节点）${NC}"
echo "----------------------------------------"

# compose hash
NODE1_COMPOSE_HASH_BEFORE=$(gate_compose_hash run_on_node1 "$PROJECT_DIR" "node1")

# 保存回滚点
echo "$NODE1_BEFORE_COMMIT" > "${DEPLOY_LOG_DIR}/last_success_commit.txt"
echo "回滚点已保存: ${NODE1_BEFORE_COMMIT:0:8}"

NODE1_HAS_STAGING=$(ssh_exec $NODE1_PUBLIC_IP "[ -d $STAGING_DIR ] && echo 'yes' || echo 'no'" 2>/dev/null)

if [ "$NODE1_HAS_STAGING" = "yes" ]; then
    # ====== Phase 2：staging 隔离 ======
    echo -e "${GREEN}[Phase 2] staging 隔离部署${NC}"
    echo ""

    # 合并为一次 SSH：git pull + 取 commit
    echo "在 staging 目录拉取代码..."
    ssh_exec $NODE1_PUBLIC_IP "cd $STAGING_DIR && git fetch origin && git checkout $GIT_BRANCH && (git stash || true) && git pull origin $GIT_BRANCH" || {
        echo -e "${RED}Node1 staging 代码拉取失败${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node1_staging_pull" "staging 代码拉取失败" "$LOCAL_COMMIT"
        exit 1
    }

    NODE1_STAGING_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $STAGING_DIR && git rev-parse HEAD" 2>/dev/null)
    echo "staging 版本: ${NODE1_STAGING_COMMIT:0:8}"

    # 备份
    echo ""
    echo "备份当前 live 目录..."
    ssh_exec $NODE1_PUBLIC_IP "rm -rf $ROLLBACK_DIR && cp -al $PROJECT_DIR $ROLLBACK_DIR" || {
        echo -e "${YELLOW}备份失败（可能是首次部署），继续...${NC}"
    }
    echo -e "${GREEN}备份完成${NC}"

    # rsync 同步（合并为一次 SSH）
    echo ""
    echo "同步代码到 live 目录..."
    RSYNC_CMD=""
    for dir in $SYNC_DIRS; do
        RSYNC_CMD="${RSYNC_CMD}[ -d $STAGING_DIR/$dir ] && rsync -a --delete $STAGING_DIR/$dir/ $PROJECT_DIR/$dir/ && "
    done
    RSYNC_CMD="${RSYNC_CMD}echo 'rsync_done'"

    RSYNC_RESULT=$(ssh_exec $NODE1_PUBLIC_IP "$RSYNC_CMD" 2>/dev/null)
    if [ "$RSYNC_RESULT" != "rsync_done" ]; then
        echo -e "${RED}rsync 同步失败，从备份回滚...${NC}"
        NODE1_HAS_ROLLBACK=$(ssh_exec $NODE1_PUBLIC_IP "[ -d $ROLLBACK_DIR/server ] && echo 'yes' || echo 'no'" 2>/dev/null)
        if [ "$NODE1_HAS_ROLLBACK" = "yes" ]; then
            for dir in $SYNC_DIRS; do
                ssh_exec $NODE1_PUBLIC_IP "[ -d $ROLLBACK_DIR/$dir ] && rsync -a --delete $ROLLBACK_DIR/$dir/ $PROJECT_DIR/$dir/" 2>/dev/null || true
            done
        fi
        gate_hot_reload "$NODE1_PUBLIC_IP" "Node1" 2
        record_deploy_history "$DEPLOYMENT_ID" "rollback" "node1_rsync_fail" "rsync 失败，已回滚" "$LOCAL_COMMIT"
        exit 1
    fi
    echo -e "${GREEN}代码同步完成${NC}"

    # 同步 git 信息到 live
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git checkout $GIT_BRANCH && (git stash || true) && git pull origin $GIT_BRANCH" 2>/dev/null || true

    NODE1_AFTER_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    echo "live 版本: ${NODE1_AFTER_COMMIT:0:8}"

    echo ""
    gate_compose_sync run_on_node1 "$PROJECT_DIR" "node1" "$NODE1_COMPOSE_HASH_BEFORE" "Node1"

else
    # ====== Phase 1：直接 git pull ======
    echo -e "${YELLOW}[Phase 1] 直接部署（未检测到 staging）${NC}"
    echo ""

    echo "在 Node1 上拉取代码..."
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git fetch origin && git checkout $GIT_BRANCH && (git stash || true) && git pull origin $GIT_BRANCH" || {
        echo -e "${RED}Node1 代码拉取失败${NC}"
        record_deploy_history "$DEPLOYMENT_ID" "failed" "node1_deploy" "代码拉取失败" "$LOCAL_COMMIT"
        exit 1
    }

    NODE1_AFTER_COMMIT=$(ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git rev-parse HEAD" 2>/dev/null)
    echo "Node1 版本: ${NODE1_AFTER_COMMIT:0:8}"

    echo ""
    gate_compose_sync run_on_node1 "$PROJECT_DIR" "node1" "$NODE1_COMPOSE_HASH_BEFORE" "Node1"
fi

echo ""
echo -e "${GREEN}[Step 4] Node1 代码部署完成${NC}"
echo ""

# ==================== Step 5: Node1 热更新 + 端点验证 ====================

echo -e "${BLUE}[Step 5/6] Node1 热更新 + 生产验证${NC}"
echo "----------------------------------------"

if [ "$NO_VERIFY" = "true" ]; then
    echo "重启 Node1 web 容器（--no-verify 模式）..."
    ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR/deploy/docker && docker compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file $PROJECT_DIR/.env restart web" || {
        echo -e "${RED}Node1 web 重启失败${NC}"
        exit 1
    }
    echo -e "${GREEN}Node1 web 重启完成${NC}"
    sleep 3
    NODE1_VERIFY="skipped"
else
    # 热更新 + 端点恢复 + 21 端点并发验证（整体最多 2 轮重试）
    if ! gate_hot_reload_and_verify "$NODE1_PUBLIC_IP" "Node1"; then
        echo -e "${RED}Node1 热更新+端点验证失败！尝试自动回滚...${NC}"

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
        gate_reload_endpoints_multi "$NODE1_PUBLIC_IP" "Node1" 4

        record_deploy_history "$DEPLOYMENT_ID" "rollback" "node1_verify_fail" "端点验证失败，已回滚" "$LOCAL_COMMIT"
        echo -e "${YELLOW}Node1 已回滚到 ${NODE1_BEFORE_COMMIT:0:8}${NC}"
        exit 1
    fi

    # 健康检查
    if ! gate_health_check "$NODE1_PUBLIC_IP" "Node1" 5 5; then
        echo -e "${RED}Node1 健康检查失败！尝试自动回滚...${NC}"

        NODE1_HAS_ROLLBACK=$(ssh_exec $NODE1_PUBLIC_IP "[ -d $ROLLBACK_DIR/server ] && echo 'yes' || echo 'no'" 2>/dev/null)
        if [ "$NODE1_HAS_ROLLBACK" = "yes" ]; then
            for dir in $SYNC_DIRS; do
                ssh_exec $NODE1_PUBLIC_IP "[ -d $ROLLBACK_DIR/$dir ] && rsync -a --delete $ROLLBACK_DIR/$dir/ $PROJECT_DIR/$dir/" 2>/dev/null || true
            done
        else
            ssh_exec $NODE1_PUBLIC_IP "cd $PROJECT_DIR && git checkout $NODE1_BEFORE_COMMIT" 2>/dev/null
        fi
        gate_hot_reload "$NODE1_PUBLIC_IP" "Node1" 2
        gate_reload_endpoints_multi "$NODE1_PUBLIC_IP" "Node1" 4

        record_deploy_history "$DEPLOYMENT_ID" "rollback" "node1_health_fail" "健康检查失败，已回滚" "$LOCAL_COMMIT"
        echo -e "${YELLOW}Node1 已回滚到 ${NODE1_BEFORE_COMMIT:0:8}${NC}"
        exit 1
    fi

    # 快速 REST 接口验证
    echo ""
    echo "关键接口验证..."
    BAZI_RESPONSE=$(curl -s --max-time 10 -X POST "http://$NODE1_PUBLIC_IP:8001/api/v1/bazi/interface" \
        -H "Content-Type: application/json" \
        -d '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}' 2>/dev/null || echo "{}")

    if echo "$BAZI_RESPONSE" | grep -q '"success":true'; then
        echo -e "${GREEN}REST 接口验证通过${NC}"
        NODE1_VERIFY="PASS"
    else
        echo -e "${YELLOW}REST 接口验证异常（但服务健康）${NC}"
        NODE1_VERIFY="WARN"
    fi
fi

# 清理缓存
echo ""
gate_clear_business_cache run_on_node1 "hifate-redis-master" "Node1"

echo ""
echo -e "${GREEN}[Step 5] Node1 验证完成${NC}"
echo ""

# ==================== Step 6: 记录部署历史 ====================

echo -e "${BLUE}[Step 6/6] 记录部署历史${NC}"
echo "----------------------------------------"

DEPLOY_END_TIME=$(date '+%Y-%m-%d %H:%M:%S')

record_deploy_history "$DEPLOYMENT_ID" "success" "complete" "门控发布成功" "$NODE1_AFTER_COMMIT"

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
echo "回滚命令（如需要）："
echo "  bash deploy/scripts/gated_deploy.sh --rollback"
echo ""
echo "部署报告："
echo "  ${DEPLOY_LOG_DIR}/deploy_${DEPLOYMENT_ID}.json"
echo ""
