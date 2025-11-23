# 支付服务快速启动指南（魔方西元）

## 快速开始

### 1. 安装依赖

```bash
pip install stripe>=7.0.0
# 或
pip install -r requirements.txt
```

### 2. 配置Stripe密钥

在项目根目录创建或编辑 `.env` 文件：

```bash
STRIPE_SECRET_KEY=sk_test_你的测试密钥
FRONTEND_BASE_URL=http://localhost:8080
```

**获取Stripe密钥**:
1. 访问 [Stripe Dashboard](https://dashboard.stripe.com/)
2. 登录或注册账号
3. 进入 "Developers" > "API keys"
4. 复制 "Secret key"（测试环境使用 `sk_test_...`，生产环境使用 `sk_live_...`）

### 3. 启动服务

```bash
# 启动所有服务（包括支付服务）
./start_all_services.sh
```

支付服务将在端口 **9006** 启动（gRPC）

### 4. 访问支付页面

打开浏览器访问：
```
http://localhost:8080/payment.html
```

或带参数：
```
http://localhost:8080/payment.html?amount=19.90&currency=USD&product=月订阅会员&email=user@example.com
```

## 测试支付

### 使用Stripe测试卡

在Stripe支付页面使用以下测试卡号：

- **卡号**: `4242 4242 4242 4242`
- **过期日期**: 任意未来日期（如 12/25）
- **CVC**: 任意3位数字（如 123）
- **邮编**: 任意5位数字（如 12345）

### 测试流程

1. 访问支付页面
2. 输入邮箱地址
3. 点击"立即支付"
4. 在Stripe页面使用测试卡号
5. 完成支付
6. 查看支付成功页面

## API测试

### 创建支付会话

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/create-session \
  -H "Content-Type: application/json" \
  -d '{
    "amount": "19.90",
    "currency": "USD",
    "product_name": "月订阅会员",
    "customer_email": "test@example.com"
  }'
```

### 验证支付状态

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/verify \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "cs_test_..."
  }'
```

## 服务端口

- **支付服务 (gRPC)**: 9006
- **主服务 (FastAPI)**: 8001
- **前端服务**: 8080

## 常见问题

### Q: 支付页面无法打开？

A: 确保前端服务已启动：
```bash
cd frontend
python3 -m http.server 8080
```

### Q: 创建支付会话失败？

A: 检查：
1. Stripe密钥是否正确配置
2. 主服务是否运行（端口8001）
3. 查看日志：`logs/payment_service_9006.log`

### Q: 如何切换到生产环境？

A: 
1. 在Stripe Dashboard切换到"Live mode"
2. 获取生产密钥（`sk_live_...`）
3. 更新 `.env` 文件中的 `STRIPE_SECRET_KEY`
4. 重启服务

## 相关文档

- 详细文档: [payment_service_guide.md](./payment_service_guide.md)
- Stripe文档: https://stripe.com/docs

