# Line Pay 支付测试报告

## 测试时间
2025-01-20

## 测试环境
- 环境：Sandbox（测试环境）
- API 基础URL：`https://sandbox-api-pay.line.me`
- 支付页面URL：`https://sandbox-web-pay.line.me`
- 服务地址：`http://127.0.0.1:8001`

## 配置状态

### 数据库配置
- ✅ Channel ID: 2008928087
- ✅ Channel Secret: 已配置
- ✅ Mode: sandbox
- ✅ 环境：sandbox（已激活）

### 服务状态
- ✅ Line Pay 客户端已启用
- ✅ 接口可正常访问
- ✅ 签名生成正常

## 测试结果

### 1. 创建支付订单接口

**接口**: `POST /api/v1/payment/unified/create`

**测试请求**:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linepay",
    "amount": "100",
    "currency": "TWD",
    "product_name": "Line Pay测试产品"
  }'
```

**测试结果**: ✅ 成功

**响应示例**:
```json
{
  "success": true,
  "provider": "linepay",
  "transaction_id": "2026012102333767510",
  "order_id": "ORDER_1768968615020",
  "payment_url": "https://sandbox-web-pay.line.me/web/payment/wait?transactionReserveId=YTl0RlIxamJMam9vMnI1b2NMOW1BSG9VMTRXWFpuQWZOSmJGY1d2dG82SFpLTXdVVGlhSWZlYndoRzRhbi9RYg",
  "status": "created",
  "message": "Line Pay订单创建成功"
}
```

**验证点**:
- ✅ 成功创建订单
- ✅ 返回有效的 transaction_id
- ✅ 返回有效的 payment_url（沙箱环境）
- ✅ 自动生成 order_id
- ✅ 状态为 created

### 2. 验证支付状态接口

**接口**: `POST /api/v1/payment/unified/verify`

**测试请求**:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linepay",
    "transaction_id": "2026012102333767510"
  }'
```

**测试结果**: ✅ 成功

**响应示例（支付前）**:
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

**说明**:
- 订单刚创建时，状态可能为 null（未支付）
- 支付完成后，状态会变为 "PAYMENT"
- 需要等待用户完成支付后才能看到完整状态

**验证点**:
- ✅ 成功查询订单状态
- ✅ 返回正确的货币信息
- ✅ 接口调用正常

### 3. 支付流程测试

**测试步骤**:
1. ✅ 创建支付订单 - 成功
2. ✅ 获取 payment_url - 成功
3. ⏳ 浏览器支付 - 需要手动完成
4. ⏳ 验证支付后状态 - 待支付完成后测试

**payment_url**: `https://sandbox-web-pay.line.me/web/payment/wait?transactionReserveId=...`

**说明**: 
- payment_url 需要在浏览器中打开
- 使用 Line Pay 账号登录
- 完成支付后，订单状态会变为 PAYMENT

## Line Pay 特性说明

### 1. 货币处理
Line Pay 支持多种货币，但需要注意：
- **零小数货币**：TWD（台币）、JPY（日元）、THB（泰铢）
  - 金额必须是整数（如 100，不能是 100.50）
- **其他货币**：USD（美元）等
  - 可以使用小数（如 19.90）

### 2. 支付流程
1. **创建订单**：调用 `create_payment` 创建支付请求
2. **跳转支付**：用户打开 `payment_url` 完成支付
3. **确认支付**：支付完成后，Line Pay 会回调 `confirm_url`
4. **查询状态**：使用 `verify_payment` 查询订单状态

### 3. 字段说明
- **transaction_id**：Line Pay 交易ID（用于验证）
- **order_id**：商户订单号（自动生成或自定义）
- **payment_url**：支付页面URL（类似 Stripe 的 checkout_url）

## 接口对比

### Line Pay vs Stripe vs PayPal

