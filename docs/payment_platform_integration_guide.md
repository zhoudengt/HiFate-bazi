# 支付平台集成指南

## 📋 概述

本系统实现了插件化支付架构，支持快速集成多种支付平台。目前支持：

| 支付平台 | 主要用途 | 适用地区 | 集成方式 |
|----------|----------|----------|----------|
| **Stripe** | 全球信用卡支付 | 美洲、欧洲、香港 | REST API |
| **PayPal** | 全球电子钱包 | 全球 | REST API |
| **Payssion** | LINE Pay 中转 | 台湾（LINE Pay） | HTTP API |
| **PayerMax** | 多支付方式聚合 | 全球（除台湾 LINE Pay） | HTTPS + RSA |
| **Alipay** | 支付宝国际版 | 中国、香港 | REST API |
| **WeChat** | 微信支付 | 中国、香港 | REST API |
| **Line Pay** | 直接集成 | 台湾、日本、泰国 | REST API |

## 🏗️ 架构设计

### 插件化架构

```
BasePaymentClient (抽象基类)
├── StripeClient
├── PayPalClient
├── PayssionClient (新增)
├── PayerMaxClient (新增)
├── AlipayClient
├── WeChatClient
└── LinePayClient
```

### 快速继承模板

新增支付平台只需：

1. **继承基类**：
```python
from .base_client import BasePaymentClient
from .client_factory import register_payment_client

@register_payment_client("your_payment")
class YourPaymentClient(BasePaymentClient):
    @property
    def provider_name(self) -> str:
        return "your_payment"

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key and self.secret)

    def create_payment(self, **kwargs):
        # 实现支付创建逻辑
        pass

    def verify_payment(self, **kwargs):
        # 实现支付验证逻辑
        pass
```

2. **注册到枚举**：
```python
class PaymentProvider(str, Enum):
    YOUR_PAYMENT = "your_payment"
```

3. **前端添加选项**：
```html
<option value="your_payment">Your Payment</option>
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 1. 启动服务
python server/start.py

# 2. 检查数据库配置
python3 scripts/db/manage_payment_configs.py list
```

### 2. 配置支付平台

#### Payssion 配置（推荐用于台湾 LINE Pay）

```bash
# 注册 Payssion 账号后，设置配置
python3 scripts/db/manage_payment_configs.py add payssion api_key YOUR_API_KEY --environment sandbox
python3 scripts/db/manage_payment_configs.py add payssion secret YOUR_SECRET --environment sandbox
python3 scripts/db/manage_payment_configs.py add payssion merchant_id YOUR_MERCHANT_ID --environment sandbox
```

#### PayerMax 配置（推荐用于全球支付）

```bash
# 生成 RSA 密钥对
openssl genrsa -out payermax_private_key.pem 2048
openssl rsa -in payermax_private_key.pem -pubout -out payermax_public_key.pem

# 设置配置
python3 scripts/db/manage_payment_configs.py add payermax app_id YOUR_APP_ID --environment test
python3 scripts/db/manage_payment_configs.py add payermax merchant_no YOUR_MERCHANT_NO --environment test
python3 scripts/db/manage_payment_configs.py add payermax private_key_path /path/to/payermax_private_key.pem --environment test
python3 scripts/db/manage_payment_configs.py add payermax public_key_path /path/to/payermax_public_key.pem --environment test
```

### 3. 测试集成

```bash
# 测试 Payssion
./test_payssion.sh

# 测试 PayerMax
./test_payermax.sh
```

## 📡 API 接口

### 创建支付

```bash
POST /api/v1/payment/unified/create
Content-Type: application/json

{
  "provider": "payssion",           // 或 "payermax"
  "amount": "19.90",
  "currency": "TWD",                // 或 "USD"
  "product_name": "测试商品",
  "customer_email": "test@example.com",
  "payment_method": "linepay"       // Payssion 专用参数
}
```

