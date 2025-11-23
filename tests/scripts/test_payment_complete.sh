#!/bin/bash

echo "=========================================="
echo "🎯 支付接口完整测试"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查环境变量
echo "🔍 步骤1: 检查配置"
echo "----------------------------------------"

if [ -z "$STRIPE_SECRET_KEY" ]; then
    echo -e "${RED}❌ 错误: STRIPE_SECRET_KEY 未设置${NC}"
    echo ""
    echo "请按以下步骤操作："
    echo "1. 访问 https://dashboard.stripe.com/test/apikeys"
    echo "2. 登录或注册Stripe账号"
    echo "3. 复制 'Secret key' (sk_test_开头)"
    echo "4. 运行: export STRIPE_SECRET_KEY=sk_test_你的密钥"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ STRIPE_SECRET_KEY 已配置${NC}"
echo "   密钥前缀: ${STRIPE_SECRET_KEY:0:15}..."
echo ""

# 检查主服务
echo "🔍 步骤2: 检查服务状态"
echo "----------------------------------------"

if lsof -i:8001 2>/dev/null | grep -q LISTEN; then
    echo -e "${GREEN}✅ 主服务运行正常 (端口 8001)${NC}"
else
    echo -e "${RED}❌ 主服务未运行${NC}"
    echo ""
    echo "请运行以下命令启动服务："
    echo "  python server/start.py"
    echo ""
    exit 1
fi
echo ""

# 测试1: 创建支付会话
echo "💳 步骤3: 创建支付会话"
echo "----------------------------------------"

TIMESTAMP=$(date +%s)
RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/create-session \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "19.90",
    "currency": "USD",
    "product_name": "测试产品-月订阅会员",
    "customer_email": "test@example.com",
    "metadata": {
      "test_id": "test_'$TIMESTAMP'",
      "source": "command_line_test"
    }
  }')

echo "📄 API响应:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# 提取session_id
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('session_id', ''))" 2>/dev/null)

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}❌ 支付会话创建失败${NC}"
    echo ""
    echo "可能的原因："
    echo "1. STRIPE_SECRET_KEY 无效"
    echo "2. 网络连接问题"
    echo "3. Stripe服务不可用"
    echo ""
    echo "详细错误信息:"
    echo "$RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ 支付会话创建成功${NC}"
echo "   Session ID: $SESSION_ID"
echo ""

# 提取checkout_url
CHECKOUT_URL=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('checkout_url', ''))" 2>/dev/null)

if [ -z "$CHECKOUT_URL" ]; then
    echo -e "${RED}❌ 无法获取支付链接${NC}"
    exit 1
fi

# 显示支付信息
echo "=========================================="
echo "💰 支付信息"
echo "=========================================="
echo ""
echo -e "${BLUE}🔗 支付链接:${NC}"
echo "$CHECKOUT_URL"
echo ""
echo "=========================================="
echo ""
echo -e "${YELLOW}📌 请在浏览器中打开上述链接完成支付${NC}"
echo ""
echo "💳 Stripe测试卡号信息:"
echo "----------------------------------------"
echo "   卡号:     4242 4242 4242 4242"
echo "   过期日期: 12/25 (任意未来日期)"
echo "   CVC:      123 (任意3位数字)"
echo "   邮编:     12345 (任意5位数字)"
echo ""
echo "其他测试卡号:"
echo "   需要3D验证: 4000 0027 6000 3184"
echo "   支付失败:   4000 0000 0000 0002"
echo "   余额不足:   4000 0000 0000 9995"
echo ""
echo "=========================================="
echo ""

# 提供快速打开选项
echo "💡 提示:"
echo "   1. 复制上面的支付链接"
echo "   2. 在浏览器中打开"
echo "   3. 使用测试卡号完成支付"
echo "   4. 支付完成后回到终端按回车继续"
echo ""

# 在macOS上自动打开浏览器
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}🚀 正在为您打开浏览器...${NC}"
    open "$CHECKOUT_URL"
    echo ""
fi

# 等待用户完成支付
echo -e "${YELLOW}⏳ 等待支付完成...${NC}"
echo "   完成支付后请按 [回车] 继续验证支付状态"
echo ""
read -r

# 测试2: 验证支付状态
echo ""
echo "🔍 步骤4: 验证支付状态"
echo "----------------------------------------"

VERIFY_RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/verify \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}")

echo "📄 验证响应:"
echo "$VERIFY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$VERIFY_RESPONSE"
echo ""

# 检查支付状态
STATUS=$(echo "$VERIFY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', ''))" 2>/dev/null)
AMOUNT=$(echo "$VERIFY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('amount', ''))" 2>/dev/null)
PAYMENT_INTENT=$(echo "$VERIFY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_intent_id', ''))" 2>/dev/null)

echo "=========================================="
echo "📊 支付结果"
echo "=========================================="
echo ""

if [ "$STATUS" = "success" ]; then
    echo -e "${GREEN}✅ 支付成功！${NC}"
    echo ""
    echo "支付详情:"
    echo "----------------------------------------"
    echo "   状态:     $STATUS"
    [ -n "$AMOUNT" ] && echo "   金额:     \$$AMOUNT USD"
    [ -n "$PAYMENT_INTENT" ] && echo "   支付ID:   $PAYMENT_INTENT"
    echo "   Session:  $SESSION_ID"
    echo ""
    echo -e "${GREEN}🎉 恭喜！支付功能测试完全成功！${NC}"
elif [ "$STATUS" = "pending" ]; then
    echo -e "${YELLOW}⏳ 支付进行中${NC}"
    echo ""
    echo "当前状态: $STATUS"
    echo "Session:  $SESSION_ID"
    echo ""
    echo "💡 提示: 支付可能仍在处理中，请稍后再次验证"
    echo ""
    echo "运行以下命令重新检查:"
    echo "curl -X POST http://127.0.0.1:8001/api/v1/payment/verify \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"session_id\": \"$SESSION_ID\"}' | python3 -m json.tool"
else
    echo -e "${RED}❌ 支付失败或未完成${NC}"
    echo ""
    echo "当前状态: $STATUS"
    echo "Session:  $SESSION_ID"
    echo ""
    echo "可能的原因："
    echo "1. 支付尚未完成"
    echo "2. 支付被取消"
    echo "3. 测试卡号使用的是失败场景"
    echo ""
    echo "请重新运行脚本进行测试"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""

# 保存session_id到文件，方便后续验证
echo "$SESSION_ID" > /tmp/last_payment_session.txt
echo "💾 Session ID 已保存到: /tmp/last_payment_session.txt"
echo ""

