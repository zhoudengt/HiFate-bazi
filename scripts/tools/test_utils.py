#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工具函数
用于设置测试环境，确保能找到所有依赖（包括虚拟环境中的包）
"""
import sys
import os
from pathlib import Path


def setup_test_environment():
    """
    设置测试环境
    1. 添加项目根目录到 sys.path
    2. 自动扩展虚拟环境的 site-packages（参考 server/start.py）
    
    Returns:
        Path: 项目根目录路径
    """
    # 获取项目根目录
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    
    # 添加项目根目录
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # 扩展虚拟环境路径
    _extend_sys_path_with_site_packages(project_root)
    
    return project_root


def _extend_sys_path_with_site_packages(project_root: Path) -> None:
    """
    兼容 .venv（项目标准），多版本 site-packages，确保在未激活虚拟环境时也能找到依赖。
    参考 server/start.py 的实现。
    """
    python_versions = [
        f"{sys.version_info.major}.{sys.version_info.minor}",
        "3.13",
        "3.12",
        "3.11",
        "3.10",
    ]
    venv_dirs = [".venv", "venv"]  # 优先使用 .venv（项目标准）
    candidates: list[Path] = []
    for venv_dir in venv_dirs:
        for version in python_versions:
            candidates.append(project_root / venv_dir / "lib" / f"python{version}" / "site-packages")

    # 过滤存在的路径后插入 sys.path
    for site_packages in candidates:
        if site_packages.exists() and site_packages.is_dir():
            if str(site_packages) not in sys.path:
                sys.path.insert(0, str(site_packages))

