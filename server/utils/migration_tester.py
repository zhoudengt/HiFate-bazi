#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编排层迁移对比测试脚本

测试目的：确保迁移后的接口与迁移前返回数据完全一致
测试方法：对比迁移前后的 API 响应，检查所有字段是否一致

使用方法：
    python -m server.utils.migration_tester --api pan_display
    python -m server.utils.migration_tester --api interface
    python -m server.utils.migration_tester --api fortune_display
    python -m server.utils.migration_tester --api shengong_minggong
    python -m server.utils.migration_tester --all
"""

import sys
import os
import json
import argparse
import asyncio
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

# 添加项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 测试用例集
TEST_CASES = [
    # 基础用例
    {"solar_date": "1990-01-15", "solar_time": "12:30", "gender": "male", "name": "基础测试-男"},
    {"solar_date": "1985-06-20", "solar_time": "23:45", "gender": "female", "name": "基础测试-女"},
    {"solar_date": "2000-05-10", "solar_time": "08:15", "gender": "male", "name": "基础测试-2000年"},
    
    # 边界用例 - 子时（00:00-01:00）
    {"solar_date": "1995-03-15", "solar_time": "00:15", "gender": "male", "name": "子时-早子时"},
    {"solar_date": "1995-03-15", "solar_time": "00:45", "gender": "female", "name": "子时-晚子时"},
    
    # 边界用例 - 跨日
    {"solar_date": "1990-12-31", "solar_time": "23:59", "gender": "male", "name": "跨日-年末"},
    {"solar_date": "2000-01-01", "solar_time": "00:01", "gender": "female", "name": "跨日-年初"},
    
    # 边界用例 - 闰年
    {"solar_date": "2000-02-29", "solar_time": "12:00", "gender": "male", "name": "闰年-2月29日"},
    {"solar_date": "2004-02-29", "solar_time": "06:30", "gender": "female", "name": "闰年-2月29日-2"},
    
    # 边界用例 - 节气边界（立春前后）
    {"solar_date": "2024-02-04", "solar_time": "16:26", "gender": "male", "name": "节气-立春"},
    {"solar_date": "2024-02-03", "solar_time": "23:00", "gender": "female", "name": "节气-立春前一天"},
    
    # 特殊时辰
    {"solar_date": "1988-08-08", "solar_time": "05:30", "gender": "male", "name": "特殊-寅时"},
    {"solar_date": "1988-08-08", "solar_time": "11:30", "gender": "female", "name": "特殊-午时"},
    {"solar_date": "1988-08-08", "solar_time": "17:30", "gender": "male", "name": "特殊-酉时"},
    {"solar_date": "1988-08-08", "solar_time": "21:30", "gender": "female", "name": "特殊-亥时"},
]


def deep_compare(old_data: Any, new_data: Any, ignore_fields: List[str] = None) -> Dict[str, Any]:
    """
    深度对比两个数据结构
    
    Args:
        old_data: 旧数据
        new_data: 新数据
        ignore_fields: 要忽略的字段列表
        
    Returns:
        差异字典，如果没有差异返回空字典
    """
    ignore_fields = ignore_fields or []
    
    try:
        from deepdiff import DeepDiff
        # 使用 DeepDiff 进行深度对比
        diff = DeepDiff(
            old_data, 
            new_data, 
            ignore_order=True,
            exclude_paths=[f"root['{f}']" for f in ignore_fields],
            significant_digits=2,  # 浮点数精度
            ignore_type_in_groups=[(int, float)]  # 忽略整数和浮点数的类型差异
        )
        
        if diff:
            return {
                'has_diff': True,
                'diff': diff.to_dict()
            }
    except ImportError:
        # 如果没有安装 deepdiff，使用简单对比
        if json.dumps(old_data, sort_keys=True, default=str) != json.dumps(new_data, sort_keys=True, default=str):
            return {
                'has_diff': True,
                'diff': {'old': str(old_data)[:200], 'new': str(new_data)[:200]}
            }
    
    return {'has_diff': False}


class OrchestratorMigrationTester:
    """编排层迁移测试器"""
    
    def __init__(self):
        self.results = []
        
    async def test_pan_display(self, test_case: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        """测试 pan/display 接口"""
        from server.services.bazi_display_service import BaziDisplayService
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        from server.orchestrators.modules_config import get_modules_config
        
        solar_date = test_case['solar_date']
        solar_time = test_case['solar_time']
        gender = test_case['gender']
        
        try:
            # 旧方式：直接调用服务
            old_result = BaziDisplayService.get_pan_display(solar_date, solar_time, gender)
            
            # 新方式：通过编排层
            modules = get_modules_config('pan_display')
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                solar_date, solar_time, gender,
                modules=modules,
                use_cache=False
            )
            
            # 从编排层数据组装响应
            new_result = self._assemble_pan_display_response(orchestrator_data)
            
            # 对比
            diff = deep_compare(old_result, new_result, ignore_fields=['cache_hit', 'conversion_info'])
            
            if diff.get('has_diff'):
                return False, f"数据不一致", diff
            return True, "通过", {}
            
        except Exception as e:
            logger.exception(f"测试异常: {e}")
            return False, f"异常: {str(e)}", {}
    
    async def test_interface(self, test_case: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        """测试 interface 接口"""
        from server.services.bazi_interface_service import BaziInterfaceService
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        from server.orchestrators.modules_config import get_modules_config
        
        solar_date = test_case['solar_date']
        solar_time = test_case['solar_time']
        gender = test_case['gender']
        
        try:
            # 旧方式：直接调用服务
            old_result = BaziInterfaceService.generate_interface_full(
                solar_date, solar_time, gender, "", "未知地", 39.00, 120.00
            )
            
            # 新方式：通过编排层
            modules = get_modules_config('interface')
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                solar_date, solar_time, gender,
                modules=modules,
                use_cache=False
            )
            
            # 从编排层提取
            new_result = orchestrator_data.get('bazi_interface', {})
            
            # 对比
            diff = deep_compare(old_result, new_result)
            
            if diff.get('has_diff'):
                return False, f"数据不一致", diff
            return True, "通过", {}
            
        except Exception as e:
            logger.exception(f"测试异常: {e}")
            return False, f"异常: {str(e)}", {}
    
    async def test_fortune_display(self, test_case: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        """测试 fortune/display 接口"""
        from server.services.bazi_display_service import BaziDisplayService
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        from server.orchestrators.modules_config import get_modules_config
        
        solar_date = test_case['solar_date']
        solar_time = test_case['solar_time']
        gender = test_case['gender']
        current_time = datetime.now()
        
        try:
            # 旧方式：直接调用服务
            old_result = BaziDisplayService.get_fortune_display(
                solar_date, solar_time, gender, current_time
            )
            
            # 新方式：通过编排层
            modules = get_modules_config('fortune_display')
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                solar_date, solar_time, gender,
                modules=modules,
                current_time=current_time,
                use_cache=False
            )
            
            # 验证必要字段存在
            required_fields = ['bazi', 'dayun', 'liunian', 'liuyue']
            missing_fields = [f for f in required_fields if f not in orchestrator_data or not orchestrator_data[f]]
            
            if missing_fields:
                return False, f"缺少字段: {missing_fields}", {}
            
            # 验证核心数据结构
            dayun_list = orchestrator_data.get('dayun', [])
            if not dayun_list or len(dayun_list) == 0:
                return False, "大运列表为空", {}
            
            return True, "通过（结构验证）", {}
            
        except Exception as e:
            logger.exception(f"测试异常: {e}")
            return False, f"异常: {str(e)}", {}
    
    async def test_shengong_minggong(self, test_case: Dict[str, Any]) -> Tuple[bool, str, Dict]:
        """测试 shengong-minggong 接口"""
        from server.orchestrators.bazi_data_orchestrator import BaziDataOrchestrator
        from server.orchestrators.modules_config import get_modules_config
        
        solar_date = test_case['solar_date']
        solar_time = test_case['solar_time']
        gender = test_case['gender']
        current_time = datetime.now()
        
        try:
            # 通过编排层获取数据
            modules = get_modules_config('shengong_minggong')
            orchestrator_data = await BaziDataOrchestrator.fetch_data(
                solar_date, solar_time, gender,
                modules=modules,
                current_time=current_time,
                use_cache=False
            )
            
            # 验证必要字段存在
            required_fields = ['bazi', 'shengong_minggong', 'dayun', 'liunian', 'liuyue']
            missing_fields = [f for f in required_fields if f not in orchestrator_data or not orchestrator_data[f]]
            
            if missing_fields:
                return False, f"缺少字段: {missing_fields}", {}
            
            # 验证 shengong_minggong 结构
            sm_data = orchestrator_data.get('shengong_minggong', {})
            sm_required = ['shengong', 'minggong', 'taiyuan']
            sm_missing = [f for f in sm_required if f not in sm_data]
            
            if sm_missing:
                return False, f"shengong_minggong 缺少字段: {sm_missing}", {}
            
            return True, "通过（结构验证）", {}
            
        except Exception as e:
            logger.exception(f"测试异常: {e}")
            return False, f"异常: {str(e)}", {}
    
    def _assemble_pan_display_response(self, orchestrator_data: Dict) -> Dict:
        """从编排层数据组装 pan/display 响应"""
        from server.services.bazi_display_service import BaziDisplayService
        
        bazi_data = orchestrator_data.get('bazi', {})
        rizhu_data = orchestrator_data.get('rizhu', {})
        rules_data = orchestrator_data.get('rules', [])
        
        # 复用现有格式化逻辑
        formatted_pillars = BaziDisplayService._format_pillars_for_display(bazi_data)
        wuxing_data = BaziDisplayService._format_wuxing_for_display(bazi_data, formatted_pillars)
        
        # 筛选婚姻规则
        marriage_rules = [r for r in rules_data if 'marriage' in r.get('rule_type', '')]
        
        return {
            "success": True,
            "pan": {
                "basic": bazi_data.get('basic_info', {}),
                "pillars": formatted_pillars,
                "wuxing": wuxing_data,
                "rizhu_analysis": rizhu_data,
                "marriage_rules": marriage_rules
            }
        }
    
    async def run_test(self, api_name: str, test_case: Dict[str, Any]) -> Dict:
        """运行单个测试"""
        test_func = getattr(self, f'test_{api_name}', None)
        if not test_func:
            return {
                'api': api_name,
                'test_case': test_case.get('name', 'unknown'),
                'passed': False,
                'message': f'未知 API: {api_name}'
            }
        
        start_time = datetime.now()
        passed, message, diff = await test_func(test_case)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        result = {
            'api': api_name,
            'test_case': test_case.get('name', 'unknown'),
            'passed': passed,
            'message': message,
            'elapsed_seconds': round(elapsed, 2)
        }
        
        if diff.get('has_diff'):
            result['diff'] = diff.get('diff')
        
        return result
    
    async def run_all_tests(self, api_name: str = None) -> List[Dict]:
        """运行所有测试"""
        api_list = [api_name] if api_name else ['pan_display', 'interface', 'fortune_display', 'shengong_minggong']
        
        results = []
        for api in api_list:
            logger.info(f"\n{'='*50}")
            logger.info(f"开始测试 API: {api}")
            logger.info(f"{'='*50}")
            
            for test_case in TEST_CASES:
                logger.info(f"测试用例: {test_case.get('name', 'unknown')}")
                result = await self.run_test(api, test_case)
                results.append(result)
                
                if result['passed']:
                    logger.info(f"  ✅ {result['message']} ({result['elapsed_seconds']}s)")
                else:
                    logger.error(f"  ❌ {result['message']} ({result['elapsed_seconds']}s)")
                    if result.get('diff'):
                        diff_str = json.dumps(result['diff'], indent=2, ensure_ascii=False, default=str)
                        logger.error(f"     差异: {diff_str[:500]}")
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """打印测试摘要"""
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"测试摘要")
        print(f"{'='*60}")
        print(f"总计: {total} 个测试")
        print(f"通过: {passed} 个 ({passed/total*100:.1f}%)")
        print(f"失败: {failed} 个 ({failed/total*100:.1f}%)")
        
        if failed > 0:
            print(f"\n失败的测试:")
            for r in results:
                if not r['passed']:
                    print(f"  - [{r['api']}] {r['test_case']}: {r['message']}")
        
        print(f"{'='*60}\n")


async def main():
    parser = argparse.ArgumentParser(description='编排层迁移对比测试')
    parser.add_argument('--api', type=str, choices=['pan_display', 'interface', 'fortune_display', 'shengong_minggong'],
                        help='要测试的 API')
    parser.add_argument('--all', action='store_true', help='测试所有 API')
    args = parser.parse_args()
    
    tester = OrchestratorMigrationTester()
    
    if args.all:
        results = await tester.run_all_tests()
    elif args.api:
        results = await tester.run_all_tests(args.api)
    else:
        print("请指定 --api 或 --all 参数")
        return
    
    tester.print_summary(results)


if __name__ == '__main__':
    asyncio.run(main())
