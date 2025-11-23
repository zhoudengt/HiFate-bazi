#!/bin/bash
# 测试微服务日志输出

echo "=== 测试微服务日志输出 ==="
echo ""
echo "1. 测试 bazi-core-service:"
curl -s -X POST http://127.0.0.1:8001/api/v1/bazi/calculate \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "14:30", "gender": "male"}' > /dev/null

sleep 1
echo "  检查日志:"
tail -n 3 logs/bazi_core_9001.log 2>/dev/null || echo "    日志为空或不存在"
echo ""

echo "2. 测试 bazi-rule-service:"
curl -s -X POST http://127.0.0.1:8001/api/v1/bazi/rules/match \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "14:30", "gender": "male", "rule_types": ["rizhu_gender_dynamic"], "include_bazi": false}' > /dev/null

sleep 1
echo "  检查日志:"
tail -n 3 logs/bazi_rule_9004.log 2>/dev/null || echo "    日志为空或不存在"
echo ""

echo "3. 检查 Web App 日志（客户端调用记录）:"
tail -n 5 logs/web_app_8001.log | grep -E "🔵|✅|❌" || echo "    无相关日志"
echo ""

echo "✅ 测试完成"
