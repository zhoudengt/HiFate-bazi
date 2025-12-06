#!/bin/bash
# ACR 配置测试脚本
# 用于验证 ACR 配置信息是否正确

# 不设置 set -e，以便在登录失败时继续显示诊断信息

echo "=========================================="
echo "🔍 ACR 配置验证测试"
echo "=========================================="
echo ""

# 从环境变量或参数读取配置
ACR_REGISTRY="${ACR_REGISTRY:-crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com}"
ACR_NAMESPACE="${ACR_NAMESPACE:-hifate-bazi-namespaces}"
# 默认值已移除，必须通过环境变量或参数传入
ACR_USERNAME="${ACR_USERNAME}"
ACR_PASSWORD="${ACR_PASSWORD}"

echo "📋 配置信息："
echo "  ACR_REGISTRY: ${ACR_REGISTRY}"
echo "  ACR_NAMESPACE: ${ACR_NAMESPACE}"
echo "  ACR_USERNAME: ${ACR_USERNAME}"
echo "  ACR_PASSWORD: ${ACR_PASSWORD:0:10}... (隐藏)"
echo ""

# 验证格式
echo "✅ 格式验证："

# 验证 ACR_REGISTRY 格式
if [[ "$ACR_REGISTRY" =~ ^[a-z0-9-]+\.[a-z0-9-]+\.personal\.cr\.aliyuncs\.com$ ]]; then
    echo "  ✅ ACR_REGISTRY 格式正确"
else
    echo "  ❌ ACR_REGISTRY 格式错误"
    echo "     期望格式: 实例ID.地域.personal.cr.aliyuncs.com"
    exit 1
fi

# 验证 ACR_NAMESPACE 不为空
if [ -n "$ACR_NAMESPACE" ]; then
    echo "  ✅ ACR_NAMESPACE 已设置"
else
    echo "  ❌ ACR_NAMESPACE 为空"
    exit 1
fi

# 验证 ACR_USERNAME 格式（AccessKey ID 通常以 LTAI 开头）
if [[ "$ACR_USERNAME" =~ ^LTAI[0-9A-Za-z]+$ ]]; then
    echo "  ✅ ACR_USERNAME 格式正确（AccessKey ID）"
else
    echo "  ⚠️  ACR_USERNAME 格式可能不正确（通常以 LTAI 开头）"
fi

# 验证 ACR_PASSWORD 不为空
if [ -n "$ACR_PASSWORD" ]; then
    echo "  ✅ ACR_PASSWORD 已设置"
else
    echo "  ❌ ACR_PASSWORD 为空"
    exit 1
fi

echo ""
echo "=========================================="
echo "🔐 测试 Docker 登录"
echo "=========================================="
echo ""

# 测试 Docker 登录
LOGIN_OUTPUT=$(echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" -u "$ACR_USERNAME" --password-stdin 2>&1)
LOGIN_EXIT_CODE=$?

if [ $LOGIN_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Docker 登录成功！"
else
    echo ""
    echo "❌ Docker 登录失败！"
    echo ""
    echo "错误详情："
    echo "$LOGIN_OUTPUT" | head -5
    echo ""
    echo "可能的原因和解决方案："
    echo ""
    echo "1. 阿里云 ACR 个人版可能需要使用'访问凭证'（访问密码）而不是 AccessKey"
    echo "   - 在阿里云控制台：仓库管理 > 访问凭证"
    echo "   - 设置访问密码，然后使用："
    echo "     ACR_USERNAME = 你的阿里云账号（通常是邮箱或手机号）"
    echo "     ACR_PASSWORD = 访问密码（不是 AccessKey Secret）"
    echo ""
    echo "2. 如果使用 AccessKey，请确认："
    echo "   - AccessKey 是否已启用（在阿里云 RAM 控制台检查）"
    echo "   - AccessKey 是否有 ACR 的访问权限"
    echo ""
    echo "3. 检查网络连接："
    echo "   - 确保可以访问: $ACR_REGISTRY"
    echo "   - 测试: curl -I https://$ACR_REGISTRY/v2/"
    echo ""
    echo "⚠️  注意：即使本地登录失败，GitHub Actions 中可能仍然可以正常工作"
    echo "   因为 GitHub Actions 的网络环境可能不同"
    echo ""
    exit 1
fi

echo ""
echo "=========================================="
echo "📦 验证镜像名称格式"
echo "=========================================="
echo ""

IMAGE_NAME="${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi"
echo "完整镜像名称格式："
echo "  ${IMAGE_NAME}:master"
echo "  ${IMAGE_NAME}:latest"
echo "  ${IMAGE_NAME}:<commit-sha>"
echo ""

# 尝试拉取 latest 镜像（如果存在）
echo "尝试拉取镜像（如果存在）..."
if docker pull "${IMAGE_NAME}:latest" 2>&1 | grep -q "not found\|unauthorized\|error"; then
    echo "  ⚠️  镜像不存在或无法访问（这是正常的，如果还没有推送过镜像）"
else
    echo "  ✅ 镜像拉取成功！"
fi

echo ""
echo "=========================================="
echo "✅ 配置验证完成！"
echo "=========================================="
echo ""
echo "📝 下一步："
echo "  1. 在 GitHub Secrets 中配置这 4 个值"
echo "  2. 推送到 master 分支触发 workflow"
echo "  3. 检查 workflow 日志确认构建和推送成功"
echo ""

