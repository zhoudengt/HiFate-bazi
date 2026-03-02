#!/bin/bash
# 在 Node1 服务器上直接执行此脚本
# 用途：重启容器部署新代码 + 安装 Stripe 依赖

set -e

echo "=========================================="
echo "Node1 容器重启部署"
echo "=========================================="
echo "目标版本: 489f96e (子时回退逻辑)"
echo ""

# 1. 拉取最新代码
echo "[1/6] 拉取最新代码..."
cd /opt/HiFate-bazi
git fetch origin
git checkout master
git reset --hard origin/master
CURRENT_VERSION=$(git rev-parse --short HEAD)
echo "✅ 当前版本: $CURRENT_VERSION"
echo ""

# 2. 检查 Stripe 依赖
echo "[2/6] 检查 Stripe 依赖..."
grep -i stripe requirements.txt || echo "⚠️  stripe 未在 requirements.txt 中"
echo ""

# 3. 在容器中安装 Stripe
echo "[3/6] 在容器中安装 Stripe 依赖..."
docker exec hifate-web pip install 'stripe>=7.0.0,<12' --no-cache-dir
echo "✅ Stripe 已安装"
echo ""

# 4. 重启容器
echo "[4/6] 重启容器（加载新代码）..."
docker compose -f deploy/docker/docker-compose.prod.yml restart hifate-web
echo "✅ 容器已重启"
echo ""

# 5. 等待服务启动
echo "[5/6] 等待服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ 服务已启动 (尝试 $i 次)"
        break
    fi
    echo "  等待中... ($i/30)"
    sleep 2
done
echo ""

# 6. 验证子时逻辑
echo "[6/6] 验证子时逻辑..."
RESULT=$(curl -s -X POST http://localhost:8001/api/v1/bazi/pan/display \
  -H "Content-Type: application/json" \
  -d '{"solar_date":"2024-12-31","solar_time":"23:30","gender":"male"}')

DAY_STEM=$(echo "$RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); pillars={p['type']:p for p in data['pan']['pillars']}; print(pillars['day']['stem']['char'])" 2>/dev/null || echo "")
DAY_BRANCH=$(echo "$RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); pillars={p['type']:p for p in data['pan']['pillars']}; print(pillars['day']['branch']['char'])" 2>/dev/null || echo "")

echo "  2024-12-31 23:30 日柱: ${DAY_STEM}${DAY_BRANCH}"

if [ "$DAY_STEM" = "庚" ] && [ "$DAY_BRANCH" = "午" ]; then
    echo "  ✅ 子时逻辑正确（23点换日）"
    echo ""
    echo "=========================================="
    echo "✅ 部署成功！"
    echo "=========================================="
else
    echo "  ❌ 子时逻辑不正确（预期: 庚午，实际: ${DAY_STEM}${DAY_BRANCH}）"
    echo ""
    echo "=========================================="
    echo "❌ 验证失败！"
    echo "=========================================="
    exit 1
fi
