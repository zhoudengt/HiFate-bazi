# 支付功能测试指南

## 测试前准备

### 1. 安装依赖

```bash
# 安装Stripe库
pip install stripe>=7.0.0

# 或使用虚拟环境
.venv/bin/pip install stripe>=7.0.0
```

### 2. 配置Stripe密钥

在`.env`文件中添加（或设置环境变量）：

```bash
# 测试环境（推荐）
STRIPE_SECRET_KEY=sk_test_你的测试密钥

# 或生产环境
STRIPE_SECRET_KEY=sk_live_你的生产密钥

# 前端基础URL（可选）
FRONTEND_BASE_URL=http://localhost:8080
```

**获取Stripe测试密钥**：
1. 访问 https://dashboard.stripe.com/
2. 登录或注册账号
3. 进入 "Developers" > "API keys"
4. 复制 "Secret key"（测试环境：`sk_test_...`）

### 3. 启动服务

```bash
# 启动所有服务（包括支付服务）
./start_all_services.sh

# 或单独启动主服务
python server/start.py
```

## 测试步骤

### 方法1：使用测试脚本（推荐）

```bash
# 设置环境变量
export STRIPE_SECRET_KEY=sk_test_你的密钥

# 运行测试脚本
bash test_payment_simple.sh
```

### 方法2：手动测试

#### 1. 测试API接口

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

**预期响应**：
```json
{
  "success": true,
  "session_id": "cs_test_...",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "status": "created",
  "message": "支付会话创建成功"
}
```

#### 2. 测试前端页面

1. 启动前端服务：
   ```bash
   cd frontend
   python3 -m http.server 8080
   ```

2. 访问支付页面：
   ```
   http://localhost:8080/payment.html
   ```

3. 填写表单：
   - 产品名称：月订阅会员
   - 支付金额：19.90
   - 货币：USD
   - 邮箱：test@example.com

4. 点击"立即支付"

5. 使用Stripe测试卡号：
   - 卡号：`4242 4242 4242 4242`
   - 过期日期：任意未来日期（如 12/25）
   - CVC：任意3位数字（如 123）
   - 邮编：任意5位数字（如 12345）

### 方法3：使用API文档

访问：`http://localhost:8001/docs`

在Swagger UI中找到"支付"标签，测试：
- `POST /api/v1/payment/create-session` - 创建支付会话
- `POST /api/v1/payment/verify` - 验证支付状态

## 常见问题排查

### 问题1：API返回404

**可能原因**：
- 支付路由未注册
- 主服务未重启

**解决方法**：
1. 检查 `server/main.py` 是否包含支付路由注册
2. 重启主服务：
   ```bash
   # 停止服务
   pkill -f "server/start.py"
   
   # 重新启动
   python server/start.py
   ```

### 问题2：Stripe库未安装

**错误信息**：
```
ModuleNotFoundError: No module named 'stripe'
```

**解决方法**：
```bash
pip install stripe>=7.0.0
```

### 问题3：STRIPE_SECRET_KEY未配置

**错误信息**：
```
STRIPE_SECRET_KEY环境变量未设置
创建支付会话失败: STRIPE_SECRET_KEY未配置
```

**解决方法**：
1. 在`.env`文件中添加密钥
2. 或在启动服务前设置环境变量：
   ```bash
   export STRIPE_SECRET_KEY=sk_test_...
   python server/start.py
   ```

### 问题4：创建支付会话失败

**可能原因**：
- Stripe密钥无效
- 网络连接问题
- 金额格式错误

**解决方法**：
1. 检查密钥是否正确
2. 检查网络连接
3. 确保金额格式正确（如：19.90，不是19.9或$19.90）

### 问题5：前端无法调用API

**错误信息**：
```
Failed to fetch
```

**解决方法**：
1. 检查主服务是否运行（端口8001）
2. 检查前端配置 `frontend/config.js` 中的API地址
3. 检查浏览器控制台的详细错误信息

## 测试检查清单

- [ ] Stripe库已安装
- [ ] STRIPE_SECRET_KEY已配置
- [ ] 主服务运行正常（端口8001）
- [ ] 支付路由已注册（可通过 `/docs` 查看）
- [ ] API接口可以正常调用
- [ ] 前端页面可以正常访问
- [ ] 可以创建支付会话
- [ ] 可以跳转到Stripe支付页面
- [ ] 可以使用测试卡号完成支付
- [ ] 支付成功页面可以正常显示

## 测试结果示例

### 成功创建支付会话

```json
{
  "success": true,
  "session_id": "cs_test_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "status": "created",
  "message": "支付会话创建成功"
}
```

### 验证支付状态

```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/verify \
  -H "Content-Type: application/json" \
  -d '{"session_id": "cs_test_..."}'
```

**成功响应**：
```json
{
  "success": true,
  "status": "success",
  "payment_intent_id": "pi_...",
  "amount": "19.90",
  "currency": "USD",
  "customer_email": "test@example.com",
  "created_at": 1234567890,
  "metadata": {},
  "message": "支付状态查询成功"
}
```

## 后续步骤

测试通过后，可以：
1. 集成到实际业务中
2. 配置Webhook接收支付事件（可选）
3. 设置生产环境密钥
4. 配置自定义支付成功/取消页面

