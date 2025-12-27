#!/bin/bash
# scripts/fix_buildx_version.sh - 修复 Docker Compose buildx 版本问题
# 用途：诊断并修复 "compose build requires buildx 0.17 or later" 错误

set -e

echo "=========================================="
echo "  Docker Compose buildx 版本修复工具"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 步骤 1：诊断当前环境
echo -e "${BLUE}[1/4] 诊断当前环境...${NC}"
echo ""

# 检查 Docker 版本
echo "📦 Docker 版本："
if command -v docker &> /dev/null; then
    docker --version || echo "  ⚠️  无法获取 Docker 版本"
else
    echo -e "  ${RED}❌ Docker 未安装${NC}"
    exit 1
fi
echo ""

# 检查 Docker Compose 版本
echo "📦 Docker Compose 版本："
if command -v docker-compose &> /dev/null; then
    docker-compose --version || echo "  ⚠️  无法获取 docker-compose 版本"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose version || echo "  ⚠️  无法获取 docker compose 版本"
else
    echo -e "  ${RED}❌ Docker Compose 未安装${NC}"
    exit 1
fi
echo ""

# 检查 buildx 版本
echo "📦 Docker Buildx 版本："
BUILDX_VERSION=""
if command -v docker &> /dev/null; then
    BUILDX_VERSION=$(docker buildx version 2>/dev/null | head -n1 || echo "")
    if [ -z "$BUILDX_VERSION" ]; then
        echo -e "  ${YELLOW}⚠️  buildx 未安装或未启用${NC}"
    else
        echo "  $BUILDX_VERSION"
        # 提取版本号
        VERSION_NUM=$(echo "$BUILDX_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "")
        if [ -n "$VERSION_NUM" ]; then
            MAJOR=$(echo "$VERSION_NUM" | cut -d. -f1)
            MINOR=$(echo "$VERSION_NUM" | cut -d. -f2)
            if [ "$MAJOR" -lt 0 ] || ([ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 17 ]); then
                echo -e "  ${RED}❌ buildx 版本 $VERSION_NUM 低于 0.17.0，需要升级${NC}"
                NEED_UPGRADE=true
            else
                echo -e "  ${GREEN}✅ buildx 版本 $VERSION_NUM 满足要求（>= 0.17.0）${NC}"
                NEED_UPGRADE=false
            fi
        else
            echo -e "  ${YELLOW}⚠️  无法解析版本号，建议升级${NC}"
            NEED_UPGRADE=true
        fi
    fi
else
    echo -e "  ${RED}❌ Docker 未安装${NC}"
    exit 1
fi
echo ""

# 查找 frontend-gateway 服务定义
echo "🔍 查找 frontend-gateway 服务定义："
FOUND_FILES=$(find . -name "docker-compose*.yml" -o -name "docker-compose*.yaml" 2>/dev/null | xargs grep -l "frontend-gateway" 2>/dev/null || echo "")
if [ -n "$FOUND_FILES" ]; then
    echo -e "  ${GREEN}✅ 找到以下文件包含 frontend-gateway：${NC}"
    echo "$FOUND_FILES" | while read -r file; do
        echo "    - $file"
    done
else
    echo -e "  ${YELLOW}⚠️  未找到包含 frontend-gateway 的 docker-compose 文件${NC}"
    echo "    提示：frontend-gateway 可能是 gRPC 服务，不是 Docker Compose 服务"
    echo "    如果确实需要 frontend-gateway 服务，请先创建 docker-compose 文件"
fi
echo ""

# 步骤 2：升级 buildx（如果需要）
if [ "$NEED_UPGRADE" = true ]; then
    echo -e "${BLUE}[2/4] 升级 buildx...${NC}"
    echo ""
    
    # 检测系统类型
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        OS="unknown"
    fi
    
    echo "检测到系统：$OS"
    echo ""
    
    # 方法 1：使用包管理器升级（推荐）
    if [ "$OS" = "centos" ] || [ "$OS" = "rhel" ] || [ "$OS" = "almalinux" ] || [ "$OS" = "alios" ]; then
        echo "使用 yum 升级 buildx..."
        if command -v sudo &> /dev/null; then
            sudo yum update -y docker-buildx-plugin 2>&1 || {
                echo -e "  ${YELLOW}⚠️  yum 升级失败，尝试手动安装...${NC}"
                MANUAL_INSTALL=true
            }
        else
            echo -e "  ${YELLOW}⚠️  需要 sudo 权限，尝试手动安装...${NC}"
            MANUAL_INSTALL=true
        fi
    elif [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
        echo "使用 apt 升级 buildx..."
        if command -v sudo &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y docker-buildx-plugin 2>&1 || {
                echo -e "  ${YELLOW}⚠️  apt 升级失败，尝试手动安装...${NC}"
                MANUAL_INSTALL=true
            }
        else
            echo -e "  ${YELLOW}⚠️  需要 sudo 权限，尝试手动安装...${NC}"
            MANUAL_INSTALL=true
        fi
    else
        echo -e "  ${YELLOW}⚠️  未知系统类型，使用手动安装...${NC}"
        MANUAL_INSTALL=true
    fi
    
    # 方法 2：手动安装最新版本
    if [ "$MANUAL_INSTALL" = true ]; then
        echo ""
        echo "手动安装 buildx 最新版本..."
        
        # 创建插件目录
        mkdir -p ~/.docker/cli-plugins
        
        # 检测架构
        ARCH=$(uname -m)
        case $ARCH in
            x86_64)
                BUILDX_ARCH="linux-amd64"
                ;;
            aarch64|arm64)
                BUILDX_ARCH="linux-arm64"
                ;;
            *)
                echo -e "  ${RED}❌ 不支持的架构：$ARCH${NC}"
                exit 1
                ;;
        esac
        
        # 下载最新版本
        BUILDX_VERSION_LATEST="v0.17.0"  # 使用固定版本确保兼容性
        BUILDX_URL="https://github.com/docker/buildx/releases/download/${BUILDX_VERSION_LATEST}/buildx-${BUILDX_VERSION_LATEST}-${BUILDX_ARCH}"
        
        echo "下载 buildx ${BUILDX_VERSION_LATEST} for ${BUILDX_ARCH}..."
        curl -L "$BUILDX_URL" -o ~/.docker/cli-plugins/docker-buildx || {
            echo -e "  ${RED}❌ 下载失败${NC}"
            exit 1
        }
        
        chmod +x ~/.docker/cli-plugins/docker-buildx
        
        echo -e "  ${GREEN}✅ buildx 手动安装完成${NC}"
    fi
    
    # 验证安装
    echo ""
    echo "验证 buildx 版本："
    NEW_VERSION=$(docker buildx version 2>/dev/null | head -n1 || echo "")
    if [ -n "$NEW_VERSION" ]; then
        echo -e "  ${GREEN}✅ $NEW_VERSION${NC}"
    else
        echo -e "  ${RED}❌ buildx 安装失败${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${BLUE}[2/4] 跳过升级（buildx 版本已满足要求）${NC}"
    echo ""
