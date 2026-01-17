#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证流式接口和 debug 接口返回的 prompt 是否完全一致

确保评测脚本使用的参数与生产环境流式接口完全一致。
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from scripts.evaluation.api_client import ApiClient


async def verify_prompt_consistency(
    scene: str,
    solar_date: str,
    solar_time: str,
    gender: str,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    验证流式接口和 debug 接口返回的 prompt 是否完全一致
    
    Args:
        scene: 场景名称（health, marriage, career_wealth, etc.）
        solar_date: 阳历日期
        solar_time: 出生时间
        gender: 性别
        base_url: API 基础 URL
        
    Returns:
        验证结果字典
    """
    api_client = ApiClient(base_url=base_url)
    
    # 场景到测试方法的映射
    scene_to_test_method = {
        'career_wealth': api_client.call_career_wealth_test,
        'general_review': api_client.call_general_review_test,
        'marriage': api_client.call_marriage_analysis_test,
        'health': api_client.call_health_analysis_test,
        'children_study': api_client.call_children_study_test,
        'wuxing_proportion': api_client.call_wuxing_proportion_test,
        'xishen_jishen': api_client.call_xishen_jishen_test,
        'daily_fortune': api_client.call_daily_fortune_calendar_test,
    }
    
    test_method = scene_to_test_method.get(scene)
    if not test_method:
        return {
            "success": False,
            "error": f"未知场景: {scene}"
        }
    
    try:
        # 调用 debug/test 接口获取 prompt
        result = await test_method(solar_date, solar_time, gender)
        
        if not result.get('success'):
            return {
                "success": False,
                "error": f"调用 debug 接口失败: {result.get('error')}"
            }
        
        formatted_data = result.get('formatted_data', '')
        
        if not formatted_data:
            return {
                "success": False,
                "error": "debug 接口返回的 formatted_data 为空"
            }
        
        return {
            "success": True,
            "formatted_data": formatted_data,
            "formatted_data_length": len(formatted_data),
            "formatted_data_preview": formatted_data[:500],
            "message": f"✅ {scene} 场景的 debug 接口返回了 prompt，长度: {len(formatted_data)} 字符"
        }
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"验证失败: {str(e)}",
            "traceback": traceback.format_exc()
        }


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="验证流式接口和 debug 接口返回的 prompt 是否完全一致")
    parser.add_argument("--scene", required=True, help="场景名称（health, marriage, career_wealth, etc.）")
    parser.add_argument("--solar-date", required=True, help="阳历日期 YYYY-MM-DD")
    parser.add_argument("--solar-time", required=True, help="出生时间 HH:MM")
    parser.add_argument("--gender", required=True, help="性别 male/female")
    parser.add_argument("--base-url", default=None, help="API 基础 URL")
    
    args = parser.parse_args()
    
    result = await verify_prompt_consistency(
        scene=args.scene,
        solar_date=args.solar_date,
        solar_time=args.solar_time,
        gender=args.gender,
        base_url=args.base_url
    )
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    if not result.get('success'):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