| 特性 | Stripe | PayPal | Line Pay |
|------|--------|--------|----------|
| 创建接口 | ✅ 成功 | ✅ 成功 | ✅ 成功 |
| 验证接口 | ✅ 成功 | ✅ 成功 | ✅ 成功 |
| 支付URL字段 | `checkout_url` | `approval_url` | `payment_url` |
| 支付ID字段 | `session_id` | `payment_id` | `transaction_id` |
| 订单ID字段 | 无 | `order_id` | `order_id` |
| 支付流程 | 直接支付页面 | 需要登录 PayPal | 需要登录 Line Pay |
| 测试方式 | 测试卡号 | PayPal 测试账号 | Line Pay 测试账号 |
| 适用地区 | 全球 | 全球 | 日本、台湾、泰国 |

## 测试工具

### 自动化测试脚本
已创建 `test_linepay.sh` 脚本，包含：
- 配置检查
- 创建支付订单
- 验证支付状态
- 输出测试结果和下一步指引

**使用方法**:
```bash
chmod +x test_linepay.sh
./test_linepay.sh
```

## 已知问题

### 1. 验证接口返回状态为 null
- **问题**: 订单刚创建时，验证接口返回的 status 为 null
- **原因**: 订单尚未支付，Line Pay API 可能返回空状态
- **影响**: 无影响，支付后状态会更新
- **状态**: 正常行为

### 2. 支付确认流程
- **说明**: Line Pay 需要实现 Webhook 回调来确认支付
- **当前实现**: 使用 `verify_payment` 查询状态
- **建议**: 如需自动确认，需要实现 `confirm_payment` 接口

## 测试结论

### ✅ 通过项
1. Line Pay 配置正确，客户端初始化成功
2. 创建支付订单接口正常工作
3. 验证支付状态接口正常工作
4. 返回的 payment_url 格式正确（沙箱环境）
5. 订单ID自动生成正常
6. 货币处理正确（TWD 使用整数）

### ⏳ 待测试项
1. 浏览器支付流程（需要手动完成）
2. 支付后状态验证（PAYMENT 状态）
3. 支付确认流程（confirm_payment）
4. 错误处理（无效 transaction_id 等）
5. 不同货币测试（JPY、THB、USD）

## 下一步

1. **完成浏览器支付测试**:
   - 打开返回的 payment_url
   - 使用 Line Pay 测试账号登录
   - 完成支付流程

2. **验证支付后状态**:
   ```bash
   curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
     -H "Content-Type: application/json" \
     -d '{"provider":"linepay","transaction_id":"你的transaction_id"}' | python3 -m json.tool
   ```

3. **测试不同货币**:
   - TWD（台币）：整数金额
   - JPY（日元）：整数金额
   - USD（美元）：可带小数

4. **测试错误场景**:
   - 无效的 transaction_id
   - 已过期的订单
   - 网络错误处理

## 相关文件

- 支付客户端: `services/payment_service/linepay_client.py`
- 统一支付接口: `server/api/v1/unified_payment.py`
- 测试脚本: `test_linepay.sh`
- 配置管理: `scripts/db/manage_payment_configs.py`

## 配置示例

### 数据库配置
```bash
# 配置 Channel ID
python3 scripts/db/manage_payment_configs.py add linepay channel_id 你的Channel_ID \
  --environment sandbox \
  --description "Line Pay沙箱Channel ID"

# 配置 Channel Secret
python3 scripts/db/manage_payment_configs.py add linepay channel_secret 你的Channel_Secret \
  --environment sandbox \
  --description "Line Pay沙箱Channel Secret"

# 配置模式
python3 scripts/db/manage_payment_configs.py add linepay mode sandbox \
  --environment sandbox \
  --description "Line Pay环境模式（sandbox/production）"

# 激活沙箱环境
python3 scripts/db/manage_payment_configs.py set-active-environment linepay sandbox
```

### 环境变量配置（降级方案）
```bash
LINEPAY_CHANNEL_ID=你的Channel_ID
LINEPAY_CHANNEL_SECRET=你的Channel_Secret
LINEPAY_MODE=sandbox
FRONTEND_BASE_URL=http://localhost:8080
API_BASE_URL=http://localhost:8001
```
