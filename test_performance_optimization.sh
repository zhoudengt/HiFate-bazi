#!/bin/bash
# 性能优化测试脚本

echo "========================================="
echo "🚀 HiFate-bazi 性能优化测试"
echo "========================================="
echo ""

# 检查服务是否运行
echo "📋 步骤1：检查服务状态..."
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ 主服务未运行！请先执行："
    echo "   ./start_all_services.sh"
    exit 1
fi
echo "✅ 主服务运行正常"

# 检查Redis
echo ""
echo "📋 步骤2：检查Redis缓存..."
if ! redis-cli -p 16379 PING > /dev/null 2>&1; then
    echo "❌ Redis未运行！"
    exit 1
fi
echo "✅ Redis运行正常"

# 清除缓存
echo ""
echo "📋 步骤3：清除Redis缓存（测试首次查询）..."
redis-cli -p 16379 FLUSHDB > /dev/null 2>&1
echo "✅ 缓存已清除"

# 测试1：财运问题（首次查询）
echo ""
echo "========================================="
echo "🧪 测试1：财运问题（首次查询，无缓存）"
echo "========================================="
echo "问题：我明年的财运如何？"
echo "八字：1990-05-15 14:00 男"
echo ""
echo "开始测试..."

start_time=$(date +%s)
response1=$(curl -s -X GET "http://localhost:8000/api/v1/smart-fortune/smart-analyze?year=1990&month=5&day=15&hour=14&gender=male&question=我明年的财运如何？&include_fortune_context=true")
end_time=$(date +%s)
duration1=$((end_time - start_time))

echo ""
echo "⏱️ 响应时间：${duration1}秒"
echo ""

# 检查响应内容
if echo "$response1" | jq -e '.success' > /dev/null 2>&1; then
    success=$(echo "$response1" | jq -r '.success')
    if [ "$success" = "true" ]; then
        echo "✅ API调用成功"
        
        # 检查是否包含fortune_context
        if echo "$response1" | jq -e '.fortune_context' > /dev/null 2>&1; then
            echo "✅ 包含流年大运分析"
            
            # 检查是否有评分
            if echo "$response1" | jq -e '.fortune_context.time_analysis.liunian_list[0].fortune_scores' > /dev/null 2>&1; then
                wealth_score=$(echo "$response1" | jq -r '.fortune_context.time_analysis.liunian_list[0].fortune_scores.wealth.score')
                wealth_level=$(echo "$response1" | jq -r '.fortune_context.time_analysis.liunian_list[0].fortune_scores.wealth.level')
                echo "✅ 包含运势评分：财运 ${wealth_score}分（${wealth_level}）"
            else
                echo "⚠️  缺少运势评分"
            fi
        else
            echo "⚠️  缺少流年大运分析"
        fi
        
        # 检查响应长度
        response_length=$(echo "$response1" | jq -r '.response' | wc -c)
        echo "📝 响应长度：${response_length} 字符"
    else
        error=$(echo "$response1" | jq -r '.error // "未知错误"')
        echo "❌ API返回失败：$error"
    fi
else
    echo "❌ API响应格式错误"
    echo "$response1" | head -n 20
fi

# 测试2：财运问题（重复查询，测试缓存）
echo ""
echo "========================================="
echo "🧪 测试2：财运问题（重复查询，测试缓存）"
echo "========================================="
echo "相同问题，相同八字"
echo ""
echo "开始测试..."

start_time=$(date +%s)
response2=$(curl -s -X GET "http://localhost:8000/api/v1/smart-fortune/smart-analyze?year=1990&month=5&day=15&hour=14&gender=male&question=我明年的财运如何？&include_fortune_context=true")
end_time=$(date +%s)
duration2=$((end_time - start_time))

echo ""
echo "⏱️ 响应时间：${duration2}秒"

# 检查是否命中缓存
if [ $duration2 -lt 2 ]; then
    echo "✅ 可能命中缓存（响应时间<2秒）"
else
    echo "⚠️  未命中缓存或缓存未生效（响应时间${duration2}秒）"
