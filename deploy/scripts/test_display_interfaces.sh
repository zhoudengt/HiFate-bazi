#!/usr/bin/env bash
# 本地测试编排层迁移的四个接口
# 使用前请确保服务已启动：python server/start.py 8001 或 docker-compose up
# 用法：./deploy/scripts/test_display_interfaces.sh [BASE_URL]
# 示例：./deploy/scripts/test_display_interfaces.sh
#       ./deploy/scripts/test_display_interfaces.sh http://127.0.0.1:8001

set -e
BASE_URL="${1:-http://127.0.0.1:8001}"
BODY='{"solar_date":"1990-01-15","solar_time":"12:30","gender":"male","calendar_type":"solar"}'

echo "=========================================="
echo "本地接口测试 - BASE_URL=$BASE_URL"
echo "=========================================="

# 健康检查
echo ""
echo "[0] 健康检查 GET /health"
if curl -sf --max-time 5 "$BASE_URL/health" > /dev/null; then
  echo "  OK 服务可达"
else
  echo "  失败 请先启动服务: python server/start.py 8001"
  exit 1
fi

# 1. pan/display
echo ""
echo "[1] POST /api/v1/bazi/pan/display"
RESP=$(curl -sf --max-time 30 -X POST "$BASE_URL/api/v1/bazi/pan/display" \
  -H "Content-Type: application/json" \
  -d "$BODY" 2>/dev/null || echo '{"success":false}')
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('success') and d.get('pan') else 1)" 2>/dev/null; then
  echo "  OK success=true, pan 有数据"
else
  echo "  失败 或 超时"
  echo "$RESP" | head -c 200
  echo ""
fi

# 2. interface
echo ""
echo "[2] POST /api/v1/bazi/interface"
RESP=$(curl -sf --max-time 30 -X POST "$BASE_URL/api/v1/bazi/interface" \
  -H "Content-Type: application/json" \
  -d "$BODY" 2>/dev/null || echo '{"success":false}')
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('data') or d.get('success') else 1)" 2>/dev/null; then
  echo "  OK 有 data 或 success"
else
  echo "  失败 或 超时"
  echo "$RESP" | head -c 200
  echo ""
fi

# 3. fortune/display
echo ""
echo "[3] POST /api/v1/bazi/fortune/display"
BODY_FORTUNE='{"solar_date":"1990-01-15","solar_time":"12:30","gender":"male","calendar_type":"solar","current_time":"今"}'
RESP=$(curl -sf --max-time 60 -X POST "$BASE_URL/api/v1/bazi/fortune/display" \
  -H "Content-Type: application/json" \
  -d "$BODY_FORTUNE" 2>/dev/null || echo '{"success":false}')
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('success') and d.get('dayun') else 1)" 2>/dev/null; then
  echo "  OK success=true, dayun 有数据"
else
  echo "  失败 或 超时"
  echo "$RESP" | head -c 200
  echo ""
fi

# 4. shengong-minggong
echo ""
echo "[4] POST /api/v1/bazi/shengong-minggong"
BODY_SM='{"solar_date":"1990-01-15","solar_time":"12:30","gender":"male","calendar_type":"solar"}'
RESP=$(curl -sf --max-time 60 -X POST "$BASE_URL/api/v1/bazi/shengong-minggong" \
  -H "Content-Type: application/json" \
  -d "$BODY_SM" 2>/dev/null || echo '{"success":false}')
if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('data') or d.get('success') else 1)" 2>/dev/null; then
  echo "  OK 有 data 或 success"
else
  echo "  失败 或 超时"
  echo "$RESP" | head -c 200
  echo ""
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
