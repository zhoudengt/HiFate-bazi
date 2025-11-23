# 💳 支付功能使用指南

## 🎯 最快5分钟实现支付成功

### 📋 准备工作

1. **获取Stripe测试密钥**
   - 访问: https://dashboard.stripe.com/test/apikeys
   - 登录/注册Stripe账号
   - 复制 **Secret key** (以 `sk_test_` 开头)

2. **安装依赖**（如未安装）
   ```bash
   pip install stripe>=7.0.0
   ```

3. **确认服务运行**
   ```bash
   # 检查主服务
   lsof -i:8001
   
   # 如未运行，启动服务
   python server/start.py
   ```

---

## 🚀 快速测试（推荐方法）

### 一键测试脚本

```bash
# 1. 设置Stripe密钥
export STRIPE_SECRET_KEY=sk_test_你的Stripe测试密钥

# 2. 运行测试脚本
./test_payment_complete.sh
```

脚本会自动：
- ✅ 检查配置
- ✅ 创建支付会话
- ✅ 打开浏览器
- ✅ 验证支付状态

### 使用测试卡号完成支付

当浏览器打开Stripe支付页面时，填入：

```
卡号: 4242 4242 4242 4242
过期: 12/25 (任意未来日期)
CVC:  123 (任意3位数字)
邮编: 12345 (任意5位数字)
```

点击"支付"即可！

---

## 📖 API接口说明

### 1. 创建支付会话

**接口**: `POST http://127.0.0.1:8001/api/v1/payment/create-session`

**请求示例**:
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

**成功响应**:
```json
{
  "success": true,
  "session_id": "cs_test_a1B2c3D4...",
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "status": "created",
  "message": "支付会话创建成功"
}
```

### 2. 验证支付状态

**接口**: `POST http://127.0.0.1:8001/api/v1/payment/verify`

**请求示例**:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/verify \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "cs_test_你的session_id"
  }'
```

**成功响应** (已支付):
```json
{
  "success": true,
  "status": "success",
  "payment_intent_id": "pi_...",
  "amount": "19.90",
  "currency": "USD",
  "customer_email": "test@example.com"
}
```

---

## 🎨 其他测试方法

### 方法2: 使用前端页面

1. 启动前端服务
   ```bash
   cd frontend
   python3 -m http.server 8080
   ```

2. 访问支付页面
   ```
   http://localhost:8080/third-party-services.html
   ```

3. 在"统一支付"模块填写表单并提交

### 方法3: 使用Swagger UI

访问: http://127.0.0.1:8001/docs

在 **payment** 标签下测试接口

---

## 💳 测试卡号参考

| 场景 | 卡号 | 说明 |
|------|------|------|
| ✅ 成功 | 4242 4242 4242 4242 | 标准测试，支付成功 |
| 🔐 3D验证 | 4000 0027 6000 3184 | 需要3D Secure验证 |
| ❌ 失败 | 4000 0000 0000 0002 | 卡片被拒绝 |
| 💰 余额不足 | 4000 0000 0000 9995 | 余额不足 |

**通用信息**:
- 过期日期: 任意未来日期（如 12/25）
- CVC: 任意3位数字（如 123）
- 邮编: 任意5位数字（如 12345）

---

## ⚠️ 常见问题

### Q1: 接口返回404

**解决**:
```bash
# 检查主服务
lsof -i:8001

# 重启服务
python server/start.py
```

### Q2: STRIPE_SECRET_KEY未配置

**解决**:
```bash
export STRIPE_SECRET_KEY=sk_test_你的密钥
```

或在 `.env` 文件中添加:
```
STRIPE_SECRET_KEY=sk_test_你的密钥
```

### Q3: stripe库未安装

**解决**:
```bash
pip install stripe>=7.0.0
```

### Q4: 创建支付失败

**检查**:
1. Stripe密钥是否正确
2. 网络连接是否正常
3. 金额格式是否正确（如 "19.90"）

---

## 📚 完整文档

| 文档 | 说明 |
|------|------|
| `docs/支付接口完整分析.md` | 完整技术文档，包含架构、代码分析 |
| `支付测试快速指南.md` | 5分钟快速上手指南 |
| `test_payment_complete.sh` | 自动化测试脚本 |
| `docs/payment_test_guide.md` | 详细测试指南 |

---

## 🏗️ 系统架构

```
前端 (8080) 
    ↓ HTTP REST API
主服务 FastAPI (8001)
    ↓ 调用 StripeClient
Stripe Python SDK
    ↓ HTTPS
Stripe API
```

**核心文件**:
- `server/api/v1/payment.py` - HTTP API路由
- `services/payment_service/stripe_client.py` - Stripe客户端
- `services/payment_service/grpc_server.py` - gRPC服务（备用）

---

## ✅ 成功标志

支付成功后会看到：

1. **API返回**: `"status": "success"`
2. **浏览器**: 显示"Payment successful"或支付成功页面
3. **Stripe Dashboard**: 可以在测试模式下看到支付记录

---

## 🔒 安全提示

1. ⚠️ 测试环境使用 `sk_test_` 密钥
2. ⚠️ 生产环境使用 `sk_live_` 密钥
3. ⚠️ 不要将密钥提交到Git仓库
4. ⚠️ 生产环境必须使用HTTPS

---

## 🆘 需要帮助？

- 查看日志: `tail -f logs/main.log | grep payment`
- 查看服务: `lsof -i:8001`
- API文档: http://127.0.0.1:8001/docs

---

## 🎉 下一步

测试成功后可以：
1. 集成到实际业务流程
2. 配置Webhook接收支付事件
3. 添加更多支付渠道（PayPal、支付宝等）
4. 配置自定义支付成功/失败页面
5. 部署到生产环境

---

**最快捷的方式**: 运行 `./test_payment_complete.sh` 一键测试！ 🚀

