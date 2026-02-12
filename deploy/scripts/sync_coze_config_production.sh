#!/bin/bash
# 同步 Coze API 配置到生产环境双机
# 用途：将本地 Coze API 配置同步到 Node1 和 Node2 的 .env 文件
#
# 使用方法：
#   bash deploy/scripts/sync_coze_config_production.sh
#
# 配置来源：
#   - 本地 config/services.env 文件中的 COZE_ACCESS_TOKEN 和 COZE_BOT_ID
#   - 或从环境变量读取（如果已设置）

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 生产环境配置
NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
ENV_FILE="$PROJECT_DIR/.env"

# SSH 密码（从环境变量或默认值读取）
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"

# SSH 执行函数（支持密码登录）
ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    
    # 检查是否有 sshpass
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
    else
        # 如果没有 sshpass，尝试使用 expect（如果可用）
        if command -v expect &> /dev/null; then
            expect << EOF
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
expect {
    "password:" {
        send "$SSH_PASSWORD\r"
        exp_continue
    }
    eof
}
EOF
        else
            # 如果都没有，尝试直接 SSH（可能需要手动输入密码或已配置密钥）
            ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@$host "$cmd"
        fi
    fi
}

# 从本地配置文件读取 Coze 配置
read_coze_config() {
    local config_file="config/services.env"
    
    if [ -f "$config_file" ]; then
        # 从 config/services.env 读取
        source "$config_file" 2>/dev/null || true
        echo -e "${GREEN}✓ 从 $config_file 读取配置${NC}"
    else
        echo -e "${YELLOW}⚠️  本地配置文件 $config_file 不存在，使用环境变量${NC}"
    fi
    
    # 从环境变量读取（如果已设置）
    COZE_ACCESS_TOKEN="${COZE_ACCESS_TOKEN:-}"
    COZE_BOT_ID="${COZE_BOT_ID:-}"
    INTENT_BOT_ID="${INTENT_BOT_ID:-}"
    FORTUNE_ANALYSIS_BOT_ID="${FORTUNE_ANALYSIS_BOT_ID:-}"
    DAILY_FORTUNE_ACTION_BOT_ID="${DAILY_FORTUNE_ACTION_BOT_ID:-}"
    
    # 验证必需配置
    if [ -z "$COZE_ACCESS_TOKEN" ]; then
        echo -e "${RED}❌ 错误：COZE_ACCESS_TOKEN 未设置${NC}"
        echo "请设置环境变量或确保 config/services.env 文件包含 COZE_ACCESS_TOKEN"
        exit 1
    fi
    
    if [ -z "$COZE_BOT_ID" ]; then
        echo -e "${RED}❌ 错误：COZE_BOT_ID 未设置${NC}"
        echo "请设置环境变量或确保 config/services.env 文件包含 COZE_BOT_ID"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 配置读取成功${NC}"
    echo "  COZE_ACCESS_TOKEN: ${COZE_ACCESS_TOKEN:0:20}..."
    echo "  COZE_BOT_ID: $COZE_BOT_ID"
    if [ -n "$INTENT_BOT_ID" ]; then
        echo "  INTENT_BOT_ID: $INTENT_BOT_ID"
    fi
    if [ -n "$FORTUNE_ANALYSIS_BOT_ID" ]; then
        echo "  FORTUNE_ANALYSIS_BOT_ID: $FORTUNE_ANALYSIS_BOT_ID"
    fi
    if [ -n "$DAILY_FORTUNE_ACTION_BOT_ID" ]; then
        echo "  DAILY_FORTUNE_ACTION_BOT_ID: $DAILY_FORTUNE_ACTION_BOT_ID"
    fi
}

