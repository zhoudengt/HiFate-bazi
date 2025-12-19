#!/bin/bash
# 验证修复结果的脚本

echo "============================================================"
echo "✅ 验证修复结果"
echo "============================================================"

echo ""
echo "📡 测试生产环境 API..."
echo ""

curl -s -X POST http://8.210.52.217:8001/api/v1/bazi/formula-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1987-01-07",
    "solar_time": "09:00",
    "gender": "male"
  }' | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    stats = data.get('data', {}).get('statistics', {})
    total = stats.get('total_matched', 0)
    
    print('✅ 生产环境匹配结果:')
    print(f\"  总匹配数: {total} 条\")
    print(f\"  财富: {stats.get('wealth_count', 0)}\")
    print(f\"  婚姻: {stats.get('marriage_count', 0)}\")
    print(f\"  事业: {stats.get('career_count', 0)}\")
    print(f\"  身体: {stats.get('health_count', 0)}\")
    print(f\"  总评: {stats.get('summary_count', 0)}\")
    print(f\"  子女: {stats.get('children_count', 0)}\")
    print(f\"  性格: {stats.get('character_count', 0)}\")
    print(f\"  十神命格: {stats.get('shishen_count', 0)}\")
    
    # 判断是否修复成功
    if total >= 1000:
        print(f\"\n🎉 修复成功！匹配数量已恢复正常 ({total} 条)\")
    elif total >= 500:
        print(f\"\n⚠️  部分修复，匹配数量有所提升 ({total} 条)，但仍有差异\")
    else:
        print(f\"\n❌ 修复未生效，匹配数量仍然不足 ({total} 条)\")
        print(f\"   建议检查:\")
        print(f\"   1. SQL 是否执行成功\")
        print(f\"   2. 缓存是否已清除\")
        print(f\"   3. 规则 enabled 状态\")
except Exception as e:
    print(f'❌ 解析失败: {e}')
"

echo ""
echo "============================================================"

