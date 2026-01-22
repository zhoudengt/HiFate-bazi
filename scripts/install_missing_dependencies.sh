#!/bin/bash
# 在运行中的 Docker 容器内安装缺失的依赖包
# 用于紧急修复依赖问题，无需重启服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== 在容器内安装缺失的依赖包 ===${NC}"

# 检测容器名称（自动检测）
CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "(hifate|bazi|web)" | head -n 1)

if [ -z "$CONTAINER_NAME" ]; then
    echo -e "${RED}❌ 错误：未找到运行中的容器${NC}"
    echo "请手动指定容器名称："
    echo "  $0 <container_name>"
    exit 1
fi

echo -e "${GREEN}✅ 找到容器: ${CONTAINER_NAME}${NC}"

# 要安装的包列表（从 requirements.txt 中提取支付相关依赖）
PACKAGES=(
    "stripe>=7.0.0"
    "alipay-sdk-python>=3.7.0"
    "wechatpy>=1.8.0"
)

echo -e "${YELLOW}准备安装以下包：${NC}"
for pkg in "${PACKAGES[@]}"; do
    echo "  - $pkg"
done

# 在容器内安装
echo -e "\n${YELLOW}正在容器内安装依赖...${NC}"
for pkg in "${PACKAGES[@]}"; do
    echo -e "${YELLOW}安装: $pkg${NC}"
    docker exec -it "$CONTAINER_NAME" pip install --no-cache-dir "$pkg" || {
        echo -e "${RED}❌ 安装 $pkg 失败，尝试使用国内镜像源...${NC}"
        docker exec -it "$CONTAINER_NAME" pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple "$pkg" || {
            echo -e "${RED}❌ 安装 $pkg 失败（使用国内源）${NC}"
        }
    }
done

# 验证安装
echo -e "\n${YELLOW}验证安装结果...${NC}"
docker exec -it "$CONTAINER_NAME" python -c "import stripe; print('✅ stripe:', stripe.__version__)" 2>/dev/null && \
    echo -e "${GREEN}✅ stripe 安装成功${NC}" || \
    echo -e "${RED}❌ stripe 验证失败${NC}"

echo -e "\n${GREEN}=== 安装完成 ===${NC}"
echo -e "${YELLOW}注意：这是临时解决方案。建议重新构建 Docker 镜像以确保依赖完整。${NC}"
echo -e "${YELLOW}重新构建命令：${NC}"
echo "  docker build --platform linux/amd64 -t hifate-bazi:latest ."
