#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冗余代码检测脚本
检测系统中的重复代码、未使用代码、功能重复的模块
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
import hashlib

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class RedundantCodeDetector:
    """冗余代码检测器"""
    
    def __init__(self):
        self.issues = []
        self.duplicate_functions = defaultdict(list)
        self.duplicate_classes = defaultdict(list)
        self.duplicate_code_blocks = defaultdict(list)
        self.unused_imports = []
        self.similar_files = defaultdict(list)
        
    def detect_all(self):
        """执行所有检测"""
        print("🔍 开始检测冗余代码...")
        
        # 1. 检测重复的客户端实现
        self._detect_duplicate_clients()
        
        # 2. 检测重复的 gRPC 配置
        self._detect_duplicate_grpc_configs()
        
        # 3. 检测重复的函数定义
        self._detect_duplicate_functions()
        
        # 4. 检测重复的代码块
        self._detect_duplicate_code_blocks()
        
        # 5. 检测相似的文件
        self._detect_similar_files()
        
        # 6. 检测重复的格式化函数
        self._detect_format_functions()
        
        print(f"\n✅ 检测完成，发现 {len(self.issues)} 个问题")
        
    def _detect_duplicate_clients(self):
        """检测重复的客户端实现"""
        print("\n📦 检测重复的客户端实现...")
        
        # HTTP 和 gRPC 客户端对
        client_pairs = [
            ("src/clients/bazi_core_client.py", "src/clients/bazi_core_client_grpc.py", "BaziCoreClient"),
            ("src/clients/bazi_fortune_client.py", "src/clients/bazi_fortune_client_grpc.py", "BaziFortuneClient"),
            ("src/clients/bazi_rule_client.py", "src/clients/bazi_rule_client_grpc.py", "BaziRuleClient"),
        ]
        
        for http_file, grpc_file, class_name in client_pairs:
            http_path = PROJECT_ROOT / http_file
            grpc_path = PROJECT_ROOT / grpc_file
            
            if http_path.exists() and grpc_path.exists():
                self.issues.append({
                    "type": "duplicate_client",
                    "severity": "medium",
                    "description": f"发现重复的客户端实现：{class_name}",
                    "files": [http_file, grpc_file],
                    "suggestion": f"考虑统一使用 gRPC 客户端（{grpc_file}），移除 HTTP 客户端（{http_file}）"
                })
                print(f"  ⚠️  {class_name}: HTTP 和 gRPC 客户端同时存在")
    
    def _detect_duplicate_grpc_configs(self):
        """检测重复的 gRPC 配置"""
        print("\n⚙️  检测重复的 gRPC 配置...")
        
        # 标准的 keepalive 配置
        standard_keepalive = [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', False),
        ]
        
        # 查找所有包含这些配置的文件
        config_pattern = r"grpc\.keepalive_time_ms.*?300000"
        files_with_config = []
        
        for py_file in PROJECT_ROOT.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                if re.search(config_pattern, content, re.DOTALL):
                    files_with_config.append(str(py_file.relative_to(PROJECT_ROOT)))
            except Exception:
                pass
        
        if len(files_with_config) > 1:
            self.issues.append({
                "type": "duplicate_grpc_config",
                "severity": "low",
                "description": f"发现 {len(files_with_config)} 个文件包含相同的 gRPC keepalive 配置",
                "files": files_with_config[:10],  # 只显示前10个
                "suggestion": "考虑将 gRPC 配置提取到公共工具类中，统一管理"
            })
            print(f"  ⚠️  发现 {len(files_with_config)} 个文件包含重复的 gRPC keepalive 配置")
    
    def _detect_duplicate_functions(self):
        """检测重复的函数定义"""
        print("\n🔧 检测重复的函数定义...")
        
        # 查找所有 Python 文件
        function_signatures = defaultdict(list)
        
        for py_file in PROJECT_ROOT.rglob("*.py"):
            # 跳过测试文件和缓存文件
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content, filename=str(py_file))
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 生成函数签名（名称 + 参数数量）
                        sig = f"{node.name}({len(node.args.args)} args)"
                        function_signatures[sig].append(str(py_file.relative_to(PROJECT_ROOT)))
            except Exception:
                pass
        
        # 找出重复的函数签名
        for sig, files in function_signatures.items():
            if len(files) > 1:
                # 检查是否是同一个文件（可能是类方法）
                unique_files = set(files)
                if len(unique_files) > 1:
                    self.duplicate_functions[sig].extend(unique_files)
        
        # 报告前10个重复函数
        count = 0
        for sig, files in list(self.duplicate_functions.items())[:10]:
            if count >= 5:  # 只报告前5个
                break
            print(f"  ⚠️  {sig}: 在 {len(files)} 个文件中发现")
            count += 1
    
    def _detect_duplicate_code_blocks(self):
        """检测重复的代码块"""
        print("\n📋 检测重复的代码块...")
        
        # 检测重复的地址解析逻辑（在 gRPC 客户端中）
        address_parsing_pattern = r"if base_url\.startswith\([\"']http://[\"']\):.*?base_url = f\"\{base_url\}:(\d+)\""
        
        files_with_address_parsing = []
        for py_file in PROJECT_ROOT.rglob("*client*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                if re.search(address_parsing_pattern, content, re.DOTALL):
                    files_with_address_parsing.append(str(py_file.relative_to(PROJECT_ROOT)))
            except Exception:
                pass
        
        if len(files_with_address_parsing) > 1:
            self.issues.append({
                "type": "duplicate_code_block",
                "severity": "medium",
                "description": f"发现 {len(files_with_address_parsing)} 个文件包含相同的地址解析逻辑",
                "files": files_with_address_parsing,
                "suggestion": "考虑将地址解析逻辑提取到公共工具函数中"
            })
            print(f"  ⚠️  发现 {len(files_with_address_parsing)} 个文件包含重复的地址解析逻辑")
    
    def _detect_similar_files(self):
        """检测相似的文件"""
        print("\n📄 检测相似的文件...")
        
        # 检测客户端文件
        client_files = list(PROJECT_ROOT.glob("src/clients/*client*.py"))
        
        if len(client_files) >= 2:
            # 计算文件相似度（简单的行数比较）
            file_sizes = {}
            for f in client_files:
                try:
                    lines = len(f.read_text(encoding='utf-8').splitlines())
                    file_sizes[str(f.relative_to(PROJECT_ROOT))] = lines
                except Exception:
                    pass
            
            # 找出大小相似的文件
            similar_pairs = []
            files_list = list(file_sizes.items())
            for i, (file1, size1) in enumerate(files_list):
                for file2, size2 in files_list[i+1:]:
                    if abs(size1 - size2) < 50:  # 行数差异小于50
                        similar_pairs.append((file1, file2, size1, size2))
            
            if similar_pairs:
                self.issues.append({
                    "type": "similar_files",
                    "severity": "low",
                    "description": f"发现 {len(similar_pairs)} 对相似的文件",
                    "files": [f"{f1} ({s1}行) vs {f2} ({s2}行)" for f1, f2, s1, s2 in similar_pairs[:5]],
                    "suggestion": "检查这些文件是否可以合并或提取公共代码"
                })
                print(f"  ⚠️  发现 {len(similar_pairs)} 对相似的文件")
    
    def _detect_format_functions(self):
        """检测重复的格式化函数"""
        print("\n🎨 检测重复的格式化函数...")
        
        format_functions = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            try:
                content = py_file.read_text(encoding='utf-8')
                # 查找格式化相关的函数
                if re.search(r"def.*format.*result|def.*format.*response|def.*_format", content, re.IGNORECASE):
                    tree = ast.parse(content, filename=str(py_file))
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and "format" in node.name.lower():
                            format_functions.append({
                                "file": str(py_file.relative_to(PROJECT_ROOT)),
                                "function": node.name,
                                "line": node.lineno
                            })
            except Exception:
                pass
        
        if len(format_functions) > 5:
            self.issues.append({
                "type": "duplicate_format_functions",
                "severity": "low",
                "description": f"发现 {len(format_functions)} 个格式化函数",
                "files": [f"{f['file']}:{f['function']}" for f in format_functions[:10]],
                "suggestion": "考虑统一格式化函数的实现，提取到公共工具类中"
            })
            print(f"  ⚠️  发现 {len(format_functions)} 个格式化函数，可能存在重复")
    
    def generate_report(self) -> str:
        """生成检测报告"""
        report_lines = [
            "# 冗余代码检测报告\n",
            f"**检测时间**: {self._get_timestamp()}\n",
            f"**发现问题数**: {len(self.issues)}\n\n",
            "## 📊 问题汇总\n\n"
        ]
        
        # 按严重程度分类
        by_severity = defaultdict(list)
        for issue in self.issues:
            by_severity[issue["severity"]].append(issue)
        
        # 高严重程度
        if "high" in by_severity:
            report_lines.append("### 🔴 高严重程度\n\n")
            for issue in by_severity["high"]:
                report_lines.append(self._format_issue(issue))
        
        # 中等严重程度
        if "medium" in by_severity:
            report_lines.append("### 🟡 中等严重程度\n\n")
            for issue in by_severity["medium"]:
                report_lines.append(self._format_issue(issue))
        
        # 低严重程度
        if "low" in by_severity:
            report_lines.append("### 🟢 低严重程度\n\n")
            for issue in by_severity["low"]:
                report_lines.append(self._format_issue(issue))
        
        # 建议总结
        report_lines.append("\n## 💡 优化建议总结\n\n")
        suggestions = set()
        for issue in self.issues:
            if "suggestion" in issue:
                suggestions.add(issue["suggestion"])
        
        for i, suggestion in enumerate(suggestions, 1):
            report_lines.append(f"{i}. {suggestion}\n")
        
        return "".join(report_lines)
    
    def _format_issue(self, issue: Dict) -> str:
        """格式化单个问题"""
        lines = [
            f"### {issue['description']}\n\n",
            f"- **类型**: {issue['type']}\n",
            f"- **严重程度**: {issue['severity']}\n",
            f"- **涉及文件**: {len(issue.get('files', []))} 个\n",
        ]
        
        if issue.get('files'):
            lines.append("\n**文件列表**:\n")
            for file in issue['files'][:5]:  # 只显示前5个
                lines.append(f"- `{file}`\n")
            if len(issue['files']) > 5:
                lines.append(f"- ... 还有 {len(issue['files']) - 5} 个文件\n")
        
        if issue.get('suggestion'):
            lines.append(f"\n**建议**: {issue['suggestion']}\n")
        
        lines.append("\n")
        return "".join(lines)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def save_report(self, output_file: str = "redundant_code_report.md"):
        """保存报告到文件"""
        report = self.generate_report()
        output_path = PROJECT_ROOT / "docs" / "reports" / output_file
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        output_path.write_text(report, encoding='utf-8')
        print(f"\n📄 报告已保存到: {output_path}")
        
        # 同时保存 JSON 格式
        json_path = output_path.with_suffix('.json')
        json_path.write_text(
            json.dumps(self.issues, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"📄 JSON 报告已保存到: {json_path}")


def main():
    """主函数"""
    detector = RedundantCodeDetector()
    detector.detect_all()
    detector.save_report()
    
    # 打印摘要
    print("\n" + "="*60)
    print("📊 检测摘要")
    print("="*60)
    print(f"总问题数: {len(detector.issues)}")
    
    by_type = defaultdict(int)
    for issue in detector.issues:
        by_type[issue['type']] += 1
    
    print("\n按类型分类:")
    for issue_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  - {issue_type}: {count}")


if __name__ == "__main__":
    main()
