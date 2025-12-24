#!/bin/bash
# ACR 配置交互式测试脚本
# 用于验证 ACR 配置信息并测试 Docker 登录

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🔍 ACR 配置交互式测试"
echo "=========================================="
echo ""

# 从阿里云控制台提取的期望值
EXPECTED_REGISTRY="crpi-llets4xvyuzoxiyx.cn-beijing.personal.cr.aliyuncs.com"
EXPECTED_NAMESPACE="hifate-bazi-namespaces"

echo "📋 基于阿里云控制台的期望值："
echo "  ACR_REGISTRY: ${EXPECTED_REGISTRY}"
echo "  ACR_NAMESPACE: ${EXPECTED_NAMESPACE}"
echo "  ACR_USERNAME: aliyun3959725177 (或 AccessKey ID)"
echo ""

# 从环境变量或用户输入读取配置
echo "请输入您的 ACR 配置信息（可以直接回车使用期望值）："
echo ""

read -p "ACR_REGISTRY [${EXPECTED_REGISTRY}]: " ACR_REGISTRY
ACR_REGISTRY="${ACR_REGISTRY:-${EXPECTED_REGISTRY}}"

read -p "ACR_NAMESPACE [${EXPECTED_NAMESPACE}]: " ACR_NAMESPACE
ACR_NAMESPACE="${ACR_NAMESPACE:-${EXPECTED_NAMESPACE}}"

read -p "ACR_USERNAME [aliyun3959725177]: " ACR_USERNAME
ACR_USERNAME="${ACR_USERNAME:-aliyun3959725177}"

read -sp "ACR_PASSWORD (输入时不会显示): " ACR_PASSWORD
echo ""

echo ""
echo "=========================================="
echo "✅ 格式验证"
echo "=========================================="
echo ""

ERRORS=0

# 验证 ACR_REGISTRY
echo "1. ACR_REGISTRY 验证："
echo "   当前值: ${ACR_REGISTRY}"
if [ "$ACR_REGISTRY" = "$EXPECTED_REGISTRY" ]; then
    echo -e "   ${GREEN}✅ 格式正确${NC}"
else
    echo -e "   ${YELLOW}⚠️  与期望值不一致${NC}"
    echo "   期望值: ${EXPECTED_REGISTRY}"
fi

if [[ "$ACR_REGISTRY" =~ ^[a-z0-9-]+\.[a-z0-9-]+\.personal\.cr\.aliyuncs\.com$ ]]; then
    echo -e "   ${GREEN}✅ 格式符合规范${NC}"
else
    echo -e "   ${RED}❌ 格式不符合规范${NC}"
    echo "   期望格式: 实例ID.地域.personal.cr.aliyuncs.com"
    ERRORS=$((ERRORS + 1))
fi

if [[ "$ACR_REGISTRY" == *"-vpc"* ]]; then
    echo -e "   ${RED}❌ 错误：使用了 VPC 地址，应使用公网地址${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "   ${GREEN}✅ 使用公网地址（正确）${NC}"
fi

echo ""

# 验证 ACR_NAMESPACE
echo "2. ACR_NAMESPACE 验证："
echo "   当前值: ${ACR_NAMESPACE}"
if [ "$ACR_NAMESPACE" = "$EXPECTED_NAMESPACE" ]; then
    echo -e "   ${GREEN}✅ 与期望值一致${NC}"
else
    echo -e "   ${YELLOW}⚠️  与期望值不一致${NC}"
    echo "   期望值: ${EXPECTED_NAMESPACE}"
fi

if [ -n "$ACR_NAMESPACE" ]; then
    echo -e "   ${GREEN}✅ 不为空${NC}"
else
    echo -e "   ${RED}❌ 为空${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 验证 ACR_USERNAME
echo "3. ACR_USERNAME 验证："
echo "   当前值: ${ACR_USERNAME}"
if [ -n "$ACR_USERNAME" ]; then
    echo -e "   ${GREEN}✅ 不为空${NC}"
else
    echo -e "   ${RED}❌ 为空${NC}"
    ERRORS=$((ERRORS + 1))
fi

if [[ "$ACR_USERNAME" =~ ^LTAI[0-9A-Za-z]+$ ]]; then
    echo -e "   ${GREEN}✅ 格式正确（AccessKey ID）${NC}"