# 更新服务器 .env 文件
update_server_env() {
    local node_ip=$1
    local node_name=$2
    
    echo ""
    echo -e "${BLUE}📝 更新 $node_name 的 .env 文件...${NC}"
    
    # 备份原文件
    ssh_exec $node_ip "cd $PROJECT_DIR && cp .env .env.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true"
    
    # 读取现有 .env 文件（如果存在）
    local existing_env=$(ssh_exec $node_ip "cd $PROJECT_DIR && cat .env 2>/dev/null || echo ''")
    
    # 创建临时脚本更新 .env 文件
    ssh_exec $node_ip "cd $PROJECT_DIR && cat > /tmp/update_env.sh << 'ENVSCRIPT'
#!/bin/bash
# 更新 .env 文件中的 Coze 配置

ENV_FILE=\"$PROJECT_DIR/.env\"

# 如果文件不存在，从模板创建
if [ ! -f \"\$ENV_FILE\" ]; then
    if [ -f \"deploy/env/env.template\" ]; then
        cp deploy/env/env.template \"\$ENV_FILE\"
    else
        touch \"\$ENV_FILE\"
    fi
fi

# 更新或添加 Coze 配置
# 使用 sed 更新现有行或追加新行
if grep -q \"^COZE_ACCESS_TOKEN=\" \"\$ENV_FILE\" 2>/dev/null; then
    sed -i \"s|^COZE_ACCESS_TOKEN=.*|COZE_ACCESS_TOKEN=$COZE_ACCESS_TOKEN|\" \"\$ENV_FILE\"
else
    echo \"COZE_ACCESS_TOKEN=$COZE_ACCESS_TOKEN\" >> \"\$ENV_FILE\"
fi

if grep -q \"^COZE_BOT_ID=\" \"\$ENV_FILE\" 2>/dev/null; then
    sed -i \"s|^COZE_BOT_ID=.*|COZE_BOT_ID=$COZE_BOT_ID|\" \"\$ENV_FILE\"
else
    echo \"COZE_BOT_ID=$COZE_BOT_ID\" >> \"\$ENV_FILE\"
fi

# 更新其他 Bot ID（如果存在）
if [ -n \"$INTENT_BOT_ID\" ]; then
    if grep -q \"^INTENT_BOT_ID=\" \"\$ENV_FILE\" 2>/dev/null; then
        sed -i \"s|^INTENT_BOT_ID=.*|INTENT_BOT_ID=$INTENT_BOT_ID|\" \"\$ENV_FILE\"
    else
        echo \"INTENT_BOT_ID=$INTENT_BOT_ID\" >> \"\$ENV_FILE\"
    fi
fi

if [ -n \"$FORTUNE_ANALYSIS_BOT_ID\" ]; then
    if grep -q \"^FORTUNE_ANALYSIS_BOT_ID=\" \"\$ENV_FILE\" 2>/dev/null; then
        sed -i \"s|^FORTUNE_ANALYSIS_BOT_ID=.*|FORTUNE_ANALYSIS_BOT_ID=$FORTUNE_ANALYSIS_BOT_ID|\" \"\$ENV_FILE\"
    else
        echo \"FORTUNE_ANALYSIS_BOT_ID=$FORTUNE_ANALYSIS_BOT_ID\" >> \"\$ENV_FILE\"
    fi
fi

if [ -n \"$DAILY_FORTUNE_ACTION_BOT_ID\" ]; then
    if grep -q \"^DAILY_FORTUNE_ACTION_BOT_ID=\" \"\$ENV_FILE\" 2>/dev/null; then
        sed -i \"s|^DAILY_FORTUNE_ACTION_BOT_ID=.*|DAILY_FORTUNE_ACTION_BOT_ID=$DAILY_FORTUNE_ACTION_BOT_ID|\" \"\$ENV_FILE\"
    else
        echo \"DAILY_FORTUNE_ACTION_BOT_ID=$DAILY_FORTUNE_ACTION_BOT_ID\" >> \"\$ENV_FILE\"
    fi
fi

echo \"✅ .env 文件已更新\"
ENVSCRIPT
chmod +x /tmp/update_env.sh && /tmp/update_env.sh && rm /tmp/update_env.sh"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $node_name .env 文件更新成功${NC}"
        
        # 验证配置
        echo "🔍 验证配置..."
        local token_check=$(ssh_exec $node_ip "cd $PROJECT_DIR && grep '^COZE_ACCESS_TOKEN=' .env | cut -d'=' -f2 | head -c 20")
        local bot_id_check=$(ssh_exec $node_ip "cd $PROJECT_DIR && grep '^COZE_BOT_ID=' .env | cut -d'=' -f2")
        
        if [ -n "$token_check" ] && [ -n "$bot_id_check" ]; then
            echo -e "${GREEN}✓ 配置验证通过${NC}"
            echo "  COZE_ACCESS_TOKEN: ${token_check}..."
            echo "  COZE_BOT_ID: $bot_id_check"
        else
            echo -e "${YELLOW}⚠️  配置验证失败，请手动检查${NC}"
        fi
    else
        echo -e "${RED}❌ $node_name .env 文件更新失败${NC}"
        return 1
    fi
}

# 重启容器以应用新配置（可选）
restart_containers() {
    local node_ip=$1
    local node_name=$2
    
    echo ""
    echo -e "${YELLOW}⚠️  需要重启容器以应用新配置${NC}"
    echo "是否重启 $node_name 的容器？(y/n)"
    read -t 10 -n 1 answer || answer="n"
    echo ""
    
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        echo "🔄 重启 $node_name 容器..."
        ssh_exec $node_ip "cd $PROJECT_DIR/deploy/docker && \
            source $PROJECT_DIR/.env && \
            docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file $PROJECT_DIR/.env restart web 2>/dev/null || \
            docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml --env-file $PROJECT_DIR/.env restart web 2>/dev/null || \
            echo '⚠️  容器重启失败，请手动重启'"
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ $node_name 容器重启成功${NC}"
        else
            echo -e "${YELLOW}⚠️  $node_name 容器重启失败，请手动重启${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  跳过容器重启，请稍后手动重启以应用新配置${NC}"
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "🔄 同步 Coze API 配置到生产环境"
    echo "========================================"
    echo ""
    
    # 1. 读取本地配置
    echo -e "${BLUE}📋 第一步：读取本地配置${NC}"
    echo "----------------------------------------"
    read_coze_config
    
    # 2. 更新 Node1
    echo ""
    echo -e "${BLUE}📋 第二步：更新 Node1 配置${NC}"
    echo "----------------------------------------"
    update_server_env "$NODE1_PUBLIC_IP" "Node1"
    
    # 3. 更新 Node2
    echo ""
    echo -e "${BLUE}📋 第三步：更新 Node2 配置${NC}"
    echo "----------------------------------------"
    update_server_env "$NODE2_PUBLIC_IP" "Node2"
    
    # 4. 提示重启容器
    echo ""
    echo -e "${BLUE}📋 第四步：应用配置（需要重启容器）${NC}"
    echo "----------------------------------------"
    echo -e "${YELLOW}⚠️  配置已更新，但需要重启容器才能生效${NC}"
    echo ""
    echo "重启命令："
    echo "  Node1: ssh root@$NODE1_PUBLIC_IP 'cd $PROJECT_DIR/deploy/docker && docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml --env-file $PROJECT_DIR/.env restart web'"
    echo "  Node2: ssh root@$NODE2_PUBLIC_IP 'cd $PROJECT_DIR/deploy/docker && docker-compose -f docker-compose.prod.yml -f docker-compose.node2.yml --env-file $PROJECT_DIR/.env restart web'"
    echo ""
    echo -e "${GREEN}✅ Coze API 配置同步完成${NC}"
}

# 执行主函数
main

