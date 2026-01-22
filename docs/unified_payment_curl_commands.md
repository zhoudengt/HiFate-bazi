# 统一支付接口 curl 命令参考

## 接口说明

所有支付方式统一使用以下接口：
- **创建支付**: `POST /api/v1/payment/unified/create`
- **验证支付**: `POST /api/v1/payment/unified/verify`

## Stripe 支付

### 创建支付订单

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "stripe",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "Stripe测试产品",
    "customer_email": "test@example.com"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "stripe",
  "payment_id": "cs_test_a1B2c3D4...",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "status": "created",
  "message": "支付会话创建成功"
}
```

### 验证支付状态

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "stripe",
    "session_id": "cs_test_你的session_id"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "stripe",
  "status": "pending",
  "payment_id": "cs_test_...",
  "amount": "19.90",
  "currency": "USD",
  "customer_email": "test@example.com",
  "message": "支付状态查询成功"
}
```

**重要字段**:
- `payment_id`: Stripe Session ID（用于验证）
- `checkout_url`: 支付页面URL（在浏览器中打开完成支付）
- `session_id`: 验证时使用此字段

---

## PayPal 支付

### 创建支付订单

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "paypal",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayPal测试产品"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "paypal",
  "payment_id": "5O190127TN364715T",
  "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=5O190127TN364715T",
  "status": "CREATED",
  "message": "PayPal订单创建成功"
}
```

### 验证支付状态

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "paypal",
    "payment_id": "5O190127TN364715T"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "paypal",
  "status": "CREATED",
  "payment_id": "5O190127TN364715T",
  "amount": "19.90",
  "currency": "USD",
  "message": "订单状态: CREATED"
}
```

**重要字段**:
- `payment_id`: PayPal 订单ID（用于验证）
- `approval_url`: 支付页面URL（在浏览器中打开完成支付）

---

## Line Pay 支付

### 创建支付订单

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linepay",
    "amount": "100",
    "currency": "TWD",
    "product_name": "Line Pay测试产品"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "linepay",
  "transaction_id": "2026012102333767510",
  "order_id": "ORDER_1768968615020",
  "payment_url": "https://sandbox-web-pay.line.me/web/payment/wait?transactionReserveId=...",
  "status": "created",
  "message": "Line Pay订单创建成功"
}
```

### 验证支付状态

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linepay",
    "transaction_id": "2026012102333767510"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "linepay",
  "status": null,
  "amount": "0",
  "currency": "TWD",
  "message": "订单状态: None"
}
```

**重要字段**:
- `transaction_id`: Line Pay 交易ID（用于验证）
- `payment_url`: 支付页面URL（在浏览器中打开完成支付）
- `order_id`: 商户订单号

**注意事项**:
- TWD、JPY、THB 是零小数货币，金额必须是整数（如 100，不能是 100.50）

---

## 三种支付方式对比

| 支付方式 | 创建接口参数 | 验证接口参数 | 支付URL字段 | 支付ID字段 |
|---------|------------|------------|------------|-----------|
| **Stripe** | `provider: "stripe"`<br>`customer_email` (必需) | `provider: "stripe"`<br>`session_id` | `checkout_url` | `payment_id` (即 session_id) |
| **PayPal** | `provider: "paypal"` | `provider: "paypal"`<br>`payment_id` | `approval_url` | `payment_id` |
| **Line Pay** | `provider: "linepay"` | `provider: "linepay"`<br>`transaction_id` | `payment_url` | `transaction_id` |

---

## 完整测试流程

### Stripe 完整测试

```bash
# 1. 创建支付
STRIPE_RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "stripe",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "Stripe测试产品",
    "customer_email": "test@example.com"
  }')

# 2. 提取 session_id
STRIPE_SESSION_ID=$(echo "$STRIPE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_id', ''))")

# 3. 验证支付
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{\"provider\":\"stripe\",\"session_id\":\"$STRIPE_SESSION_ID\"}" | python3 -m json.tool
```

### PayPal 完整测试

```bash
# 1. 创建支付
PAYPAL_RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "paypal",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayPal测试产品"
  }')

# 2. 提取 payment_id
PAYPAL_PAYMENT_ID=$(echo "$PAYPAL_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_id', ''))")

# 3. 验证支付
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{\"provider\":\"paypal\",\"payment_id\":\"$PAYPAL_PAYMENT_ID\"}" | python3 -m json.tool
```

### Line Pay 完整测试

```bash
# 1. 创建支付
LINEPAY_RESPONSE=$(curl -s -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linepay",
    "amount": "100",
    "currency": "TWD",
    "product_name": "Line Pay测试产品"
  }')

# 2. 提取 transaction_id
LINEPAY_TRANSACTION_ID=$(echo "$LINEPAY_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('transaction_id', ''))")

# 3. 验证支付
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{\"provider\":\"linepay\",\"transaction_id\":\"$LINEPAY_TRANSACTION_ID\"}" | python3 -m json.tool
```

---

## 常见错误

### 错误 1: Stripe 缺少 customer_email

```json
{
  "detail": "Stripe支付需要提供customer_email"
}
```

**解决**: 在创建支付请求中添加 `customer_email` 字段

### 错误 2: Line Pay 金额格式错误

```json
{
  "error": "金额格式错误"
}
```

**解决**: TWD、JPY、THB 必须使用整数，不能有小数（如 100，不能是 100.50）

### 错误 3: 验证时缺少必要参数

```json
{
  "detail": "Stripe验证需要提供session_id"
}
```

**解决**: 根据支付方式提供对应的ID：
- Stripe: `session_id`
- PayPal: `payment_id`
- Line Pay: `transaction_id`

---

## 相关文档

- 统一支付接口: `server/api/v1/unified_payment.py`
- Stripe 客户端: `services/payment_service/stripe_client.py`
- PayPal 客户端: `services/payment_service/paypal_client.py`
- Line Pay 客户端: `services/payment_service/linepay_client.py`
