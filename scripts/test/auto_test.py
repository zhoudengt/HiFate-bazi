#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试自动化工具
用途：自动执行所有测试，生成测试报告

使用方法：
  python3 scripts/test/auto_test.py --all              # 运行所有测试
  python3 scripts/test/auto_test.py --unit             # 只运行单元测试
  python3 scripts/test/auto_test.py --api              # 只运行 API 测试
  python3 scripts/test/auto_test.py --e2e              # 只运行端到端测试
  python3 scripts/test/auto_test.py --coverage         # 生成覆盖率报告
"""

import sys
import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class AutoTester:
    """测试自动化工具"""
    
    def __init__(self):
        self.results = {
            'unit': {'passed': 0, 'failed': 0, 'errors': []},
            'api': {'passed': 0, 'failed': 0, 'errors': []},
            'integration': {'passed': 0, 'failed': 0, 'errors': []},
            'e2e': {'passed': 0, 'failed': 0, 'errors': []},
        }
        self.coverage = None
    
    def run_all(self) -> bool:
        """运行所有测试"""
        print(f"{BLUE}🧪 开始运行所有测试...{NC}\n")
        
        # 1. 单元测试
        print(f"{BLUE}1. 运行单元测试{NC}")
        unit_passed = self.run_unit_tests()
        
        # 2. API 测试
        print(f"\n{BLUE}2. 运行 API 测试{NC}")
        api_passed = self.run_api_tests()
        
        # 3. 集成测试
        print(f"\n{BLUE}3. 运行集成测试{NC}")
        integration_passed = self.run_integration_tests()
        
        # 4. 端到端测试
        print(f"\n{BLUE}4. 运行端到端测试{NC}")
        e2e_passed = self.run_e2e_tests()
        
        # 输出总结
        self._print_summary()
        
        return unit_passed and api_passed and integration_passed and e2e_passed
    
    def run_unit_tests(self) -> bool:
        """运行单元测试"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/unit/', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=60
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✓{NC} 单元测试通过")
                self.results['unit']['passed'] = 1
                return True
            else:
                print(f"  {RED}✗{NC} 单元测试失败")
                print(f"  {RED}输出: {result.stdout[-500:]}{NC}")
                self.results['unit']['failed'] = 1
                self.results['unit']['errors'].append(result.stdout)
                return False
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗{NC} 单元测试超时")
            return False
        except FileNotFoundError:
            print(f"  {YELLOW}⚠️  pytest 未安装，跳过单元测试{NC}")
            return True
    
    def run_api_tests(self) -> bool:
        """运行 API 测试"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/api/', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=120
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✓{NC} API 测试通过")
                self.results['api']['passed'] = 1
                return True
            else:
                print(f"  {RED}✗{NC} API 测试失败")
                print(f"  {RED}输出: {result.stdout[-500:]}{NC}")
                self.results['api']['failed'] = 1
                self.results['api']['errors'].append(result.stdout)
                return False
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗{NC} API 测试超时")
            return False
        except FileNotFoundError:
            print(f"  {YELLOW}⚠️  pytest 未安装，跳过 API 测试{NC}")
            return True
    
    def run_integration_tests(self) -> bool:
        """运行集成测试"""
        try:
            result = subprocess.run(
                ['pytest', 'tests/integration/', '-v', '--tb=short'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=180
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✓{NC} 集成测试通过")
                self.results['integration']['passed'] = 1
                return True
            else:
                print(f"  {RED}✗{NC} 集成测试失败")
                print(f"  {RED}输出: {result.stdout[-500:]}{NC}")
                self.results['integration']['failed'] = 1
                self.results['integration']['errors'].append(result.stdout)
                return False
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗{NC} 集成测试超时")
            return False
        except FileNotFoundError:
            print(f"  {YELLOW}⚠️  pytest 未安装，跳过集成测试{NC}")
            return True
    
    def run_e2e_tests(self) -> bool:
        """运行端到端测试"""
        e2e_test_file = PROJECT_ROOT / 'tests/e2e_production_test.py'
        if not e2e_test_file.exists():
            print(f"  {YELLOW}⚠️  端到端测试文件不存在{NC}")
            return True
        
        try:
            result = subprocess.run(
                ['python3', str(e2e_test_file)],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=300
            )
            
            if result.returncode == 0:
                print(f"  {GREEN}✓{NC} 端到端测试通过")
                self.results['e2e']['passed'] = 1
                return True
            else:
                print(f"  {RED}✗{NC} 端到端测试失败")
                print(f"  {RED}输出: {result.stdout[-500:]}{NC}")
                self.results['e2e']['failed'] = 1
                self.results['e2e']['errors'].append(result.stdout)
                return False
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗{NC} 端到端测试超时")
            return False
        except Exception as e:
            print(f"  {YELLOW}⚠️  端到端测试异常: {e}{NC}")
            return True
    
    def generate_coverage_report(self) -> Dict:
        """生成覆盖率报告"""
        print(f"{BLUE}📊 生成测试覆盖率报告...{NC}\n")
        
        try:
            result = subprocess.run(
                ['pytest', '--cov=server', '--cov=src', '--cov-report=term-missing', '--cov-report=json'],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=300
            )
            
            # 读取 JSON 覆盖率报告
            coverage_file = PROJECT_ROOT / 'coverage.json'
            if coverage_file.exists():
                with open(coverage_file, 'r', encoding='utf-8') as f:
                    coverage_data = json.load(f)
                    self.coverage = coverage_data
                    
                    total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                    print(f"  {GREEN}总覆盖率: {total_coverage:.2f}%{NC}")
                    
                    return coverage_data
            
            return {}
        except subprocess.TimeoutExpired:
            print(f"  {RED}✗{NC} 覆盖率报告生成超时")
            return {}
        except FileNotFoundError:
            print(f"  {YELLOW}⚠️  pytest 未安装，无法生成覆盖率报告{NC}")
            return {}
        except Exception as e:
            print(f"  {YELLOW}⚠️  生成覆盖率报告失败: {e}{NC}")
            return {}
    
    def _print_summary(self):
        """输出测试总结"""
        print(f"\n{BLUE}📊 测试总结：{NC}\n")
        
        total_passed = sum(r['passed'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        
        for test_type, result in self.results.items():
            status = f"{GREEN}✓{NC}" if result['passed'] > 0 and result['failed'] == 0 else f"{RED}✗{NC}"
            print(f"  {status} {test_type}: 通过 {result['passed']}, 失败 {result['failed']}")
        
        print(f"\n  总计: 通过 {total_passed}, 失败 {total_failed}")
        
        if total_failed == 0:
            print(f"\n{GREEN}✅ 所有测试通过！{NC}\n")
        else:
            print(f"\n{RED}❌ 部分测试失败，请检查{NC}\n")
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        return {
            'timestamp': datetime.now().isoformat(),
            'results': self.results,
            'coverage': self.coverage,
            'summary': {
                'total_passed': sum(r['passed'] for r in self.results.values()),
                'total_failed': sum(r['failed'] for r in self.results.values()),
            }
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试自动化工具')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    parser.add_argument('--unit', action='store_true', help='只运行单元测试')
    parser.add_argument('--api', action='store_true', help='只运行 API 测试')
    parser.add_argument('--integration', action='store_true', help='只运行集成测试')
    parser.add_argument('--e2e', action='store_true', help='只运行端到端测试')
    parser.add_argument('--coverage', action='store_true', help='生成覆盖率报告')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式报告')
    parser.add_argument('--exit-on-failure', action='store_true', help='测试失败时退出（用于 CI/CD）')
    
    args = parser.parse_args()
    
    tester = AutoTester()
    success = False
    
    if args.all:
        success = tester.run_all()
        if args.coverage:
            tester.generate_coverage_report()
    elif args.unit:
        success = tester.run_unit_tests()
    elif args.api:
        success = tester.run_api_tests()
    elif args.integration:
        success = tester.run_integration_tests()
    elif args.e2e:
        success = tester.run_e2e_tests()
    elif args.coverage:
        tester.generate_coverage_report()
        success = True
    else:
        parser.print_help()
        sys.exit(1)
    
    if args.json:
        report = tester.generate_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    if args.exit_on_failure and not success:
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

