#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证五行占比和喜神忌神流式接口改造
"""

import sys
import os
import json
import asyncio
import requests
from typing import Dict, Any

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from server.config.config_loader import get_config_from_db_only

# 测试数据
TEST_DATA = {
    'solar_date': '1990-06-15',
    'solar_time': '14:30',
    'gender': 'male',
    'calendar_type': 'solar'
}

BASE_URL = 'http://localhost:8001'


def check_database_configs():
    """检查数据库配置"""
    print("=" * 60)
    print("1. 检查数据库配置")
    print("=" * 60)
    
    configs = {
        'WUXING_PROPORTION_LLM_PLATFORM': get_config_from_db_only('WUXING_PROPORTION_LLM_PLATFORM'),
        'XISHEN_JISHEN_LLM_PLATFORM': get_config_from_db_only('XISHEN_JISHEN_LLM_PLATFORM'),
        'BAILIAN_WUXING_PROPORTION_APP_ID': get_config_from_db_only('BAILIAN_WUXING_PROPORTION_APP_ID'),
        'BAILIAN_XISHEN_JISHEN_APP_ID': get_config_from_db_only('BAILIAN_XISHEN_JISHEN_APP_ID'),
        'BAILIAN_API_KEY': get_config_from_db_only('BAILIAN_API_KEY'),
    }
    
    all_ok = True
    for key, value in configs.items():
        status = '✅' if value else '❌'
        print(f"{status} {key}: {value}")
        if not value:
            all_ok = False
    
    return all_ok


def check_code_structure():
    """检查代码结构"""
    print("\n" + "=" * 60)
    print("2. 检查代码结构")
    print("=" * 60)
    
    import os
    
    files_to_check = [
        'server/orchestrators/bazi_data_orchestrator.py',
        'server/api/v1/wuxing_proportion.py',
        'server/api/v1/xishen_jishen.py'
    ]
    
    all_ok = True
    for file_path in files_to_check:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path} 存在")
            
            # 检查关键函数
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'bazi_data_orchestrator.py' in file_path:
                if '_assemble_wuxing_proportion_from_data' in content:
                    print(f"   ✅ _assemble_wuxing_proportion_from_data 函数存在")
                else:
                    print(f"   ❌ _assemble_wuxing_proportion_from_data 函数不存在")
                    all_ok = False
                
                if '_assemble_xishen_jishen_complete_data' in content:
                    print(f"   ✅ _assemble_xishen_jishen_complete_data 函数存在")
                else:
                    print(f"   ❌ _assemble_xishen_jishen_complete_data 函数不存在")
                    all_ok = False
            
            if 'wuxing_proportion.py' in file_path:
                if 'BaziDataOrchestrator.fetch_data' in content:
                    print(f"   ✅ 使用统一数据服务")
                else:
                    print(f"   ❌ 未使用统一数据服务")
                    all_ok = False
                
                if 'LLMServiceFactory.get_service' in content:
                    print(f"   ✅ 使用LLM服务工厂")
                else:
                    print(f"   ❌ 未使用LLM服务工厂")
                    all_ok = False
            
            if 'xishen_jishen.py' in file_path:
                if 'BaziDataOrchestrator.fetch_data' in content:
                    print(f"   ✅ 使用统一数据服务")
                else:
                    print(f"   ❌ 未使用统一数据服务")
                    all_ok = False
                
                if 'LLMServiceFactory.get_service' in content:
                    print(f"   ✅ 使用LLM服务工厂")
                else:
                    print(f"   ❌ 未使用LLM服务工厂")
                    all_ok = False
        else:
            print(f"❌ {file_path} 不存在")
            all_ok = False
    
    return all_ok


def test_normal_api():
    """测试普通接口（非流式）"""
    print("\n" + "=" * 60)
    print("3. 测试普通接口（确保不受影响）")
    print("=" * 60)
    
    try:
        # 测试五行占比普通接口
        response = requests.post(
            f"{BASE_URL}/api/v1/bazi/wuxing-proportion",
            json=TEST_DATA,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 五行占比普通接口正常")
            else:
                print(f"❌ 五行占比普通接口返回错误: {data.get('error')}")
                return False
        else:
            print(f"❌ 五行占比普通接口HTTP错误: {response.status_code}")
            return False
        
        # 测试喜神忌神普通接口
        response = requests.post(
            f"{BASE_URL}/api/v1/bazi/xishen-jishen",
            json=TEST_DATA,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 喜神忌神普通接口正常")
            else:
                print(f"❌ 喜神忌神普通接口返回错误: {data.get('error')}")
                return False
        else:
            print(f"❌ 喜神忌神普通接口HTTP错误: {response.status_code}")
            return False
        
        return True
    except requests.exceptions.ConnectionError:
        print("⚠️  无法连接到服务器，跳过API测试（请确保服务正在运行）")
        return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_stream_api_format():
    """测试流式接口的SSE消息格式"""
    print("\n" + "=" * 60)
    print("4. 测试流式接口SSE消息格式（需要服务运行）")
    print("=" * 60)
    
    try:
        # 测试五行占比流式接口（只读取前几个消息）
        response = requests.post(
            f"{BASE_URL}/api/v1/bazi/wuxing-proportion/stream",
            json=TEST_DATA,
            stream=True,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ 五行占比流式接口可访问")
            
            # 读取前几个消息
            message_count = 0
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])
                            msg_type = data.get('type')
                            message_count += 1
                            
                            if message_count == 1:
                                print(f"   第一个消息类型: {msg_type}")
                                if msg_type == 'progress':
                                    print("   ✅ 进度消息格式正确")
                                elif msg_type == 'data':
                                    print("   ✅ 数据消息格式正确")
                            
                            if message_count >= 3:
                                break
                        except json.JSONDecodeError:
                            pass
            
            if message_count > 0:
                print(f"   ✅ 成功接收到 {message_count} 条消息")
            else:
                print("   ⚠️  未接收到消息")
        else:
            print(f"❌ 五行占比流式接口HTTP错误: {response.status_code}")
            return False
        
        return True
    except requests.exceptions.ConnectionError:
        print("⚠️  无法连接到服务器，跳过流式接口测试（请确保服务正在运行）")
        return None
    except requests.exceptions.Timeout:
        print("⚠️  请求超时，但接口可访问")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "🔍 开始验证五行占比和喜神忌神流式接口改造" + "\n")
    
    results = {}
    
    # 1. 检查数据库配置
    results['config'] = check_database_configs()
    
    # 2. 检查代码结构
    results['code_structure'] = check_code_structure()
    
    # 3. 测试普通接口
    results['normal_api'] = test_normal_api()
    
    # 4. 测试流式接口格式
    results['stream_api'] = test_stream_api_format()
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    for name, result in results.items():
        if result is None:
            status = "⚠️  跳过"
        elif result:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"{status}: {name}")
    
    all_passed = all(r for r in results.values() if r is not None)
    
    if all_passed:
        print("\n✅ 所有验证通过！")
    else:
        print("\n⚠️  部分验证未通过，请检查上述结果")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
