#!/bin/bash
# ============================================
# 门控检查函数库
# 供 gated_deploy.sh 使用
# ============================================
# 提供：热更新、健康检查、回归测试、门控决策、部署历史记录
# ============================================

# 颜色（若主脚本未定义则提供默认值）
RED="${RED:-\033[0;31m}"
GREEN="${GREEN:-\033[0;32m}"
YELLOW="${YELLOW:-\033[1;33m}"
BLUE="${BLUE:-\033[0;34m}"
NC="${NC:-\033[0m}"

# 热更新 API 路径
HOT_RELOAD_PATH="/api/v1/hot-reload/reload-all"
RELOAD_ENDPOINTS_PATH="/api/v1/hot-reload/reload-endpoints"
HEALTH_PATH="/api/v1/health"
HEALTH_PORT="${HEALTH_PORT:-8001}"
NODE2_PORT="${NODE2_PORT:-8001}"

# ----------------------------------------
# gate_clear_business_cache <ssh_func> <redis_container> <label>
# ----------------------------------------
gate_clear_business_cache() {
    local ssh_func="$1"
    local redis_container="$2"
    local label="$3"
    # 完整覆盖所有计算结果缓存 key（bazi_data/bazi_full/xishen/llm_* 等均在列）
    # 用 xargs -r 防止 scan 返回空集时触发 DEL 参数缺失报错
    local cmd="docker exec $redis_container sh -c 'for p in \"bazi*\" \"fortune*\" \"special_liunians*\" \"desk_fengshui_rules*\" \"cache:*\" \"wangshuai*\" \"xishen*\" \"llm_xishen*\" \"llm_wuxing*\" \"llm_*\" \"formula*\"; do redis-cli --scan --pattern \"\$p\" 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null; done'"

    echo "清理 ${label} Redis 业务缓存（保留会话历史）..."
    if $ssh_func "$cmd" 2>/dev/null; then
        echo -e "${GREEN}${label} 业务缓存已清理${NC}"
    else
        echo -e "${YELLOW}${label} 缓存清理失败或 Redis 不可用，继续...${NC}"
    fi
    return 0
}

# ----------------------------------------
# gate_reload_endpoints_multi <host> <label> [count] [port]
# 多次调用 reload-endpoints，覆盖多 worker
# ----------------------------------------
gate_reload_endpoints_multi() {
    local host="$1"
    local label="$2"
    local count="${3:-4}"
    local port="${4:-$HEALTH_PORT}"
    local url="http://${host}:${port}${RELOAD_ENDPOINTS_PATH}"
    local i=1
    local fail_count=0

    echo "触发 ${label} gRPC 端点恢复（${count} 次，覆盖多 worker）..."
    while [ $i -le $count ]; do
        if ! curl -s -X POST --max-time 10 "$url" > /dev/null 2>&1; then
            ((fail_count++)) || true
        fi
        sleep 0.5
        ((i++)) || true
    done
    if [ $fail_count -ge $count ]; then
        echo -e "${RED}${label} gRPC 端点恢复全部失败（${fail_count}/${count}），服务可能异常${NC}"
        return 1
    elif [ $fail_count -gt 0 ]; then
        echo -e "${YELLOW}${label} gRPC 端点恢复部分失败（${fail_count}/${count}），可能有 worker 未覆盖${NC}"
    else
        echo -e "${GREEN}${label} gRPC 端点恢复完成（${count}/${count}）${NC}"
    fi
    return 0
}

# ----------------------------------------
# gate_hot_reload <host> <label> [retries] [port] [ssh_host] [ssh_pass]
# ----------------------------------------
gate_hot_reload() {
    local host="$1"
    local label="$2"
    local retries="${3:-2}"
    local port="${4:-$HEALTH_PORT}"
    local ssh_host="${5:-}"
    local ssh_pass="${6:-}"
    local i=1

    echo "触发 ${label} 热更新..."
    while [ $i -le $retries ]; do
        if [ -n "$ssh_host" ]; then
            if sshpass -p "$ssh_pass" ssh -o StrictHostKeyChecking=no root@"$ssh_host" "curl -s -X POST --max-time 60 http://localhost:${port}${HOT_RELOAD_PATH}" > /dev/null 2>&1; then
                echo -e "${GREEN}${label} 热更新成功${NC}"
                sleep 1
                return 0
            fi
        else
            if curl -s -X POST --max-time 60 "http://${host}:${port}${HOT_RELOAD_PATH}" > /dev/null 2>&1; then
                echo -e "${GREEN}${label} 热更新成功${NC}"
                sleep 1
                return 0
            fi
        fi
        echo -e "${YELLOW}${label} 热更新第 ${i}/${retries} 次失败，重试...${NC}"
        sleep 2
        ((i++)) || true
    done
    echo -e "${RED}${label} 热更新失败（${retries} 次重试后）${NC}"
    return 1
}

