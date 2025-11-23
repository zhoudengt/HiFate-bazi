#!/bin/bash
# 打开浏览器调试工具

echo "正在打开浏览器调试工具..."
echo ""
echo "方法1: 使用调试工具页面"
echo "  在浏览器中打开: http://127.0.0.1:8080/debug_fortune.html"
echo ""
echo "方法2: 直接在fortune.html页面调试"
echo "  1. 打开: http://127.0.0.1:8080/fortune.html"
echo "  2. 按 F12 打开开发者工具"
echo "  3. 切换到 Console 标签"
echo "  4. 输入八字信息并查询"
echo "  5. 点击大运，查看控制台输出"
echo ""
echo "方法3: 使用测试脚本"
echo "  运行: .venv/bin/python test_fortune_debug.py"
echo ""

# 尝试自动打开浏览器（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "http://127.0.0.1:8080/debug_fortune.html" 2>/dev/null || echo "请手动打开浏览器"
fi
