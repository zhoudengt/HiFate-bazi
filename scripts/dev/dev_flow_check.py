#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提交前开发流程检查

对变更的 Python 文件做语法检查，确保无语法错误。

用法：
    python scripts/dev/dev_flow_check.py --files file1.py file2.py
"""

import argparse
import py_compile
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="开发流程检查：Python 语法验证")
    parser.add_argument("--files", nargs="*", default=[], help="待检查的 Python 文件列表")
    args = parser.parse_args()

    files = [f for f in args.files if f and f.endswith(".py")]
    if not files:
        return 0

    errors = []
    for filepath in files:
        path = Path(filepath)
        if not path.exists():
            errors.append(f"文件不存在: {filepath}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{filepath}: {e}")

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
