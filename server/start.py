#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产环境启动脚本

作用：
1. 优先使用项目自带的虚拟环境运行，避免依赖缺失。
2. 如果仍无法导入 uvicorn，给出明确的中文提示。
"""

from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

import os
import sys
from pathlib import Path
from typing import Iterable, Optional


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _get_venv_python(project_root: Path) -> Optional[Path]:
    """
    根据操作系统推断虚拟环境 python 路径。
    项目使用 .venv 作为虚拟环境目录。
    macOS/Linux: .venv/bin/python3
    Windows: .venv/Scripts/python.exe
    """
    venv_dirs = [".venv", "venv"]  # 优先使用 .venv（项目标准）
    candidates = []
    if os.name == "nt":
        for venv_dir in venv_dirs:
            candidates.extend([
                project_root / venv_dir / "Scripts" / "python.exe",
                project_root / venv_dir / "Scripts" / "python",
            ])
    else:
        for venv_dir in venv_dirs:
            candidates.extend([
                project_root / venv_dir / "bin" / "python3",
                project_root / venv_dir / "bin" / "python",
            ])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _ensure_running_in_venv() -> None:
    """
    如果当前解释器不是虚拟环境里的 python，尝试自动切换到 .venv。
    """
    project_root = _get_project_root()
    venv_python = _get_venv_python(project_root)
    if not venv_python:
        return  # 项目里没有 .venv，后续会提示安装依赖

    current_exe = Path(sys.executable).resolve()
    venv_exe = venv_python.resolve()
    if current_exe != venv_exe:
        try:
            os.execv(
                str(venv_exe),
                [str(venv_exe), __file__, *sys.argv[1:]]
            )
        except OSError as exc:
            raise RuntimeError(
                f"自动切换到虚拟环境失败，请手动执行：\n"
                f"source {venv_exe.parent}/activate  # macOS/Linux\n"
                f"或\n"
                f"{venv_exe.parent}/activate.bat    # Windows\n"
                f"然后再次运行 python server/start.py\n"
                f"（系统错误信息：{exc}）"
            ) from exc


def _load_uvicorn():
    try:
        import uvicorn  # type: ignore
        return uvicorn
    except ModuleNotFoundError:
        project_root = _get_project_root()
        _extend_sys_path_with_site_packages(project_root)
        try:
            import uvicorn  # type: ignore
            return uvicorn
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "当前 Python 环境中没有安装 uvicorn。\n"
                "请先执行：pip install -r requirements.txt\n"
                "或确认已激活虚拟环境（source .venv/bin/activate）。"
            ) from exc


def _extend_sys_path_with_site_packages(project_root: Path) -> None:
    """
    兼容 .venv（项目标准），多版本 site-packages，确保在未激活虚拟环境时也能找到依赖。
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
            sys.path.insert(0, str(site_packages))


def main() -> None:
    project_root = _get_project_root()
    sys.path.insert(0, str(project_root))
    os.environ.setdefault("PYTHONPATH", str(project_root))

    # 加载微服务环境变量配置
    services_env_file = project_root / "config" / "services.env"
    if services_env_file.exists():
        import subprocess
        try:
            # 读取并解析环境变量文件
            with open(services_env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "export " in line:
                        # 解析 export KEY="VALUE" 格式
                        if "=" in line:
                            key_value = line.replace("export ", "").strip()
                            if "=" in key_value:
                                key, value = key_value.split("=", 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                os.environ.setdefault(key, value)
        except Exception as exc:
            logger.info(f"⚠️  加载环境变量配置失败: {exc}", file=sys.stderr)

    uvicorn = _load_uvicorn()
    
    # 自动检测CPU核心数，匹配CPU核心数以提高性能
    cpu_count = os.cpu_count() or 4
    workers = cpu_count  # 8个workers（匹配8核心CPU）
    
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8001,
        workers=workers,  # 根据CPU核心数自动调整（当前：8个workers）
        loop="asyncio",
        limit_concurrency=1000,  # 最大并发数
        limit_max_requests=10000,  # 最大请求数
        backlog=2048,  # 等待队列大小
        timeout_keep_alive=30,
        access_log=True
    )


if __name__ == "__main__":
    _ensure_running_in_venv()
    main()

