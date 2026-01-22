# PayPal 支付测试报告

## 测试时间
2025-01-20

## 测试环境
- 环境：Sandbox（测试环境）
- API 基础URL：`https://api.sandbox.paypal.com`
- 服务地址：`http://127.0.0.1:8001`

## 配置状态

### 数据库配置
- ✅ Client ID: 已配置
- ✅ Client Secret: 已配置
- ✅ Mode: sandbox
- ✅ 环境：production（配置在 production 环境，但 mode 为 sandbox）

### 服务状态
- ✅ PayPal 客户端已启用
- ✅ 访问令牌获取成功
- ✅ 接口可正常访问

## 测试结果

### 1. 创建支付订单接口

**接口**: `POST /api/v1/payment/unified/create`

**测试请求**:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "paypal",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayPal测试产品"
  }'
```

**测试结果**: ✅ 成功

**响应示例**:
```json
{
  "success": true,
  "provider": "paypal",
  "payment_id": "20W920026U4046126",
  "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=20W920026U4046126",
  "status": "CREATED",
  "message": "PayPal订单创建成功"
}
```

**验证点**:
- ✅ 成功创建订单
- ✅ 返回有效的 payment_id
- ✅ 返回有效的 approval_url（沙箱环境）
- ✅ 状态为 CREATED

### 2. 验证支付状态接口

**接口**: `POST /api/v1/payment/unified/verify`

**测试请求**:
```bash
curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "paypal",
    "payment_id": "20W920026U4046126"
  }'
```

**测试结果**: ✅ 成功

**响应示例（支付前）**:
```json
{
  "success": true,
  "provider": "paypal",
  "status": "CREATED",
  "payment_id": "20W920026U4046126",
  "amount": "19.90",
  "currency": "USD",
  "customer_email": null,
  "paid_time": null,
  "message": "订单状态: CREATED"
}
```

**验证点**:
- ✅ 成功查询订单状态
- ✅ 返回正确的金额和货币
- ✅ 状态为 CREATED（未支付）

### 3. 支付流程测试

**测试步骤**:
1. ✅ 创建支付订单 - 成功
2. ✅ 获取 approval_url - 成功
3. ⏳ 浏览器支付 - 需要手动完成
4. ⏳ 验证支付后状态 - 待支付完成后测试

**approval_url**: `https://www.sandbox.paypal.com/checkoutnow?token=20W920026U4046126`

**说明**: 
- approval_url 需要在浏览器中打开
- 使用 PayPal 沙箱测试账号登录
- 完成支付后，订单状态会变为 COMPLETED

## 接口对比

### PayPal vs Stripe

| 特性 | Stripe | PayPal |
|------|--------|--------|
| 创建接口 | ✅ 成功 | ✅ 成功 |
| 验证接口 | ✅ 成功 | ✅ 成功 |
| 支付URL字段 | `checkout_url` | `approval_url` |
| 支付ID字段 | `session_id` | `payment_id` |
| 支付流程 | 直接支付页面 | 需要登录 PayPal |
| 测试方式 | 测试卡号 | PayPal 测试账号 |

## 测试工具

### 自动化测试脚本
已创建 `test_paypal.sh` 脚本，包含：
- 配置检查
- 创建支付订单
- 验证支付状态
- 输出测试结果和下一步指引

**使用方法**:
```bash
chmod +x test_paypal.sh
./test_paypal.sh
```

## 已知问题

### 1. 配置环境不一致
- **问题**: 配置存储在 production 环境，但 mode 为 sandbox
- **影响**: 无影响，功能正常
- **建议**: 可以创建独立的 sandbox 环境配置

### 2. 支付后状态验证
- **说明**: 需要手动在浏览器中完成支付后才能测试支付后状态
- **状态**: 待用户完成支付测试

## 测试结论

### ✅ 通过项
1. PayPal 配置正确，客户端初始化成功
2. 创建支付订单接口正常工作
3. 验证支付状态接口正常工作
4. 返回的 approval_url 格式正确（沙箱环境）
5. 订单状态查询准确

### ⏳ 待测试项
1. 浏览器支付流程（需要手动完成）
2. 支付后状态验证（COMPLETED 状态）
3. 支付取消流程
4. 错误处理（无效订单ID等）

## 下一步

1. **完成浏览器支付测试**:
   - 打开返回的 approval_url
   - 使用 PayPal 沙箱测试账号登录
   - 完成支付流程

2. **验证支付后状态**:
   ```bash
   curl -X POST http://127.0.0.1:8001/api/v1/payment/unified/verify \
     -H "Content-Type: application/json" \
     -d '{"provider":"paypal","payment_id":"你的payment_id"}' | python3 -m json.tool
   ```

3. **测试错误场景**:
   - 无效的 payment_id
   - 已过期的订单
   - 网络错误处理

## 相关文件

- 支付客户端: `services/payment_service/paypal_client.py`
- 统一支付接口: `server/api/v1/unified_payment.py`
- 测试脚本: `test_paypal.sh`
- 配置管理: `scripts/db/manage_payment_configs.py`
