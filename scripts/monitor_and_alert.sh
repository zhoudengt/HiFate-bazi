#!/bin/bash
# 监控并告警脚本

echo "============================================================"
echo "🔍 监控生产环境规则匹配状态"
echo "============================================================"

LOG_FILE="/tmp/test_until_fixed.log"
CHECK_INTERVAL=30  # 每 30 秒检查一次

while true; do
    # 检查日志文件
    if [ -f "$LOG_FILE" ]; then
        # 检查是否已解决
        if grep -q "🎉 问题已解决" "$LOG_FILE"; then
            echo ""
            echo "✅ 检测到问题已解决！"
            tail -30 "$LOG_FILE" | grep -A 20 "问题已解决"
            break
        fi
        
        # 显示最新状态
        echo ""
        echo "[$(date '+%H:%M:%S')] 检查状态..."
        tail -5 "$LOG_FILE" | grep -E "总匹配数|问题已解决|仍需修复" || echo "  等待中..."
    else
        echo "[$(date '+%H:%M:%S')] 日志文件尚未生成，等待中..."
    fi
    
    # 同时运行快速状态检查
    python3 scripts/check_status.py 2>/dev/null | tail -15
    
    sleep $CHECK_INTERVAL
done

