#!/bin/bash
# PayerMax 生产环境测试脚本

echo "=== PayerMax 统一支付接口测试 ==="
echo ""

# 生产环境地址（Node1）
PROD_HOST="8.210.52.217"
PROD_PORT="8001"
BASE_URL="http://${PROD_HOST}:${PROD_PORT}"

echo "📋 测试 1: 创建支付订单（收银台模式）"
echo "----------------------------------------"
curl -X POST ${BASE_URL}/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax测试产品",
    "customer_email": "test@example.com"
  }' | python3 -m json.tool

echo ""
echo ""
echo "📋 测试 2: 创建支付订单（直接支付模式 - 信用卡）"
echo "----------------------------------------"
curl -X POST ${BASE_URL}/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax信用卡支付测试",
    "customer_email": "test@example.com",
    "payment_method": "card"
  }' | python3 -m json.tool

echo ""
echo ""
echo "📋 测试 3: 创建支付订单（直接支付模式 - 支付宝）"
echo "----------------------------------------"
curl -X POST ${BASE_URL}/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "100.00",
    "currency": "CNY",
    "product_name": "PayerMax支付宝支付测试",
    "customer_email": "test@example.com",
    "payment_method": "alipay"
  }' | python3 -m json.tool

echo ""
echo ""
echo "✅ 测试完成！"
echo ""
echo "💡 提示："
echo "1. 如果返回错误 '支付渠道 payermax 未启用'，请检查生产数据库 payment_configs 表中的配置"
echo "2. 验证支付时，可以使用返回的 transaction_id 或 order_id"
echo "3. 验证命令示例："
echo "   curl -X POST ${BASE_URL}/api/v1/payment/unified/verify \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"provider\":\"payermax\",\"transaction_id\":\"YOUR_TRANSACTION_ID\"}' | python3 -m json.tool"
