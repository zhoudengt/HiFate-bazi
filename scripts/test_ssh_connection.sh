#!/bin/bash
# 测试SSH连接配置

echo "=========================================="
echo "测试 HiFate-bazi 生产环境 SSH 连接"
echo "=========================================="
echo ""

# 测试 Node1
echo "🔍 测试 Node1 (8.210.52.217)..."
if ssh -o ConnectTimeout=5 hifate-node1 "echo '✅ Node1 SSH密钥认证成功'" 2>/dev/null; then
    echo "✅ Node1 连接成功（使用SSH密钥）"
    time ssh hifate-node1 "echo '测试命令执行'" > /dev/null 2>&1
else
    echo "❌ Node1 连接失败"
fi
echo ""

# 测试 Node2
echo "🔍 测试 Node2 (47.243.160.43)..."
if ssh -o ConnectTimeout=5 hifate-node2 "echo '✅ Node2 SSH密钥认证成功'" 2>/dev/null; then
    echo "✅ Node2 连接成功（使用SSH密钥）"
    time ssh hifate-node2 "echo '测试命令执行'" > /dev/null 2>&1
else
    echo "❌ Node2 连接失败"
fi
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
