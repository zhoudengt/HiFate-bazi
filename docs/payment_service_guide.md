# 支付服务使用指南（魔方西元）

## 概述

支付服务是一个独立的微服务，集成了Stripe支付渠道，用于处理魔方西元的支付业务。服务支持创建支付会话、验证支付状态等功能。

## 服务架构

- **服务名称**: payment-service
- **端口**: 9006 (gRPC)
- **协议**: gRPC + FastAPI REST
- **支付渠道**: Stripe

## 环境配置

### 1. 安装依赖

```bash
pip install stripe>=7.0.0
```

或使用requirements.txt：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在`.env`文件或系统环境变量中设置：

```bash
# Stripe密钥（必需）
STRIPE_SECRET_KEY=sk_test_...  # 测试环境
# 或
STRIPE_SECRET_KEY=sk_live_...  # 生产环境

# 前端基础URL（可选，用于支付成功/取消回调）
FRONTEND_BASE_URL=http://localhost:8080
```

### 3. 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
./start_all_services.sh
```

#### 方式二：单独启动支付服务

```bash
# gRPC服务
python services/payment_service/grpc_server.py --port 9006

# 或使用FastAPI（用于测试）
uvicorn services.payment_service.main:app --port 9007
```

## API接口

### REST API（通过主服务）

主服务地址：`http://127.0.0.1:8001`

#### 1. 创建支付会话

**接口**: `POST /api/v1/payment/create-session`

**请求体**:
```json
{
  "amount": "19.90",
  "currency": "USD",
  "product_name": "月订阅会员",
  "customer_email": "user@example.com",
  "metadata": {
    "source": "mofang_xiyuan",
    "product": "月订阅会员"
  }
}
```

**响应**:
```json
{
  "success": true,
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "status": "created",
  "message": "支付会话创建成功"
}
```

#### 2. 验证支付状态

**接口**: `POST /api/v1/payment/verify`

**请求体**:
```json
{
  "session_id": "cs_test_..."
}
```

**响应**:
```json
{
  "success": true,
  "status": "success",
  "payment_intent_id": "pi_...",
  "amount": "19.90",
  "currency": "USD",
  "customer_email": "user@example.com",
  "created_at": 1234567890,
  "metadata": {},
  "message": "支付状态查询成功"
}
```

### gRPC API

#### 服务定义

参考 `proto/payment.proto`

#### 使用示例

```python
import grpc
from proto.generated import payment_pb2, payment_pb2_grpc

channel = grpc.insecure_channel('127.0.0.1:9006')
stub = payment_pb2_grpc.PaymentServiceStub(channel)

# 创建支付会话
request = payment_pb2.CreatePaymentSessionRequest(
    amount="19.90",
    currency="USD",
    product_name="月订阅会员",
    customer_email="user@example.com"
)
response = stub.CreatePaymentSession(request)
print(f"Checkout URL: {response.checkout_url}")
```

## 前端集成

### 支付页面

访问：`http://localhost:8080/payment.html`

支持URL参数：
- `amount`: 支付金额（默认：19.90）
- `currency`: 货币代码（默认：USD）
- `product`: 产品名称（默认：月订阅会员）
- `email`: 预填邮箱（可选）

示例：
```
http://localhost:8080/payment.html?amount=19.90&currency=USD&product=月订阅会员&email=user@example.com
```

### 支付成功页面

`payment-success.html` - 自动验证支付状态并显示结果

### 支付取消页面

`payment-cancel.html` - 显示取消信息

## 支付流程

1. **用户发起支付**
   - 前端调用 `/api/v1/payment/create-session` 创建支付会话
   - 获取 `checkout_url`

2. **跳转到Stripe支付页面**
   - 用户完成支付或取消支付

3. **支付回调**
   - 成功：跳转到 `payment-success.html?session_id=xxx`
   - 取消：跳转到 `payment-cancel.html`

4. **验证支付状态**
   - 前端调用 `/api/v1/payment/verify` 验证支付结果
   - 显示支付详情

## 测试

### 使用Stripe测试卡

Stripe提供测试卡号用于测试：

- **成功支付**: `4242 4242 4242 4242`
- **需要3D验证**: `4000 0025 0000 3155`
- **支付失败**: `4000 0000 0000 9995`

其他测试信息：
- 任意未来日期作为过期日期
- 任意3位数字作为CVC
- 任意邮箱地址

### 测试步骤

1. 启动所有服务
2. 访问支付页面：`http://localhost:8080/payment.html`
3. 输入邮箱和金额
4. 点击"立即支付"
5. 在Stripe支付页面使用测试卡号
6. 完成支付后查看支付成功页面

## 注意事项

1. **密钥安全**
   - 生产环境必须使用生产密钥（`sk_live_...`）
   - 测试环境使用测试密钥（`sk_test_...`）
   - 不要将密钥提交到代码仓库

2. **Webhook配置**（可选）
   - 建议配置Stripe Webhook接收支付事件
   - Webhook URL: `https://your-domain.com/api/v1/payment/webhook`
   - 需要验证签名以确保安全性

3. **错误处理**
   - 所有API调用都应包含错误处理
   - 支付失败时给用户友好的提示

4. **日志记录**
   - 支付相关操作都会记录日志
   - 日志文件：`logs/payment_service_9006.log`

## 故障排查

### 问题1：无法创建支付会话

**可能原因**:
- Stripe密钥未配置或配置错误
- 网络连接问题

**解决方法**:
- 检查环境变量 `STRIPE_SECRET_KEY` 是否正确设置
- 检查网络连接和防火墙设置

### 问题2：支付验证失败

**可能原因**:
- Session ID无效或已过期
- Stripe API调用失败

**解决方法**:
- 检查Session ID是否正确
- 查看服务日志获取详细错误信息

### 问题3：前端无法调用API

**可能原因**:
- CORS配置问题
- API地址配置错误

**解决方法**:
- 检查 `frontend/config.js` 中的API地址
- 确保主服务已启动（端口8001）

## 相关文件

- Proto定义: `proto/payment.proto`
- 服务代码: `services/payment_service/`
- API路由: `server/api/v1/payment.py`
- 前端页面: `frontend/payment.html`, `payment-success.html`, `payment-cancel.html`

## 更新日志

- 2024-01-XX: 初始版本，集成Stripe支付

