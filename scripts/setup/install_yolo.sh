#!/bin/bash
# 安装YOLO和相关依赖

set -e

echo "================================================"
echo "  安装 YOLO 物品检测模块"
echo "================================================"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "【步骤1】安装 ultralytics (YOLOv8)..."
pip3 install ultralytics opencv-python pillow numpy -q

echo ""
echo "【步骤2】下载 YOLOv8 nano 模型..."
python3 << 'PYTHON'
from ultralytics import YOLO
import os

print("正在下载 YOLOv8n 模型...")
model = YOLO('yolov8n.pt')
print(f"✅ 模型下载成功！")
print(f"   模型路径: {os.path.expanduser('~')}/.cache/ultralytics/yolov8n.pt")

# 测试模型
print("\n测试模型加载...")
result = model.predict(source='https://ultralytics.com/images/bus.jpg', verbose=False)
print(f"✅ 模型测试成功！检测到 {len(result[0].boxes)} 个物品")
PYTHON

echo ""
echo "【步骤3】验证安装..."
python3 << 'PYTHON'
import sys
try:
    from ultralytics import YOLO
    import cv2
    import numpy as np
    print("✅ ultralytics: 已安装")
    print("✅ opencv-python: 已安装")
    print("✅ numpy: 已安装")
    
    # 检查模型
    model = YOLO('yolov8n.pt')
    print(f"✅ YOLOv8 模型: 已加载")
    print(f"   支持类别数: {len(model.names)}")
    
    sys.exit(0)
except Exception as e:
    print(f"❌ 安装验证失败: {e}")
    sys.exit(1)
PYTHON

if [ $? -eq 0 ]; then
    echo ""
    echo "================================================"
    echo "  ✅ YOLO 安装成功！"
    echo "================================================"
    echo ""
    echo "下一步："
    echo "  1. 重启办公桌风水服务"
    echo "     ./scripts/stop_desk_fengshui_service.sh"
    echo "     ./scripts/start_desk_fengshui_service.sh"
    echo ""
    echo "  2. 测试物品检测"
    echo "     访问: http://localhost:8001/frontend/desk-fengshui.html"
    echo ""
else
    echo ""
    echo "❌ 安装失败，请检查错误信息"
    exit 1
fi

