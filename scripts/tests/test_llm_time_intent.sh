#!/bin/bash
# 测试LLM时间意图识别功能

echo "========================================="
echo "LLM时间意图识别测试"
echo "========================================="
echo ""

BASE_URL="http://localhost:8001"
BAZI_PARAMS="year=1987&month=1&day=7&hour=9&gender=male"

# 测试用例
test_cases=(
    "我后三年的财运如何"
    "我2025-2028年能发财吗"
    "明年我的事业运怎么样"
    "我的财运怎么样"
    "你好，在吗"
)

for question in "${test_cases[@]}"; do
    echo "【测试】$question"
    echo "--------------------------------"
    
    # URL编码问题
    encoded_question=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$question'))")
    
    # 调用API
    response=$(curl -s "$BASE_URL/api/v1/smart-analyze?question=$encoded_question&$BAZI_PARAMS&include_fortune_context=false")
    
    # 解析结果
    python3 << EOF
import json
response = '''$response'''
try:
    data = json.loads(response)
    
    # 检查是否成功
    success = data.get('success', False)
    print(f"成功: {success}")
    
    # 检查意图结果
    intent_result = data.get('intent_result', {})
    is_fortune_related = intent_result.get('is_fortune_related', True)
    intents = intent_result.get('intents', [])
    
    print(f"命理相关: {is_fortune_related}")
    print(f"事项意图: {intents}")
    
    # 检查时间意图
    time_intent = intent_result.get('time_intent', {})
    if time_intent:
        time_type = time_intent.get('type', 'N/A')
        target_years = time_intent.get('target_years', [])
        description = time_intent.get('description', 'N/A')
        is_explicit = time_intent.get('is_explicit', False)
        
        print(f"时间类型: {time_type}")
        print(f"目标年份: {target_years}")
        print(f"时间描述: {description}")
        print(f"明确指定: {is_explicit}")
    else:
        print("❌ 未找到时间意图")
    
    # 婉拒消息
    if not is_fortune_related:
        reject_message = intent_result.get('reject_message', '')
        print(f"婉拒话术: {reject_message}")
    
except Exception as e:
    print(f"❌ 解析失败: {e}")
    print(f"原始响应: {response[:200]}...")

EOF
    
    echo ""
    echo "================================="
    echo ""
done

echo "测试完成！"

