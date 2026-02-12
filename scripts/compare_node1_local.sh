#!/bin/bash
# 比较 Node1 与本地代码（只比较，不修改）
# 用途：检查代码差异，不执行任何同步操作

set -e

NODE1_IP="8.210.52.217"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
PROJECT_DIR="/opt/HiFate-bazi"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "🔍 Node1 与本地代码比较（只比较，不修改）"
echo "========================================"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"
echo ""

# SSH 执行函数
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd" 2>/dev/null || echo ""
    else
        ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd" 2>/dev/null || echo ""
    fi
}

# 1. Git 版本比较
echo -e "${BLUE}【1】Git 版本比较${NC}"
echo "----------------------------------------"

LOCAL_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "")
LOCAL_COMMIT_MSG=$(git log -1 --format='%s' 2>/dev/null || echo "")
NODE1_COMMIT=$(ssh_exec $NODE1_IP "cd $PROJECT_DIR && git rev-parse HEAD 2>/dev/null" || echo "")
NODE1_COMMIT_MSG=$(ssh_exec $NODE1_IP "cd $PROJECT_DIR && git log -1 --format='%s' 2>/dev/null" || echo "")

echo "本地 Git 版本："
if [ -n "$LOCAL_COMMIT" ]; then
    echo "  Commit: ${LOCAL_COMMIT:0:8}"
    echo "  提交信息: $LOCAL_COMMIT_MSG"
else
    echo "  ${RED}无法获取本地 Git 版本${NC}"
fi

echo ""
echo "Node1 Git 版本："
if [ -n "$NODE1_COMMIT" ]; then
    echo "  Commit: ${NODE1_COMMIT:0:8}"
    echo "  提交信息: $NODE1_COMMIT_MSG"
else
    echo "  ${RED}无法获取 Node1 Git 版本${NC}"
fi

echo ""
if [ -n "$LOCAL_COMMIT" ] && [ -n "$NODE1_COMMIT" ]; then
    if [ "$LOCAL_COMMIT" = "$NODE1_COMMIT" ]; then
        echo -e "${GREEN}✅ Git 版本一致${NC}"
    else
        echo -e "${RED}❌ Git 版本不一致${NC}"
        echo ""
        echo "差异分析："
        # 检查本地是否有 Node1 的提交
        if git log --oneline | grep -q "${NODE1_COMMIT:0:8}"; then
            echo "  - 本地包含 Node1 的提交"
        else
            echo "  - 本地不包含 Node1 的提交"
        fi
        # 检查 Node1 是否有本地的提交
        NODE1_HAS_LOCAL=$(ssh_exec $NODE1_IP "cd $PROJECT_DIR && git log --oneline | grep -q '${LOCAL_COMMIT:0:8}' && echo 'yes' || echo 'no'")
        if [ "$NODE1_HAS_LOCAL" = "yes" ]; then
            echo "  - Node1 包含本地的提交"
        else
            echo "  - Node1 不包含本地的提交"
        fi
    fi
fi

echo ""
echo ""

# 2. 关键文件比较
echo -e "${BLUE}【2】关键文件比较${NC}"
echo "----------------------------------------"

# 关键文件列表
KEY_FILES=(
    "server/api/grpc_gateway.py"
    "server/api/v2/desk_fengshui_api.py"
    "deploy/docker/docker-compose.prod.yml"
    "requirements.txt"
    "proto/generated/bazi_core_pb2_grpc.py"
)

