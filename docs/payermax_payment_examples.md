# PayerMax 统一支付接口调用示例

## 接口说明

PayerMax 已完全集成到统一支付接口中，使用以下接口：
- **创建支付**: `POST /api/v1/payment/unified/create`
- **验证支付**: `POST /api/v1/payment/unified/verify`

---

## 1. 创建支付订单

### 1.1 收银台模式（推荐）

不指定 `payment_method`，用户可在 PayerMax 收银台选择支付方式。

```bash
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax测试产品",
    "customer_email": "test@example.com"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "payermax",
  "payment_id": "TXN202401221234567890",
  "transaction_id": "TXN202401221234567890",
  "order_id": "PAYERMAX_1705992000000",
  "payment_url": "https://pay-gate-uat.payermax.com/cashier/...",
  "status": "created",
  "message": "PayerMax支付订单创建成功"
}
```

### 1.2 直接支付模式

指定 `payment_method`，直接跳转到指定支付方式。

```bash
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax测试产品",
    "customer_email": "test@example.com",
    "payment_method": "card"
  }' | python3 -m json.tool
```

**支持的支付方式** (`payment_method` 参数):
- `card`: 信用卡/借记卡
- `alipay`: 支付宝
- `wechat`: 微信支付
- `gcash`: GCash（菲律宾）
- `grabpay`: GrabPay（东南亚）
- `paymaya`: PayMaya（菲律宾）
- `dana`: DANA（印尼）
- `ovo`: OVO（印尼）
- 其他 PayerMax 支持的支付方式（详见 PayerMax 官方文档）

**响应示例**:
```json
{
  "success": true,
  "provider": "payermax",
  "payment_id": "TXN202401221234567890",
  "transaction_id": "TXN202401221234567890",
  "order_id": "PAYERMAX_1705992000000",
  "payment_url": "https://pay-gate-uat.payermax.com/payment/...",
  "status": "created",
  "message": "PayerMax支付订单创建成功"
}
```

---

## 2. 验证支付状态

PayerMax 支持使用 `transaction_id` 或 `order_id` 验证。

### 2.1 使用 transaction_id 验证

```bash
curl -X POST http://localhost:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "transaction_id": "TXN202401221234567890"
  }' | python3 -m json.tool
```

### 2.2 使用 order_id 验证

```bash
curl -X POST http://localhost:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "order_id": "PAYERMAX_1705992000000"
  }' | python3 -m json.tool
```

**响应示例**:
```json
{
  "success": true,
  "provider": "payermax",
  "status": "success",
  "paid": true,
  "transaction_id": "TXN202401221234567890",
  "order_id": "PAYERMAX_1705992000000",
  "amount": "19.90",
  "currency": "USD",
  "paid_time": "2024-01-22 12:34:56",
  "message": "支付状态: success"
}
```

**状态说明**:
- `status: "success"`: 支付成功
- `status: "pending"`: 待支付
- `status: "failed"`: 支付失败
- `status: "cancelled"`: 已取消

---

## 3. 完整测试流程

### 3.1 收银台模式测试

```bash
# 1. 创建支付（收银台模式）
PAYERMAX_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax测试产品",
    "customer_email": "test@example.com"
  }')

# 2. 查看响应
echo "$PAYERMAX_RESPONSE" | python3 -m json.tool

# 3. 提取 transaction_id 和 order_id
TRANSACTION_ID=$(echo "$PAYERMAX_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('transaction_id', ''))")
ORDER_ID=$(echo "$PAYERMAX_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('order_id', ''))")
PAYMENT_URL=$(echo "$PAYERMAX_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('payment_url', ''))")

echo "Transaction ID: $TRANSACTION_ID"
echo "Order ID: $ORDER_ID"
echo "Payment URL: $PAYMENT_URL"

# 4. 验证支付（使用 transaction_id）
curl -X POST http://localhost:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{\"provider\":\"payermax\",\"transaction_id\":\"$TRANSACTION_ID\"}" | python3 -m json.tool

# 5. 验证支付（使用 order_id）
curl -X POST http://localhost:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d "{\"provider\":\"payermax\",\"order_id\":\"$ORDER_ID\"}" | python3 -m json.tool
```

### 3.2 直接支付模式测试（信用卡）

```bash
# 1. 创建支付（直接支付 - 信用卡）
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax信用卡支付测试",
    "customer_email": "test@example.com",
    "payment_method": "card"
  }' | python3 -m json.tool
```

### 3.3 直接支付模式测试（支付宝）

```bash
# 1. 创建支付（直接支付 - 支付宝）
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "100.00",
    "currency": "CNY",
    "product_name": "PayerMax支付宝支付测试",
    "customer_email": "test@example.com",
    "payment_method": "alipay"
  }' | python3 -m json.tool
```

---

## 4. 重要字段说明

| 字段 | 说明 | 用途 |
|------|------|------|
| `payment_id` | PayerMax 交易ID | 统一接口字段，与 `transaction_id` 相同 |
| `transaction_id` | PayerMax 交易ID | 用于验证支付状态 |
| `order_id` | 商户订单号 | 也可用于验证支付状态 |
| `payment_url` | 支付页面URL | 在浏览器中打开完成支付 |
| `status` | 支付状态 | `created`（已创建）、`success`（成功）、`pending`（待支付）、`failed`（失败）、`cancelled`（已取消） |

---

## 5. 配置要求

PayerMax 需要在数据库中配置以下参数（`payment_configs` 表）：

| 配置项 | config_key | 说明 |
|--------|-----------|------|
| App ID | `app_id` | PayerMax 应用ID |
| 商户号 | `merchant_no` | PayerMax 商户号 |
| 私钥路径 | `private_key_path` | RSA 私钥文件路径 |
| 公钥路径 | `public_key_path` | RSA 公钥文件路径 |
| 环境 | `mode` | `production` 或 `sandbox` |

**示例 SQL**:
```sql
INSERT INTO payment_configs (provider, config_key, config_value, environment, is_active, created_at, updated_at)
VALUES
  ('payermax', 'app_id', 'your_app_id', 'production', 1, NOW(), NOW()),
  ('payermax', 'merchant_no', 'your_merchant_no', 'production', 1, NOW(), NOW()),
  ('payermax', 'private_key_path', '/path/to/private_key.pem', 'production', 1, NOW(), NOW()),
  ('payermax', 'public_key_path', '/path/to/public_key.pem', 'production', 1, NOW(), NOW()),
  ('payermax', 'mode', 'sandbox', 'production', 1, NOW(), NOW());
```

---

## 6. 常见错误

### 错误 1: 配置不完整

```json
{
  "detail": "支付渠道 payermax 未启用，请检查配置"
}
```

**解决**: 检查数据库 `payment_configs` 表中 PayerMax 的配置是否完整（app_id、merchant_no、private_key_path 等）

### 错误 2: 验证时缺少参数

```json
{
  "detail": "PayerMax验证需要提供transaction_id或order_id"
}
```

**解决**: 提供 `transaction_id` 或 `order_id` 中的任意一个

### 错误 3: 签名验证失败

```json
{
  "success": false,
  "error": "创建订单失败: 签名验证失败"
}
```

**解决**: 检查 RSA 私钥和公钥是否正确配置，密钥文件路径是否正确

---

## 7. 相关文档

- 统一支付接口文档: `docs/unified_payment_curl_commands.md`
- PayerMax 客户端代码: `services/payment_service/payermax_client.py`
- 统一支付接口代码: `server/api/v1/unified_payment.py`
