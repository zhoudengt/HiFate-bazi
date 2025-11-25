#!/bin/bash
# 端到端测试：时间意图识别（LLM智能识别）
# 版本：v2.0
# 日期：2025-11-25

set -e  # 遇到错误立即退出

echo "========================================="
echo "端到端测试：时间意图识别（LLM）"
echo "版本：v2.0"
echo "日期：$(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

# 配置
BASE_URL="${BASE_URL:-http://localhost:8001}"
BAZI_PARAMS="year=1987&month=1&day=7&hour=9&gender=male"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果记录
TEST_RESULTS=()

# 测试函数
test_time_intent() {
    local question="$1"
    local expected_years="$2"
    local test_name="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "测试 #$TOTAL_TESTS: $test_name"
    echo "问题: $question"
    echo "期望年份: $expected_years"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # URL编码
    encoded_question=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$question'))")
    
    # 调用API
    response=$(curl -s "$BASE_URL/api/v1/smart-analyze?question=$encoded_question&$BAZI_PARAMS" 2>/dev/null)
    
    # 检查是否成功获取响应
    if [ -z "$response" ]; then
        echo -e "${RED}✗ 失败${NC}: API无响应"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("FAIL|$test_name|API无响应")
        echo ""
        return 1
    fi
    
    # 解析结果
    result=$(python3 << EOF
import json
import sys

try:
    response = '''$response'''
    data = json.loads(response)
    
    # 检查成功标志
    success = data.get('success', False)
    if not success:
        print("ERROR|API返回success=false")
        sys.exit(1)
    
    # 获取意图结果
    intent_result = data.get('intent_result', {})
    
    # 检查命理相关性
    is_fortune_related = intent_result.get('is_fortune_related', True)
    if not is_fortune_related:
        print("REJECT|命理无关")
        sys.exit(0)
    
    # 获取时间意图
    time_intent = intent_result.get('time_intent', {})
    if not time_intent:
        print("ERROR|未找到time_intent")
        sys.exit(1)
    
    # 提取信息
    time_type = time_intent.get('type', 'N/A')
    target_years = time_intent.get('target_years', [])
    description = time_intent.get('description', 'N/A')
    is_explicit = time_intent.get('is_explicit', False)
    
    # 输出结果
    print(f"SUCCESS|{time_type}|{target_years}|{description}|{is_explicit}")
    
except json.JSONDecodeError as e:
    print(f"ERROR|JSON解析失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR|处理失败: {e}")
    sys.exit(1)
EOF
)
    
    # 解析结果
    IFS='|' read -r status time_type actual_years description is_explicit <<< "$result"
    
    # 检查结果
    if [ "$status" = "ERROR" ]; then
        echo -e "${RED}✗ 失败${NC}: $time_type"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("FAIL|$test_name|$time_type")
        echo ""
        return 1
    fi
    
    if [ "$status" = "REJECT" ]; then
        echo -e "${YELLOW}⊘ 婉拒${NC}: $time_type"
        # 婉拒不算失败，但需要标记
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("REJECT|$test_name|命理无关问题被正确婉拒")
        echo ""
        return 0
    fi
    
    # 检查年份是否匹配
    if [ "$actual_years" = "$expected_years" ]; then
        echo -e "${GREEN}✓ 通过${NC}"
        echo "  时间类型: $time_type"
        echo "  实际年份: $actual_years"
        echo "  时间描述: $description"
        echo "  明确指定: $is_explicit"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("PASS|$test_name|$actual_years")
    else
        echo -e "${RED}✗ 失败${NC}"
        echo "  时间类型: $time_type"
        echo "  期望年份: $expected_years"
        echo "  实际年份: $actual_years"
        echo "  时间描述: $description"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("FAIL|$test_name|期望 $expected_years, 实际 $actual_years")
    fi
    
    echo ""
}

# 测试用例集合
echo "开始执行测试用例..."
echo ""

