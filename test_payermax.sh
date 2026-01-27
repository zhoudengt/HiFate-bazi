#!/bin/bash

echo "🔍 PayerMax 支付测试开始..."
echo ""

PROD_IP="8.210.52.217"
SSH_PASS="Yuanqizhan@163"

# 1. 检查配置
echo "1️⃣ 检查 PayerMax 配置..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no root@$PROD_IP "docker exec hifate-web python3 scripts/db/manage_payment_configs.py list --provider payermax --environment production" 2>&1 | grep -v "WARNING\|ERROR\|连接\|Redis\|MySQL\|✗\|⚠️\|异步"

# 2. 清除缓存
echo ""
echo "2️⃣ 清除配置缓存..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no root@$PROD_IP "docker exec hifate-web python3 -c \"
from services.payment_service.payment_config_loader import reload_payment_config
reload_payment_config(provider='payermax')
print('✓ 缓存已清除')
\"" 2>&1 | grep -v "WARNING\|ERROR\|连接\|Redis\|MySQL\|✗\|⚠️\|异步"

# 3. 检查客户端初始化状态
echo ""
echo "3️⃣ 检查 PayerMax 客户端初始化状态..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no root@$PROD_IP "docker exec hifate-web python3 << 'PYEOF'
import sys
sys.path.insert(0, '/app')
from services.payment_service.payermax_client import PayerMaxClient
from services.payment_service.payment_config_loader import get_payment_config, get_payment_environment
import os

env = get_payment_environment()
print(f'Environment: {env}')

client = PayerMaxClient(environment=env)
print(f'is_enabled: {client.is_enabled}')
print(f'app_id: {client.app_id}')
print(f'merchant_no: {client.merchant_no}')
print(f'private_key loaded: {client.private_key is not None}')
print(f'public_key loaded: {client.public_key is not None}')

# 检查密钥文件路径
private_path = get_payment_config('payermax', 'private_key_path', env)
public_path = get_payment_config('payermax', 'public_key_path', env)
print(f'private_key_path from DB: {private_path}')
print(f'public_key_path from DB: {public_path}')

if private_path:
    print(f'private_key file exists: {os.path.exists(private_path)}')
if public_path:
    print(f'public_key file exists: {os.path.exists(public_path)}')
PYEOF
" 2>&1 | grep -v "WARNING\|ERROR\|连接\|Redis\|MySQL\|✗\|⚠️\|异步" | tail -15

# 4. 测试支付接口
echo ""
echo "4️⃣ 测试支付接口..."
RESPONSE=$(curl -s -X POST http://$PROD_IP:8001/api/v1/payment/unified/create \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "payermax",
    "amount": "19.90",
    "currency": "USD",
    "product_name": "PayerMax测试产品",
    "customer_email": "test@example.com"
  }')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

# 5. 检查最近的错误日志
echo ""
echo "5️⃣ 检查最近的错误日志..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no root@$PROD_IP "docker logs hifate-web --tail 50 2>&1 | grep -i 'payermax\|创建订单\|error\|exception' | tail -10"

echo ""
echo "✅ 测试完成！"
