#!/bin/bash

echo "🔍 PayPal 支付测试开始..."
echo ""

# 1. 检查配置
echo "1️⃣ 检查 PayPal 配置..."
python3 scripts/db/manage_payment_configs.py list --provider paypal

# 2. 创建支付订单
echo ""
echo "2️⃣ 创建 PayPal 支付订单..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "paypal",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayPal测试产品"
  }')

echo "$RESPONSE" | python3 -m json.tool

# 提取 payment_id 和 approval_url
PAYMENT_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_id', ''))")
APPROVAL_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('approval_url', ''))")

if [ -z "$PAYMENT_ID" ]; then
    echo "❌ 创建支付订单失败"
    exit 1
fi

echo ""
echo "✅ 支付订单创建成功"
echo "📋 Payment ID: $PAYMENT_ID"
echo "🔗 Approval URL: $APPROVAL_URL"
echo ""
echo "💡 请在浏览器中打开 approval_url 完成支付测试"
echo ""

# 3. 查询订单状态（支付前）
echo "3️⃣ 查询订单状态（支付前）..."
sleep 2
curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{
    \"provider\": \"paypal\",
    \"payment_id\": \"$PAYMENT_ID\"
  }" | python3 -m json.tool

echo ""
echo "✅ 测试完成！"
echo ""
echo "📝 下一步："
echo "   1. 在浏览器中打开: $APPROVAL_URL"
echo "   2. 使用 PayPal 测试账号登录并完成支付"
echo "   3. 支付完成后，再次运行验证接口查看状态"
echo ""
echo "💡 验证支付状态命令："
echo "   curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"provider\":\"paypal\",\"payment_id\":\"$PAYMENT_ID\"}' | python3 -m json.tool"
