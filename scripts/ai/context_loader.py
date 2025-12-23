#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上下文加载器
功能：
1. 自动加载项目上下文（.cursorrules、代码结构）
2. 根据开发类型加载对应知识库
3. 生成上下文摘要供 AI 使用

使用方法：
    python3 scripts/ai/context_loader.py --type api
    python3 scripts/ai/context_loader.py --type rule
    python3 scripts/ai/context_loader.py --summary
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 颜色定义
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class ContextLoader:
    """上下文加载器"""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.cursorrules_path = self.project_root / ".cursorrules"
        self.knowledge_base_path = self.project_root / "docs" / "knowledge_base"
        self.context_templates_path = self.knowledge_base_path / "context_templates"
    
    def load_cursorrules(self, max_length: int = 5000) -> Dict:
        """
        加载 .cursorrules 文件
        
        Args:
            max_length: 最大长度（字符数）
            
        Returns:
            .cursorrules 内容摘要
        """
        if not self.cursorrules_path.exists():
            return {
                "exists": False,
                "content": None,
                "summary": "规范文件不存在"
            }
        
        try:
            with open(self.cursorrules_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 提取关键章节
            summary_parts = []
            
            # 提取核心原则
            if "核心原则" in content:
                start = content.find("核心原则")
                end = content.find("##", start + 1)
                if end == -1:
                    end = start + 2000
                summary_parts.append(content[start:end][:1000])
            
            # 提取开发规范
            if "新功能开发强制规范" in content:
                start = content.find("新功能开发强制规范")
                end = content.find("##", start + 1)
                if end == -1:
                    end = start + 2000
                summary_parts.append(content[start:end][:1000])
            
            # 提取热更新规范
            if "热更新强制规范" in content:
                start = content.find("热更新强制规范")
                end = content.find("##", start + 1)
                if end == -1:
                    end = start + 2000
                summary_parts.append(content[start:end][:1000])
            
            summary = "\n\n".join(summary_parts)
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            
            return {
                "exists": True,
                "content_length": len(content),
                "summary": summary,
                "key_sections": [
                    "核心原则",
                    "新功能开发强制规范",
                    "热更新强制规范",
                    "gRPC 交互规范",
                    "规则开发规范"
                ]
            }
        except Exception as e:
            return {
                "exists": True,
                "error": str(e),
                "summary": f"加载规范文件时出错: {str(e)}"
            }
    
    def load_knowledge_base(self, dev_type: Optional[str] = None) -> Dict:
        """
        加载知识库
        
        Args:
            dev_type: 开发类型（可选）
            
        Returns:
            知识库内容
        """
        knowledge = {
            "base_path": str(self.knowledge_base_path),
            "exists": self.knowledge_base_path.exists(),
            "files": {}
        }
        
        if not self.knowledge_base_path.exists():
            return knowledge
        
        # 加载通用知识库文件
        knowledge_files = {
            "development_rules": "development_rules.md",
            "common_issues": "common_issues.md",
            "best_practices": "best_practices.md",
            "problem_history": "problem_history.md"
        }
        
        for key, filename in knowledge_files.items():
            file_path = self.knowledge_base_path / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    knowledge["files"][key] = {
                        "exists": True,
                        "content_length": len(content),
                        "summary": content[:1000] + "..." if len(content) > 1000 else content
                    }
                except Exception as e:
                    knowledge["files"][key] = {
                        "exists": True,
                        "error": str(e)
                    }
            else:
                knowledge["files"][key] = {
                    "exists": False
                }
        
        # 加载开发类型特定的模板
        if dev_type and self.context_templates_path.exists():
            template_file = self.context_templates_path / f"{dev_type}_development.md"
            if template_file.exists():
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    knowledge["template"] = {
                        "type": dev_type,
                        "exists": True,
                        "content": content
                    }
                except Exception as e:
                    knowledge["template"] = {
                        "type": dev_type,
                        "exists": True,
                        "error": str(e)
                    }
        
        return knowledge
    
    def load_project_structure(self) -> Dict:
        """
        加载项目结构
        
        Returns:
            项目结构信息
        """
        structure = {
            "root": str(self.project_root),
            "key_directories": {}
        }
        
        key_dirs = {
            "server": "server",
            "src": "src",
            "services": "services",
            "local_frontend": "local_frontend",
            "scripts": "scripts",
            "docs": "docs",
            "tests": "tests"
        }
        
        for key, dir_name in key_dirs.items():
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                # 统计文件数量
                py_files = list(dir_path.rglob("*.py"))
                structure["key_directories"][key] = {
                    "exists": True,
                    "path": str(dir_path),
                    "python_files": len(py_files)
                }
            else:
                structure["key_directories"][key] = {
                    "exists": False
                }
        
        return structure
    
    def generate_context_summary(self, dev_type: Optional[str] = None) -> Dict:
        """
        生成上下文摘要
        
        Args:
            dev_type: 开发类型（可选）
            
        Returns:
            上下文摘要
        """
        context = {
            "project_root": str(self.project_root),
            "cursorrules": self.load_cursorrules(),
            "knowledge_base": self.load_knowledge_base(dev_type),
            "project_structure": self.load_project_structure(),
            "dev_type": dev_type
        }
        
        return context
    
    def print_summary(self, context: Dict):
        """打印上下文摘要"""
        print(f"\n{BLUE}{'='*60}{NC}")
        print(f"{BLUE}📚 项目上下文摘要{NC}")
        print(f"{BLUE}{'='*60}{NC}\n")
        
        # 规范文件
        cursorrules = context.get("cursorrules", {})
        if cursorrules.get("exists"):
            print(f"{GREEN}✅ 开发规范文件存在{NC}")
            print(f"  文件大小: {cursorrules.get('content_length', 0)} 字符")
            if cursorrules.get("key_sections"):
                print(f"  关键章节: {', '.join(cursorrules['key_sections'])}")
        else:
            print(f"{RED}❌ 开发规范文件不存在{NC}")
        
        # 知识库
        knowledge_base = context.get("knowledge_base", {})
        if knowledge_base.get("exists"):
            print(f"\n{GREEN}✅ 知识库存在{NC}")
            files = knowledge_base.get("files", {})
            for key, file_info in files.items():
                if file_info.get("exists"):
                    print(f"  ✅ {key}: {file_info.get('content_length', 0)} 字符")
                else:
                    print(f"  ❌ {key}: 不存在")
        else:
            print(f"\n{YELLOW}⚠️  知识库不存在{NC}")
        
        # 项目结构
        structure = context.get("project_structure", {})
        print(f"\n{GREEN}项目结构：{NC}")
        for key, dir_info in structure.get("key_directories", {}).items():
            if dir_info.get("exists"):
                print(f"  ✅ {key}: {dir_info.get('python_files', 0)} Python 文件")
            else:
                print(f"  ❌ {key}: 不存在")
        
        print(f"\n{BLUE}{'='*60}{NC}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="上下文加载器")
    parser.add_argument("--type", type=str, choices=["api", "rule", "frontend"], help="开发类型")
    parser.add_argument("--summary", action="store_true", help="显示摘要")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    
    args = parser.parse_args()
    
    loader = ContextLoader()
    context = loader.generate_context_summary(args.type)
    
    if args.json:
        import json
        print(json.dumps(context, ensure_ascii=False, indent=2))
    else:
        if args.summary:
            loader.print_summary(context)
        else:
            import json
            print(json.dumps(context, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

