#!/bin/bash
# 端到端功能测试脚本 - 测试所有功能

BASE_URL="http://localhost:8001"
GRPC_WEB_URL="http://localhost:8001/api/grpc-web/frontend.gateway.FrontendGateway/Call"

echo "=========================================="
echo "HiFate-bazi 端到端功能测试"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试计数器
PASSED=0
FAILED=0
SKIPPED=0

# 测试结果数组
declare -a TEST_RESULTS

# 测试函数
test_endpoint() {
    local name=$1
    local endpoint=$2
    local payload=$3
    local method=${4:-POST}
    
    echo -n "测试: $name ... "
    
    if [ "$method" = "POST" ]; then
        response=$(curl -s -X POST "$endpoint" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            -w "\n%{http_code}" 2>&1)
    else
        response=$(curl -s -X GET "$endpoint" \
            -w "\n%{http_code}" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        # 检查响应是否包含错误
        if echo "$body" | grep -q '"error"'; then
            echo -e "${RED}失败${NC} (返回错误)"
            echo "  响应: $(echo "$body" | head -c 200)"
            echo ""
            FAILED=$((FAILED + 1))
            TEST_RESULTS+=("❌ $name")
        else
            echo -e "${GREEN}通过${NC}"
            PASSED=$((PASSED + 1))
            TEST_RESULTS+=("✅ $name")
        fi
    else
        echo -e "${RED}失败${NC} (HTTP $http_code)"
        echo "  响应: $(echo "$body" | head -c 200)"
        echo ""
        FAILED=$((FAILED + 1))
        TEST_RESULTS+=("❌ $name (HTTP $http_code)")
    fi
}

# gRPC-Web 测试函数
test_grpc_web() {
    local name=$1
    local endpoint=$2
    local payload=$3
    
    echo -n "测试: $name (gRPC-Web) ... "
    
    # 构建 gRPC-Web 请求（简化版，直接发送 JSON）
    grpc_payload=$(cat <<EOF
{
    "endpoint": "$endpoint",
    "payload_json": "$(echo "$payload" | jq -c . 2>/dev/null | sed 's/"/\\"/g' || echo "$payload")"
}
EOF
)
    
    response=$(curl -s -X POST "$GRPC_WEB_URL" \
        -H "Content-Type: application/json" \
        -H "grpc-web: 1" \
        -d "$grpc_payload" \
        -w "\n%{http_code}" 2>&1)
    
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        # 检查是否是 gRPC-Web 格式响应
        if echo "$body" | grep -q "grpc-status"; then
            grpc_status=$(echo "$body" | grep -oP 'grpc-status: \K[0-9]+' || echo "")
            if [ "$grpc_status" = "0" ] || [ -z "$grpc_status" ]; then
                echo -e "${GREEN}通过${NC}"
                PASSED=$((PASSED + 1))
                TEST_RESULTS+=("✅ $name")
            else
                echo -e "${RED}失败${NC} (gRPC status: $grpc_status)"
            FAILED=$((FAILED + 1))
                TEST_RESULTS+=("❌ $name (gRPC $grpc_status)")
            fi
        elif echo "$body" | grep -q '"error"'; then
            echo -e "${RED}失败${NC} (返回错误)"
            echo "  响应: $(echo "$body" | head -c 200)"
            echo ""
            FAILED=$((FAILED + 1))
            TEST_RESULTS+=("❌ $name")
        else
            echo -e "${GREEN}通过${NC}"
            PASSED=$((PASSED + 1))
            TEST_RESULTS+=("✅ $name")
        fi
    else
        echo -e "${RED}失败${NC} (HTTP $http_code)"
        echo "  响应: $(echo "$body" | head -c 200)"
        echo ""
        FAILED=$((FAILED + 1))
        TEST_RESULTS+=("❌ $name (HTTP $http_code)")
    fi
}

# 检查服务是否运行
echo -e "${BLUE}检查服务状态...${NC}"
if ! curl -s "$BASE_URL" > /dev/null 2>&1; then
    echo -e "${RED}错误: 服务未运行在 $BASE_URL${NC}"
    echo "请先启动服务: python server/start.py"
    exit 1
fi
echo -e "${GREEN}服务运行正常${NC}"
echo ""

# 1. 测试登录功能
echo -e "${BLUE}1. 测试登录功能${NC}"
echo "----------------------------------------"
test_endpoint "REST API 登录" \
    "$BASE_URL/api/v1/auth/login" \
    '{"username":"admin","password":"admin123"}'

# 获取 token
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"admin123"}')
# 使用 Python 解析 JSON（不依赖 jq）
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}无法获取 token，跳过需要认证的测试${NC}"
    SKIPPED=$((SKIPPED + 5))
else
    echo -e "${GREEN}Token 获取成功${NC}"
    echo ""
    
    # 2. 测试 gRPC-Web 登录
    echo -e "${BLUE}2. 测试 gRPC-Web 登录${NC}"
    echo "----------------------------------------"
    test_grpc_web "gRPC-Web 登录" \
        "/auth/login" \
        '{"username":"admin","password":"admin123"}'
    
    echo ""
    # 3. 测试八字计算
    echo -e "${BLUE}3. 测试八字计算${NC}"
    echo "----------------------------------------"
    test_grpc_web "八字盘显示" \
        "/bazi/pan/display" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    test_grpc_web "旺衰分析" \
        "/bazi/wangshuai" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    echo ""
    # 4. 测试公式分析
    echo -e "${BLUE}4. 测试公式分析${NC}"
    echo "----------------------------------------"
    test_grpc_web "公式分析（全部类型）" \
        "/bazi/formula-analysis" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    test_grpc_web "公式分析（财富）" \
        "/bazi/formula-analysis" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male","rule_types":["wealth"]}'
    
    echo ""
    # 5. 测试运势功能
    echo -e "${BLUE}5. 测试运势功能${NC}"
    echo "----------------------------------------"
    test_grpc_web "今日运势" \
        "/bazi/daily-fortune" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    test_grpc_web "当月运势" \
        "/bazi/monthly-fortune" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    test_grpc_web "大运流年" \
        "/bazi/fortune/display" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    test_grpc_web "大运显示" \
        "/bazi/dayun/display" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    test_grpc_web "流年显示" \
        "/bazi/liunian/display" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
    
    echo ""
    # 6. 测试易卦功能
    echo -e "${BLUE}6. 测试易卦功能${NC}"
    echo "----------------------------------------"
    test_grpc_web "易卦占卜" \
        "/bazi/yigua/divinate" \
        '{"question":"测试问题"}'
    
    echo ""
    # 7. 测试支付功能（仅测试接口可用性）
    echo -e "${BLUE}7. 测试支付接口（可用性）${NC}"
    echo "----------------------------------------"
    test_grpc_web "支付提供商列表" \
        "/payment/providers" \
        '{}'
    
    echo ""
    # 8. 测试智能分析
    echo -e "${BLUE}8. 测试智能分析${NC}"
    echo "----------------------------------------"
    test_grpc_web "智能运势分析" \
        "/smart-analyze" \
        '{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'
fi

echo ""
echo "=========================================="
echo -e "${BLUE}测试结果汇总${NC}"
echo "=========================================="
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done
echo ""
echo "统计:"
echo -e "  ${GREEN}通过: $PASSED${NC}"
echo -e "  ${RED}失败: $FAILED${NC}"
if [ $SKIPPED -gt 0 ]; then
    echo -e "  ${YELLOW}跳过: $SKIPPED${NC}"
fi
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}有 $FAILED 个测试失败${NC}"
    exit 1
fi

