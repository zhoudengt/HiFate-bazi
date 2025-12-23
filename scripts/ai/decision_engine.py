#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能决策引擎
功能：
1. 判断是否需要热更新（100%需要，禁止重启）
2. 判断是否需要重启（100%禁止）
3. 判断是否需要测试
4. 判断是否需要部署
5. 提供明确的执行建议

使用方法：
    python3 scripts/ai/decision_engine.py --analyze <文件路径>
    python3 scripts/ai/decision_engine.py --check <变更类型>
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
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


class ChangeType(Enum):
    """变更类型"""
    PYTHON_CODE = "python_code"          # Python代码
    CONFIG_FILE = "config_file"          # 配置文件
    RULE_DATA = "rule_data"              # 规则数据
    FRONTEND_CODE = "frontend_code"      # 前端代码
    DEPENDENCY = "dependency"            # 依赖变更
    DATABASE_SCHEMA = "database_schema"  # 数据库结构
    DOCKERFILE = "dockerfile"            # Dockerfile
    ENV_VAR = "env_var"                  # 环境变量


class ActionType(Enum):
    """操作类型"""
    HOT_RELOAD = "hot_reload"            # 热更新（必须）
    RESTART = "restart"                  # 重启（禁止）
    TEST = "test"                        # 测试
    DEPLOY = "deploy"                    # 部署
    DB_MIGRATION = "db_migration"        # 数据库迁移


