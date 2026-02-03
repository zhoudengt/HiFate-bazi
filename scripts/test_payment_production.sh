#!/bin/bash
# 生产环境支付测试：Stripe / PayerMax，带成功页与取消页
# 使用：bash scripts/test_payment_production.sh
# 可改 HOST、SUCCESS_URL、CANCEL_URL

HOST="${HOST:-http://8.210.52.217:8001}"
SUCCESS_URL="${SUCCESS_URL:-https://www.yuanqistation.com/payment/success?session_id={CHECKOUT_SESSION_ID}}"
CANCEL_URL="${CANCEL_URL:-https://www.yuanqistation.com/payment/cancel}"

echo "=== Stripe 创建支付（带成功/取消页）==="
curl -s -X POST "$HOST/api/v1/payment/unified/create" \
  -H "Content-Type: application/json" \
  -d "{
    \"provider\": \"stripe\",
    \"amount\": \"4.10\",
    \"currency\": \"USD\",
    \"product_name\": \"Stripe测试\",
    \"customer_email\": \"test@example.com\",
    \"success_url\": \"$SUCCESS_URL\",
    \"cancel_url\": \"$CANCEL_URL\"
  }" | python3 -m json.tool

echo ""
echo "=== PayerMax 创建支付（带成功/取消页）==="
curl -s -X POST "$HOST/api/v1/payment/unified/create" \
  -H "Content-Type: application/json" \
  -d "{
    \"provider\": \"payermax\",
    \"amount\": \"19.90\",
    \"currency\": \"USD\",
    \"product_name\": \"PayerMax测试\",
    \"customer_email\": \"test@example.com\",
    \"success_url\": \"$SUCCESS_URL\",
    \"cancel_url\": \"$CANCEL_URL\"
  }" | python3 -m json.tool
