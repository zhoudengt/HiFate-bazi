#!/usr/bin/env bash
# 生产环境流式接口诊断脚本（在服务器上执行，不改业务逻辑）
# 用法：在 Node1 上执行 bash scripts/diagnose_stream_production.sh
#       或 BASE_URL=http://8.210.52.217 bash scripts/diagnose_stream_production.sh（从本机测公网）

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 直连 8001（本机，不经过 Nginx）
DIRECT="http://127.0.0.1:8001"
# 可选：通过 Nginx/公网（脚本外可 export BASE_URL）
PUBLIC="${BASE_URL:-}"

TIMEOUT=8
STREAM_BODY='{"solar_date":"1990-01-15","solar_time":"12:00","gender":"male"}'

echo "=========================================="
echo "流式接口生产诊断（timeout=${TIMEOUT}s）"
echo "=========================================="

# 1) 即时端点：直连 8001
echo ""
echo "1. 即时端点 GET /api/v1/diagnose-stream（直连 127.0.0.1:8001）"
if out=$(curl -s -m "$TIMEOUT" "${DIRECT}/api/v1/diagnose-stream" 2>&1); then
  if echo "$out" | grep -q '"ok":true'; then
    echo -e "${GREEN}OK${NC} 直连 8001 可达"
    echo "$out" | head -c 200
    echo ""
  else
    echo -e "${YELLOW}非预期响应${NC}"
    echo "$out" | head -c 300
    echo ""
  fi
else
  echo -e "${RED}失败/超时${NC} 直连 8001 无响应"
fi

# 2) 流式端点：直连 8001，只收前 5 秒
echo ""
echo "2. 流式端点 POST /api/v1/bazi/xishen-jishen/stream（直连 127.0.0.1:8001，收前 ${TIMEOUT}s）"
if out=$(curl -s -N -m "$TIMEOUT" -X POST "${DIRECT}/api/v1/bazi/xishen-jishen/stream" \
  -H "Content-Type: application/json" \
  -d "$STREAM_BODY" 2>&1); then
  if echo "$out" | grep -q 'data:'; then
    echo -e "${GREEN}OK${NC} 直连流式有数据"
    echo "$out" | head -5
  else
    echo -e "${YELLOW}无 data 行${NC}"
    echo "$out" | head -5
  fi
else
  echo -e "${RED}失败/超时${NC} 直连流式无数据（${TIMEOUT}s 内）"
fi

# 3) 若设置了 BASE_URL，再测公网/Nginx
if [ -n "$PUBLIC" ]; then
  echo ""
  echo "3. 即时端点 GET /api/v1/diagnose-stream（通过 BASE_URL=$PUBLIC）"
  if out=$(curl -s -m "$TIMEOUT" "${PUBLIC}/api/v1/diagnose-stream" 2>&1); then
    if echo "$out" | grep -q '"ok":true'; then
      echo -e "${GREEN}OK${NC} 经 BASE_URL 可达"
    else
      echo -e "${YELLOW}非预期${NC}"
      echo "$out" | head -c 200
      echo ""
    fi
  else
    echo -e "${RED}失败/超时${NC} 经 BASE_URL 无响应"
  fi

  echo ""
  echo "4. 流式端点 POST .../stream（通过 BASE_URL，收前 ${TIMEOUT}s）"
  if out=$(curl -s -N -m "$TIMEOUT" -X POST "${PUBLIC}/api/v1/bazi/xishen-jishen/stream" \
    -H "Content-Type: application/json" \
    -d "$STREAM_BODY" 2>&1); then
    if echo "$out" | grep -q 'data:'; then
      echo -e "${GREEN}OK${NC} 经 BASE_URL 流式有数据"
      echo "$out" | head -5
    else
      echo -e "${YELLOW}无 data 行${NC} 经 BASE_URL 流式可能被缓冲"
      echo "$out" | head -5
    fi
  else
    echo -e "${RED}失败/超时${NC} 经 BASE_URL 流式无数据"
  fi
else
  echo ""
  echo "3. 跳过经 Nginx/公网 测试（需 export BASE_URL=http://IP 再执行）"
fi

echo ""
echo "=========================================="
echo "结论：若 1、2 正常而 3、4 超时/无数据，则根因为 Nginx 缓冲/超时"
echo "=========================================="