**响应示例**：
```json
{
  "success": true,
  "provider": "payssion",
  "transaction_id": "PAYSSION_1234567890",
  "payment_url": "https://pay.payssion.com/payment/xxx",
  "status": "created",
  "message": "Payssion支付订单创建成功"
}
```

### 验证支付

```bash
POST /api/v1/payment/unified/verify
Content-Type: application/json

{
  "provider": "payssion",
  "transaction_id": "PAYSSION_1234567890"
}
```

### 获取支付平台列表

```bash
GET /api/v1/payment/providers
```

### 智能推荐

```bash
GET /api/v1/payment/recommend?region=taiwan&currency=TWD
```

## 💡 使用建议

### 香港公司场景

1. **台湾市场**：使用 Payssion 接入 LINE Pay
   - 无需台湾公司注册
   - 支持香港公司直接接入
   - 费用：1.5%-2.5%

2. **全球市场**：使用 PayerMax
   - 600+ 支付方式
   - 支持多地区、多货币
   - 统一管理界面

### 地区路由策略

```python
# 智能路由逻辑
if region == "taiwan":
    # 优先 LINE Pay（通过 Payssion）
    return ["payssion", "stripe", "paypal"]
elif region == "china":
    # 优先本地支付
    return ["alipay", "wechat", "stripe"]
else:
    # 全球通用
    return ["stripe", "paypal", "payermax"]
```

## 🔧 配置管理

### 数据库配置

```sql
-- 查看所有支付配置
SELECT * FROM payment_configs WHERE is_active = 1;

-- 查看特定平台配置
SELECT * FROM payment_configs WHERE provider = 'payssion' AND environment = 'sandbox';
```

### 环境变量

支持的环境变量：
- `PAYSSION_API_KEY`
- `PAYSSION_SECRET`
- `PAYSSION_MERCHANT_ID`
- `PAYERMAX_APP_ID`
- `PAYERMAX_MERCHANT_NO`
- `PAYERMAX_PRIVATE_KEY_PATH`
- `PAYERMAX_PUBLIC_KEY_PATH`

## 🧪 测试指南

### 沙箱环境测试

1. **Payssion 测试**：
   ```bash
   ./test_payssion.sh
   ```

2. **PayerMax 测试**：
   ```bash
   ./test_payermax.sh
   ```

### 生产环境检查

```bash
# 1. 检查配置完整性
python3 scripts/db/manage_payment_configs.py list --provider payssion --environment production
python3 scripts/db/manage_payment_configs.py list --provider payermax --environment production

# 2. 验证客户端状态
curl http://127.0.0.1:8001/api/v1/payment/providers

# 3. 测试小金额交易
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{"provider": "payssion", "amount": "1.00", "currency": "USD", "product_name": "测试"}'
```

## 🚨 故障排除

### Payssion 常见问题

1. **API 密钥无效**：
   - 检查 Payssion 商户后台的 API 密钥
   - 确认沙箱/生产环境配置正确

2. **LINE Pay 不支持**：
   - Payssion 支持 LINE Pay，但可能因地区限制
   - 检查目标地区的 LINE Pay 可用性

### PayerMax 常见问题

1. **RSA 签名失败**：
   ```bash
   # 检查密钥文件
   openssl rsa -in private_key.pem -check
   openssl rsa -in public_key.pem -pubin -check
   ```

2. **支付方式不支持**：
   - 检查 PayerMax 支持的支付方式列表
   - 确认目标地区的可用性

## 📚 相关文档

- [Payssion API 文档](https://www.payssion.com/cn/docs/)
- [PayerMax 开发者中心](https://developer.payermax.com/)
- [Stripe API 文档](https://docs.stripe.com/)
- [PayPal API 文档](https://developer.paypal.com/)

## 🔄 更新日志

- **2026-01-24**: 新增 Payssion 和 PayerMax 支持
- **2026-01-24**: 重构为插件化架构
- **2026-01-24**: 优化智能路由机制