#!/bin/bash
# 快速检查端口冲突脚本

echo "=========================================="
echo "端口冲突检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 80 端口占用
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. 检查 80 端口占用情况"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PORT_80_INFO=""
if command -v ss >/dev/null 2>&1; then
    PORT_80_INFO=$(sudo ss -tlnp | grep ":80 " 2>/dev/null || echo "")
elif command -v netstat >/dev/null 2>&1; then
    PORT_80_INFO=$(sudo netstat -tlnp | grep ":80 " 2>/dev/null || echo "")
fi

if [ -z "$PORT_80_INFO" ]; then
    echo -e "${GREEN}✅ 80 端口未被占用${NC}"
else
    echo -e "${RED}❌ 80 端口已被占用！${NC}"
    echo ""
    echo "占用详情："
    echo "$PORT_80_INFO"
    
    # 提取进程ID
    PID=$(echo "$PORT_80_INFO" | grep -oP '\d+(?=/nginx)' | head -1)
    if [ -n "$PID" ]; then
        echo ""
        echo "占用端口的进程信息："
        ps -p "$PID" -o pid,user,cmd,etime 2>/dev/null || echo "无法获取进程信息"
    fi
fi
echo ""

# 检查 Docker 容器
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. 检查 Docker 容器中的 Nginx"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v docker >/dev/null 2>&1; then
    DOCKER_NGINX=$(docker ps --format "{{.Names}}\t{{.Ports}}" | grep -i nginx || echo "")
    
    if [ -z "$DOCKER_NGINX" ]; then
        echo "未发现运行中的 Nginx 相关 Docker 容器"
    else
        echo "发现 Nginx 相关的 Docker 容器："
        echo "$DOCKER_NGINX" | while read line; do
            CONTAINER_NAME=$(echo "$line" | awk '{print $1}')
            PORTS=$(echo "$line" | cut -f2)
            
            echo ""
            echo "容器: $CONTAINER_NAME"
            echo "  端口映射: $PORTS"
            
            # 检查是否映射了 80 端口
            if echo "$PORTS" | grep -q "0.0.0.0:80\|:::80"; then
                echo -e "  ${RED}⚠️  此容器映射了 80 端口！${NC}"
                
                # 检查是否是后端容器
                if echo "$CONTAINER_NAME" | grep -qv "frontend"; then
                    echo -e "  ${YELLOW}⚠️  这是后端 Nginx 容器，可能与前端冲突！${NC}"
                fi
            fi
            
            # 获取容器详细信息
            echo "  详细端口映射:"
            docker port "$CONTAINER_NAME" 2>/dev/null | grep -E "80|443" || echo "    （无 80/443 端口映射）"
        done
    fi
else
    echo "Docker 未安装或不在 PATH"
fi
echo ""

# 检查系统级 Nginx 进程
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. 检查系统级 Nginx 进程"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

NGINX_PROCESSES=$(ps aux | grep nginx | grep -v grep || echo "")
if [ -z "$NGINX_PROCESSES" ]; then
    echo "未发现运行中的 Nginx 进程"
else
    echo "发现 Nginx 进程："
    echo "$NGINX_PROCESSES"
    echo ""
    
    # 统计进程数
    NGINX_COUNT=$(echo "$NGINX_PROCESSES" | wc -l)
    if [ "$NGINX_COUNT" -gt 1 ]; then
        echo -e "${YELLOW}⚠️  发现 $NGINX_COUNT 个 Nginx 进程，可能存在多个 Nginx 实例${NC}"
    fi
    
    # 检查主进程
    NGINX_MASTER=$(echo "$NGINX_PROCESSES" | grep "nginx: master" | head -1)
    if [ -n "$NGINX_MASTER" ]; then
        MASTER_PID=$(echo "$NGINX_MASTER" | awk '{print $2}')
        echo ""
        echo "主进程 PID: $MASTER_PID"
        echo "主进程详细信息："
        echo "$NGINX_MASTER"
        
        # 尝试获取配置文件路径
        if [ -d "/proc/$MASTER_PID" ]; then
            CMD_LINE=$(cat "/proc/$MASTER_PID/cmdline" 2>/dev/null | tr '\0' ' ')
            echo "  命令行: $CMD_LINE"
        fi
    fi
fi
echo ""

# 检查前端 Nginx 配置目录
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. 检查前端 Nginx 配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

FRONTEND_NGINX_CONF="/opt/hifate-frontend/nginx/nginx.conf"
if [ -f "$FRONTEND_NGINX_CONF" ]; then
    echo -e "${GREEN}✅ 前端 Nginx 配置文件存在: $FRONTEND_NGINX_CONF${NC}"
    echo ""
    echo "配置中的监听端口："
    grep -i "listen" "$FRONTEND_NGINX_CONF" | grep -v "^#" | head -5
    echo ""
    echo "配置中的 root 路径："
    grep "root" "$FRONTEND_NGINX_CONF" | grep -v "^#" | head -3
else
    echo -e "${YELLOW}⚠️  前端 Nginx 配置文件不存在: $FRONTEND_NGINX_CONF${NC}"
fi
echo ""

# 总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "检查总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CONFLICT_FOUND=0

# 检查是否有端口冲突
if [ -n "$PORT_80_INFO" ]; then
    echo -e "${RED}❌ 发现 80 端口占用${NC}"
    CONFLICT_FOUND=1
    
    # 检查是否是 Docker 容器占用
    if command -v docker >/dev/null 2>&1; then
        DOCKER_80=$(docker ps --format "{{.Names}}\t{{.Ports}}" | grep -i nginx | grep -E "0.0.0.0:80|:::80" || echo "")
        if [ -n "$DOCKER_80" ]; then
            echo -e "${YELLOW}⚠️  后端 Docker Nginx 容器正在占用 80 端口${NC}"
            echo "  这会导致前端系统级 Nginx 无法绑定 80 端口"
            echo ""
            echo "解决方案："
            echo "  1. 停止后端 Docker Nginx: docker stop hifate-nginx"
            echo "  2. 或修改后端 Nginx 端口映射"
        fi
    fi
fi

# 检查是否有多个 Nginx 进程
if [ -n "$NGINX_PROCESSES" ]; then
    NGINX_COUNT=$(echo "$NGINX_PROCESSES" | wc -l)
    if [ "$NGINX_COUNT" -gt 2 ]; then
        echo -e "${YELLOW}⚠️  发现多个 Nginx 进程（可能包括前端和后端）${NC}"
        CONFLICT_FOUND=1
    fi
fi

if [ "$CONFLICT_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✅ 未发现明显的端口冲突${NC}"
    echo "但前端文件仍不生效，可能是配置路径问题"
fi

echo ""

