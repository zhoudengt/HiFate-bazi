#!/bin/bash

echo "🔍 Payssion 支付测试开始..."
echo "================================"

# 检查 Payssion 配置
echo "1️⃣ 检查 Payssion 配置..."
python3 scripts/db/manage_payment_configs.py list --provider payssion

echo ""
echo "2️⃣ 创建 Payssion 支付订单..."

# 测试创建支付订单
RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payssion",
    "amount": "19.90",
    "currency": "TWD",
    "product_name": "Payssion 测试商品",
    "customer_email": "test@example.com",
    "payment_method": "linepay"
  }')

echo "创建支付响应:"
echo "$RESPONSE" | python3 -m json.tool

# 提取 transaction_id
TRANSACTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('transaction_id', ''))")

if [ -n "$TRANSACTION_ID" ]; then
    echo ""
    echo "3️⃣ 验证 Payssion 支付状态..."
    echo "Transaction ID: $TRANSACTION_ID"

    # 等待用户完成支付（如果有 payment_url）
    PAYMENT_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_url', ''))")
    if [ -n "$PAYMENT_URL" ]; then
        echo "支付链接: $PAYMENT_URL"
        echo "请在浏览器中打开上述链接完成支付，然后按回车继续..."
        read
    fi

    # 验证支付状态
    VERIFY_RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
      -H "Content-Type: application/json" \
      -d "{\"provider\":\"payssion\",\"transaction_id\":\"$TRANSACTION_ID\"}")

    echo "验证支付响应:"
    echo "$VERIFY_RESPONSE" | python3 -m json.tool
else
    echo "❌ 创建支付订单失败，无法进行验证"
fi

echo ""
echo "4️⃣ 测试完成说明"
echo "================================"
echo "Payssion 测试要点："
echo "✅ 支持 LINE Pay 等第三方支付"
echo "✅ 香港公司无需台湾实体即可接入"
echo "✅ 支持多种货币：USD, HKD, TWD, JPY, THB, CNY, EUR"
echo "✅ API 简单，集成成本低"
echo ""
echo "配置要求："
echo "- API Key: 从 Payssion 商户后台获取"
echo "- Secret: 从 Payssion 商户后台获取"
echo "- Merchant ID: 从 Payssion 商户后台获取"
echo ""
echo "设置配置命令："
echo "python3 scripts/db/manage_payment_configs.py add payssion api_key YOUR_API_KEY --environment sandbox"
echo "python3 scripts/db/manage_payment_configs.py add payssion secret YOUR_SECRET --environment sandbox"
echo "python3 scripts/db/manage_payment_configs.py add payssion merchant_id YOUR_MERCHANT_ID --environment sandbox"