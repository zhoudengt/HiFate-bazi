#!/bin/bash
# 简单的支付测试脚本

echo "========================================"
echo "支付功能测试"
echo "========================================"
echo ""

# 1. 检查主服务
echo "1. 检查主服务..."
if curl -s http://127.0.0.1:8001/healthz > /dev/null 2>&1; then
    echo "   ✓ 主服务运行正常"
else
    echo "   ✗ 主服务未运行，请先启动: python server/start.py"
    exit 1
fi

# 2. 检查Stripe库
echo ""
echo "2. 检查Stripe库..."
if python3 -c "import stripe" 2>/dev/null; then
    STRIPE_VERSION=$(python3 -c "import stripe; print(stripe.__version__)" 2>/dev/null)
    echo "   ✓ Stripe库已安装 (版本: $STRIPE_VERSION)"
else
    echo "   ✗ Stripe库未安装"
    echo "   请运行: pip install stripe>=7.0.0"
    exit 1
fi

# 3. 检查Stripe密钥
echo ""
echo "3. 检查Stripe密钥..."
if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo "   ✗ STRIPE_SECRET_KEY未设置"
    echo "   请在.env文件中设置或执行: export STRIPE_SECRET_KEY=sk_test_..."
    exit 1
else
    MASKED_KEY="${STRIPE_SECRET_KEY:0:20}..."
    echo "   ✓ STRIPE_SECRET_KEY已设置: $MASKED_KEY"
    if [[ $STRIPE_SECRET_KEY == sk_test_* ]]; then
        echo "   ℹ 使用测试密钥"
    elif [[ $STRIPE_SECRET_KEY == sk_live_* ]]; then
        echo "   ⚠ 使用生产密钥"
    fi
fi

# 4. 测试创建支付会话
echo ""
echo "4. 测试创建支付会话..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/create-session \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "19.90",
    "currency": "USD",
    "product_name": "测试产品-月订阅会员",
    "customer_email": "test@example.com"
  }')

echo "   响应: $RESPONSE"

if echo "$RESPONSE" | grep -q "checkout_url"; then
    echo "   ✓ 支付会话创建成功!"
    SESSION_ID=$(echo "$RESPONSE" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
    CHECKOUT_URL=$(echo "$RESPONSE" | grep -o '"checkout_url":"[^"]*"' | cut -d'"' -f4)
    echo "   Session ID: $SESSION_ID"
    echo "   Checkout URL: ${CHECKOUT_URL:0:80}..."
    echo ""
    echo "   您可以在浏览器中打开此URL进行支付测试"
else
    echo "   ✗ 创建支付会话失败"
    echo "   请检查错误信息: $RESPONSE"
    exit 1
fi

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"

