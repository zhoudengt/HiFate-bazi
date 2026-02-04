# 支付成功页未使用请求体 success_url — 根因与修改计划

## 一、测试结论（根因）

1. **实际使用的 Stripe 客户端是 `stripe_client_v2`**  
   `services/payment_service/__init__.py` 中写的是：
   ```python
   from .stripe_client_v2 import StripeClient  # 新版插件化 Stripe 客户端
   ```
   因此 `get_payment_client("stripe")` 返回的是 **stripe_client_v2.StripeClient**，不是 stripe_client.py。

2. **stripe_client_v2 未把请求里的 success_url/cancel_url 传下去**  
   在 `services/payment_service/stripe_client_v2.py` 的 `create_payment(self, **kwargs)` 中：
   - 只从 kwargs 里取了：amount, currency, product_name, customer_email, metadata, order_id, enable_adaptive_pricing, enable_link
   - **没有**取 `success_url`、`cancel_url`
   - 调用 `create_checkout_session(...)` 时也**没有**传入 success_url、cancel_url  
   因此 `create_checkout_session` 里始终收到 `success_url=None`、`cancel_url=None`，会走默认逻辑：
   - `frontend_base = get_payment_config(...) or os.getenv("FRONTEND_BASE_URL", "http://localhost:8001")`
   - `success_url = f"{frontend_base}/frontend/payment-success.html?provider=stripe"`
   - `cancel_url = f"{frontend_base}/frontend/payment-cancel.html?provider=stripe"`  
   所以无论请求体里传什么 success_url/cancel_url，最终都会用上述默认 URL（或你环境里 8080 的配置），导致端口、路径与请求不一致。

3. **unified_payment 已正确传参**  
   `server/api/v1/unified_payment.py` 已把 `request.success_url`、`request.cancel_url` 放进 `payment_params` 并调用 `payment_client.create_payment(**payment_params)`，无需再改。

---

## 二、修改计划（仅动支付相关、最小改动）

### 修改文件（仅 1 个）

| 文件 | 改动说明 |
|------|----------|
| `services/payment_service/stripe_client_v2.py` | 在 `create_payment` 中从 kwargs 读取 success_url、cancel_url，并传入 `create_checkout_session` |

### 具体改动

1. **在 `create_payment` 中增加对 success_url、cancel_url 的读取**  
   在现有 `kwargs.get(...)` 之后（例如在 `order_id = kwargs.get('order_id')` 之后）增加：
   - `success_url = kwargs.get('success_url')`
   - `cancel_url = kwargs.get('cancel_url')`

2. **调用 `create_checkout_session` 时传入这两个参数**  
   在现有 `return self.create_checkout_session(...)` 的实参中增加：
   - `success_url=success_url`
   - `cancel_url=cancel_url`

### 不改动的部分

- 不修改 `server/api/v1/unified_payment.py`（已传 success_url/cancel_url）
- 不修改 `stripe_client.py`（当前未作为 "stripe" 的注册实现使用）
- 不修改其他支付 client、网关、前端或业务逻辑

---

## 三、验收

- 请求体带 `success_url`、`cancel_url` 时，Stripe 创建会话使用的成功/取消页为请求中的 URL（例如 `http://localhost:5173/payment/success?session_id={CHECKOUT_SESSION_ID}`、`http://localhost:5173/payment/cancel`）。
- 不传时行为不变，仍使用 stripe_client_v2 内默认的 frontend_base + `/frontend/payment-success.html` 等。