# ----------------------------------------
# gate_hot_reload_and_verify <host> <label> [port] [ssh_host] [ssh_pass]
# 热更新 + 端点恢复 + 端点验证，整体最多重试 2 轮
# ----------------------------------------
gate_hot_reload_and_verify() {
    local host="$1"
    local label="$2"
    local port="${3:-$HEALTH_PORT}"
    local ssh_host="${4:-}"
    local ssh_pass="${5:-}"
    local round=1
    local max_rounds=2

    while [ $round -le $max_rounds ]; do
        echo ""
        if [ $round -gt 1 ]; then
            echo -e "${YELLOW}${label} 第 ${round} 轮重试：重新热更新 + 端点恢复...${NC}"
        fi

        gate_hot_reload "$host" "$label" 2 "$port" "$ssh_host" "$ssh_pass" || echo -e "${YELLOW}${label} 热更新超时，继续尝试端点恢复...${NC}"

        gate_reload_endpoints_multi "$host" "$label" 4 "$port"

        if gate_verify_grpc_endpoints "$host" "$label" "$port"; then
            return 0
        fi

        ((round++)) || true
    done

    echo -e "${RED}${label} 热更新+端点验证 ${max_rounds} 轮后仍失败${NC}"
    return 1
}

# ----------------------------------------
# gate_verify_grpc_endpoints <host> <label> [port]
# 并发验证 21 个关键 gRPC 端点（只在 Node1 调用）
# ----------------------------------------
gate_verify_grpc_endpoints() {
    local host="$1"
    local label="$2"
    local port="${3:-$HEALTH_PORT}"

    echo "验证 ${label} gRPC 端点（并发测试 21 个端点）..."

    local response
    response=$(curl -s --max-time 10 -X POST "http://${host}:${port}/api/v1/hot-reload/reload-endpoints" 2>/dev/null || echo "{}")

    if [ -z "$response" ] || [ "$response" = "{}" ]; then
        echo -e "${RED}${label} 无法连接到 reload-endpoints API${NC}"
        return 1
    fi

    local endpoint_count
    endpoint_count=$(echo "$response" | grep -o '"new_count":[0-9]*' | grep -o '[0-9]*' || echo "0")
    echo "  当前已注册端点数量: ${endpoint_count}"

    if [ "$endpoint_count" -lt 20 ]; then
        echo -e "${RED}${label} 端点数量异常（${endpoint_count} < 20），可能热更新失败${NC}"
        return 1
    fi

    local test_endpoints=(
        "/bazi/interface"
        "/bazi/pan/display"
        "/bazi/fortune/display"
        "/bazi/shengong-minggong"
        "/bazi/wangshuai"
        "/bazi/formula-analysis"
        "/bazi/rizhu-liujiazi"
        "/bazi/data"
        "/bazi/wuxing-proportion/test"
        "/bazi/wuxing-proportion/stream"
        "/bazi/xishen-jishen/test"
        "/bazi/xishen-jishen/stream"
        "/bazi/marriage-analysis/stream"
        "/career-wealth/stream"
        "/children-study/stream"
        "/health/stream"
        "/general-review/stream"
        "/annual-report/stream"
        "/daily-fortune-calendar/query"
        "/daily-fortune-calendar/stream"
        "/homepage/contents"
    )

    local tmpdir
    tmpdir=$(mktemp -d)

    for endpoint in "${test_endpoints[@]}"; do
        local safe_name
        safe_name=$(echo "$endpoint" | tr '/' '_')
        (
            local resp
            resp=$(curl -s --max-time 5 -X POST "http://${host}:${port}/api/v1/grpc-web/frontend.gateway.FrontendGateway/Call" \
                -H "Content-Type: application/grpc-web+proto" \
                -d "{\"endpoint\":\"${endpoint}\",\"payload_json\":\"{\\\"solar_date\\\":\\\"1990-01-15\\\",\\\"solar_time\\\":\\\"12:00\\\",\\\"gender\\\":\\\"male\\\"}\"}" 2>/dev/null || echo "")
            if echo "$resp" | grep -q "Unsupported endpoint"; then
                echo "MISS" > "$tmpdir/$safe_name"
            else
                echo "OK" > "$tmpdir/$safe_name"
            fi
        ) &
    done
    wait

    local missing_count=0
    local missing_list=""
    local tested=0
    for endpoint in "${test_endpoints[@]}"; do
        local safe_name
        safe_name=$(echo "$endpoint" | tr '/' '_')
        local result
        result=$(cat "$tmpdir/$safe_name" 2>/dev/null || echo "MISS")
        if [ "$result" = "MISS" ]; then
            ((missing_count++)) || true
            missing_list="${missing_list}\n  - ${endpoint}"
        else
            ((tested++)) || true
        fi
    done
    rm -rf "$tmpdir"

    if [ $missing_count -gt 0 ]; then
        echo -e "${RED}${label} 缺失 ${missing_count} 个端点:${missing_list}${NC}"
        return 1
    fi

    echo -e "${GREEN}${label} 端点验证通过（注册: ${endpoint_count}, 调用测试: ${tested}/21, 支付端点: 仅注册验证）${NC}"
    return 0
}

