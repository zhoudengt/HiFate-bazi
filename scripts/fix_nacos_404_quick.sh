#!/bin/bash
# 快速修复 Nacos 404 错误
# 用途：直接在服务器上添加配置并重启 Nginx

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 服务器配置
NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
NGINX_CONTAINER="hifate-nginx"
NGINX_CONF="$PROJECT_DIR/deploy/nginx/conf.d/hifate.conf"

# Nacos 配置内容
NACOS_CONFIG='
    # Nacos 配置中心代理（必须在 / 之前，避免被静态文件匹配）
    location /nacos {
        proxy_pass http://172.17.0.1:9060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（Nacos 需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 禁用缓冲（实时更新）
        proxy_buffering off;
    }
'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}快速修复 Nacos 404 错误${NC}"
echo -e "${BLUE}========================================${NC}"

# 函数：在服务器上执行命令
ssh_exec_root() {
    local node_ip=$1
    shift
    ssh -o StrictHostKeyChecking=no root@$node_ip "$@"
}

# 函数：修复单个节点
fix_node() {
    local node_ip=$1
    local node_name=$2
    
    echo -e "\n${YELLOW}修复 $node_name ($node_ip)...${NC}"
    
    # 1. 检查配置文件是否存在
    if ! ssh_exec_root $node_ip "test -f $NGINX_CONF"; then
        echo -e "${RED}✗ 配置文件不存在: $NGINX_CONF${NC}"
        return 1
    fi
    
    # 2. 检查是否已包含 Nacos 配置
    if ssh_exec_root $node_ip "grep -q 'location /nacos' $NGINX_CONF"; then
        echo -e "${YELLOW}⚠ 配置文件中已包含 Nacos 配置，跳过添加${NC}"
    else
        echo -e "${BLUE}添加 Nacos 配置...${NC}"
        
        # 找到 location / 的位置，在其之前插入配置
        ssh_exec_root $node_ip "sed -i '/# 本地前端静态文件/i\\$NACOS_CONFIG' $NGINX_CONF" || {
            # 如果 sed 失败，使用更安全的方法
            echo -e "${YELLOW}使用备用方法添加配置...${NC}"
            ssh_exec_root $node_ip "cat > /tmp/nacos_config.txt << 'EOF'
$NACOS_CONFIG
EOF
            # 找到 location / 的行号
            LINE_NUM=\$(grep -n 'location / {' $NGINX_CONF | head -1 | cut -d: -f1)
            # 在 location / 之前插入配置
            sed -i \"\${LINE_NUM}i\\$(cat /tmp/nacos_config.txt | sed 's/\$/\\\\\$/g')\" $NGINX_CONF
            rm -f /tmp/nacos_config.txt"
        }
        
        echo -e "${GREEN}✓ 配置已添加${NC}"
    fi
    
    # 3. 验证配置语法
    echo -e "${BLUE}验证配置语法...${NC}"
    if ssh_exec_root $node_ip "docker exec $NGINX_CONTAINER nginx -t 2>&1"; then
        echo -e "${GREEN}✓ 配置语法验证通过${NC}"
    else
        echo -e "${RED}✗ 配置语法验证失败${NC}"
        return 1
    fi
    
    # 4. 重启 Nginx 容器
    echo -e "${BLUE}重启 Nginx 容器...${NC}"
    if ssh_exec_root $node_ip "docker restart $NGINX_CONTAINER"; then
        echo -e "${GREEN}✓ Nginx 容器重启成功${NC}"
    else
        echo -e "${RED}✗ Nginx 容器重启失败${NC}"
        return 1
    fi
    
    # 5. 等待容器启动
    echo -e "${BLUE}等待容器启动...${NC}"
    sleep 3
    
    # 6. 测试访问
    echo -e "${BLUE}测试访问...${NC}"
    local http_code=$(curl -s -o /dev/null -w '%{http_code}' "http://$node_ip/nacos/index.html" || echo "000")
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ 访问成功 (HTTP $http_code)${NC}"
    elif [ "$http_code" = "302" ] || [ "$http_code" = "301" ]; then
        echo -e "${GREEN}✓ 访问成功 (HTTP $http_code - 重定向)${NC}"
    else
        echo -e "${YELLOW}⚠ 访问返回 HTTP $http_code${NC}"
        echo -e "${YELLOW}提示：请检查 Nacos 服务是否在运行（端口 9060）${NC}"
    fi
    
    echo -e "${GREEN}✓ $node_name 修复完成${NC}"
}

# 主流程
echo -e "\n${YELLOW}开始修复...${NC}"

# 修复 Node1
fix_node $NODE1_IP "Node1"

# 修复 Node2
fix_node $NODE2_IP "Node2"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}修复完成${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n测试访问："
echo -e "  Node1: http://$NODE1_IP/nacos/index.html"
echo -e "  Node2: http://$NODE2_IP/nacos/index.html"

