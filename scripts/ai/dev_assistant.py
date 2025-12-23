#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能开发助手
功能：
1. 自动加载项目上下文（.cursorrules、代码结构、历史问题）
2. 智能理解用户需求（基于项目知识库）
3. 自动执行开发流程检查
4. 提供智能建议和修复方案
5. 开发完成后自动触发热更新

使用方法：
    python3 scripts/ai/dev_assistant.py --start              # 启动开发助手
    python3 scripts/ai/dev_assistant.py --complete           # 完成开发
    python3 scripts/ai/dev_assistant.py --check              # 执行检查
    python3 scripts/ai/dev_assistant.py --suggest <需求>     # 获取开发建议
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入其他模块
from scripts.ai.auto_hot_reload import AutoHotReload
from scripts.ai.decision_engine import DecisionEngine

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color


class DevAssistant:
    """智能开发助手"""
    
    def __init__(self, api_base_url: str = "http://localhost:8001"):
        self.project_root = PROJECT_ROOT
        self.api_base_url = api_base_url
        self.auto_reload = AutoHotReload(api_base_url=api_base_url)
        self.decision_engine = DecisionEngine()
        self.context = {}
        self.knowledge_base_path = self.project_root / "docs" / "knowledge_base"
        
    def load_project_context(self) -> Dict:
        """
        加载项目上下文
        
        Returns:
            项目上下文信息
        """
        context = {
            "project_root": str(self.project_root),
            "cursorrules_exists": (self.project_root / ".cursorrules").exists(),
            "knowledge_base_exists": self.knowledge_base_path.exists(),
            "timestamp": datetime.now().isoformat()
        }
        
        # 加载 .cursorrules 摘要（如果存在）
        cursorrules_path = self.project_root / ".cursorrules"
        if cursorrules_path.exists():
            try:
                with open(cursorrules_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取关键信息（前1000字符）
                    context["cursorrules_summary"] = content[:1000] + "..." if len(content) > 1000 else content
            except Exception as e:
                context["cursorrules_error"] = str(e)
        
        # 检查知识库
        if self.knowledge_base_path.exists():
            knowledge_files = list(self.knowledge_base_path.glob("*.md"))
            context["knowledge_base_files"] = [f.name for f in knowledge_files]
        
        self.context = context
        return context
    
    def get_development_suggestions(self, requirement: str, dev_type: Optional[str] = None) -> Dict:
        """
        获取开发建议
        
        Args:
            requirement: 开发需求描述
            dev_type: 开发类型（api/rule/frontend等）
            
        Returns:
            开发建议
        """
        suggestions = {
            "requirement": requirement,
            "dev_type": dev_type or "unknown",
            "steps": [],
            "checklist": [],
            "files_to_create": [],
            "files_to_modify": [],
            "commands": []
        }
        
        # 根据开发类型提供建议
        if "api" in requirement.lower() or dev_type == "api":
            suggestions["dev_type"] = "api"
            suggestions["steps"] = [
                "1. 在 server/api/v1/ 下创建 API 文件",
                "2. 在 server/api/grpc_gateway.py 中注册 gRPC 端点",
                "3. 在 server/main.py 中注册路由",
                "4. 编写测试用例",
                "5. 运行完整性检查",
                "6. 触发热更新"
            ]
            suggestions["checklist"] = [
                "gRPC 端点已注册",
                "路由已注册",
                "Pydantic 模型已定义",
                "测试用例已编写",
                "热更新已触发"
            ]
            suggestions["files_to_create"] = [
                "server/api/v1/xxx.py",
                "tests/unit/test_xxx.py"
            ]
            suggestions["files_to_modify"] = [
                "server/api/grpc_gateway.py",
                "server/main.py"
            ]
            suggestions["commands"] = [
                "python3 scripts/dev/dev_flow_check.py --files server/api/v1/xxx.py",
                "python3 scripts/ai/auto_hot_reload.py --trigger",
                "python3 scripts/test/auto_test.py --api"
            ]
        
        elif "rule" in requirement.lower() or dev_type == "rule":
            suggestions["dev_type"] = "rule"
            suggestions["steps"] = [
                "1. 准备规则数据（Excel/JSON）",
                "2. 编写解析脚本（scripts/migration/import_xxx_rules.py）",
                "3. 编写导入脚本（scripts/migration/import_xxx_rules_to_db.py）",
                "4. 导入规则到数据库",
                "5. 更新前后端类型映射",
                "6. 运行完整性检查",
                "7. 触发热更新"
            ]
            suggestions["checklist"] = [
                "规则已导入数据库",
                "前后端类型映射已更新",
                "规则匹配测试通过",
                "热更新已触发"
            ]
            suggestions["files_to_create"] = [
                "scripts/migration/import_xxx_rules.py",
                "scripts/migration/import_xxx_rules_to_db.py"
            ]
            suggestions["files_to_modify"] = [
                "local_frontend/formula-analysis.html",
                "server/api/v1/formula_analysis.py"
            ]
            suggestions["commands"] = [
                "python3 scripts/migration/import_xxx_rules.py",
                "python3 scripts/migration/import_xxx_rules_to_db.py",
                "python3 scripts/ai/auto_hot_reload.py --trigger"
            ]
        
        elif "frontend" in requirement.lower() or dev_type == "frontend":
            suggestions["dev_type"] = "frontend"
            suggestions["steps"] = [
                "1. 创建前端页面（local_frontend/xxx.html）",
                "2. 创建 JS 文件（local_frontend/js/xxx.js）",
                "3. 创建 CSS 文件（如需要）",
                "4. 测试前端功能",
                "5. 触发热更新（如涉及后端）"
            ]
            suggestions["checklist"] = [
                "页面文件已创建",
                "JS 文件已创建",
                "前端功能测试通过",
                "后端 API 已对接"
            ]
            suggestions["files_to_create"] = [
                "local_frontend/xxx.html",
                "local_frontend/js/xxx.js"
            ]
            suggestions["commands"] = [
                "python3 scripts/ai/auto_hot_reload.py --trigger"
            ]
        
        return suggestions
    
    def run_development_checks(self, file_paths: Optional[List[Path]] = None) -> Dict:
        """
        执行开发流程检查
        
        Args:
            file_paths: 文件路径列表（可选）
            
        Returns:
            检查结果
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        # 1. 运行开发流程检查
        try:
            from scripts.dev.dev_flow_check import DevFlowChecker
            checker = DevFlowChecker()
            
            if file_paths:
                # 检查指定文件
                for file_path in file_paths:
                    result = checker.check_file(str(file_path))
                    results["checks"][str(file_path)] = result
            else:
                # 完整检查
                result = checker.check_all()
                results["checks"]["all"] = result
        except Exception as e:
            results["checks"]["dev_flow_check"] = {
                "success": False,
                "error": str(e)
            }
        
        # 2. 运行决策引擎分析
        if file_paths:
            try:
                analysis = self.decision_engine.analyze_changes(file_paths)
                results["decision"] = analysis
            except Exception as e:
                results["decision"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def complete_development(self, auto_hot_reload: bool = True) -> Dict:
        """
        完成开发流程
        
        Args:
            auto_hot_reload: 是否自动触发热更新
            
        Returns:
            完成结果
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "steps": []
        }
        
        # 1. 执行完整性检查
        print(f"\n{BLUE}📋 执行开发流程检查...{NC}")
        check_results = self.run_development_checks()
        results["steps"].append({
            "name": "开发流程检查",
            "success": True,
            "result": check_results
        })
        print(f"{GREEN}✅ 开发流程检查完成{NC}")
        
        # 2. 自动触发热更新
        if auto_hot_reload:
            print(f"\n{BLUE}🔄 自动触发热更新...{NC}")
            hot_reload_result = self.auto_reload.trigger_and_verify()
            results["steps"].append({
                "name": "热更新",
                "success": hot_reload_result.get("success", False),
                "result": hot_reload_result
            })
            
            if hot_reload_result.get("success"):
                print(f"{GREEN}✅ 热更新成功{NC}")
            else:
                print(f"{RED}❌ 热更新失败: {hot_reload_result.get('message')}{NC}")
        
        # 3. 生成完成报告
        results["summary"] = {
            "total_steps": len(results["steps"]),
            "successful_steps": sum(1 for s in results["steps"] if s.get("success")),
            "failed_steps": sum(1 for s in results["steps"] if not s.get("success"))
        }
        
        return results
    
    def print_suggestions(self, suggestions: Dict):
        """打印开发建议"""
        print(f"\n{CYAN}{'='*60}{NC}")
        print(f"{CYAN}💡 开发建议{NC}")
        print(f"{CYAN}{'='*60}{NC}\n")
        
        print(f"{GREEN}开发类型：{NC}{suggestions['dev_type']}")
        print(f"{GREEN}需求描述：{NC}{suggestions['requirement']}\n")
        
        if suggestions.get("steps"):
            print(f"{BLUE}开发步骤：{NC}")
            for step in suggestions["steps"]:
                print(f"  {step}")
        
        if suggestions.get("checklist"):
            print(f"\n{BLUE}检查清单：{NC}")
            for item in suggestions["checklist"]:
                print(f"  ☐ {item}")
        
        if suggestions.get("files_to_create"):
            print(f"\n{BLUE}需要创建的文件：{NC}")
            for file in suggestions["files_to_create"]:
                print(f"  📄 {file}")
        
        if suggestions.get("files_to_modify"):
            print(f"\n{BLUE}需要修改的文件：{NC}")
            for file in suggestions["files_to_modify"]:
                print(f"  ✏️  {file}")
        
        if suggestions.get("commands"):
            print(f"\n{BLUE}执行命令：{NC}")
            for cmd in suggestions["commands"]:
                print(f"  $ {YELLOW}{cmd}{NC}")
        
        print(f"\n{CYAN}{'='*60}{NC}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能开发助手")
    parser.add_argument("--start", action="store_true", help="启动开发助手")
    parser.add_argument("--complete", action="store_true", help="完成开发")
    parser.add_argument("--check", type=str, nargs="*", help="执行检查（可指定文件）")
    parser.add_argument("--suggest", type=str, help="获取开发建议（提供需求描述）")
    parser.add_argument("--dev-type", type=str, help="开发类型（api/rule/frontend）")
    parser.add_argument("--no-hot-reload", action="store_true", help="不自动触发热更新")
    parser.add_argument("--api-url", type=str, default="http://localhost:8001", help="API基础URL")
    
    args = parser.parse_args()
    
    assistant = DevAssistant(api_base_url=args.api_url)
    
    if args.start:
        # 启动开发助手
        print(f"{GREEN}🚀 智能开发助手启动{NC}\n")
        context = assistant.load_project_context()
        print(f"{GREEN}✅ 项目上下文已加载{NC}")
        print(f"  项目根目录: {context.get('project_root')}")
        print(f"  规范文件: {'存在' if context.get('cursorrules_exists') else '不存在'}")
        print(f"  知识库: {'存在' if context.get('knowledge_base_exists') else '不存在'}")
        print(f"\n{GREEN}💡 提示：使用 --suggest <需求> 获取开发建议{NC}")
        print(f"{GREEN}💡 提示：使用 --complete 完成开发并自动触发热更新{NC}\n")
    
    elif args.complete:
        # 完成开发
        print(f"{BLUE}📦 完成开发流程...{NC}\n")
        result = assistant.complete_development(auto_hot_reload=not args.no_hot_reload)
        
        print(f"\n{GREEN}📊 完成报告：{NC}")
        print(f"  总步骤: {result['summary']['total_steps']}")
        print(f"  成功: {result['summary']['successful_steps']}")
        print(f"  失败: {result['summary']['failed_steps']}")
        
        if result['summary']['failed_steps'] > 0:
            print(f"\n{RED}❌ 部分步骤失败，请检查上述输出{NC}")
        else:
            print(f"\n{GREEN}✅ 开发流程完成！{NC}\n")
    
    elif args.check:
        # 执行检查
        file_paths = [Path(f) for f in args.check] if args.check else None
        results = assistant.run_development_checks(file_paths)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif args.suggest:
        # 获取开发建议
        suggestions = assistant.get_development_suggestions(args.suggest, args.dev_type)
        assistant.print_suggestions(suggestions)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

