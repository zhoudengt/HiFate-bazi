#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能检查清单
功能：
1. 根据开发类型自动加载对应检查清单
2. 自动执行检查项
3. 生成检查报告
4. 提供修复建议

使用方法：
    python3 scripts/ai/smart_checklist.py --type api --name xxx
    python3 scripts/ai/smart_checklist.py --type rule --name xxx
    python3 scripts/ai/smart_checklist.py --type frontend --name xxx
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入完整性验证器
from scripts.ai.completeness_validator import CompletenessValidator

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class SmartChecklist:
    """智能检查清单"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.validator = CompletenessValidator()
        self.checklist_path = self.project_root / "docs" / "checklists"
    
    def get_checklist_for_type(self, dev_type: str) -> List[Dict]:
        """
        根据开发类型获取检查清单
        
        Args:
            dev_type: 开发类型（api/rule/frontend）
            
        Returns:
            检查清单项列表
        """
        checklists = {
            "api": [
                {"name": "API 文件已创建", "check": "api_file", "required": True},
                {"name": "gRPC 端点已注册", "check": "grpc_registration", "required": True},
                {"name": "路由已注册", "check": "router_registration", "required": True},
                {"name": "Pydantic 模型已定义", "check": "pydantic_model", "required": True},
                {"name": "测试文件已创建", "check": "test_file", "required": True},
            ],
            "rule": [
                {"name": "导入脚本已创建", "check": "import_script", "required": True},
                {"name": "数据库导入脚本已创建", "check": "import_db_script", "required": True},
                {"name": "前端类型映射已添加", "check": "frontend_mapping", "required": True},
                {"name": "后端类型映射已添加", "check": "backend_mapping", "required": True},
            ],
            "frontend": [
                {"name": "HTML 文件已创建", "check": "html_file", "required": True},
                {"name": "JS 文件已创建", "check": "js_file", "required": True},
                {"name": "CSS 文件已创建", "check": "css_file", "required": False},
                {"name": "API 对接已实现", "check": "api_integration", "required": True},
            ]
        }
        
        return checklists.get(dev_type, [])
    
    def run_checklist(self, dev_type: str, name: str) -> Dict:
        """
        运行检查清单
        
        Args:
            dev_type: 开发类型
            name: 名称
            
        Returns:
            检查结果
        """
        # 1. 获取检查清单
        checklist_items = self.get_checklist_for_type(dev_type)
        
        # 2. 运行完整性验证
        if dev_type == "api":
            validation_results = self.validator.validate_api_development(name)
        elif dev_type == "rule":
            validation_results = self.validator.validate_rule_development(name)
        elif dev_type == "frontend":
            validation_results = self.validator.validate_frontend_development(name)
        else:
            return {
                "success": False,
                "error": f"不支持的开发类型: {dev_type}"
            }
        
        # 3. 匹配检查清单和验证结果
        results = {
            "type": dev_type,
            "name": name,
            "items": [],
            "total": len(checklist_items),
            "passed": 0,
            "failed": 0,
            "optional": 0
        }
        
        for item in checklist_items:
            check_name = item["check"]
            required = item.get("required", True)
            
            check_result = validation_results.get("checks", {}).get(check_name, False)
            
            result_item = {
                "name": item["name"],
                "check": check_name,
                "required": required,
                "passed": check_result is True,
                "status": "passed" if check_result is True else ("optional" if not required and check_result is None else "failed")
            }
            
            results["items"].append(result_item)
            
            if result_item["status"] == "passed":
                results["passed"] += 1
            elif result_item["status"] == "optional":
                results["optional"] += 1
            else:
                results["failed"] += 1
        
        results["completeness"] = validation_results.get("completeness", 0)
        results["missing"] = validation_results.get("missing", [])
        
        return results
    
    def print_report(self, results: Dict):
        """打印检查报告"""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}📋 智能检查清单报告{NC}")
        print(f"{BLUE}{'='*60}{NC}\n")
        
        print(f"{GREEN}开发类型：{NC}{results['type']}")
        print(f"{GREEN}名称：{NC}{results['name']}")
        print(f"{GREEN}完整性：{NC}{results['completeness']:.1f}%")
        print(f"{GREEN}检查项：{NC}{results['passed']}/{results['total']} 通过\n")
        
        print(f"{BLUE}检查项详情：{NC}")
        for item in results["items"]:
            status_icon = {
                "passed": f"{GREEN}✅{NC}",
                "failed": f"{RED}❌{NC}",
                "optional": f"{YELLOW}⚪{NC}"
            }.get(item["status"], "  ")
            
            required_mark = "" if item["required"] else " (可选)"
            print(f"  {status_icon} {item['name']}{required_mark}")
        
        if results.get("missing"):
            print(f"\n{RED}缺失的项：{NC}")
            for item in results["missing"]:
                print(f"  ❌ {item}")
        
        print(f"\n{BLUE}{'='*60}{NC}\n")
        
        # 如果完整性 < 100%，提供修复建议
        if results["completeness"] < 100:
            print(f"{YELLOW}💡 修复建议：{NC}")
            print(f"  1. 检查上述缺失的项")
            print(f"  2. 使用完整性验证器获取详细报告：")
            print(f"     python3 scripts/ai/completeness_validator.py --type {results['type']} --name {results['name']}")
            print(f"  3. 完成所有必需项后，运行开发助手完成流程：")
            print(f"     python3 scripts/ai/dev_assistant.py --complete\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能检查清单")
    parser.add_argument("--type", type=str, required=True, choices=["api", "rule", "frontend"], help="开发类型")
    parser.add_argument("--name", type=str, required=True, help="名称")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    checklist = SmartChecklist()
    results = checklist.run_checklist(args.type, args.name)
    
    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        checklist.print_report(results)
        
        # 如果完整性 < 100%，退出码为 1
        if results.get("completeness", 0) < 100:
            sys.exit(1)


if __name__ == "__main__":
    main()

