#!/bin/bash
# ============================================================================
# 标准化增量部署脚本 (Standard Incremental Deploy)
# ============================================================================
#
# 用途：从本地 Git 仓库部署代码到生产环境，支持热更新和回滚
#
# 使用：
#   bash deploy/scripts/deploy_standard.sh              # 正常部署
#   bash deploy/scripts/deploy_standard.sh --dry-run    # 模拟部署（不执行）
#   bash deploy/scripts/deploy_standard.sh --skip-test  # 跳过部署后测试
#
# 部署流程（6步）：
#   1. 预检查：本地代码状态、远程连通性、容器健康
#   2. 代码同步：git pull 到生产服务器
#   3. 热更新：触发所有 Worker 重载代码 + 清理缓存
#   4. 等待就绪：确认所有 Worker 完成重载
#   5. 冒烟测试：验证核心接口返回正确数据
#   6. 报告：输出部署摘要
#
# 约束：
#   - 仅支持增量部署（Python 代码 / 配置 / 规则 / proto）
#   - 如果改了 Dockerfile / requirements.txt，需要完整部署
#   - 不会 docker restart，仅热更新
# ============================================================================

set -euo pipefail

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ---- 配置 ----
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
CONFIG_FILE="${SCRIPT_DIR}/deploy.conf"

# 加载配置文件（仅在环境变量已就绪时才加载，避免 ${:?} 导致 shell 退出）
if [ -f "$CONFIG_FILE" ]; then
    if (source "$CONFIG_FILE") 2>/dev/null; then
        source "$CONFIG_FILE"
    fi
fi

# 从配置或环境变量读取
NODE1_HOST="${NODE1_SSH_ALIAS:-hifate-node1}"
NODE1_PUBLIC_IP="${NODE1_PUBLIC_IP:-8.210.52.217}"
REMOTE_DIR="${REMOTE_PROJECT_DIR:-/opt/HiFate-bazi}"
WEB_PORT="${WEB_PORT:-8001}"
BASE_URL="http://${NODE1_PUBLIC_IP}:${WEB_PORT}"
GIT_BRANCH="${GIT_BRANCH:-master}"

# 参数解析
DRY_RUN=false
SKIP_TEST=false
for arg in "$@"; do
    case $arg in
        --dry-run)  DRY_RUN=true ;;
        --skip-test) SKIP_TEST=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--skip-test]"
            exit 0 ;;
    esac
done

# ---- 工具函数 ----
step() { echo -e "\n${BOLD}${BLUE}[$1/6]${NC} ${BOLD}$2${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
die()  { fail "$1"; echo -e "\n${RED}部署中止${NC}"; exit 1; }

DEPLOY_START=$(date +%s)

echo ""
echo "============================================================"
echo -e "${BOLD}  HiFate 标准化增量部署${NC}"
echo "============================================================"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "  目标: ${NODE1_HOST} (${NODE1_PUBLIC_IP})"
echo "  分支: ${GIT_BRANCH}"
echo "  模式: $([ "$DRY_RUN" = true ] && echo "模拟" || echo "正式")"
echo "============================================================"

# ============================================================
# Step 1: 预检查
# ============================================================
step 1 "预检查"

# 1a. 本地是否在正确分支且已推送
LOCAL_BRANCH=$(cd "$PROJECT_ROOT" && git branch --show-current)
if [ "$LOCAL_BRANCH" != "$GIT_BRANCH" ]; then
    die "本地分支为 $LOCAL_BRANCH，非 $GIT_BRANCH"
fi

# 检查是否有未推送的提交
UNPUSHED=$(cd "$PROJECT_ROOT" && git log origin/${GIT_BRANCH}..HEAD --oneline 2>/dev/null | wc -l | tr -d ' ')
if [ "$UNPUSHED" -gt 0 ]; then
    die "有 $UNPUSHED 个未推送的提交，请先 git push"
fi
ok "本地分支 ${GIT_BRANCH}，已推送到远端"

# 1b. SSH 连通性
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$NODE1_HOST" "echo ok" >/dev/null 2>&1; then
    die "无法 SSH 连接 ${NODE1_HOST}"
fi
ok "SSH 连接正常"

# 1c. 远程 Web 容器健康
HEALTH=$(curl -s --max-time 10 "${BASE_URL}/health" 2>/dev/null || echo "FAIL")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    ok "Web 服务健康"
else
    die "Web 服务不健康: $HEALTH"
fi

# 1d. 检查是否有 Dockerfile/requirements 变更（需要完整部署）
CHANGED_FILES=$(cd "$PROJECT_ROOT" && git diff origin/${GIT_BRANCH}~1..origin/${GIT_BRANCH} --name-only 2>/dev/null || echo "")
NEEDS_FULL_DEPLOY=false
for f in $CHANGED_FILES; do
    case "$f" in
        Dockerfile|requirements.txt|docker-compose.yml)
            NEEDS_FULL_DEPLOY=true
            warn "检测到 $f 变更，可能需要完整部署（镜像重建）"
            ;;
    esac
done

# 1e. 显示将要部署的变更
COMMIT_MSG=$(cd "$PROJECT_ROOT" && git log origin/${GIT_BRANCH}~1..origin/${GIT_BRANCH} --oneline 2>/dev/null | head -5)
if [ -n "$COMMIT_MSG" ]; then
    echo -e "  最近提交:"
    echo "$COMMIT_MSG" | while read line; do echo "    $line"; done
fi

if [ "$DRY_RUN" = true ]; then
    echo -e "\n${YELLOW}[DRY-RUN] 预检查完成，不执行后续步骤${NC}"
    exit 0
fi

# ============================================================
# Step 2: 代码同步
# ============================================================
step 2 "代码同步 (git pull)"

