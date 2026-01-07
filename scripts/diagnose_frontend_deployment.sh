#!/bin/bash
# 前端文件部署问题诊断脚本（只读检查）
# 用途：诊断为什么前端文件放在 /opt/hifate-frontend/nginx/html/dist 下不生效

set -e

echo "=========================================="
echo "前端文件部署问题诊断（只读检查）"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步骤 1: 检查文件是否存在
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1: 检查文件是否存在"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TARGET_DIR="/opt/hifate-frontend/nginx/html/dist"

if [ -d "$TARGET_DIR" ]; then
    echo -e "${GREEN}✅ 目录存在: $TARGET_DIR${NC}"
    echo ""
    echo "目录内容："
    ls -lah "$TARGET_DIR" | head -20
    echo ""
    
    if [ -f "$TARGET_DIR/index.html" ]; then
        echo -e "${GREEN}✅ index.html 文件存在${NC}"
    else
        echo -e "${RED}❌ index.html 文件不存在${NC}"
    fi
    
    FILE_COUNT=$(find "$TARGET_DIR" -type f | wc -l)
    echo "文件总数: $FILE_COUNT"
else
    echo -e "${RED}❌ 目录不存在: $TARGET_DIR${NC}"
fi
echo ""

# 步骤 2: 检查前端独立 Nginx 配置文件
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2: 检查前端独立 Nginx 配置"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 优先检查前端目录下的 Nginx 配置
FRONTEND_NGINX_DIR="/opt/hifate-frontend/nginx"
if [ -d "$FRONTEND_NGINX_DIR" ]; then
    echo -e "${GREEN}✅ 前端 Nginx 目录存在: $FRONTEND_NGINX_DIR${NC}"
    echo ""
    echo "前端 Nginx 目录结构："
    find "$FRONTEND_NGINX_DIR" -type f -name "*.conf" 2>/dev/null | head -10
    echo ""
    
    # 查找 nginx.conf
    if [ -f "$FRONTEND_NGINX_DIR/nginx.conf" ]; then
        echo "找到前端 Nginx 配置文件: $FRONTEND_NGINX_DIR/nginx.conf"
        echo "配置内容中的 root 和 location："
        grep -A 5 "root\|location" "$FRONTEND_NGINX_DIR/nginx.conf" 2>/dev/null | head -50
        echo ""
    fi
    
    # 查找 conf.d 目录
    if [ -d "$FRONTEND_NGINX_DIR/conf.d" ]; then
        echo "前端 Nginx conf.d 目录："
        ls -la "$FRONTEND_NGINX_DIR/conf.d/" 2>/dev/null
        echo ""
        echo "查找 root 和 location 配置："
        grep -A 5 "root\|location" "$FRONTEND_NGINX_DIR/conf.d"/*.conf 2>/dev/null | head -50
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  前端 Nginx 配置目录不存在: $FRONTEND_NGINX_DIR${NC}"
    echo "尝试查找其他可能的配置位置..."
    echo ""
fi

# 检查系统级 Nginx 配置（可能是后端，但也要检查）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "检查系统级 Nginx 配置（可能是后端）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "/etc/nginx/nginx.conf" ]; then
    echo "系统主配置文件: /etc/nginx/nginx.conf"
    echo "注意：这可能是后端 Nginx 配置"
    echo "相关配置片段："
    sudo grep -A 10 "server\|location" /etc/nginx/nginx.conf 2>/dev/null | head -30 || echo "（需要 sudo 权限）"
    echo ""
fi

if [ -d "/etc/nginx/conf.d" ]; then
    echo "系统配置目录: /etc/nginx/conf.d（可能是后端）"
    echo "配置文件列表："
    ls -la /etc/nginx/conf.d/ 2>/dev/null || echo "（需要权限）"
    echo ""
    echo "查找 root 和 location 配置："
    sudo grep -A 5 "root\|location" /etc/nginx/conf.d/*.conf 2>/dev/null | head -50 || echo "（需要 sudo 权限）"
    echo ""
fi

echo "查找包含 hifate-frontend 或 dist 的配置文件："
find /etc/nginx -name "*.conf" -exec grep -l "hifate-frontend\|dist" {} \; 2>/dev/null | head -10 || echo "系统配置中未找到相关配置"
find "$FRONTEND_NGINX_DIR" -name "*.conf" -exec grep -l "dist\|html" {} \; 2>/dev/null | head -10 || echo "前端配置中未找到相关配置"
echo ""

# 步骤 3: 检查端口占用和 Nginx 进程冲突
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 3: 检查端口占用和 Nginx 进程冲突"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "检查 80 和 443 端口占用情况："
if command -v netstat >/dev/null 2>&1; then
    echo "端口 80:"
    sudo netstat -tlnp | grep ":80 " || echo "端口 80 未被占用"
    echo ""
    echo "端口 443:"
    sudo netstat -tlnp | grep ":443 " || echo "端口 443 未被占用"
elif command -v ss >/dev/null 2>&1; then
    echo "端口 80:"
    sudo ss -tlnp | grep ":80 " || echo "端口 80 未被占用"
    echo ""
    echo "端口 443:"
    sudo ss -tlnp | grep ":443 " || echo "端口 443 未被占用"
else
    echo "无法检查端口占用（需要 netstat 或 ss 命令）"
fi
echo ""

echo "所有 Nginx 进程："
ps aux | grep nginx | grep -v grep || echo "未找到 Nginx 进程"
echo ""

# 检查是否有多个 Nginx 进程（可能是前端和后端）
NGINX_PIDS=$(pgrep nginx)
NGINX_COUNT=$(echo "$NGINX_PIDS" | wc -l)

if [ -n "$NGINX_PIDS" ] && [ "$NGINX_COUNT" -gt 0 ]; then
    echo "发现 $NGINX_COUNT 个 Nginx 进程，可能包括前端和后端："
    echo ""
    
    for pid in $NGINX_PIDS; do
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "进程 $pid 详细信息："
        ps -p $pid -o pid,user,cmd,etime 2>/dev/null || continue
        echo ""
        
        # 检查进程使用的配置文件
        CONFIG_FILE=$(ps -p $pid -o args= 2>/dev/null | grep -oP "(?<=-c\s)\S+" || echo "")
        if [ -n "$CONFIG_FILE" ]; then
            echo "  配置文件: $CONFIG_FILE"
            
            # 检查是前端还是后端配置
            if echo "$CONFIG_FILE" | grep -q "hifate-frontend"; then
                echo -e "  类型: ${GREEN}前端 Nginx${NC}"
            elif echo "$CONFIG_FILE" | grep -q "/etc/nginx"; then
                echo -e "  类型: ${YELLOW}系统/后端 Nginx${NC}"
            else
                echo "  类型: 未知"
            fi
        else
            echo "  配置文件: 未指定（可能使用默认配置）"
        fi
        
        # 检查进程的工作目录
        WORK_DIR=$(readlink /proc/$pid/cwd 2>/dev/null || echo "")
        if [ -n "$WORK_DIR" ]; then
            echo "  工作目录: $WORK_DIR"
            if echo "$WORK_DIR" | grep -q "hifate-frontend"; then
                echo -e "  类型: ${GREEN}前端 Nginx${NC}"
            fi
        fi
        
        # 检查进程监听的端口
        echo "  监听端口:"
        if command -v lsof >/dev/null 2>&1; then
            sudo lsof -p $pid -iTCP -sTCP:LISTEN -nP 2>/dev/null | grep -v "COMMAND" || echo "    （需要权限查看）"
        fi
        echo ""
    done
    
    # 检查是否有端口冲突
    if [ "$NGINX_COUNT" -gt 1 ]; then
        echo -e "${YELLOW}⚠️  警告：检测到多个 Nginx 进程，可能存在端口冲突！${NC}"
        echo "如果多个 Nginx 都监听 80 端口，只有第一个启动的会成功绑定端口。"
        echo ""
    fi
else
    echo "未找到运行中的 Nginx 进程"
fi

# 检查系统 Nginx 配置（后端）
if command -v nginx >/dev/null 2>&1; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "系统 Nginx 配置检查（后端）："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 检查后端是否也监听 80 端口
    BACKEND_LISTENS_80=$(sudo nginx -T 2>/dev/null | grep -c "listen.*80" || echo "0")
    if [ "$BACKEND_LISTENS_80" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  后端 Nginx 也在监听 80 端口！${NC}"
        echo "这可能导致端口冲突。"
        echo ""
    fi
    
    echo "后端 Nginx 配置中的 root 路径："
    sudo nginx -T 2>/dev/null | grep -E "^\s*root" | head -10 || echo "（需要 sudo 权限或 Nginx 未安装）"
    echo ""
    
    echo "后端 Nginx 监听 80 端口的服务器配置："
    sudo nginx -T 2>/dev/null | grep -B 5 -A 10 "listen.*80" | head -60 || echo "（需要 sudo 权限）"
    echo ""
    
    # 检查后端是否配置了反向代理到前端
    echo "检查后端是否配置了反向代理或负载均衡："
    BACKEND_PROXY=$(sudo nginx -T 2>/dev/null | grep -E "proxy_pass|upstream" | head -10 || echo "")
    if [ -n "$BACKEND_PROXY" ]; then
        echo "$BACKEND_PROXY"
        echo ""
        echo -e "${YELLOW}⚠️  后端 Nginx 配置了反向代理或负载均衡${NC}"
        echo "这可能会影响前端访问。"
    else
        echo "未找到反向代理配置"
    fi
else
    echo -e "${YELLOW}⚠️  系统 Nginx 命令未找到${NC}"
fi

# 检查前端目录下是否有自定义 nginx
if [ -f "$FRONTEND_NGINX_DIR/nginx.conf" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "前端 Nginx 配置文件检查："
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "前端配置中的 root 路径："
    grep -E "^\s*root" "$FRONTEND_NGINX_DIR/nginx.conf" 2>/dev/null || echo "未找到 root 配置"
    
    echo ""
    echo "前端配置中的 location 块："
    grep -A 10 "location" "$FRONTEND_NGINX_DIR/nginx.conf" 2>/dev/null | head -30 || echo "未找到 location 配置"
fi
echo ""

# 步骤 4: 检查文件权限
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 4: 检查文件权限"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "/opt/hifate-frontend" ]; then
    echo "目录权限结构："
    ls -lad /opt/hifate-frontend 2>/dev/null || echo "（需要权限）"
    
    if [ -d "/opt/hifate-frontend/nginx" ]; then
        ls -lad /opt/hifate-frontend/nginx 2>/dev/null || echo "（需要权限）"
        
        if [ -d "/opt/hifate-frontend/nginx/html" ]; then
            ls -lad /opt/hifate-frontend/nginx/html 2>/dev/null || echo "（需要权限）"
            
            if [ -d "$TARGET_DIR" ]; then
                echo ""
                echo "目标目录权限："
                ls -lad "$TARGET_DIR" 2>/dev/null || echo "（需要权限）"
                
                echo ""
                echo "目标目录文件权限示例："
                ls -lah "$TARGET_DIR" | head -10
            fi
        fi
    fi
fi

echo ""
echo "Nginx 进程信息："
ps aux | grep nginx | grep -v grep | head -5 || echo "未找到 Nginx 进程"
echo ""

if pgrep nginx >/dev/null 2>&1; then
    NGINX_USER=$(ps aux | grep "nginx: master" | grep -v grep | awk '{print $1}' | head -1)
    if [ -n "$NGINX_USER" ]; then
        echo "Nginx 主进程运行用户: $NGINX_USER"
        echo ""
        echo "检查用户 $NGINX_USER 对目标目录的访问权限："
        if [ -d "$TARGET_DIR" ]; then
            sudo -u "$NGINX_USER" test -r "$TARGET_DIR" && echo -e "${GREEN}✅ 用户 $NGINX_USER 可以读取目录${NC}" || echo -e "${RED}❌ 用户 $NGINX_USER 无法读取目录${NC}"
            if [ -f "$TARGET_DIR/index.html" ]; then
                sudo -u "$NGINX_USER" test -r "$TARGET_DIR/index.html" && echo -e "${GREEN}✅ 用户 $NGINX_USER 可以读取 index.html${NC}" || echo -e "${RED}❌ 用户 $NGINX_USER 无法读取 index.html${NC}"
            fi
        fi
    fi
fi
echo ""

# 步骤 5: 检查 Nginx 错误日志
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 5: 检查 Nginx 错误日志"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查前端目录下的日志
if [ -d "$FRONTEND_NGINX_DIR/logs" ]; then
    echo "前端 Nginx 日志目录："
    ls -lah "$FRONTEND_NGINX_DIR/logs/" 2>/dev/null | head -10
    echo ""
    
    FRONTEND_ERROR_LOG="$FRONTEND_NGINX_DIR/logs/error.log"
    if [ -f "$FRONTEND_ERROR_LOG" ]; then
        echo "前端错误日志（最后 50 行）："
        tail -50 "$FRONTEND_ERROR_LOG" 2>/dev/null || echo "（需要权限）"
        echo ""
    fi
    
    FRONTEND_ACCESS_LOG="$FRONTEND_NGINX_DIR/logs/access.log"
    if [ -f "$FRONTEND_ACCESS_LOG" ]; then
        echo "前端访问日志中的 404 错误："
        tail -50 "$FRONTEND_ACCESS_LOG" 2>/dev/null | grep "404" | tail -20 || echo "未找到 404 错误"
        echo ""
    fi
fi

# 检查系统级日志（可能是后端）
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "系统 Nginx 日志（可能是后端）："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ERROR_LOG="/var/log/nginx/error.log"
if [ -f "$ERROR_LOG" ]; then
    echo "系统错误日志（最后 50 行）："
    sudo tail -50 "$ERROR_LOG" 2>/dev/null || echo "（需要 sudo 权限）"
else
    echo "系统错误日志文件不存在: $ERROR_LOG"
fi
echo ""

ACCESS_LOG="/var/log/nginx/access.log"
if [ -f "$ACCESS_LOG" ]; then
    echo "系统访问日志中的 404 错误："
    sudo tail -50 "$ACCESS_LOG" 2>/dev/null | grep "404" | tail -20 || echo "未找到 404 错误"
else
    echo "系统访问日志文件不存在: $ACCESS_LOG"
fi

# 查找所有可能的 Nginx 日志
echo ""
echo "查找其他可能的日志位置："
find /opt/hifate-frontend -name "*error*.log" -o -name "*access*.log" 2>/dev/null | head -10
find /var/log -name "*nginx*error*" -o -name "*nginx*access*" 2>/dev/null | head -10
echo ""

# 步骤 6: 检查后端 Nginx 对前端的影响
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 6: 检查后端 Nginx 是否影响前端"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查是否有 Docker 容器运行后端 Nginx
echo "检查 Docker 容器中的后端 Nginx："
if command -v docker >/dev/null 2>&1; then
    DOCKER_NGINX=$(docker ps --format "{{.Names}}" | grep -i nginx || echo "")
    if [ -n "$DOCKER_NGINX" ]; then
        echo "发现 Nginx 相关的 Docker 容器："
        echo "$DOCKER_NGINX"
        echo ""
        
        for container in $DOCKER_NGINX; do
            echo "容器 $container："
            # 检查容器映射的端口
            docker port "$container" 2>/dev/null | grep -E "80|443" || echo "  未映射 80/443 端口"
            
            # 检查是否是后端容器
            if echo "$container" | grep -qv "frontend"; then
                echo -e "  类型: ${YELLOW}可能是后端 Nginx${NC}"
                echo "  如果映射了 80 端口，可能与前端 Nginx 冲突"
            fi
            echo ""
        done
    else
        echo "未发现运行中的 Nginx 相关 Docker 容器"
    fi
else
    echo "Docker 命令未找到，跳过 Docker 检查"
fi

# 检查系统服务
echo "检查 Nginx 系统服务状态："
if systemctl list-units --type=service 2>/dev/null | grep -q nginx; then
    echo "Nginx 系统服务："
    sudo systemctl status nginx --no-pager -l 2>/dev/null | head -15 || echo "（需要 sudo 权限）"
    echo ""
fi

# 总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "诊断总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "请检查以下关键点："
echo "1. ✅ 文件是否在正确位置: $TARGET_DIR"
echo "2. ✅ 前端 Nginx 配置的 root 路径是否匹配文件位置"
echo "3. ✅ Nginx 进程用户是否有权限读取文件"
echo "4. ✅ 是否存在端口冲突（多个 Nginx 监听 80 端口）"
echo "5. ✅ 后端 Nginx 是否配置了反向代理影响前端"
echo "6. ✅ Docker 容器中的后端 Nginx 是否占用 80 端口"
echo "7. ✅ Nginx 错误日志中是否有相关错误"
echo "8. ✅ Nginx 访问日志中是否有 404 错误"
echo ""

# 检查发现的潜在问题
ISSUES_FOUND=0

if [ -n "$NGINX_PIDS" ] && [ "$NGINX_COUNT" -gt 1 ]; then
    echo -e "${YELLOW}⚠️  发现潜在问题：多个 Nginx 进程运行${NC}"
    ISSUES_FOUND=1
fi

if [ "$BACKEND_LISTENS_80" -gt 0 ] 2>/dev/null; then
    echo -e "${YELLOW}⚠️  发现潜在问题：后端 Nginx 也在监听 80 端口${NC}"
    echo "   这可能导致前端 Nginx 无法绑定 80 端口"
    ISSUES_FOUND=1
fi

if [ "$ISSUES_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✅ 未发现明显的进程冲突问题${NC}"
fi

echo ""
echo "如果发现问题，请："
echo "- 检查是否有端口冲突（多个 Nginx 监听同一端口）"
echo "- 确认前端 Nginx 配置文件中的 root 路径"
echo "- 确认文件权限是否正确"
echo "- 检查后端 Nginx 是否配置了反向代理影响前端"
echo "- 检查 Nginx 是否已重新加载配置"
echo ""

