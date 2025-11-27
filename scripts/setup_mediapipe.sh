#!/bin/bash
# -*- coding: utf-8 -*-
# 面相分析V2 - AI模型环境安装脚本

set -e

echo "========================================="
echo "面相分析V2 - MediaPipe环境安装"
echo "========================================="

# 检查Python环境
if [ ! -d ".venv" ]; then
    echo "❌ 未找到虚拟环境，请先运行: python3 -m venv .venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

echo "📦 安装基础AI库..."
pip install --upgrade pip

# 安装核心依赖
pip install mediapipe>=0.10.0
pip install opencv-python>=4.8.0
pip install Pillow>=10.0.0
pip install numpy>=1.26.0

echo "📦 安装图像处理库..."
pip install scikit-learn>=1.3.0
pip install scipy>=1.11.0

# 可选：安装dlib（需要cmake）
echo "⚙️ 检查是否安装dlib..."
if command -v cmake &> /dev/null; then
    echo "✓ 找到cmake，安装dlib..."
    pip install dlib>=19.24.0
    pip install face-recognition>=1.3.0
else
    echo "⚠️  未找到cmake，跳过dlib安装（可选）"
    echo "   如需安装：brew install cmake，然后重新运行此脚本"
fi

# 可选：安装PyTorch（用于高级模型）
echo "⚙️ 检查是否安装PyTorch..."
read -p "是否安装PyTorch（用于face-parsing）？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 安装PyTorch（CPU版本）..."
    pip install torch>=2.0.0 torchvision>=0.15.0 --index-url https://download.pytorch.org/whl/cpu
fi

echo ""
echo "✅ 安装完成！"
echo ""
echo "验证安装："
python3 -c "import mediapipe as mp; print(f'✓ MediaPipe {mp.__version__}')"
python3 -c "import cv2; print(f'✓ OpenCV {cv2.__version__}')"
python3 -c "import numpy as np; print(f'✓ NumPy {np.__version__}')"

echo ""
echo "========================================="
echo "环境准备完成，可以开始开发面相分析服务"
echo "========================================="