fi

# 检查Redis中的key
echo ""
echo "📊 Redis缓存状态："
cache_keys=$(redis-cli -p 16379 KEYS "fortune_analysis:*" 2>/dev/null | wc -l)
echo "   缓存key数量：${cache_keys}"

# 测试3：问题过滤（明显不相关）
echo ""
echo "========================================="
echo "🧪 测试3：问题过滤（明显不相关）"
echo "========================================="
echo "问题：你吃了吗？"
echo ""
echo "开始测试..."

start_time=$(date +%s)
response3=$(curl -s -X GET "http://localhost:8000/api/v1/smart-fortune/smart-analyze?year=1990&month=5&day=15&hour=14&gender=male&question=你吃了吗？")
end_time=$(date +%s)
duration3=$((end_time - start_time))

echo ""
echo "⏱️ 响应时间：${duration3}秒"

if echo "$response3" | jq -e '.success' > /dev/null 2>&1; then
    success=$(echo "$response3" | jq -r '.success')
    if [ "$success" = "false" ]; then
        message=$(echo "$response3" | jq -r '.message')
        echo "✅ 正确拒绝无关问题"
        echo "   提示：${message}"
        
        if [ $duration3 -lt 2 ]; then
            echo "✅ 快速过滤（<2秒）"
        else
            echo "⚠️  过滤较慢（${duration3}秒）"
        fi
    else
        echo "❌ 未正确过滤无关问题"
    fi
else
    echo "❌ API响应格式错误"
fi

# 测试4：流式输出检查
echo ""
echo "========================================="
echo "🧪 测试4：流式输出API"
echo "========================================="
echo "检查流式API endpoint是否可用..."
echo ""

if curl -s -I "http://localhost:8000/api/v1/smart-fortune/smart-analyze-stream?year=1990&month=5&day=15&hour=14&gender=male&question=测试" | grep -q "text/event-stream"; then
    echo "✅ 流式API endpoint正常"
    echo "   访问地址：http://localhost:8001/smart-fortune-stream.html"
else
    echo "⚠️  流式API endpoint可能未启用"
fi

# 性能总结
echo ""
echo "========================================="
echo "📊 性能测试总结"
echo "========================================="
echo ""
echo "🔹 首次查询（无缓存）：${duration1}秒"
echo "🔹 重复查询（有缓存）：${duration2}秒"
echo "🔹 问题过滤：${duration3}秒"
echo ""

if [ $duration1 -le 15 ]; then
    echo "✅ 首次查询性能优秀（≤15秒）"
elif [ $duration1 -le 20 ]; then
    echo "⚠️  首次查询性能良好，可进一步优化"
else
    echo "❌ 首次查询较慢（>20秒），建议检查："
    echo "   1. Coze Bot Prompt是否应用精简版"
    echo "   2. Coze Bot参数是否优化"
    echo "   3. 网络连接是否正常"
fi

if [ $duration2 -le 2 ]; then
    echo "✅ 缓存机制正常（≤2秒）"
else
    echo "❌ 缓存可能未生效，建议检查："
    echo "   1. Redis是否正常运行"
    echo "   2. 环境变量是否配置"
    echo "   3. 日志中是否有Redis错误"
fi

echo ""
echo "========================================="
echo "📝 下一步建议"
echo "========================================="
echo ""
echo "1. 如果首次查询>15秒："
echo "   → 应用精简版Prompt到Coze Bot"
echo "   → 调整Bot参数（见 docs/Coze_Bot性能优化指南.md）"
echo ""
echo "2. 如果缓存未生效："
echo "   → 检查Redis配置"
echo "   → 查看日志：tail -f logs/server.log | grep Redis"
echo ""
echo "3. 测试流式输出："
echo "   → 浏览器访问：http://localhost:8001/smart-fortune-stream.html"
echo "   → 体验实时流式展示效果"
echo ""
echo "4. 查看完整报告："
echo "   → 文档：docs/性能优化实施报告.md"
echo ""

echo "========================================="
echo "✅ 测试完成！"
echo "========================================="

