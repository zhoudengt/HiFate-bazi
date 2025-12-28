#!/bin/bash
# Nacos 404 错误诊断脚本
# 用途：诊断为什么 Nacos 访问返回 404

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服务器配置
NODE1_IP="8.210.52.217"
NODE2_IP="47.243.160.43"
PROJECT_DIR="/opt/HiFate-bazi"
NGINX_CONTAINER="hifate-nginx"
NGINX_CONF="$PROJECT_DIR/deploy/nginx/conf.d/hifate.conf"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Nacos 404 错误诊断${NC}"
echo -e "${BLUE}========================================${NC}"

# 函数：在服务器上执行命令
ssh_exec_root() {
    local node_ip=$1
    shift
    ssh -o StrictHostKeyChecking=no root@$node_ip "$@"
}

# 函数：诊断单个节点
diagnose_node() {
    local node_ip=$1
    local node_name=$2
    
    echo -e "\n${YELLOW}诊断 $node_name ($node_ip)...${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
    
    # 1. 检查配置文件是否存在
    echo -e "\n${BLUE}1. 检查配置文件...${NC}"
    if ssh_exec_root $node_ip "test -f $NGINX_CONF"; then
        echo -e "${GREEN}✓ 配置文件存在${NC}"
    else
        echo -e "${RED}✗ 配置文件不存在: $NGINX_CONF${NC}"
        echo -e "${YELLOW}提示：需要先拉取代码${NC}"
        return 1
    fi
    
    # 2. 检查是否包含 Nacos 配置
    echo -e "\n${BLUE}2. 检查 Nacos 配置...${NC}"
    if ssh_exec_root $node_ip "grep -q 'location /nacos' $NGINX_CONF"; then
        echo -e "${GREEN}✓ 配置文件中包含 Nacos 配置${NC}"
        echo -e "${YELLOW}配置内容：${NC}"
        ssh_exec_root $node_ip "grep -A 20 'location /nacos' $NGINX_CONF | head -25"
    else
        echo -e "${RED}✗ 配置文件中未找到 Nacos 配置${NC}"
        echo -e "${YELLOW}提示：需要先提交代码并推送到 GitHub，然后在服务器上拉取${NC}"
        return 1
    fi
    
    # 3. 检查配置位置（是否在 location / 之前）
    echo -e "\n${BLUE}3. 检查配置位置...${NC}"
    local nacos_line=$(ssh_exec_root $node_ip "grep -n 'location /nacos' $NGINX_CONF | cut -d: -f1")
    local root_line=$(ssh_exec_root $node_ip "grep -n 'location / {' $NGINX_CONF | head -1 | cut -d: -f1")
    
    if [ -n "$nacos_line" ] && [ -n "$root_line" ] && [ "$nacos_line" -lt "$root_line" ]; then
        echo -e "${GREEN}✓ 配置位置正确（在 location / 之前）${NC}"
        echo -e "  Nacos 配置行号: $nacos_line"
        echo -e "  location / 行号: $root_line"
    else
        echo -e "${RED}✗ 配置位置可能有问题${NC}"
        echo -e "  Nacos 配置行号: $nacos_line"
        echo -e "  location / 行号: $root_line"
    fi
    
    # 4. 验证 Nginx 配置语法
    echo -e "\n${BLUE}4. 验证 Nginx 配置语法...${NC}"
    if ssh_exec_root $node_ip "docker exec $NGINX_CONTAINER nginx -t 2>&1"; then
        echo -e "${GREEN}✓ 配置语法验证通过${NC}"
    else
        echo -e "${RED}✗ 配置语法验证失败${NC}"
        return 1
    fi
    
    # 5. 检查 Nginx 容器状态
    echo -e "\n${BLUE}5. 检查 Nginx 容器状态...${NC}"
    if ssh_exec_root $node_ip "docker ps | grep -q $NGINX_CONTAINER"; then
        echo -e "${GREEN}✓ Nginx 容器正在运行${NC}"
        ssh_exec_root $node_ip "docker ps | grep $NGINX_CONTAINER"
    else
        echo -e "${RED}✗ Nginx 容器未运行${NC}"
        return 1
    fi
    
    # 6. 检查 Nacos 服务是否在宿主机上运行
    echo -e "\n${BLUE}6. 检查 Nacos 服务状态...${NC}"
    local nacos_status=$(ssh_exec_root $node_ip "netstat -tlnp 2>/dev/null | grep ':9060' || ss -tlnp 2>/dev/null | grep ':9060' || echo 'not_found'")
    
    if echo "$nacos_status" | grep -q "9060"; then
        echo -e "${GREEN}✓ Nacos 服务正在运行（端口 9060）${NC}"
        echo -e "${YELLOW}服务信息：${NC}"
        echo "$nacos_status"
    else
        echo -e "${RED}✗ Nacos 服务未运行（端口 9060 未监听）${NC}"
        echo -e "${YELLOW}提示：需要启动 Nacos 服务${NC}"
    fi
    
    # 7. 检查 Docker 网络网关
    echo -e "\n${BLUE}7. 检查 Docker 网络配置...${NC}"
    local docker_gateway=$(ssh_exec_root $node_ip "docker network inspect bridge 2>/dev/null | grep Gateway | head -1 | cut -d: -f2 | tr -d '\" ,' || ip route | grep default | awk '{print \$3}' | head -1")
    
    if [ -n "$docker_gateway" ]; then
        echo -e "${GREEN}✓ Docker 网关: $docker_gateway${NC}"
        echo -e "${YELLOW}提示：配置中使用 172.17.0.1，实际网关是 $docker_gateway${NC}"
        
        if [ "$docker_gateway" != "172.17.0.1" ]; then
            echo -e "${YELLOW}⚠ 网关地址不匹配，可能需要修改配置${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ 无法获取 Docker 网关信息${NC}"
    fi
    
    # 8. 测试从容器内访问 Nacos
    echo -e "\n${BLUE}8. 测试从容器内访问 Nacos...${NC}"
    local test_result=$(ssh_exec_root $node_ip "docker exec $NGINX_CONTAINER wget -q -O- --timeout=5 http://172.17.0.1:9060/nacos/index.html 2>&1 | head -20 || echo 'connection_failed'")
    
    if echo "$test_result" | grep -q "connection_failed\|Connection refused\|timeout"; then
        echo -e "${RED}✗ 无法从容器内访问 Nacos (172.17.0.1:9060)${NC}"
        echo -e "${YELLOW}测试结果：${NC}"
        echo "$test_result"
        echo -e "${YELLOW}提示：可能需要修改代理地址${NC}"
    elif echo "$test_result" | grep -q "html\|nacos"; then
        echo -e "${GREEN}✓ 可以从容器内访问 Nacos${NC}"
    else
        echo -e "${YELLOW}⚠ 测试结果不确定${NC}"
        echo "$test_result"
    fi
    
    # 9. 检查 Nginx 日志
    echo -e "\n${BLUE}9. 检查 Nginx 错误日志（最近 10 行）...${NC}"
    ssh_exec_root $node_ip "docker logs $NGINX_CONTAINER --tail 10 2>&1 | grep -i 'nacos\|error\|404' || echo '无相关日志'"
    
    # 10. 测试外部访问
    echo -e "\n${BLUE}10. 测试外部访问...${NC}"
    local http_code=$(curl -s -o /dev/null -w '%{http_code}' "http://$node_ip/nacos/index.html" || echo "000")
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ 外部访问成功 (HTTP $http_code)${NC}"
    elif [ "$http_code" = "302" ] || [ "$http_code" = "301" ]; then
        echo -e "${GREEN}✓ 外部访问成功 (HTTP $http_code - 重定向)${NC}"
    elif [ "$http_code" = "404" ]; then
        echo -e "${RED}✗ 外部访问返回 404${NC}"
    else
        echo -e "${YELLOW}⚠ 外部访问返回 HTTP $http_code${NC}"
    fi
    
    echo -e "\n${YELLOW}----------------------------------------${NC}"
}

# 主流程
echo -e "\n${YELLOW}开始诊断...${NC}"

# 诊断 Node1
diagnose_node $NODE1_IP "Node1"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}诊断完成${NC}"
echo -e "${BLUE}========================================${NC}"

echo -e "\n${YELLOW}常见问题解决方案：${NC}"
echo -e "1. 如果配置未部署："
echo -e "   git pull origin master"
echo -e ""
echo -e "2. 如果 Nacos 服务未运行："
echo -e "   检查 Nacos 服务状态并启动"
echo -e ""
echo -e "3. 如果 Docker 网关不匹配："
echo -e "   修改配置中的 172.17.0.1 为实际网关地址"
echo -e "   或使用 host.docker.internal:9060（Docker 20.10+）"
echo -e ""
echo -e "4. 如果配置语法错误："
echo -e "   检查配置文件并修复语法错误"

