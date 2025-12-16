#!/bin/bash
# 测试前端页面访问权限
# 验证认证中间件是否正确放行静态文件

echo "=========================================="
echo "前端页面访问权限测试"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8001"

echo "1. 测试静态文件访问（应该返回文件内容，不是JSON）"
echo "--------------------------------------------------"
echo ""

echo "测试: ${BASE_URL}/frontend/login.html"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/frontend/login.html")
if [ "$RESPONSE" = "200" ]; then
    echo "✅ 状态码: $RESPONSE (成功)"
    CONTENT=$(curl -s "${BASE_URL}/frontend/login.html" | head -n 5)
    if [[ "$CONTENT" == *"<!DOCTYPE html>"* ]]; then
        echo "✅ 返回内容: HTML (正确)"
    elif [[ "$CONTENT" == *"{"* ]]; then
        echo "❌ 返回内容: JSON (错误 - 被认证中间件拦截)"
        echo "   内容预览: $(echo "$CONTENT" | head -n 1)"
    else
        echo "⚠️  返回内容: 其他格式"
    fi
else
    echo "❌ 状态码: $RESPONSE (失败)"
fi

echo ""
echo "测试: ${BASE_URL}/frontend/js/core/error-handler.js"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/frontend/js/core/error-handler.js")
if [ "$RESPONSE" = "200" ]; then
    echo "✅ 状态码: $RESPONSE (成功)"
    CONTENT=$(curl -s "${BASE_URL}/frontend/js/core/error-handler.js" | head -n 3)
    if [[ "$CONTENT" == *"ErrorHandler"* ]] || [[ "$CONTENT" == *"class"* ]]; then
        echo "✅ 返回内容: JavaScript (正确)"
    elif [[ "$CONTENT" == *"{"* ]]; then
        echo "❌ 返回内容: JSON (错误 - 被认证中间件拦截)"
    else
        echo "⚠️  返回内容: 其他格式"
    fi
else
    echo "❌ 状态码: $RESPONSE (失败)"
fi

echo ""
echo "测试: ${BASE_URL}/frontend/css/common.css"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/frontend/css/common.css")
if [ "$RESPONSE" = "200" ]; then
    echo "✅ 状态码: $RESPONSE (成功)"
    CONTENT=$(curl -s "${BASE_URL}/frontend/css/common.css" | head -n 3)
    if [[ "$CONTENT" == *"error-message"* ]] || [[ "$CONTENT" == *"/*"* ]]; then
        echo "✅ 返回内容: CSS (正确)"
    elif [[ "$CONTENT" == *"{"* ]]; then
        echo "❌ 返回内容: JSON (错误 - 被认证中间件拦截)"
    else
        echo "⚠️  返回内容: 其他格式"
    fi
else
    echo "❌ 状态码: $RESPONSE (失败)"
fi

echo ""
echo "2. 测试API端点（应该需要认证）"
echo "--------------------------------------------------"
echo ""

echo "测试: ${BASE_URL}/api/v1/bazi/calculate (无认证)"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/bazi/calculate" -X POST)
if [ "$RESPONSE" = "401" ]; then
    echo "✅ 状态码: $RESPONSE (正确 - 需要认证)"
else
    echo "⚠️  状态码: $RESPONSE (预期: 401)"
fi

echo ""
echo "3. 测试白名单端点（应该不需要认证）"
echo "--------------------------------------------------"
echo ""

echo "测试: ${BASE_URL}/api/v1/auth/login"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/api/v1/auth/login" -X POST)
if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "422" ] || [ "$RESPONSE" = "400" ]; then
    echo "✅ 状态码: $RESPONSE (正确 - 不需要认证，可能参数错误)"
else
    echo "⚠️  状态码: $RESPONSE (预期: 200/400/422)"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "如果静态文件返回JSON错误，说明认证中间件拦截了静态文件请求"
echo "需要检查 server/middleware/auth_middleware.py 中的白名单配置"