elif [[ "$ACR_USERNAME" == "aliyun3959725177" ]]; then
    echo -e "   ${GREEN}✅ 格式正确（阿里云账号名）${NC}"
else
    echo -e "   ${YELLOW}⚠️  格式可能不正确（通常为账号名或 AccessKey ID）${NC}"
fi

echo ""

# 验证 ACR_PASSWORD
echo "4. ACR_PASSWORD 验证："
if [ -n "$ACR_PASSWORD" ]; then
    PASSWORD_LEN=${#ACR_PASSWORD}
    echo -e "   ${GREEN}✅ 已设置（长度: ${PASSWORD_LEN} 字符）${NC}"
    
    if [ $PASSWORD_LEN -lt 10 ]; then
        echo -e "   ${YELLOW}⚠️  密码长度较短，请确认是否正确${NC}"
    fi
else
    echo -e "   ${RED}❌ 为空${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 显示镜像名称格式
echo "=========================================="
echo "📦 镜像名称格式"
echo "=========================================="
echo ""
IMAGE_BASE="${ACR_REGISTRY}/${ACR_NAMESPACE}/hifate-bazi"
echo "完整镜像名称格式:"
echo "  ${IMAGE_BASE}:<tag>"
echo ""
echo "示例："
echo "  - ${IMAGE_BASE}:master"
echo "  - ${IMAGE_BASE}:latest"
echo ""

# 总结
echo "=========================================="
echo "📊 验证结果"
echo "=========================================="
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 格式验证通过！${NC}"
    echo ""
    echo "下一步："
    echo "  1. 使用 GitHub Actions 测试实际登录（推荐）"
    echo "     https://github.com/zhoudengt/HiFate-bazi/actions/workflows/test-acr-config.yml"
    echo ""
    echo "  2. 本地测试 Docker 登录（如果已安装 Docker）："
    read -p "    是否测试 Docker 登录？(y/n): " TEST_LOGIN
    if [ "$TEST_LOGIN" = "y" ] || [ "$TEST_LOGIN" = "Y" ]; then
        echo ""
        echo "=========================================="
        echo "🔐 测试 Docker 登录"
        echo "=========================================="
        echo ""
        
        if ! command -v docker &> /dev/null; then
            echo -e "${RED}❌ Docker 未安装，无法测试登录${NC}"
            echo "   请安装 Docker 或使用 GitHub Actions 测试"
        else
            echo "正在测试 Docker 登录..."
            echo ""
            
            if echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" -u "$ACR_USERNAME" --password-stdin 2>&1; then
                echo ""
                echo -e "${GREEN}✅ Docker 登录成功！${NC}"
                echo ""
                echo "配置正确，可以正常使用！"
                echo ""
                echo "退出 Docker 登录..."
                docker logout "$ACR_REGISTRY" 2>/dev/null || true
            else
                echo ""
                echo -e "${RED}❌ Docker 登录失败！${NC}"
                echo ""
                echo "可能的原因："
                echo "  1. ACR_USERNAME 不正确"
                echo "  2. ACR_PASSWORD 不正确"
                echo "  3. AccessKey 未启用或没有 ACR 访问权限"
                echo "  4. 网络连接问题"
                echo ""
                echo "建议："
                echo "  1. 检查 ACR_USERNAME 和 ACR_PASSWORD 是否正确"
                echo "  2. 如果使用 AccessKey，确认 AccessKey 已启用"
                echo "  3. 在 GitHub Actions 中测试（推荐）"
            fi
        fi
    fi
else
    echo -e "${RED}❌ 格式验证失败！发现 ${ERRORS} 个错误${NC}"
    echo ""
    echo "请根据上述错误信息修正配置"
fi

echo ""
echo "=========================================="
echo "📝 GitHub Actions 测试方法"
echo "=========================================="
echo ""
echo "1. 访问: https://github.com/zhoudengt/HiFate-bazi/actions"
echo "2. 选择 '🧪 Test ACR Configuration'"
echo "3. 点击 'Run workflow'"
echo "4. 选择测试类型: 'login_only'"
echo "5. 点击 'Run workflow' 按钮"
echo "6. 查看测试结果"
echo ""

