#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Intent Service 测试脚本
#

set -e

BASE_URL="http://localhost:8001"
TEST_INTENT_URL="${BASE_URL}/api/v1/test-intent"
SMART_ANALYZE_URL="${BASE_URL}/api/v1/smart-analyze"

echo "========================================"
echo "  Intent Service 功能测试"
echo "========================================"
echo ""

# 测试函数
test_intent() {
  local question="$1"
  local expected_intent="$2"
  
  echo "测试: ${question}"
  
  response=$(curl -s "${TEST_INTENT_URL}?question=${question}")
  
  # 提取意图
  intents=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['intents'][0] if 'result' in json.load(sys.stdin) else 'error')" 2>/dev/null || echo "error")
  
  if [[ "$intents" == "$expected_intent" ]]; then
    echo "  ✓ 通过 (识别为: ${intents})"
  else
    echo "  ✗ 失败 (期望: ${expected_intent}, 实际: ${intents})"
  fi
  
  echo ""
}

# 基础测试
echo "【基础测试】"
test_intent "我的事业运势怎么样" "career"
test_intent "我能发财吗" "wealth"
test_intent "我什么时候结婚" "marriage"
test_intent "我的身体健康吗" "health"
test_intent "我是什么性格" "personality"

# 口语化测试
echo "【口语化表达测试】"
test_intent "我这辈子能不能发财" "wealth"
test_intent "我老公对我好吗" "marriage"

# 专业术语测试
echo "【专业术语测试】"
test_intent "我的食神旺不旺" "shishen"
test_intent "我的用神是什么" "yongji"

# 模糊问题测试
echo "【模糊问题测试】"
test_intent "我咋样" "general"
test_intent "帮我算算" "general"

# 完整分析测试
echo "【完整分析测试】"
echo "测试: 智能运势分析API"

full_response=$(curl -s "${SMART_ANALYZE_URL}?question=我的事业运势怎么样&year=1990&month=1&day=1&hour=12&gender=male")

success=$(echo "$full_response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null || echo "false")

if [[ "$success" == "True" ]]; then
  echo "  ✓ 通过 (完整分析成功)"
else
  echo "  ✗ 失败"
  echo "  响应: ${full_response:0:200}..."
fi

echo ""
echo "========================================"
echo "  测试完成"
echo "========================================"

