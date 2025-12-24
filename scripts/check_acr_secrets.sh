#!/bin/bash
# ACR Secrets 配置检查脚本
# 用于验证 GitHub Secrets 中的 ACR 配置格式是否正确

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🔍 ACR Secrets 配置准确性检查"
echo "=========================================="
echo ""

# 从阿里云控制台提取的期望值（基于图片信息）
EXPECTED_REGISTRY="crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com"
EXPECTED_NAMESPACE="hifate-bazi-namespaces"
EXPECTED_USERNAME_PATTERN="aliyun3959725177"  # 阿里云账号名

echo "📋 期望的配置值（基于阿里云控制台）："
echo "  ACR_REGISTRY: ${EXPECTED_REGISTRY}"
echo "  ACR_NAMESPACE: ${EXPECTED_NAMESPACE}"
echo "  ACR_USERNAME: ${EXPECTED_USERNAME_PATTERN} (阿里云账号名)"
echo "  ACR_PASSWORD: [需要您在 GitHub Secrets 中配置]"
echo ""

echo "=========================================="
echo "✅ 配置格式验证"
echo "=========================================="
echo ""

# 验证 ACR_REGISTRY 格式
echo "1. ACR_REGISTRY 格式检查："
echo "   期望值: ${EXPECTED_REGISTRY}"
echo "   格式要求:"
echo "     ✅ 使用公网地址（不是 VPC 地址）"
echo "     ✅ 格式: 实例ID.地域.personal.cr.aliyuncs.com"
echo "     ✅ 不应包含 http:// 或 https:// 前缀"
echo ""

# 验证 ACR_NAMESPACE 格式
echo "2. ACR_NAMESPACE 格式检查："
echo "   期望值: ${EXPECTED_NAMESPACE}"
echo "   格式要求:"
echo "     ✅ 与阿里云控制台中的命名空间名称完全一致"
echo "     ✅ 注意大小写（全小写）"
echo ""

# 验证 ACR_USERNAME 格式
echo "3. ACR_USERNAME 格式检查："
echo "   期望值: ${EXPECTED_USERNAME_PATTERN} (阿里云账号名)"
echo "   格式说明:"
echo "     ✅ 可以使用阿里云账号名（如: aliyun3959725177）"
echo "     ✅ 也可以使用 AccessKey ID（格式: LTAI...）"
echo "     ⚠️  注意：如果是 RAM 子账号，不支持包含点号的别名"
echo ""

# 验证 ACR_PASSWORD 格式
echo "4. ACR_PASSWORD 格式检查："
echo "   格式说明:"
echo "     ✅ 如果使用账号密码：是开通服务时设置的访问密码"
echo "     ✅ 如果使用 AccessKey：是 AccessKey Secret"
echo "     ✅ 完整复制，不要有多余的空格或换行"
echo ""

echo "=========================================="
echo "📦 镜像名称格式验证"
echo "=========================================="
echo ""

IMAGE_BASE="${EXPECTED_REGISTRY}/${EXPECTED_NAMESPACE}/hifate-bazi"
echo "完整镜像名称格式:"
echo "  ${IMAGE_BASE}:<tag>"
echo ""
echo "示例："
echo "  - ${IMAGE_BASE}:master"
echo "  - ${IMAGE_BASE}:latest"
echo "  - ${IMAGE_BASE}:abc1234"
echo ""

echo "=========================================="
echo "🧪 验证方法"
echo "=========================================="
echo ""

echo "方法 1: 使用 GitHub Actions 测试（推荐）"
echo "  1. 访问: https://github.com/zhoudengt/HiFate-bazi/actions"
echo "  2. 选择 '🧪 Test ACR Configuration'"
echo "  3. 点击 'Run workflow'"
echo "  4. 选择测试类型: 'login_only'"
echo "  5. 点击 'Run workflow' 按钮"
echo "  6. 查看测试结果"
echo ""

echo "方法 2: 本地测试 Docker 登录"
echo "  如果需要在本地测试，运行："
echo "  docker login ${EXPECTED_REGISTRY} -u <您的用户名>"
echo "  # 然后输入密码"
echo ""

echo "=========================================="
echo "✅ 配置检查清单"
echo "=========================================="
echo ""

echo "请在 GitHub Secrets 中检查以下配置："
echo ""
echo "  [ ] ACR_REGISTRY"
echo "      期望: ${EXPECTED_REGISTRY}"
echo "      当前: 请在 GitHub Secrets 中查看"
echo ""
echo "  [ ] ACR_NAMESPACE"
echo "      期望: ${EXPECTED_NAMESPACE}"
echo "      当前: 请在 GitHub Secrets 中查看"
echo ""
echo "  [ ] ACR_USERNAME"
echo "      期望: ${EXPECTED_USERNAME_PATTERN} 或 AccessKey ID"
echo "      当前: 请在 GitHub Secrets 中查看"
echo ""
echo "  [ ] ACR_PASSWORD"
echo "      期望: 访问密码或 AccessKey Secret"
echo "      当前: 已在 GitHub Secrets 中配置（隐藏）"
echo ""

echo "=========================================="
echo "⚠️  常见问题"
echo "=========================================="
echo ""

echo "1. 如果 Docker 登录失败："
echo "   - 检查 ACR_USERNAME 是否正确（账号名或 AccessKey ID）"
echo "   - 检查 ACR_PASSWORD 是否正确（密码或 AccessKey Secret）"
echo "   - 如果使用 AccessKey，确认 AccessKey 已启用且有 ACR 访问权限"
echo ""
echo "2. 如果镜像推送失败："
echo "   - 确认 ACR_REGISTRY 使用公网地址（不是 VPC 地址）"
echo "   - 确认 ACR_NAMESPACE 与阿里云控制台中的命名空间名称一致"
echo "   - 确认账号有推送镜像的权限"
echo ""
echo "3. 如果构建失败："
echo "   - 检查 Dockerfile 是否存在"
echo "   - 检查构建上下文是否正确"
echo "   - 查看 GitHub Actions 日志获取详细错误信息"
echo ""

echo "=========================================="
echo "📝 下一步操作"
echo "=========================================="
echo ""

echo "1. 确认 GitHub Secrets 配置正确"
echo "2. 使用 GitHub Actions 测试配置（推荐方法 1）"
echo "3. 如果测试通过，可以推送代码触发 build-and-push.yml"
echo "4. 查看构建日志，确认镜像成功推送到 ACR"
echo ""

echo "GitHub Secrets 配置页面："
echo "  https://github.com/zhoudengt/HiFate-bazi/settings/secrets/actions"
echo ""

echo "GitHub Actions 测试页面："
echo "  https://github.com/zhoudengt/HiFate-bazi/actions/workflows/test-acr-config.yml"
echo ""

