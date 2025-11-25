#!/bin/bash

echo "🧪 深度分析测试脚本"
echo "=========================================="
echo ""
echo "⚠️  请确保您已在Coze平台更新了新的Prompt！"
echo ""
echo "测试内容："
echo "  - LLM深度分析是否生成"
echo "  - 因果推理是否深入"
echo "  - 是否包含'为什么'、'原因'等关键词"
echo "  - 分析长度和质量"
echo ""
echo "=========================================="
echo ""
echo "⏳ 开始测试（预计30秒）..."
echo ""

python3 << 'EOF'
import requests
import time

url = "http://localhost:8001/api/v1/smart-analyze"
params = {
    "question": "我后年能发财吗？",
    "year": 1987,
    "month": 9,
    "day": 16,
    "hour": 5,
    "gender": "male",
    "include_fortune_context": True
}

start_time = time.time()

try:
    response = requests.get(url, params=params, timeout=90)
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success"):
            text = data['response']
            
            has_llm = "【🔮 命理专家深度解读】" in text
            
            if has_llm:
                # 提取LLM部分
                start = text.index("【🔮 命理专家深度解读】")
                if "="*60 in text[start:]:
                    end = text.index("="*60, start)
                    llm_section = text[start:end]
                else:
                    llm_section = text[start:min(start+5000, len(text))]
                
                # 质量检查
                has_why = llm_section.count("为什么") + llm_section.count("原因")
                has_because = llm_section.count("因为")
                has_result = llm_section.count("导致") + llm_section.count("结果")
                has_example = llm_section.count("表现为") + llm_section.count("比如")
                has_number = llm_section.count("分") + llm_section.count("%")
                
                length = len(llm_section)
                
                print("="*80)
                print("✅ 测试成功！LLM深度解读已生成")
                print("="*80)
                print(f"\n【性能指标】")
                print(f"  ⏱️  响应时间: {elapsed:.1f}秒")
                print(f"  📏 分析长度: {length} 字符")
                print(f"\n【质量指标】")
                print(f"  '为什么'/'原因' 出现: {has_why} 次 {'✅' if has_why >= 5 else '❌需优化'}")
                print(f"  '因为' 出现: {has_because} 次 {'✅' if has_because >= 10 else '❌需优化'}")
                print(f"  '导致'/'结果' 出现: {has_result} 次 {'✅' if has_result >= 5 else '❌需优化'}")
                print(f"  '表现为'/'比如' 出现: {has_example} 次 {'✅' if has_example >= 3 else '❌需优化'}")
                print(f"  数字量化 出现: {has_number} 次 {'✅' if has_number >= 5 else '❌需优化'}")
                
                # 计算总分
                score = 0
                if has_why >= 5: score += 20
                if has_because >= 10: score += 20
                if has_result >= 5: score += 20
                if has_example >= 3: score += 20
                if has_number >= 5: score += 20
                
                print(f"\n【综合评分】: {score}/100分")
                
                if score >= 80:
                    print(f"  🎉🎉🎉 优秀！深度分析质量很高！")
                elif score >= 60:
                    print(f"  ✅ 良好！已有明显改善")
                else:
                    print(f"  ⚠️  需要进一步优化Prompt")
                
                print(f"\n【分析内容预览】（前2000字符）")
                print("="*80)
                print(llm_section[:2000])
                print("="*80)
                
                if length > 2000:
                    print(f"\n... (完整内容共{length}字符)")
                
            else:
                print("❌ LLM深度解读未生成")
                print("\n可能原因：")
                print("  1. Bot的Prompt还没有更新")
                print("  2. Bot处理超时")
                print("  3. Bot返回格式不正确")
        else:
            print(f"❌ API失败: {data.get('message')}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
        
except Exception as e:
    print(f"❌ 测试异常: {e}")
    import traceback
    traceback.print_exc()
EOF

