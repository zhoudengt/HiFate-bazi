#!/bin/bash
# -*- coding: utf-8 -*-
"""
二进制打包脚本 - 使用 PyInstaller
适用于：测试服务器快速部署
"""

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "HiFate-bazi 二进制打包工具"
echo "=========================================="

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 未找到虚拟环境 .venv"
    echo "请先创建虚拟环境：python3 -m venv .venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查 PyInstaller
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "📦 安装 PyInstaller..."
    pip install pyinstaller
fi

# 创建打包目录
BUILD_DIR="dist/binary"
mkdir -p "$BUILD_DIR"

echo ""
echo "【步骤 1/4】清理旧的构建文件..."
rm -rf build/ dist/ *.spec

echo ""
echo "【步骤 2/4】生成 PyInstaller 配置文件..."
cat > hifate_bazi.spec << 'SPEC'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['server/start.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('config', 'config'),
        ('data', 'data'),
        ('proto', 'proto'),
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'pydantic',
        'grpc',
        'pymysql',
        'redis',
        'langchain',
        'langchain_core',
        'langgraph',
        'mediapipe',
        'cv2',
        'torch',
        'numpy',
        'scipy',
        'sklearn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='hifate-bazi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
SPEC

echo ""
echo "【步骤 3/4】开始打包（这可能需要几分钟）..."
pyinstaller hifate_bazi.spec \
    --clean \
    --noconfirm \
    --log-level=INFO

echo ""
echo "【步骤 4/4】整理打包文件..."
if [ -d "dist/hifate-bazi" ]; then
    cp -r dist/hifate-bazi/* "$BUILD_DIR/"
    echo "✅ 二进制文件已生成到: $BUILD_DIR"
    echo ""
    echo "📦 打包内容："
    ls -lh "$BUILD_DIR/hifate-bazi" 2>/dev/null || ls -lh "$BUILD_DIR/"
else
    echo "❌ 打包失败，请查看上面的错误信息"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 打包完成！"
echo "=========================================="
echo ""
echo "📦 打包文件位置: $BUILD_DIR"
echo ""
echo "🚀 使用方法："
echo "   1. 将 $BUILD_DIR 目录上传到服务器"
echo "   2. 在服务器上执行: ./hifate-bazi"
echo ""
echo "⚠️  注意："
echo "   - 需要确保服务器有相同的系统架构（Linux x86_64）"
echo "   - 需要确保服务器有必要的系统库"
echo "   - 配置文件需要单独配置（config/services.env）"
echo ""

