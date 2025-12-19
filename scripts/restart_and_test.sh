#!/bin/bash
# 重启服务并测试API

echo "=========================================="
echo "重启服务并测试API"
echo "=========================================="
echo ""

# 1. 尝试热更新
echo "1. 尝试热更新..."
curl -X POST http://localhost:8001/api/v1/hot-reload/check 2>&1 | head -10
echo ""
sleep 2

# 2. 测试API
echo "2. 测试API字段名..."
python3 scripts/test_daily_fortune_api_live.py 2>&1 | grep -A 20 "响应数据字段检查"

echo ""
echo "如果字段检查仍有问题，请手动重启服务："
echo "  - docker-compose restart web"
echo "  - 或 sudo systemctl restart hifate-bazi"
