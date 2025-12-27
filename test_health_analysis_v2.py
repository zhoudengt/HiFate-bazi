#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
身体健康分析 V2 接口端到端测试
验证大运流年数据格式和每个大运最多2条流年的限制
"""

import sys
import os
import json
import requests
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 测试配置
BASE_URL = "http://localhost:8001"
ENDPOINT = "/api/v1/health-analysis-v2/stream"

# 测试用例
TEST_CASES = [
    {
        "name": "测试用例1：男性，1990-05-15 14:30",
        "solar_date": "1990-05-15",
        "solar_time": "14:30",
        "gender": "male"
    },
    {
        "name": "测试用例2：女性，1995-08-20 09:00",
        "solar_date": "1995-08-20",
        "solar_time": "09:00",
        "gender": "female"
    }
]


def test_health_analysis_v2_stream(test_case: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试健康分析 V2 流式接口
    
    Returns:
        dict: 测试结果
    """
    print(f"\n{'=' * 80}")
    print(f"测试: {test_case['name']}")
    print(f"{'=' * 80}")
    
    # 准备请求数据
    request_data = {
        "solar_date": test_case["solar_date"],
        "solar_time": test_case["solar_time"],
        "gender": test_case["gender"]
    }
    
    print(f"请求数据: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
    print(f"请求URL: {BASE_URL}{ENDPOINT}")
    
    try:
        # 发送 POST 请求
        response = requests.post(
            f"{BASE_URL}{ENDPOINT}",
            json=request_data,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP 状态码错误: {response.status_code}")
            print(f"响应内容: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
        
        print(f"✅ HTTP 状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        # 解析 SSE 流
        full_content = ""
        chunk_count = 0
        error_occurred = False
        
        print("\n开始接收流式数据...")
        for line in response.iter_lines():
            if not line:
                continue
            
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                chunk_count += 1
                data_str = line_str[6:]  # 去掉 "data: " 前缀
                
                try:
                    data = json.loads(data_str)
                    chunk_type = data.get('type', 'unknown')
                    content = data.get('content', '')
                    
                    if chunk_type == 'progress':
                        full_content += content
                        if chunk_count % 10 == 0:  # 每10个chunk打印一次
                            print(f"  [进度] 已接收 {chunk_count} 个chunk，内容长度: {len(full_content)}")
                    elif chunk_type == 'complete':
                        full_content += content
                        print(f"  [完成] 总共接收 {chunk_count} 个chunk")
                        print(f"  [完成] 最终内容长度: {len(full_content)}")
                        break
                    elif chunk_type == 'error':
                        error_occurred = True
                        print(f"  [错误] {content}")
                        return {
                            "success": False,
                            "error": content,
                            "chunk_count": chunk_count
                        }
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  JSON 解析失败: {e}")
                    print(f"  原始数据: {data_str[:200]}")
        
        if error_occurred:
            return {
                "success": False,
                "error": "流式处理过程中发生错误",
                "chunk_count": chunk_count
            }
        
        # 验证结果
        print(f"\n{'=' * 80}")
        print("验证结果")
        print(f"{'=' * 80}")
        
        # 检查关键内容
        checks = {
            "包含'命盘体质总论'": "命盘体质总论" in full_content or "体质总论" in full_content,
            "包含'五行病理推演'": "五行病理推演" in full_content or "病理推演" in full_content,
            "包含'大运流年健康警示'": "大运流年健康警示" in full_content or "健康警示" in full_content,
            "包含'体质调理建议'": "体质调理建议" in full_content or "调理建议" in full_content,
            "包含'关键流年'": "关键流年" in full_content,
            "内容长度 > 100": len(full_content) > 100
        }
        
        all_passed = True
        for check_name, check_result in checks.items():
            status = "✅" if check_result else "❌"
            print(f"{status} {check_name}: {check_result}")
            if not check_result:
                all_passed = False
        
        # 检查大运流年格式（通过关键词验证）
        dayun_keywords = ["第", "步大运", "关键流年"]
        has_dayun_format = any(keyword in full_content for keyword in dayun_keywords)
        print(f"{'✅' if has_dayun_format else '❌'} 包含大运流年格式关键词: {has_dayun_format}")
        
        if not has_dayun_format:
            all_passed = False
        
        # 显示内容预览
        print(f"\n内容预览（前500字符）:")
        print(f"{full_content[:500]}...")
        
        return {
            "success": all_passed,
            "chunk_count": chunk_count,
            "content_length": len(full_content),
            "checks": checks,
            "has_dayun_format": has_dayun_format,
            "content_preview": full_content[:500]
        }
        
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（60秒）")
        return {
            "success": False,
            "error": "请求超时"
        }
    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 请确保服务已启动（{BASE_URL}）")
        return {
            "success": False,
            "error": "连接失败"
        }
    except Exception as e:
        import traceback
        print(f"❌ 测试失败: {e}")
        print(f"堆栈跟踪:\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def main():
    """主测试函数"""
    print("=" * 80)
    print("身体健康分析 V2 接口端到端测试")
    print("=" * 80)
    print(f"测试URL: {BASE_URL}{ENDPOINT}")
    print(f"测试用例数: {len(TEST_CASES)}")
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n\n{'#' * 80}")
        print(f"测试用例 {i}/{len(TEST_CASES)}")
        print(f"{'#' * 80}")
        
        result = test_health_analysis_v2_stream(test_case)
        result["test_case"] = test_case["name"]
        results.append(result)
        
        if result.get("success"):
            print(f"\n✅ 测试用例 {i} 通过")
        else:
            print(f"\n❌ 测试用例 {i} 失败: {result.get('error', '未知错误')}")
    
    # 汇总结果
    print(f"\n\n{'=' * 80}")
    print("测试汇总")
    print(f"{'=' * 80}")
    
    passed = sum(1 for r in results if r.get("success"))
    total = len(results)
    
    print(f"总测试用例: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed / total * 100:.1f}%")
    
    # 详细结果
    print(f"\n详细结果:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success") else "❌"
        print(f"{status} 测试用例 {i}: {result.get('test_case', '未知')}")
        if result.get("chunk_count"):
            print(f"   接收chunk数: {result['chunk_count']}")
        if result.get("content_length"):
            print(f"   内容长度: {result['content_length']}")
        if result.get("error"):
            print(f"   错误: {result['error']}")
    
    # 返回退出码
    if passed == total:
        print(f"\n✅ 所有测试通过！")
        return 0
    else:
        print(f"\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