fi

# 步骤 3：检查 frontend-gateway 服务
echo -e "${BLUE}[3/4] 检查 frontend-gateway 服务...${NC}"
echo ""

if [ -n "$FOUND_FILES" ]; then
    echo "检查服务定义..."
    for file in $FOUND_FILES; do
        echo "文件：$file"
        if grep -q "build:" "$file"; then
            echo -e "  ${YELLOW}⚠️  服务包含 build 配置，需要构建${NC}"
            echo "  如果不需要构建，可以："
            echo "    1. 使用预构建镜像（image: 字段）"
            echo "    2. 使用 --no-build 标志：docker-compose up -d --no-build frontend-gateway"
        else
            echo -e "  ${GREEN}✅ 服务使用预构建镜像，无需构建${NC}"
        fi
    done
else
    echo -e "  ${YELLOW}⚠️  未找到 frontend-gateway 服务定义${NC}"
    echo ""
    echo "可能的原因："
    echo "  1. frontend-gateway 是 gRPC 服务，不是 Docker Compose 服务"
    echo "  2. 服务定义在其他位置或使用其他名称"
    echo "  3. 需要创建新的 docker-compose 文件"
    echo ""
    echo "建议："
    echo "  - 如果 frontend-gateway 是 gRPC 服务，应该通过主服务访问"
    echo "  - 如果需要独立的 Docker 服务，请创建 docker-compose 文件"
fi
echo ""

# 步骤 4：验证修复
echo -e "${BLUE}[4/4] 验证修复...${NC}"
echo ""

# 再次检查 buildx 版本
FINAL_VERSION=$(docker buildx version 2>/dev/null | head -n1 || echo "")
if [ -n "$FINAL_VERSION" ]; then
    VERSION_NUM=$(echo "$FINAL_VERSION" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1 || echo "")
    if [ -n "$VERSION_NUM" ]; then
        MAJOR=$(echo "$VERSION_NUM" | cut -d. -f1)
        MINOR=$(echo "$VERSION_NUM" | cut -d. -f2)
        if [ "$MAJOR" -lt 0 ] || ([ "$MAJOR" -eq 0 ] && [ "$MINOR" -lt 17 ]); then
            echo -e "  ${RED}❌ buildx 版本仍然低于 0.17.0${NC}"
            echo "  请手动升级或联系管理员"
            exit 1
        else
            echo -e "  ${GREEN}✅ buildx 版本 $VERSION_NUM 满足要求${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️  无法验证版本，但 buildx 已安装${NC}"
    fi
else
    echo -e "  ${RED}❌ buildx 未安装或无法访问${NC}"
    exit 1
fi
echo ""

# 测试 Docker Compose 构建（如果可能）
if [ -n "$FOUND_FILES" ]; then
    echo "测试 Docker Compose 构建..."
    FIRST_FILE=$(echo "$FOUND_FILES" | head -n1)
    if docker-compose -f "$FIRST_FILE" config > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Docker Compose 配置有效${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Docker Compose 配置可能有误${NC}"
    fi
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ 修复完成${NC}"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 如果 frontend-gateway 服务存在，可以尝试："
echo "     docker-compose up -d frontend-gateway"
echo ""
echo "  2. 如果不需要构建，使用："
echo "     docker-compose up -d --no-build frontend-gateway"
echo ""
echo "  3. 如果 frontend-gateway 是 gRPC 服务，应该通过主服务访问"
echo ""

