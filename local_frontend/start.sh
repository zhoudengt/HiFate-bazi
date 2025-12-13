#!/bin/bash
# 启动前端本地服务器

cd "$(dirname "$0")"

echo "正在启动前端本地服务器..."
echo "访问地址: http://127.0.0.1:8080"
echo ""
echo "按 Ctrl+C 停止服务器"
echo ""

# 使用 Python 启动简单 HTTP 服务器
python3 -m http.server 8080

