#!/bin/bash
# 实时查看所有服务日志

cd /Users/zhoudt/Downloads/project/HiFate-bazi

echo "======================================"
echo "🔍 实时监控所有服务日志"
echo "======================================"
echo ""
echo "📂 监控的日志文件:"
echo "  - logs/intent_service.log (Intent识别)"
echo "  - logs/main_service.log (八字、流年、大运、十神等)"
echo ""
echo "⚠️  按 Ctrl+C 停止监控"
echo ""
echo "======================================"
echo ""

# 同时监控两个日志文件
tail -f logs/intent_service.log logs/main_service.log

