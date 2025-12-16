#!/bin/bash
# 检查并修复认证中间件问题

echo "=========================================="
echo "认证中间件诊断和修复工具"
echo "=========================================="
echo ""

# 1. 检查中间件代码
echo "1. 检查中间件代码..."
MIDDLEWARE_FILE="server/middleware/auth_middleware.py"

if [ ! -f "$MIDDLEWARE_FILE" ]; then
    echo "❌ 中间件文件不存在: $MIDDLEWARE_FILE"
    exit 1
fi

# 检查白名单配置
if grep -q "/frontend" "$MIDDLEWARE_FILE"; then
    echo "✅ 中间件代码包含 /frontend 白名单前缀"
else
    echo "❌ 中间件代码缺少 /frontend 白名单前缀"
    exit 1
fi

# 2. 检查服务器是否运行
echo ""
echo "2. 检查服务器状态..."
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "✅ 服务器正在运行"
    
    # 3. 测试静态文件访问
    echo ""
    echo "3. 测试静态文件访问..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/frontend/login.html)
    
    if [ "$RESPONSE" = "200" ]; then
        echo "✅ 静态文件可以访问 (HTTP 200)"
        CONTENT=$(curl -s http://localhost:8001/frontend/login.html | head -n 1)
        if [[ "$CONTENT" == *"<!DOCTYPE html>"* ]]; then
            echo "✅ 返回HTML内容（正常）"
        else
            echo "⚠️  返回内容异常: $CONTENT"
        fi
    elif [ "$RESPONSE" = "401" ]; then
        echo "❌ 静态文件被拦截 (HTTP 401)"
        echo ""
        echo "🔧 问题诊断："
        echo "   中间件代码已修复，但服务器还在运行旧代码"
        echo ""
        echo "📋 修复步骤："
        echo "   1. 停止服务器（找到运行服务的终端，按 Ctrl+C）"
        echo "   2. 重新启动服务器："
        echo "      cd $(pwd)"
        echo "      python3 server/start.py"
        echo ""
        echo "   3. 重启后运行测试："
        echo "      python3 scripts/e2e_test_all_pages.py"
        exit 1
    else
        echo "⚠️  未知状态码: $RESPONSE"
    fi
else
    echo "⚠️  服务器未运行"
    echo "   启动服务器后再次运行此脚本"
    exit 1
fi

echo ""
echo "✅ 所有检查通过！"

