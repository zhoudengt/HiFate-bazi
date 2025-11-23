#!/bin/bash
# Stripe 支付完整测试脚本

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           🎯 Stripe 支付完整测试流程                         ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

cd /Users/zhoudt/Downloads/project/HiFate-bazi

# 步骤1：检查服务状态
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 步骤1：检查服务状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if lsof -i:8001 > /dev/null 2>&1; then
    echo "✅ 主服务 (8001端口) 运行中"
else
    echo "❌ 主服务未运行"
    echo "请先运行: ./start_all_services.sh"
    exit 1
fi
echo ""

# 步骤2：创建支付会话
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💳 步骤2：创建支付会话"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/create-session \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "19.90",
    "currency": "USD",
    "product_name": "月订阅会员",
    "customer_email": "test@example.com"
  }')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null

# 提取关键信息
SESSION_ID=$(echo "$RESPONSE" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
CHECKOUT_URL=$(echo "$RESPONSE" | grep -o '"checkout_url":"[^"]*"' | cut -d'"' -f4)

if [ -z "$SESSION_ID" ]; then
    echo ""
    echo "❌ 创建支付会话失败！"
    exit 1
fi

echo ""
echo "✅ 支付会话创建成功！"
echo ""

# 步骤3：显示支付信息
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 步骤3：支付信息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Session ID:"
echo "  $SESSION_ID"
echo ""
echo "支付链接:"
echo "  $CHECKOUT_URL"
echo ""

# 保存到文件
echo "$CHECKOUT_URL" > /tmp/stripe_checkout_url.txt
echo "$SESSION_ID" > /tmp/stripe_session_id.txt

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 步骤4：在浏览器中完成支付"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. 复制上面的支付链接，在浏览器中打开"
echo "2. 或执行以下命令自动打开："
echo "   open '$CHECKOUT_URL'"
echo ""
echo "3. 在Stripe支付页面填写测试卡信息："
echo "   卡号：     4242 4242 4242 4242"
echo "   过期日期：  12/34（任意未来日期）"
echo "   CVC：      123（任意3位数字）"
echo "   邮编：     12345（任意5位数字）"
echo ""
echo "4. 点击"支付"按钮完成支付"
echo ""

# 询问是否自动打开浏览器
read -p "是否自动在浏览器中打开支付页面? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "$CHECKOUT_URL"
    echo "✅ 已在浏览器中打开支付页面"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 步骤5：验证支付状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "完成支付后，运行以下命令验证支付状态："
echo ""
echo "curl -X POST http://127.0.0.1:8001/api/v1/payment/verify \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"session_id\": \"$SESSION_ID\"}' | python3 -m json.tool"
echo ""

# 等待用户完成支付
read -p "完成支付后按回车键验证支付状态..." 
echo ""

# 验证支付状态
echo "正在验证支付状态..."
VERIFY_RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/verify \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}")

echo "$VERIFY_RESPONSE" | python3 -m json.tool 2>/dev/null

# 检查支付状态
STATUS=$(echo "$VERIFY_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

echo ""
if [ "$STATUS" = "success" ]; then
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║           🎉 支付成功！测试完成！                           ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
else
    echo "⚠️  支付状态: $STATUS"
    echo "如果还未完成支付，请完成支付后再次运行验证命令"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 其他有用的命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# 查看API文档"
echo "open http://127.0.0.1:8001/docs"
echo ""
echo "# 查看Stripe后台"
echo "open https://dashboard.stripe.com/test/payments"
echo ""
echo "# 测试前端页面"
echo "open http://localhost:8080/third-party-services.html"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 测试流程结束"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

