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
NODE2_PORT="${NODE2_PORT:-8001}"  # Node2 可能使用不同端口

# ----------------------------------------
# gate_reload_endpoints_multi <host> <label> [count] [port]
# 多次调用 reload-endpoints，覆盖多 worker（解决部分 worker 端点空问题）
# ----------------------------------------
gate_reload_endpoints_multi() {
    local host="$1"
    local label="$2"
    local count="${3:-8}"
    local port="${4:-$HEALTH_PORT}"
    local url="http://${host}:${port}${RELOAD_ENDPOINTS_PATH}"
    local i=1

    echo "触发 ${label} gRPC 端点恢复（${count} 次，覆盖多 worker）..."
    while [ $i -le $count ]; do
        curl -s -X POST --max-time 15 "$url" > /dev/null 2>&1 || true
        sleep 1
        ((i++))
    done
    echo -e "${GREEN}${label} gRPC 端点恢复完成${NC}"
    return 0
}

# ----------------------------------------
# gate_hot_reload <host> <label> [retries] [port] [ssh_host] [ssh_pass]
# 触发热更新，重试指定次数。port 可选。
# 当 ssh_host 提供时，通过 SSH 在远程执行 curl localhost:port（用于 Node2 公网端口未开放）
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
                sleep 3
                return 0
            fi
        else
            if curl -s -X POST --max-time 60 "http://${host}:${port}${HOT_RELOAD_PATH}" > /dev/null 2>&1; then
                echo -e "${GREEN}${label} 热更新成功${NC}"
                sleep 3
                return 0
            fi
        fi
        echo -e "${YELLOW}${label} 热更新第 ${i}/${retries} 次失败，重试...${NC}"
        sleep 2
        ((i++))
    done
    echo -e "${RED}${label} 热更新失败（${retries} 次重试后）${NC}"
    return 1
}

# ----------------------------------------
# gate_verify_grpc_endpoints <host> <label> [port]
# 验证 23 个关键 gRPC 端点是否全部注册（部署后强制检查）
# ----------------------------------------
gate_verify_grpc_endpoints() {
    local host="$1"
    local label="$2"
    local port="${3:-$HEALTH_PORT}"
    
    # 23 个关键业务端点（必须全部注册）
    local key_endpoints=(
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
        "/payment/unified/create"
        "/payment/unified/verify"
        "/homepage/contents"
    )
    
    echo "验证 ${label} gRPC 端点注册（23 个关键端点）..."
    
    local missing_count=0
    local missing_list=""
    
    # 先触发一次 reload-endpoints 确保端点已加载，并获取端点列表
    local response=$(curl -s --max-time 10 -X POST "http://${host}:${port}/api/v1/hot-reload/reload-endpoints" 2>/dev/null || echo "{}")
    
    if [ -z "$response" ] || [ "$response" = "{}" ]; then
        echo -e "${RED}${label} 无法连接到 reload-endpoints API${NC}"
        return 1
    fi
    
    # 提取端点数量
    local endpoint_count=$(echo "$response" | grep -o '"new_count":[0-9]*' | grep -o '[0-9]*' || echo "0")
    echo "  当前已注册端点数量: ${endpoint_count}"
    
    if [ "$endpoint_count" -lt 20 ]; then
        echo -e "${RED}${label} 端点数量异常（${endpoint_count} < 20），可能热更新失败${NC}"
        return 1
    fi
    
    # 检查每个关键端点（通过实际调用测试）
    local test_endpoints=(
        "/bazi/interface"
        "/bazi/pan/display"
        "/bazi/fortune/display"
    )
    
    for endpoint in "${test_endpoints[@]}"; do
        local test_response=$(curl -s --max-time 5 -X POST "http://${host}:${port}/api/v1/grpc-web/frontend.gateway.FrontendGateway/Call" \
            -H "Content-Type: application/grpc-web+proto" \
            -d "{\"endpoint\":\"${endpoint}\",\"payload_json\":\"{\\\"solar_date\\\":\\\"1990-01-15\\\",\\\"solar_time\\\":\\\"12:00\\\",\\\"gender\\\":\\\"male\\\"}\"}" 2>/dev/null || echo "")
        
        if echo "$test_response" | grep -q "Unsupported endpoint"; then
            ((missing_count++))
            missing_list="${missing_list}\n  - ${endpoint}"
        fi
    done
    
    if [ $missing_count -gt 0 ]; then
        echo -e "${RED}${label} 缺失 ${missing_count} 个关键端点:${missing_list}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}${label} 关键端点验证通过（总数: ${endpoint_count}）${NC}"
    return 0
}

# ----------------------------------------
# gate_health_check <host> <label> [retries] [timeout] [port] [ssh_host] [ssh_pass]
# 健康检查，重试指定次数。port 可选。
# 当 ssh_host 提供时，通过 SSH 在远程执行 curl localhost:port（用于 Node2 公网端口未开放）
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
        ((i++))
    done
    echo -e "${RED}${label} 健康检查失败（${retries} 次重试后）${NC}"
    return 1
}

# ----------------------------------------
# gate_regression_test <env> <categories> <parallel> <project_root> [ssh_host] [ssh_pass]
# 运行 API 回归测试
# env: node2 | production | local
# 当 env=node2 且 ssh_host 提供时，通过 SSH 在 Node2 容器内执行（Python 3.11，与 Node1 一致）
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
        # 在 Node2 容器内执行（scripts 已挂载，Python 3.11 与 Node1 一致）
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
# pass: true | false
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
# 追加一条部署历史到 deploy_history.jsonl
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
# generate_deploy_report <deploy_id> <status> <node2_result> <node1_verify> <commit> <start_time> <end_time>
# 生成单次部署的 JSON 报告
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