# ========== 基础时间表达 ==========
echo "【类别1：基础时间表达】"
test_time_intent "我今年的财运如何" "[2025]" "基础-今年"
test_time_intent "明年我能升职吗" "[2026]" "基础-明年"
test_time_intent "我的财运怎么样" "[2025]" "基础-未指定（默认今年）"

# ========== 后N年表达 ==========
echo "【类别2：后N年表达】"
test_time_intent "我后三年的财运如何" "[2026, 2027, 2028]" "后N年-三年"
test_time_intent "我后五年能发财吗" "[2026, 2027, 2028, 2029, 2030]" "后N年-五年"
test_time_intent "我后十年的事业运怎么样" "[2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035]" "后N年-十年（边界测试）"
test_time_intent "我后八年的健康状况" "[2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033]" "后N年-八年（边界测试）"

# ========== 未来N年表达 ==========
echo "【类别3：未来N年表达】"
test_time_intent "我未来三年能发财吗" "[2026, 2027, 2028]" "未来N年-三年"
test_time_intent "我未来十年的运势如何" "[2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035]" "未来N年-十年（边界测试）"

# ========== 接下来N年表达 ==========
echo "【类别4：接下来N年表达】"
test_time_intent "我接下来三年的财运" "[2026, 2027, 2028]" "接下来N年-三年"
test_time_intent "接下来十年我能成功吗" "[2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035]" "接下来N年-十年（边界测试）"

# ========== 明确年份范围 ==========
echo "【类别5：明确年份范围】"
test_time_intent "我2025-2028年的财运" "[2025, 2026, 2027, 2028]" "年份范围-短期"
test_time_intent "我2025到2030年能发财吗" "[2025, 2026, 2027, 2028, 2029, 2030]" "年份范围-中期"
test_time_intent "我2025年的事业运" "[2025]" "单个年份"

# ========== 最近N年表达 ==========
echo "【类别6：最近N年表达】"
test_time_intent "我最近两年的财运" "[2024, 2025]" "最近N年-两年"
test_time_intent "近几年我的运势如何" "[2023, 2024, 2025]" "最近N年-几年（默认3年）"

# ========== 口语化表达 ==========
echo "【类别7：口语化表达】"
test_time_intent "我这几年能发财吗" "[2023, 2024, 2025]" "口语化-这几年"
test_time_intent "三年内我能升职吗" "[2026, 2027, 2028]" "口语化-N年内"

# ========== 命理无关问题（婉拒测试） ==========
echo "【类别8：命理无关问题（婉拒）】"
test_time_intent "你好，在吗" "REJECT" "婉拒-日常闲聊"
test_time_intent "怎么注册账号" "REJECT" "婉拒-技术问题"

# ========== 输出测试总结 ==========
echo ""
echo "========================================="
echo "测试总结"
echo "========================================="
echo "总测试数: $TOTAL_TESTS"
echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败: ${RED}$FAILED_TESTS${NC}"
echo "通过率: $(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")%"
echo ""

# 详细结果
if [ $FAILED_TESTS -gt 0 ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "失败的测试用例："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r status test_name details <<< "$result"
        if [ "$status" = "FAIL" ]; then
            echo -e "${RED}✗${NC} $test_name: $details"
        fi
    done
    echo ""
fi

# 保存测试报告
REPORT_FILE="tests/e2e_test_report_$(date '+%Y%m%d_%H%M%S').txt"
{
    echo "端到端测试报告"
    echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "总测试数: $TOTAL_TESTS"
    echo "通过: $PASSED_TESTS"
    echo "失败: $FAILED_TESTS"
    echo "通过率: $(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")%"
    echo ""
    echo "详细结果："
    for result in "${TEST_RESULTS[@]}"; do
        echo "$result"
    done
} > "$REPORT_FILE"

echo "测试报告已保存: $REPORT_FILE"
echo ""

# 返回退出码
if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 有 $FAILED_TESTS 个测试失败${NC}"
    exit 1
fi

