#!/bin/bash

echo "🔍 Line Pay 支付测试开始..."
echo ""

# 1. 检查配置
echo "1️⃣ 检查 Line Pay 配置..."
python3 scripts/db/manage_payment_configs.py list --provider linepay

# 2. 创建支付订单
echo ""
echo "2️⃣ 创建 Line Pay 支付订单..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linepay",
    "amount": "100",
    "currency": "TWD",
    "product_name": "Line Pay测试产品"
  }')

echo "$RESPONSE" | python3 -m json.tool

# 提取 transaction_id 和 payment_url
TRANSACTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('transaction_id', ''))")
PAYMENT_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_url', ''))")
ORDER_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order_id', ''))")

if [ -z "$TRANSACTION_ID" ]; then
    echo "❌ 创建支付订单失败"
    exit 1
fi

echo ""
echo "✅ 支付订单创建成功"
echo "📋 Transaction ID: $TRANSACTION_ID"
echo "📋 Order ID: $ORDER_ID"
echo "🔗 Payment URL: $PAYMENT_URL"
echo ""
echo "💡 请在浏览器中打开 payment_url 完成支付测试"
echo ""

# 3. 查询订单状态（支付前）
echo "3️⃣ 查询订单状态（支付前）..."
sleep 2
curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{
    \"provider\": \"linepay\",
    \"transaction_id\": \"$TRANSACTION_ID\"
  }" | python3 -m json.tool

echo ""
echo "✅ 测试完成！"
echo ""
echo "📝 下一步："
echo "   1. 在浏览器中打开: $PAYMENT_URL"
echo "   2. 使用 Line Pay 账号登录并完成支付"
echo "   3. 支付完成后，再次运行验证接口查看状态"
echo ""
echo "💡 验证支付状态命令："
echo "   curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"provider\":\"linepay\",\"transaction_id\":\"$TRANSACTION_ID\"}' | python3 -m json.tool"
echo ""
echo "📌 注意："
echo "   - Line Pay 使用 transaction_id 进行验证（不是 payment_id）"
echo "   - TWD、JPY、THB 是零小数货币，金额必须是整数"
echo "   - 测试环境使用 sandbox-web-pay.line.me"
