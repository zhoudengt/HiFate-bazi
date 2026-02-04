# 支付系统规范

> 本文档包含支付系统的架构、配置和开发规范。

## 🔴 核心原则

> **只启用 Stripe 和 PayerMax 两个支付渠道，所有支付接口必须秒出（< 2秒）。**

---

## 一、支付渠道配置

### 1.1 启用的支付渠道

| 渠道 | 说明 | 适用地区 | 状态 |
|------|------|----------|------|
| **Stripe** | 全球主流支付平台 | 美洲、欧洲、香港、全球 | ✅ 启用 |
| **PayerMax** | 新兴市场聚合支付 | 东南亚、中东、非洲、全球 | ✅ 启用 |

### 1.2 禁用的支付渠道

以下渠道已禁用，如需启用请修改 `services/payment_service/client_factory.py`：

- PayPal
- Payssion
- Alipay
- WeChat Pay
- LinePay

### 1.3 配置位置

**启用渠道配置**：`services/payment_service/client_factory.py`

```python
class PaymentClientFactory:
    # 只启用这些支付渠道
    ENABLED_PROVIDERS = {"stripe", "payermax"}
```

---

## 二、支付接口

### 2.1 核心接口

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 创建支付 | POST | `/api/v1/payment/unified/create` | 创建支付订单 |
| 验证支付 | POST | `/api/v1/payment/unified/verify` | 验证支付状态 |
| 渠道状态 | GET | `/api/v1/payment/providers` | 获取可用渠道 |
| 渠道推荐 | GET | `/api/v1/payment/recommend` | 推荐支付渠道 |

### 2.2 创建支付请求

```json
{
    "provider": "stripe",  // 或 "payermax"
    "amount": "19.90",
    "currency": "USD",
    "product_name": "产品名称",
    "customer_email": "customer@example.com",
    "success_url": "https://example.com/success",
    "cancel_url": "https://example.com/cancel"
}
```

### 2.3 响应示例

```json
{
    "success": true,
    "provider": "stripe",
    "payment_id": "cs_test_xxx",
    "payment_url": "https://checkout.stripe.com/xxx",
    "status": "created"
}
```

---

## 三、性能优化

### 3.1 缓存机制

为确保接口秒出，实现了以下缓存：

1. **客户端实例缓存**：避免每次请求都重新初始化支付客户端
2. **状态缓存**：支付渠道状态缓存 5 分钟（TTL=300秒）

**代码位置**：`services/payment_service/client_factory.py`

```python
class PaymentClientFactory:
    def __init__(self):
        self._instances: Dict[str, BasePaymentClient] = {}  # 客户端实例缓存
        self._provider_status: Dict[str, bool] = {}  # 状态缓存
        self._status_cache_ttl: float = 300  # 5分钟
```

### 3.2 性能指标

| 接口 | 目标响应时间 | 实际响应时间 |
|------|--------------|--------------|
| 渠道状态 | < 2s | ~1s |
| 创建支付 | < 3s | ~2s |
| 验证支付 | < 3s | ~2s |

---

## 四、配置管理

### 4.1 Stripe 配置

**数据库配置**（`service_configs` 表）：
- `STRIPE_SECRET_KEY`：API 密钥
- `STRIPE_PUBLISHABLE_KEY`：公开密钥
- `STRIPE_WEBHOOK_SECRET`：Webhook 密钥

**环境变量**（备选）：
```bash
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

### 4.2 PayerMax 配置

**数据库配置**（`payment_configs` 表）：
- `app_id`：应用 ID
- `merchant_no`：商户号
- `private_key_path`：私钥文件路径
- `public_key_path`：公钥文件路径

**密钥文件位置**（生产环境）：
```
/opt/secure/keys/payermax_private_key.pem
/opt/secure/keys/payermax_public_key.pem
```

---

## 五、测试规范

### 5.1 回归测试

**脚本位置**：`scripts/evaluation/api_regression_test.py`

```bash
# 测试支付接口
python3 scripts/evaluation/api_regression_test.py --category payment

# 生产环境测试
python3 scripts/evaluation/api_regression_test.py --env production --category payment
```

### 5.2 测试用例

| 测试名称 | 接口 | 说明 |
|----------|------|------|
| Stripe创建订单 | `/payment/unified/create` | Stripe 支付创建 |
| PayerMax创建订单 | `/payment/unified/create` | PayerMax 支付创建 |
| 支付渠道状态 | `/payment/providers` | 渠道状态检查 |

### 5.3 手动测试

```bash
# Stripe 创建订单
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "stripe",
    "amount": "4.10",
    "currency": "USD",
    "product_name": "测试产品",
    "customer_email": "test@example.com",
    "success_url": "http://localhost/success",
    "cancel_url": "http://localhost/cancel"
  }'

# PayerMax 创建订单
curl -X POST http://localhost:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "测试产品",
    "customer_email": "test@example.com",
    "success_url": "http://localhost/success",
    "cancel_url": "http://localhost/cancel"
  }'

# 检查渠道状态
curl http://localhost:8001/api/v1/payment/providers
```

---

## 六、开发检查清单

### 6.1 新增支付渠道

- [ ] 实现 `BasePaymentClient` 接口
- [ ] 使用 `@register_payment_client` 装饰器注册
- [ ] 添加到 `ENABLED_PROVIDERS` 集合
- [ ] 配置数据库或环境变量
- [ ] 添加回归测试用例
- [ ] 更新本文档

### 6.2 修改支付逻辑

- [ ] 本地测试通过
- [ ] 回归测试通过
- [ ] 性能指标达标（< 2秒）
- [ ] 生产环境验证

---

## 七、故障排查

### 7.1 常见问题

**问题**：`不支持的支付平台: xxx`
- **原因**：支付渠道未启用或配置不完整
- **解决**：检查 `ENABLED_PROVIDERS` 配置和渠道配置

**问题**：支付接口超时
- **原因**：缓存未生效或外部 API 响应慢
- **解决**：检查缓存状态，增加超时时间

**问题**：PayerMax 配置不完整
- **原因**：密钥文件不存在或配置缺失
- **解决**：检查密钥文件路径和数据库配置

### 7.2 日志位置

```bash
# Web 服务日志
tail -f logs/web_app_8001.log | grep -i payment

# 支付 API 调用日志
tail -f logs/payment_api.log
```

---

## 八、相关文档

- **支付客户端工厂**：`services/payment_service/client_factory.py`
- **Stripe 客户端**：`services/payment_service/stripe_client_v2.py`
- **PayerMax 客户端**：`services/payment_service/payermax_client.py`
- **统一支付接口**：`server/api/v1/unified_payment.py`
- **回归测试**：`scripts/evaluation/api_regression_test.py`