for file in "${KEY_FILES[@]}"; do
    echo ""
    echo "📄 文件: $file"
    
    # 检查本地文件
    if [ ! -f "$file" ]; then
        echo "  ${RED}本地文件不存在${NC}"
        continue
    fi
    
    # 检查 Node1 文件
    NODE1_EXISTS=$(ssh_exec $NODE1_IP "test -f $PROJECT_DIR/$file && echo 'yes' || echo 'no'")
    if [ "$NODE1_EXISTS" != "yes" ]; then
        echo "  ${RED}Node1 文件不存在${NC}"
        continue
    fi
    
    # 计算文件哈希
    LOCAL_HASH=$(md5 -q "$file" 2>/dev/null || md5sum "$file" 2>/dev/null | cut -d' ' -f1)
    NODE1_HASH=$(ssh_exec $NODE1_IP "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
    
    if [ -z "$NODE1_HASH" ]; then
        echo "  ${RED}无法获取 Node1 文件哈希${NC}"
        continue
    fi
    
    if [ "$LOCAL_HASH" = "$NODE1_HASH" ]; then
        echo -e "  ${GREEN}✅ 文件内容一致${NC} (哈希: ${LOCAL_HASH:0:8}...)"
    else
        echo -e "  ${RED}❌ 文件内容不一致${NC}"
        echo "    本地哈希: ${LOCAL_HASH:0:16}..."
        echo "    Node1哈希: ${NODE1_HASH:0:16}..."
        
        # 显示差异行数（前10行）
        echo "    差异预览（前10行）："
        LOCAL_LINES=$(wc -l < "$file" 2>/dev/null || echo "0")
        NODE1_LINES=$(ssh_exec $NODE1_IP "wc -l < $PROJECT_DIR/$file 2>/dev/null" | tr -d ' ' || echo "0")
        echo "      本地行数: $LOCAL_LINES"
        echo "      Node1行数: $NODE1_LINES"
    fi
done

echo ""
echo ""

# 3. 关键内容检查
echo -e "${BLUE}【3】关键内容检查${NC}"
echo "----------------------------------------"

# 3.1 硬编码路径检查
echo ""
echo "🔍 硬编码路径检查（/Users/zhoudt）"
LOCAL_HARDCODED=$(grep -r "/Users/zhoudt" server/api/grpc_gateway.py server/api/v2/desk_fengshui_api.py 2>/dev/null | wc -l | tr -d ' ' || echo "0")
NODE1_HARDCODED=$(ssh_exec $NODE1_IP "grep -r '/Users/zhoudt' $PROJECT_DIR/server/api/grpc_gateway.py $PROJECT_DIR/server/api/v2/desk_fengshui_api.py 2>/dev/null | wc -l" | tr -d ' ' || echo "0")

echo "  本地: $LOCAL_HARDCODED 个（应为0）"
echo "  Node1: $NODE1_HARDCODED 个（应为0）"
if [ "$LOCAL_HARDCODED" = "0" ] && [ "$NODE1_HARDCODED" = "0" ]; then
    echo -e "  ${GREEN}✅ 一致（无硬编码路径）${NC}"
elif [ "$LOCAL_HARDCODED" = "$NODE1_HARDCODED" ]; then
    echo -e "  ${YELLOW}⚠️  一致（但都有硬编码路径）${NC}"
else
    echo -e "  ${RED}❌ 不一致${NC}"
fi

# 3.2 gRPC 兼容性检查
echo ""
echo "🔍 gRPC 兼容性检查（add_registered_method_handlers）"
LOCAL_GRPC=$(grep -r "add_registered_method_handlers" proto/generated/*_pb2_grpc.py 2>/dev/null | wc -l | tr -d ' ' || echo "0")
NODE1_GRPC=$(ssh_exec $NODE1_IP "grep -r 'add_registered_method_handlers' $PROJECT_DIR/proto/generated/*_pb2_grpc.py 2>/dev/null | wc -l" | tr -d ' ' || echo "0")

echo "  本地: $LOCAL_GRPC 个（应为0）"
echo "  Node1: $NODE1_GRPC 个（应为0）"
if [ "$LOCAL_GRPC" = "0" ] && [ "$NODE1_GRPC" = "0" ]; then
    echo -e "  ${GREEN}✅ 一致（无兼容性问题）${NC}"
elif [ "$LOCAL_GRPC" = "$NODE1_GRPC" ]; then
    echo -e "  ${YELLOW}⚠️  一致（但都有兼容性问题）${NC}"
else
    echo -e "  ${RED}❌ 不一致${NC}"
fi

# 3.3 容器挂载配置检查
echo ""
echo "🔍 容器挂载配置检查（proto:/app/proto）"
LOCAL_MOUNT=$(grep -c "proto:/app/proto" deploy/docker/docker-compose.prod.yml 2>/dev/null || echo "0")
NODE1_MOUNT=$(ssh_exec $NODE1_IP "grep -c 'proto:/app/proto' $PROJECT_DIR/deploy/docker/docker-compose.prod.yml 2>/dev/null" | tr -d ' ' || echo "0")

echo "  本地: $LOCAL_MOUNT 个（应为10）"
echo "  Node1: $NODE1_MOUNT 个（应为10）"
if [ "$LOCAL_MOUNT" = "$NODE1_MOUNT" ]; then
    if [ "$LOCAL_MOUNT" = "10" ]; then
        echo -e "  ${GREEN}✅ 一致（配置正确）${NC}"
    else
        echo -e "  ${YELLOW}⚠️  一致（但配置可能不完整）${NC}"
    fi
else
    echo -e "  ${RED}❌ 不一致${NC}"
fi

echo ""
echo ""

# 4. Git 提交历史比较
echo -e "${BLUE}【4】Git 提交历史比较${NC}"
echo "----------------------------------------"

echo "本地最近 5 次提交："
git log --oneline -5 2>/dev/null || echo "  无法获取本地提交历史"

echo ""
echo "Node1 最近 5 次提交："
ssh_exec $NODE1_IP "cd $PROJECT_DIR && git log --oneline -5 2>/dev/null" || echo "  无法获取 Node1 提交历史"

echo ""
echo ""

# 5. 未提交更改检查
echo -e "${BLUE}【5】未提交更改检查${NC}"
echo "----------------------------------------"

echo "本地未提交更改："
LOCAL_CHANGES=$(git status --short 2>/dev/null || echo "")
if [ -z "$LOCAL_CHANGES" ]; then
    echo -e "  ${GREEN}✅ 无未提交更改${NC}"
else
    echo -e "  ${YELLOW}⚠️  有未提交更改：${NC}"
    echo "$LOCAL_CHANGES" | head -10 | sed 's/^/    /'
fi

echo ""
echo "Node1 未提交更改："
NODE1_CHANGES=$(ssh_exec $NODE1_IP "cd $PROJECT_DIR && git status --short 2>/dev/null" || echo "")
if [ -z "$NODE1_CHANGES" ]; then
    echo -e "  ${GREEN}✅ 无未提交更改${NC}"
else
    echo -e "  ${YELLOW}⚠️  有未提交更改：${NC}"
    echo "$NODE1_CHANGES" | head -10 | sed 's/^/    /'
fi

echo ""
echo ""

# 6. 总结
echo "========================================"
echo "📊 比较结果总结"
echo "========================================"

DIFF_COUNT=0

# 统计差异
if [ -n "$LOCAL_COMMIT" ] && [ -n "$NODE1_COMMIT" ] && [ "$LOCAL_COMMIT" != "$NODE1_COMMIT" ]; then
    DIFF_COUNT=$((DIFF_COUNT + 1))
    echo -e "${RED}❌ Git 版本不一致${NC}"
fi

for file in "${KEY_FILES[@]}"; do
    if [ -f "$file" ]; then
        LOCAL_HASH=$(md5 -q "$file" 2>/dev/null || md5sum "$file" 2>/dev/null | cut -d' ' -f1)
        NODE1_HASH=$(ssh_exec $NODE1_IP "md5sum $PROJECT_DIR/$file 2>/dev/null | cut -d' ' -f1" || echo "")
        if [ -n "$NODE1_HASH" ] && [ "$LOCAL_HASH" != "$NODE1_HASH" ]; then
            DIFF_COUNT=$((DIFF_COUNT + 1))
        fi
    fi
done

if [ "$DIFF_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查项一致，代码完全一致！${NC}"
else
    echo -e "${YELLOW}⚠️  发现 $DIFF_COUNT 处差异${NC}"
    echo ""
    echo "建议："
    echo "  1. 检查差异原因"
    echo "  2. 如需同步，使用增量部署脚本："
    echo "     bash deploy/scripts/incremental_deploy_production.sh"
    echo "  3. 或手动同步："
    echo "     ssh root@$NODE1_IP 'cd $PROJECT_DIR && git pull origin master'"
fi

echo ""
echo "========================================"
echo "✅ 比较完成（未执行任何修改）"
echo "========================================"

