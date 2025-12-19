#!/bin/bash
# 修复并测试每日运势API字段名问题

echo "=========================================="
echo "修复并测试每日运势API字段名"
echo "=========================================="
echo ""

# 1. 验证代码
echo "1. 验证代码修改..."
python3 scripts/test_daily_fortune_api_complete.py
echo ""

# 2. 清理缓存
echo "2. 清理缓存..."
python3 scripts/clear_daily_fortune_cache.py 2>&1
echo ""

# 3. 提示重启服务
echo "3. 请重启后端服务:"
echo "   - 如果使用 uvicorn: 按 Ctrl+C 停止，然后重新运行 python3 server/start.py"
echo "   - 如果使用 systemd: sudo systemctl restart hifate-bazi"
echo "   - 如果使用 docker: docker-compose restart web"
echo ""

# 4. 等待用户重启后测试
read -p "重启服务后，按 Enter 继续测试..." 

# 5. 测试API
echo ""
echo "4. 测试API..."
python3 scripts/test_daily_fortune_api_live.py 2>&1 | tail -30