PULL_OUTPUT=$(ssh "$NODE1_HOST" "cd ${REMOTE_DIR} && git fetch origin ${GIT_BRANCH} && git reset --hard origin/${GIT_BRANCH} 2>&1" 2>&1)
PULL_EXIT=$?

if [ $PULL_EXIT -ne 0 ]; then
    fail "git pull 失败:"
    echo "$PULL_OUTPUT"
    die "代码同步失败"
fi
ok "代码已同步到 ${NODE1_HOST}:${REMOTE_DIR}"

# 验证关键文件存在
ssh "$NODE1_HOST" "test -f ${REMOTE_DIR}/core/calculators/LunarConverter.py && test -f ${REMOTE_DIR}/server/hot_reload/reloaders.py" \
    || die "关键文件缺失"
ok "关键文件验证通过"

# ============================================================
# Step 3: 热更新
# ============================================================
step 3 "触发热更新"

RELOAD_RESULT=$(curl -s --max-time 120 -X POST "${BASE_URL}/api/v1/hot-reload/reload-all" 2>/dev/null || echo '{"success":false}')
RELOAD_SUCCESS=$(echo "$RELOAD_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success',False))" 2>/dev/null || echo "False")

if [ "$RELOAD_SUCCESS" = "True" ]; then
    RELOAD_MSG=$(echo "$RELOAD_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null)
    ok "热更新成功: $RELOAD_MSG"
else
    fail "热更新结果: $RELOAD_RESULT"
    die "热更新失败"
fi

# ============================================================
# Step 4: 等待 Worker 就绪
# ============================================================
step 4 "等待 Worker 就绪"

# 等待几秒让 Worker 同步完成
sleep 5

# 发 3 次健康检查确保所有 Worker 都正常
ALL_HEALTHY=true
for i in 1 2 3; do
    H=$(curl -s --max-time 10 "${BASE_URL}/health" 2>/dev/null || echo "FAIL")
    if echo "$H" | grep -q '"status":"healthy"'; then
        ok "健康检查 $i/3 通过"
    else
        warn "健康检查 $i/3 失败"
        ALL_HEALTHY=false
        sleep 3
    fi
done

if [ "$ALL_HEALTHY" = false ]; then
    warn "部分健康检查未通过，继续执行冒烟测试..."
fi

# ============================================================
# Step 5: 冒烟测试
# ============================================================
step 5 "冒烟测试"

SMOKE_PASS=0
SMOKE_FAIL=0
SMOKE_TOTAL=0

# 测试函数
smoke_test() {
    local name="$1"
    local endpoint="$2"
    local payload="$3"
    local check_field="$4"
    local expected="$5"
    
    SMOKE_TOTAL=$((SMOKE_TOTAL + 1))
    
    RESP=$(curl -s --max-time 20 -X POST "${BASE_URL}${endpoint}" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null || echo '{}')
    
    ACTUAL=$(echo "$RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    keys = '${check_field}'.split('.')
    v = d
    for k in keys:
        v = v.get(k, {}) if isinstance(v, dict) else {}
    print(str(v) if v != {} else '')
except:
    print('')
" 2>/dev/null)
    
    if [ "$ACTUAL" = "$expected" ]; then
        ok "$name: $check_field=$ACTUAL"
        SMOKE_PASS=$((SMOKE_PASS + 1))
    else
        fail "$name: 期望 $check_field=$expected, 实际=$ACTUAL"
        SMOKE_FAIL=$((SMOKE_FAIL + 1))
    fi
}

if [ "$SKIP_TEST" = false ]; then
    # 基础排盘测试
    smoke_test "排盘-正常时间" "/api/v1/bazi/interface" \
        '{"solar_date":"2024-02-03","solar_time":"14:00","gender":"male"}' \
        "data.bazi_pillars.day" "丁酉"
    
    # 23 点不换日柱测试
    smoke_test "排盘-23点子时" "/api/v1/bazi/interface" \
        '{"solar_date":"2024-02-03","solar_time":"23:30","gender":"male","name":"smoke_test"}' \
        "data.bazi_pillars.day" "丁酉"
    
    smoke_test "排盘-23点时柱" "/api/v1/bazi/interface" \
        '{"solar_date":"2024-02-03","solar_time":"23:30","gender":"male","name":"smoke_test"}' \
        "data.bazi_pillars.hour" "庚子"
    
    # 身宫命宫测试
    smoke_test "身宫命宫" "/api/v1/bazi/shengong-minggong" \
        '{"solar_date":"1990-01-15","solar_time":"08:30","gender":"male"}' \
        "success" "True"
    
    echo ""
    if [ $SMOKE_FAIL -eq 0 ]; then
        ok "冒烟测试全部通过 ($SMOKE_PASS/$SMOKE_TOTAL)"
    else
        fail "冒烟测试失败 $SMOKE_FAIL/$SMOKE_TOTAL"
        die "冒烟测试未通过，请检查"
    fi
else
    warn "跳过冒烟测试 (--skip-test)"
fi

# ============================================================
# Step 6: 部署报告
# ============================================================
step 6 "部署报告"

DEPLOY_END=$(date +%s)
DEPLOY_DURATION=$((DEPLOY_END - DEPLOY_START))

echo ""
echo "============================================================"
echo -e "${GREEN}${BOLD}  部署成功${NC}"
echo "============================================================"
echo "  耗时: ${DEPLOY_DURATION}s"
echo "  目标: ${NODE1_HOST} (${NODE1_PUBLIC_IP})"
echo "  方式: 热更新"
echo "  测试: ${SMOKE_PASS}/${SMOKE_TOTAL} 通过"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================================"
echo ""
