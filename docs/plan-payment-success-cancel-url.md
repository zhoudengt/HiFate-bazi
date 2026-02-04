# 支付成功/取消页配置 — 开发计划

## 目标

- 支持在「统一创建支付」请求中传入**成功跳转 URL**、**取消页 URL**（可选）。
- 成功页需携带 **session_id**，供前端调用 `/payment/unified/verify` 校验支付状态。
- 仅修改支付相关代码，其它模块不动。

---

## 成功页 / 取消页 URL（约定）

| 用途 | URL |
|------|-----|
| 成功页 | `http://localhost:5173/payment/success`（需带 session_id） |
| 取消页 | `http://localhost:5173/payment/cancel` |

**session_id 说明**：Stripe 重定向时会把 success_url 中的占位符 `{CHECKOUT_SESSION_ID}` 替换为实际 session_id。因此 success_url 必须包含该占位符，例如：

- `http://localhost:5173/payment/success?session_id={CHECKOUT_SESSION_ID}`

前端成功页从 URL query 取 `session_id`，再调用 `/payment/unified/verify`（传 `provider: "stripe"`, `session_id`）完成校验。

---

## 涉及文件（仅 1 个）

| 文件 | 改动说明 |
|------|----------|
| `server/api/v1/unified_payment.py` | 请求体增加可选 `success_url`、`cancel_url`；构建 `payment_params` 时传入 |

不修改：`services/payment_service/` 下各 client、grpc_gateway、前端及其它 API。

---

## 实现步骤

### 1. 请求体增加可选字段

在 **CreatePaymentRequest** 中增加（默认 None，保持向后兼容）：

- `success_url: Optional[str] = None` — 支付成功跳转 URL；Stripe 须含占位符 `{CHECKOUT_SESSION_ID}`，否则前端无法拿到 session_id。
- `cancel_url: Optional[str] = None` — 支付取消跳转 URL。

位置：紧接现有 `metadata` 字段后。

### 2. 构建 payment_params 时传入 URL

在 **create_unified_payment** 内，在现有 `payment_params = {...}` 之后、`if provider_str == "stripe":` 之前：

- 若 `request.success_url` 存在：
  - `payment_params["success_url"] = request.success_url`（Stripe）
  - `payment_params["return_url"] = request.success_url`（PayPal / Alipay / LinePay 等）
- 若 `request.cancel_url` 存在：
  - `payment_params["cancel_url"] = request.cancel_url`

各支付客户端已支持从 kwargs 读取上述字段并有默认值，无需改 client。

### 3. 接口文档说明

在 **CreatePaymentRequest** 或路由 docstring 中说明：

- `success_url`、`cancel_url` 为可选；不传时由各渠道按环境/配置生成默认 URL。
- Stripe：success_url 须包含 `{CHECKOUT_SESSION_ID}`，重定向后前端可从 query 取 `session_id` 并调用 verify 接口。

---

## 调用示例

指定成功页（带 session_id）、取消页：

```bash
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "stripe",
    "amount": "4.10",
    "currency": "USD",
    "product_name": "Stripe测试产品",
    "customer_email": "test@example.com",
    "success_url": "http://localhost:5173/payment/success?session_id={CHECKOUT_SESSION_ID}",
    "cancel_url": "http://localhost:5173/payment/cancel"
  }'
```

不传 URL 时行为与当前一致（依赖各 client 默认逻辑）。

---

## 验收

- 不传 `success_url`/`cancel_url` 时，行为与当前一致。
- 传上述 success_url（含 `{CHECKOUT_SESSION_ID}`）、cancel_url 时：Stripe 支付成功跳转到 `http://localhost:5173/payment/success?session_id=<实际 session_id>`，取消跳转到 `http://localhost:5173/payment/cancel`。
- 前端成功页可从 URL 取 `session_id` 并调用 `/payment/unified/verify`。
- 仅改动 `unified_payment.py`，不动其它非支付代码。
