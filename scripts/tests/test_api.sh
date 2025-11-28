#!/bin/bash
# HiFate系统 - API 测试脚本

BASE_URL="http://127.0.0.1:8001"

echo "=========================================="
echo "HiFate系统 - API 测试"
echo "=========================================="
echo ""

# 检查 jq 是否安装
if ! command -v jq &> /dev/null; then
    echo "⚠️  未安装 jq，输出将不会美化"
    echo "   安装命令: brew install jq (macOS) 或 apt-get install jq (Linux)"
    echo ""
    JQ_CMD="cat"
else
    JQ_CMD="jq ."
fi

# 1. 健康检查
echo "1. 健康检查"
echo "----------------------------------------"
curl -s "${BASE_URL}/health" | $JQ_CMD
echo ""
echo ""

# 2. 基础八字计算
echo "2. 基础八字计算"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/bazi/calculate" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male"
  }' | $JQ_CMD '.success, .data.bazi.bazi_pillars'
echo ""
echo ""

# 3. 规则类型列表
echo "3. 获取规则类型列表"
echo "----------------------------------------"
curl -s "${BASE_URL}/api/v1/bazi/rules/types" | $JQ_CMD
echo ""
echo ""

# 4. 规则统计信息
echo "4. 获取规则统计信息"
echo "----------------------------------------"
curl -s "${BASE_URL}/api/v1/bazi/rules/stats" | $JQ_CMD
echo ""
echo ""

# 5. 匹配所有规则
echo "5. 匹配所有规则"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/bazi/rules/match" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "rule_types": null,
    "include_bazi": true
  }' | $JQ_CMD '.success, .rule_count'
echo ""
echo ""

# 6. 匹配日柱性别分析
echo "6. 匹配日柱性别分析"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/bazi/rules/match" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "rule_types": ["rizhu_gender_dynamic"],
    "include_bazi": false
  }' | $JQ_CMD '.success, .rule_count'
echo ""
echo ""

# 7. 详细八字（包含大运流年）
echo "7. 详细八字（包含大运流年）"
echo "----------------------------------------"
curl -s -X POST "${BASE_URL}/api/v1/bazi/detail" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "14:30",
    "gender": "male",
    "current_time": "2025-01-15 10:00"
  }' | $JQ_CMD '.success, .data.fortune.current_dayun, .data.fortune.current_liunian'
echo ""
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="

