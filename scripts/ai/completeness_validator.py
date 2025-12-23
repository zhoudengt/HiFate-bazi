#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整性验证系统
功能：
1. 检查所有必需文件是否创建
2. 检查所有必需注册是否完成
3. 检查所有必需测试是否编写
4. 生成完整性报告

使用方法：
    python3 scripts/ai/completeness_validator.py --type api --name xxx
    python3 scripts/ai/completeness_validator.py --type rule --name xxx
    python3 scripts/ai/completeness_validator.py --type frontend --name xxx
"""

import os
import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set
from enum import Enum

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class DevType(Enum):
    """开发类型"""
    API = "api"
    RULE = "rule"
    FRONTEND = "frontend"
    MICROSERVICE = "microservice"


class CompletenessValidator:
    """完整性验证器"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.missing_items = []
        self.passed_items = []
    
    def validate_api_development(self, api_name: str) -> Dict:
        """
        验证 API 开发完整性
        
        Args:
            api_name: API 名称（如 "bazi"）
            
        Returns:
            验证结果
        """
        results = {
            "type": "api",
            "name": api_name,
            "checks": {},
            "missing": [],
            "passed": []
        }
        
        # 1. 检查 API 文件是否存在
        api_file = self.project_root / "server" / "api" / "v1" / f"{api_name}.py"
        if api_file.exists():
            results["checks"]["api_file"] = True
            results["passed"].append(f"API 文件存在: {api_file}")
        else:
            results["checks"]["api_file"] = False
            results["missing"].append(f"API 文件不存在: {api_file}")
        
        # 2. 检查 gRPC 端点注册
        grpc_gateway_file = self.project_root / "server" / "api" / "grpc_gateway.py"
        if grpc_gateway_file.exists():
            try:
                with open(grpc_gateway_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否有注册该 API 的端点
                    pattern = rf'@_register\(["\']/.*{api_name}'
                    if re.search(pattern, content, re.IGNORECASE):
                        results["checks"]["grpc_registration"] = True
                        results["passed"].append(f"gRPC 端点已注册")
                    else:
                        results["checks"]["grpc_registration"] = False
                        results["missing"].append(f"gRPC 端点未注册（需要在 grpc_gateway.py 中注册）")
            except Exception as e:
                results["checks"]["grpc_registration"] = False
                results["missing"].append(f"检查 gRPC 注册时出错: {str(e)}")
        else:
            results["checks"]["grpc_registration"] = False
            results["missing"].append(f"grpc_gateway.py 文件不存在")
        
        # 3. 检查路由注册
        main_file = self.project_root / "server" / "main.py"
        if main_file.exists():
            try:
                with open(main_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否有注册该路由
                    pattern = rf'{api_name}_router|router_manager\.register_router\(["\'].*{api_name}'
                    if re.search(pattern, content, re.IGNORECASE):
                        results["checks"]["router_registration"] = True
                        results["passed"].append(f"路由已注册")
                    else:
                        results["checks"]["router_registration"] = False
                        results["missing"].append(f"路由未注册（需要在 main.py 中注册）")
            except Exception as e:
                results["checks"]["router_registration"] = False
                results["missing"].append(f"检查路由注册时出错: {str(e)}")
        else:
            results["checks"]["router_registration"] = False
            results["missing"].append(f"main.py 文件不存在")
        
        # 4. 检查测试文件
        test_file = self.project_root / "tests" / "unit" / f"test_{api_name}.py"
        if test_file.exists():
            results["checks"]["test_file"] = True
            results["passed"].append(f"测试文件存在: {test_file}")
        else:
            results["checks"]["test_file"] = False
            results["missing"].append(f"测试文件不存在: {test_file}")
        
        # 5. 检查 Pydantic 模型
        if api_file.exists():
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否有 Pydantic 模型定义
                    if re.search(r'class\s+\w+Request.*BaseModel', content):
                        results["checks"]["pydantic_model"] = True
                        results["passed"].append(f"Pydantic 模型已定义")
                    else:
                        results["checks"]["pydantic_model"] = False
                        results["missing"].append(f"Pydantic 模型未定义（需要定义 Request 和 Response 模型）")
            except Exception as e:
                results["checks"]["pydantic_model"] = False
                results["missing"].append(f"检查 Pydantic 模型时出错: {str(e)}")
        
        # 计算完整性
        total_checks = len(results["checks"])
        passed_checks = sum(1 for v in results["checks"].values() if v)
        results["completeness"] = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        results["total_checks"] = total_checks
        results["passed_checks"] = passed_checks
        
        return results
    
    def validate_rule_development(self, rule_type: str) -> Dict:
        """
        验证规则开发完整性
        
        Args:
            rule_type: 规则类型（如 "wealth"）
            
        Returns:
            验证结果
        """
        results = {
            "type": "rule",
            "name": rule_type,
            "checks": {},
            "missing": [],
            "passed": []
        }
        
        # 1. 检查导入脚本
        import_script = self.project_root / "scripts" / "migration" / f"import_*_rules.py"
        import_scripts = list(self.project_root.glob(f"scripts/migration/import_*{rule_type}*rules.py"))
        if import_scripts:
            results["checks"]["import_script"] = True
            results["passed"].append(f"导入脚本存在: {import_scripts[0]}")
        else:
            results["checks"]["import_script"] = False
            results["missing"].append(f"导入脚本不存在（需要创建 scripts/migration/import_*{rule_type}*rules.py）")
        
        # 2. 检查数据库导入脚本
        import_db_script = list(self.project_root.glob(f"scripts/migration/import_*{rule_type}*rules_to_db.py"))
        if import_db_script:
            results["checks"]["import_db_script"] = True
            results["passed"].append(f"数据库导入脚本存在: {import_db_script[0]}")
        else:
            results["checks"]["import_db_script"] = False
            results["missing"].append(f"数据库导入脚本不存在（需要创建 scripts/migration/import_*{rule_type}*rules_to_db.py）")
        
        # 3. 检查前端类型映射
        frontend_file = self.project_root / "local_frontend" / "formula-analysis.html"
        if frontend_file.exists():
            try:
                with open(frontend_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否有该规则类型的映射
                    pattern = rf'{rule_type}.*:|["\']{rule_type}["\']'
                    if re.search(pattern, content, re.IGNORECASE):
                        results["checks"]["frontend_mapping"] = True
                        results["passed"].append(f"前端类型映射已添加")
                    else:
                        results["checks"]["frontend_mapping"] = False
                        results["missing"].append(f"前端类型映射未添加（需要在 formula-analysis.html 中添加 {rule_type}）")
            except Exception as e:
                results["checks"]["frontend_mapping"] = False
                results["missing"].append(f"检查前端映射时出错: {str(e)}")
        else:
            results["checks"]["frontend_mapping"] = False
            results["missing"].append(f"formula-analysis.html 文件不存在")
        
        # 4. 检查后端类型映射
        backend_file = self.project_root / "server" / "api" / "v1" / "formula_analysis.py"
        if backend_file.exists():
            try:
                with open(backend_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否有该规则类型的映射
                    pattern = rf'{rule_type}.*:|["\']{rule_type}["\']'
                    if re.search(pattern, content, re.IGNORECASE):
                        results["checks"]["backend_mapping"] = True
                        results["passed"].append(f"后端类型映射已添加")
                    else:
                        results["checks"]["backend_mapping"] = False
                        results["missing"].append(f"后端类型映射未添加（需要在 formula_analysis.py 中添加 {rule_type}）")
            except Exception as e:
                results["checks"]["backend_mapping"] = False
                results["missing"].append(f"检查后端映射时出错: {str(e)}")
        else:
            results["checks"]["backend_mapping"] = False
            results["missing"].append(f"formula_analysis.py 文件不存在")
        
        # 计算完整性
        total_checks = len(results["checks"])
        passed_checks = sum(1 for v in results["checks"].values() if v)
        results["completeness"] = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        results["total_checks"] = total_checks
        results["passed_checks"] = passed_checks
        
        return results
    
    def validate_frontend_development(self, page_name: str) -> Dict:
        """
        验证前端开发完整性
        
        Args:
            page_name: 页面名称（如 "fortune"）
            
        Returns:
            验证结果
        """
        results = {
            "type": "frontend",
            "name": page_name,
            "checks": {},
            "missing": [],
            "passed": []
        }
        
        # 1. 检查 HTML 文件
        html_file = self.project_root / "local_frontend" / f"{page_name}.html"
        if html_file.exists():
            results["checks"]["html_file"] = True
            results["passed"].append(f"HTML 文件存在: {html_file}")
        else:
            results["checks"]["html_file"] = False
            results["missing"].append(f"HTML 文件不存在: {html_file}")
        
        # 2. 检查 JS 文件
        js_file = self.project_root / "local_frontend" / "js" / f"{page_name}.js"
        if js_file.exists():
            results["checks"]["js_file"] = True
            results["passed"].append(f"JS 文件存在: {js_file}")
        else:
            results["checks"]["js_file"] = False
            results["missing"].append(f"JS 文件不存在: {js_file}")
        
        # 3. 检查 CSS 文件（可选）
        css_file = self.project_root / "local_frontend" / "css" / f"{page_name}.css"
        if css_file.exists():
            results["checks"]["css_file"] = True
            results["passed"].append(f"CSS 文件存在: {css_file}")
        else:
            results["checks"]["css_file"] = None  # 可选
            results["missing"].append(f"CSS 文件不存在（可选）: {css_file}")
        
        # 4. 检查后端 API 对接
        if html_file.exists():
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 检查是否有 API 调用
                    if re.search(r'api\.(post|get|put|delete)', content, re.IGNORECASE):
                        results["checks"]["api_integration"] = True
                        results["passed"].append(f"API 对接已实现")
                    else:
                        results["checks"]["api_integration"] = False
                        results["missing"].append(f"API 对接未实现（需要在 HTML/JS 中添加 API 调用）")
            except Exception as e:
                results["checks"]["api_integration"] = False
                results["missing"].append(f"检查 API 对接时出错: {str(e)}")
        
        # 计算完整性（CSS 文件不计入）
        total_checks = sum(1 for k, v in results["checks"].items() if k != "css_file" and v is not None)
        passed_checks = sum(1 for k, v in results["checks"].items() if k != "css_file" and v is True)
        results["completeness"] = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        results["total_checks"] = total_checks
        results["passed_checks"] = passed_checks
        
        return results
    
    def generate_report(self, results: Dict) -> str:
        """
        生成完整性报告
        
        Args:
            results: 验证结果
            
        Returns:
            报告文本
        """
        lines = []
        lines.append(f"\n{BLUE}{'='*60}{NC}")
        lines.append(f"{BLUE}📋 完整性验证报告{NC}")
        lines.append(f"{BLUE}{'='*60}{NC}\n")
        
        lines.append(f"{GREEN}开发类型：{NC}{results['type']}")
        lines.append(f"{GREEN}名称：{NC}{results['name']}")
        lines.append(f"{GREEN}完整性：{NC}{results['completeness']:.1f}% ({results['passed_checks']}/{results['total_checks']})\n")
        
        if results.get("passed"):
            lines.append(f"{GREEN}✅ 已完成的项：{NC}")
            for item in results["passed"]:
                lines.append(f"  ✅ {item}")
        
        if results.get("missing"):
            lines.append(f"\n{RED}❌ 缺失的项：{NC}")
            for item in results["missing"]:
                lines.append(f"  ❌ {item}")
        
        lines.append(f"\n{BLUE}{'='*60}{NC}\n")
        
        return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="完整性验证系统")
    parser.add_argument("--type", type=str, required=True, choices=["api", "rule", "frontend"], help="开发类型")
    parser.add_argument("--name", type=str, required=True, help="名称（API名称/规则类型/页面名称）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    validator = CompletenessValidator()
    
    if args.type == "api":
        results = validator.validate_api_development(args.name)
    elif args.type == "rule":
        results = validator.validate_rule_development(args.name)
    elif args.type == "frontend":
        results = validator.validate_frontend_development(args.name)
    else:
        print(f"{RED}❌ 不支持的开发类型: {args.type}{NC}")
        return
    
    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        report = validator.generate_report(results)
        print(report)
        
        # 如果完整性 < 100%，退出码为 1
        if results["completeness"] < 100:
            sys.exit(1)


if __name__ == "__main__":
    main()

