#!/bin/bash
# 快速部署 homepage_contents 相关更改到 Node1
# 包括：代码拉取、数据库迁移、热更新

set -e

NODE1_IP="8.210.52.217"
PROJECT_DIR="/opt/HiFate-bazi"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

echo "=========================================="
echo "🚀 部署 homepage_contents 到 Node1"
echo "=========================================="
echo ""

# SSH 执行函数
ssh_exec() {
    local cmd="$@"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE1_IP "$cmd"
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$NODE1_IP "$cmd"
    fi
}

# 步骤1：拉取代码
echo "📥 步骤1: 拉取最新代码..."
ssh_exec "cd $PROJECT_DIR && git fetch origin && git pull origin master"
echo "✅ 代码拉取完成"
echo ""

# 步骤2：执行数据库迁移
echo "🗄️  步骤2: 执行数据库迁移（添加 image_url 字段）..."
ssh_exec "cd $PROJECT_DIR && python3 scripts/db/add_image_url_field.py"
echo "✅ 数据库迁移完成"
echo ""

# 步骤3：触发热更新
echo "🔄 步骤3: 触发热更新..."
curl -X POST "http://$NODE1_IP:8001/api/v1/hot-reload/check" -s | python3 -m json.tool || echo "热更新触发中..."
sleep 3

# 重新加载端点
curl -X POST "http://$NODE1_IP:8001/api/v1/hot-reload/reload-endpoints" -s | python3 -m json.tool || echo "端点重新加载中..."
echo "✅ 热更新完成"
echo ""

# 步骤4：验证部署
echo "🧪 步骤4: 验证部署..."
echo "测试创建接口..."
RESPONSE=$(curl -s -X POST "http://$NODE1_IP:8001/api/v1/admin/homepage/contents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "部署验证测试",
    "tags": ["测试"],
    "description": "验证部署是否成功",
    "image_url": "https://destiny-ducket.oss-cn-hongkong.aliyuncs.com/deploy-test.jpeg",
    "sort_order": 999
  }')

if echo "$RESPONSE" | grep -q "success.*true"; then
    echo "✅ 部署验证成功！"
    echo "$RESPONSE" | python3 -m json.tool
else
    echo "❌ 部署验证失败："
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
