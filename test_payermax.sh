#!/bin/bash

echo "🔍 PayerMax 支付测试开始..."
echo "================================"

# 检查 PayerMax 配置
echo "1️⃣ 检查 PayerMax 配置..."
python3 scripts/db/manage_payment_configs.py list --provider payermax

echo ""
echo "2️⃣ 创建 PayerMax 支付订单..."

# 测试创建支付订单（使用收银台模式）
RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax 测试商品",
    "customer_email": "test@example.com"
  }')

echo "创建支付响应:"
echo "$RESPONSE" | python3 -m json.tool

# 提取 transaction_id
TRANSACTION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('transaction_id', ''))")

if [ -n "$TRANSACTION_ID" ]; then
    echo ""
    echo "3️⃣ 验证 PayerMax 支付状态..."
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
      -d "{\"provider\":\"payermax\",\"transaction_id\":\"$TRANSACTION_ID\"}")

    echo "验证支付响应:"
    echo "$VERIFY_RESPONSE" | python3 -m json.tool
else
    echo "❌ 创建支付订单失败，无法进行验证"
fi

echo ""
echo "4️⃣ 测试完成说明"
echo "================================"
echo "PayerMax 测试要点："
echo "✅ 支持 600+ 全球支付方式"
echo "✅ RSA 签名保证安全性"
echo "✅ 支持收银台、API、PayByLink 三种集成模式"
echo "✅ 支持多种货币和地区"
echo ""
echo "配置要求："
echo "- App ID: 从 PayerMax 开发者中心获取"
echo "- Merchant No: 从 PayerMax 商户后台获取"
echo "- Private Key: RSA 私钥文件路径"
echo "- Public Key: RSA 公钥文件路径"
echo ""
echo "设置配置命令："
echo "python3 scripts/db/manage_payment_configs.py add payermax app_id YOUR_APP_ID --environment test"
echo "python3 scripts/db/manage_payment_configs.py add payermax merchant_no YOUR_MERCHANT_NO --environment test"
echo "python3 scripts/db/manage_payment_configs.py add payermax private_key_path /path/to/private_key.pem --environment test"
echo "python3 scripts/db/manage_payment_configs.py add payermax public_key_path /path/to/public_key.pem --environment test"
echo ""
echo "RSA 密钥生成："
echo "openssl genrsa -out private_key.pem 2048"
echo "openssl rsa -in private_key.pem -pubout -out public_key.pem"