# ----------------------------------------
# gate_health_check <host> <label> [retries] [timeout] [port] [ssh_host] [ssh_pass]
# ----------------------------------------
gate_health_check() {
    local host="$1"
    local label="$2"
    local retries="${3:-5}"
    local timeout="${4:-5}"
    local port="${5:-$HEALTH_PORT}"
    local ssh_host="${6:-}"
    local ssh_pass="${7:-}"
    local i=1

    echo "检查 ${label} 健康状态..."
    while [ $i -le $retries ]; do
        local resp
        if [ -n "$ssh_host" ]; then
            resp=$(sshpass -p "$ssh_pass" ssh -o StrictHostKeyChecking=no root@"$ssh_host" "curl -s --max-time $timeout http://localhost:${port}${HEALTH_PATH}" 2>/dev/null || echo "")
        else
            resp=$(curl -s --max-time "$timeout" "http://${host}:${port}${HEALTH_PATH}" 2>/dev/null || echo "")
        fi
        if echo "$resp" | grep -qE '"status"\s*:\s*"(healthy|ok)"|"success"\s*:\s*true'; then
            echo -e "${GREEN}${label} 健康检查通过${NC}"
            return 0
        fi
        echo -e "${YELLOW}${label} 健康检查第 ${i}/${retries} 次失败，重试...${NC}"
        sleep 2
        ((i++)) || true
    done
    echo -e "${RED}${label} 健康检查失败（${retries} 次重试后）${NC}"
    return 1
}

# ----------------------------------------
# gate_regression_test <env> <categories> <parallel> <project_root> [ssh_host] [ssh_pass]
# ----------------------------------------
gate_regression_test() {
    local env="$1"
    local categories="$2"
    local parallel="$3"
    local project_root="$4"
    local ssh_host="${5:-}"
    local ssh_pass="${6:-}"

    local cat_args=""
    for cat in $categories; do
        cat_args="$cat_args --category $cat"
    done
    [ "$parallel" = "true" ] && cat_args="$cat_args --parallel"

    if [ "$env" = "node2" ] && [ -n "$ssh_host" ]; then
        local cmd="docker exec hifate-web python3 /app/scripts/evaluation/api_regression_test.py --env node2-docker $cat_args"
        if [ -n "$ssh_pass" ]; then
            sshpass -p "$ssh_pass" ssh -o StrictHostKeyChecking=no root@"$ssh_host" "$cmd"
        else
            ssh root@"$ssh_host" "$cmd"
        fi
        return $?
    else
        (cd "$project_root" && python3 scripts/evaluation/api_regression_test.py --env "$env" $cat_args)
        return $?
    fi
}

# ----------------------------------------
# print_gate_decision <title> <pass> <message>
# ----------------------------------------
print_gate_decision() {
    local title="$1"
    local pass="$2"
    local message="$3"

    echo ""
    echo "========================================"
    if [ "$pass" = "true" ]; then
        echo -e "${GREEN}✓ ${title}: 通过${NC}"
        echo -e "  ${message}"
    else
        echo -e "${RED}✗ ${title}: 未通过${NC}"
        echo -e "  ${message}"
    fi
    echo "========================================"
    echo ""
}

# ----------------------------------------
# record_deploy_history <deploy_id> <status> <stage> <message> <commit>
# ----------------------------------------
record_deploy_history() {
    local deploy_id="$1"
    local status="$2"
    local stage="$3"
    local message="$4"
    local commit="$5"

    local log_file="${DEPLOY_LOG_DIR}/deploy_history.jsonl"
    mkdir -p "$(dirname "$log_file")"
    local ts
    ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S')
    echo "{\"deploy_id\":\"$deploy_id\",\"status\":\"$status\",\"stage\":\"$stage\",\"message\":\"$message\",\"commit\":\"$commit\",\"ts\":\"$ts\"}" >> "$log_file"
}

# ----------------------------------------
# generate_deploy_report
# ----------------------------------------
generate_deploy_report() {
    local deploy_id="$1"
    local status="$2"
    local node2_result="$3"
    local node1_verify="$4"
    local commit="$5"
    local start_time="$6"
    local end_time="$7"

    local report_file="${DEPLOY_LOG_DIR}/deploy_${deploy_id}.json"
    mkdir -p "$(dirname "$report_file")"
    cat > "$report_file" << EOF
{
  "deploy_id": "$deploy_id",
  "status": "$status",
  "node2_result": "$node2_result",
  "node1_verify": "$node1_verify",
  "commit": "$commit",
  "start_time": "$start_time",
  "end_time": "$end_time"
}
EOF
    echo "部署报告已保存: $report_file"
}