class DecisionEngine:
    """智能决策引擎"""
    
    # 文件类型到变更类型的映射
    FILE_TYPE_MAP = {
        ".py": ChangeType.PYTHON_CODE,
        ".yaml": ChangeType.CONFIG_FILE,
        ".yml": ChangeType.CONFIG_FILE,
        ".json": ChangeType.CONFIG_FILE,
        ".env": ChangeType.ENV_VAR,
        ".html": ChangeType.FRONTEND_CODE,
        ".js": ChangeType.FRONTEND_CODE,
        ".css": ChangeType.FRONTEND_CODE,
        "Dockerfile": ChangeType.DOCKERFILE,
        "requirements.txt": ChangeType.DEPENDENCY,
        "docker-compose.yml": ChangeType.DOCKERFILE,
    }
    
    # 目录到变更类型的映射
    DIR_TYPE_MAP = {
        "server": ChangeType.PYTHON_CODE,
        "src": ChangeType.PYTHON_CODE,
        "services": ChangeType.PYTHON_CODE,
        "local_frontend": ChangeType.FRONTEND_CODE,
        "scripts/migration": ChangeType.RULE_DATA,
        "deploy": ChangeType.CONFIG_FILE,
    }
    
    def __init__(self):
        self.decisions: List[Dict] = []
    
    def analyze_file(self, file_path: Path) -> ChangeType:
        """
        分析文件变更类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            变更类型
        """
        # 检查文件扩展名
        suffix = file_path.suffix.lower()
        if suffix in self.FILE_TYPE_MAP:
            return self.FILE_TYPE_MAP[suffix]
        
        # 检查文件名
        file_name = file_path.name.lower()
        if file_name in self.FILE_TYPE_MAP:
            return self.FILE_TYPE_MAP[file_name]
        
        # 检查目录
        for dir_name, change_type in self.DIR_TYPE_MAP.items():
            if dir_name in str(file_path):
                return change_type
        
        # 默认：Python代码
        return ChangeType.PYTHON_CODE
    
    def decide_actions(self, change_type: ChangeType, file_path: Optional[Path] = None) -> Dict:
        """
        根据变更类型决定需要执行的操作
        
        Args:
            change_type: 变更类型
            file_path: 文件路径（可选，用于更精确的判断）
            
        Returns:
            决策结果
        """
        actions = []
        reasons = []
        priority = "medium"
        
        # 规则1：所有代码变更都需要热更新，禁止重启
        if change_type in [ChangeType.PYTHON_CODE, ChangeType.FRONTEND_CODE, ChangeType.CONFIG_FILE]:
            actions.append(ActionType.HOT_RELOAD)
            reasons.append("代码/配置变更需要热更新（禁止重启）")
            priority = "high"
        
        # 规则2：规则数据变更需要热更新
        if change_type == ChangeType.RULE_DATA:
            actions.append(ActionType.HOT_RELOAD)
            reasons.append("规则数据变更需要热更新")
            actions.append(ActionType.TEST)
            reasons.append("规则变更需要测试验证")
            priority = "high"
        
        # 规则3：环境变量变更可能需要重启（但优先尝试热更新）
        if change_type == ChangeType.ENV_VAR:
            actions.append(ActionType.HOT_RELOAD)
            reasons.append("环境变量变更优先使用热更新")
            priority = "medium"
        
        # 规则4：依赖变更需要完整部署（但禁止重启，使用热更新）
        if change_type == ChangeType.DEPENDENCY:
            actions.append(ActionType.DEPLOY)
            reasons.append("依赖变更需要完整部署")
            actions.append(ActionType.TEST)
            reasons.append("依赖变更需要测试验证")
            priority = "high"
            # 注意：即使依赖变更，也禁止重启，应该使用完整部署流程
        
        # 规则5：Dockerfile变更需要完整部署
        if change_type == ChangeType.DOCKERFILE:
            actions.append(ActionType.DEPLOY)
            reasons.append("Dockerfile变更需要完整部署")
            priority = "high"
        
        # 规则6：数据库结构变更需要迁移
        if change_type == ChangeType.DATABASE_SCHEMA:
            actions.append(ActionType.DB_MIGRATION)
            reasons.append("数据库结构变更需要迁移")
            actions.append(ActionType.TEST)
            reasons.append("数据库变更需要测试验证")
            priority = "critical"
        
        # 规则7：所有变更都需要测试（除了配置文件）
        if change_type != ChangeType.CONFIG_FILE:
            if ActionType.TEST not in actions:
                actions.append(ActionType.TEST)
                reasons.append("代码变更需要测试验证")
        
        # 规则8：禁止重启（强制使用热更新）
        if ActionType.RESTART in actions:
            actions.remove(ActionType.RESTART)
            reasons.append("⚠️ 禁止重启服务，必须使用热更新")
        
        return {
            "change_type": change_type.value,
            "actions": [action.value for action in actions],
            "reasons": reasons,
            "priority": priority,
            "restart_forbidden": True,
            "hot_reload_required": ActionType.HOT_RELOAD in actions
        }
    
    def analyze_changes(self, file_paths: List[Path]) -> Dict:
        """
        分析多个文件变更
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            综合分析结果
        """
        change_types = set()
        all_actions = set()
        all_reasons = []
        max_priority = "low"
        
        for file_path in file_paths:
            change_type = self.analyze_file(file_path)
            change_types.add(change_type)
            
            decision = self.decide_actions(change_type, file_path)
            all_actions.update([ActionType(action) for action in decision["actions"]])
            all_reasons.extend(decision["reasons"])
            
            # 优先级：critical > high > medium > low
            priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            if priority_order.get(decision["priority"], 0) > priority_order.get(max_priority, 0):
                max_priority = decision["priority"]
        
        # 生成综合建议
        recommendations = []
        
        # 强制热更新
        if ActionType.HOT_RELOAD in all_actions:
            recommendations.append({
                "action": "hot_reload",
                "required": True,
                "message": "必须执行热更新（禁止重启服务）",
                "command": "python3 scripts/ai/auto_hot_reload.py --trigger"
            })
        
        # 禁止重启
        recommendations.append({
            "action": "restart",
            "forbidden": True,
            "message": "⚠️ 禁止重启服务，必须使用热更新",
            "alternative": "使用热更新代替重启"
        })
        
        # 测试建议
        if ActionType.TEST in all_actions:
            recommendations.append({
                "action": "test",
                "required": True,
                "message": "需要执行测试验证",
                "command": "python3 scripts/test/auto_test.py --all"
            })
        
        # 部署建议
        if ActionType.DEPLOY in all_actions:
            recommendations.append({
                "action": "deploy",
                "required": True,
                "message": "需要完整部署（依赖或Dockerfile变更）",
                "command": "python3 scripts/deploy/auto_deploy.py --mode full"
            })
        
        # 数据库迁移建议
        if ActionType.DB_MIGRATION in all_actions:
            recommendations.append({
                "action": "db_migration",
                "required": True,
                "message": "需要执行数据库迁移",
                "command": "python3 scripts/db/detect_db_changes.py"
            })
        
        return {
            "change_types": [ct.value for ct in change_types],
            "actions": [action.value for action in all_actions],
            "reasons": list(set(all_reasons)),  # 去重
            "priority": max_priority,
            "recommendations": recommendations,
            "restart_forbidden": True,
            "hot_reload_required": ActionType.HOT_RELOAD in all_actions
        }
    
    def get_decision_summary(self, analysis_result: Dict) -> str:
        """
        生成决策摘要
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            摘要文本
        """
        lines = []
        lines.append(f"\n{BLUE}{'='*60}{NC}")
        lines.append(f"{BLUE}📋 智能决策结果{NC}")
        lines.append(f"{BLUE}{'='*60}{NC}\n")
        
        # 变更类型
        lines.append(f"{GREEN}变更类型：{NC}{', '.join(analysis_result['change_types'])}")
        
        # 优先级
        priority_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }
        priority = analysis_result.get("priority", "low")
        lines.append(f"{GREEN}优先级：{NC}{priority_emoji.get(priority, '⚪')} {priority.upper()}")
        
        # 必需操作
        lines.append(f"\n{GREEN}必需操作：{NC}")
        for rec in analysis_result.get("recommendations", []):
            if rec.get("required"):
                lines.append(f"  ✅ {rec['message']}")
                if "command" in rec:
                    lines.append(f"     命令: {YELLOW}{rec['command']}{NC}")
        
        # 禁止操作
        lines.append(f"\n{RED}禁止操作：{NC}")
        for rec in analysis_result.get("recommendations", []):
            if rec.get("forbidden"):
                lines.append(f"  ❌ {rec['message']}")
                if "alternative" in rec:
                    lines.append(f"     替代方案: {YELLOW}{rec['alternative']}{NC}")
        
        # 原因
        if analysis_result.get("reasons"):
            lines.append(f"\n{GREEN}决策原因：{NC}")
            for reason in analysis_result["reasons"]:
                lines.append(f"  • {reason}")
        
        lines.append(f"\n{BLUE}{'='*60}{NC}\n")
        
        return "\n".join(lines)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能决策引擎")
    parser.add_argument("--analyze", type=str, nargs="+", help="分析文件路径")
    parser.add_argument("--check", type=str, help="检查变更类型")
    parser.add_argument("--summary", action="store_true", help="显示决策摘要")
    
    args = parser.parse_args()
    
    engine = DecisionEngine()
    
    if args.analyze:
        # 分析文件
        file_paths = [Path(f) for f in args.analyze]
        result = engine.analyze_changes(file_paths)
        
        if args.summary:
            print(engine.get_decision_summary(result))
        else:
            import json
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.check:
        # 检查变更类型
        try:
            change_type = ChangeType(args.check)
            decision = engine.decide_actions(change_type)
            import json
            print(json.dumps(decision, ensure_ascii=False, indent=2))
        except ValueError:
            print(f"{RED}❌ 无效的变更类型: {args.check}{NC}")
            print(f"可用类型: {', '.join([ct.value for ct in ChangeType])}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

