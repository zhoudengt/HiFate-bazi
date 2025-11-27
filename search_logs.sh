#!/bin/bash
# 搜索日志中的关键信息

cd /Users/zhoudt/Downloads/project/HiFate-bazi

echo "======================================"
echo "🔍 日志搜索工具"
echo "======================================"
echo ""
echo "可用命令:"
echo "  1. 查看八字信息:     ./search_logs.sh bazi"
echo "  2. 查看十神信息:     ./search_logs.sh shishen"
echo "  3. 查看流年信息:     ./search_logs.sh liunian"
echo "  4. 查看大运信息:     ./search_logs.sh dayun"
echo "  5. 查看喜忌神:       ./search_logs.sh xiji"
echo "  6. 查看完整JSON:     ./search_logs.sh json"
echo "  7. 查看某个年份:     ./search_logs.sh 2029"
echo ""

case "$1" in
  bazi)
    echo "🔎 查找八字信息..."
    echo ""
    grep -A 15 "STEP2.*八字计算完成" logs/main_service.log | tail -50
    ;;
  shishen)
    echo "🔎 查找十神信息..."
    echo ""
    grep "十神:" logs/main_service.log | tail -10
    ;;
  liunian)
    echo "🔎 查找流年信息..."
    echo ""
    grep -E "流年列表:|流年年份:" logs/main_service.log | tail -20
    ;;
  dayun)
    echo "🔎 查找大运信息..."
    echo ""
    grep "大运:" logs/main_service.log | tail -10
    ;;
  xiji)
    echo "🔎 查找喜忌神信息..."
    echo ""
    grep "喜忌神:" logs/main_service.log | tail -10
    ;;
  json)
    echo "🔎 查找完整JSON数据..."
    echo ""
    grep -A 60 "STEP5.*传递给最终LLM" logs/main_service.log | tail -100
    ;;
  [0-9]*)
    echo "🔎 查找 $1 年的信息..."
    echo ""
    grep "$1" logs/main_service.log | tail -20
    ;;
  *)
    echo "❌ 请指定搜索类型"
    echo ""
    echo "示例:"
    echo "  ./search_logs.sh bazi"
    echo "  ./search_logs.sh 2029"
    ;;
esac

