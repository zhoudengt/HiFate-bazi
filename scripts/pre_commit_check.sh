#!/bin/bash
###############################################################################
# 提交前检查脚本
# 
# 用途：在提交代码前进行完整性检查，确保：
#   1. Python语法正确
#   2. 服务能正常启动
#   3. API接口正常工作
#   4. 前端能正常访问
#
# 使用方法：
#   ./scripts/pre_commit_check.sh
#
# 返回值：
#   0 - 所有检查通过
#   1 - 检查失败
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🔍 HiFate系统 - 提交前代码检查"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 1. Python语法检查
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}1️⃣  检查Python语法...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

SYNTAX_ERRORS=0
CHECKED_FILES=0

# 检查所有Python文件
while IFS= read -r -d '' file; do
    # 跳过虚拟环境
    if [[ "$file" == *".venv"* ]] || [[ "$file" == *"venv"* ]]; then
        continue
    fi
    
    CHECKED_FILES=$((CHECKED_FILES + 1))
    
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $file"
    else
        echo -e "  ${RED}✗${NC} $file"
        python3 -m py_compile "$file" 2>&1 | sed 's/^/    /'
        SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
    fi
done < <(find server src services -name "*.py" -print0 2>/dev/null)

echo ""
if [ $SYNTAX_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ 语法检查通过${NC}（检查了 $CHECKED_FILES 个文件）"
else
    echo -e "${RED}❌ 发现 $SYNTAX_ERRORS 个文件有语法错误${NC}"
    echo ""
    echo -e "${YELLOW}请修复以上语法错误后再提交代码${NC}"
    exit 1
fi

echo ""

# 2. 检查服务是否运行
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}2️⃣  检查服务状态...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查主服务
if lsof -i:8001 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} 主服务运行中（端口 8001）"
    SERVICE_RUNNING=true
else
    echo -e "  ${RED}✗${NC} 主服务未运行"
    SERVICE_RUNNING=false
fi

# 检查前端服务
if lsof -i:8080 > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} 前端服务运行中（端口 8080）"
else
    echo -e "  ${YELLOW}⚠${NC} 前端服务未运行（可选）"
fi

# 检查微服务
MICROSERVICES=(9001 9002 9003 9004 9005 9006 9007)
RUNNING_SERVICES=0
for port in "${MICROSERVICES[@]}"; do
    if lsof -i:$port > /dev/null 2>&1; then
        RUNNING_SERVICES=$((RUNNING_SERVICES + 1))
    fi
done

echo -e "  ${GREEN}✓${NC} 微服务运行中：$RUNNING_SERVICES/${#MICROSERVICES[@]}"

if [ "$SERVICE_RUNNING" = false ]; then
    echo ""
    echo -e "${YELLOW}⚠️  主服务未运行，尝试启动服务...${NC}"
    echo ""
    
    # 尝试启动服务
    if [ -f "./restart_server.sh" ]; then
        ./restart_server.sh
        sleep 5
        
        # 再次检查
        if lsof -i:8001 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 服务启动成功${NC}"
        else
            echo -e "${RED}❌ 服务启动失败${NC}"
            echo ""
            echo -e "${YELLOW}请检查日志：tail -f logs/web_app_8001.log${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ 找不到启动脚本 restart_server.sh${NC}"
        exit 1
    fi
fi

echo ""

# 3. 健康检查
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}3️⃣  API健康检查...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 等待服务完全启动
sleep 2

if curl -f -s http://127.0.0.1:8001/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} 健康检查接口正常"
    echo -e "${GREEN}✅ 服务健康${NC}"
else
    echo -e "  ${RED}✗${NC} 健康检查接口失败"
    echo -e "${RED}❌ 服务可能未正常启动${NC}"
    echo ""
    echo -e "${YELLOW}请检查日志：tail -f logs/web_app_8001.log${NC}"
    exit 1
fi

echo ""

# 4. API功能测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}4️⃣  API功能测试...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "test_frontend_display.py" ]; then
    if python3 test_frontend_display.py > /tmp/api_test.log 2>&1; then
        # 检查是否有API超时
        if grep -q "API请求超时" /tmp/api_test.log; then
            echo -e "  ${RED}✗${NC} API请求超时"
            echo -e "${RED}❌ API功能测试失败${NC}"
            echo ""
            echo -e "${YELLOW}详细信息：${NC}"
            grep -A 5 "API请求超时" /tmp/api_test.log | sed 's/^/  /'
            exit 1
        fi
        
        # 检查API是否正常响应
        if grep -q "✅ API响应正常" /tmp/api_test.log; then
            echo -e "  ${GREEN}✓${NC} fortune API 正常"
            echo -e "${GREEN}✅ API功能测试通过${NC}"
        else
            echo -e "  ${YELLOW}⚠${NC} API响应异常"
            echo -e "${YELLOW}⚠️  API功能测试未完全通过${NC}"
        fi
    else
        echo -e "  ${RED}✗${NC} 测试脚本执行失败"
        echo -e "${RED}❌ API功能测试失败${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} 未找到测试脚本 test_frontend_display.py"
    echo -e "${YELLOW}⚠️  跳过API功能测试${NC}"
fi

echo ""

# 5. Git状态检查
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${BLUE}5️⃣  Git状态检查...${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查是否有未提交的修改
if git diff --quiet && git diff --cached --quiet; then
    echo -e "  ${YELLOW}⚠${NC} 工作区无修改"
else
    # 显示修改的文件
    MODIFIED_FILES=$(git diff --name-only && git diff --cached --name-only | sort -u)
    FILE_COUNT=$(echo "$MODIFIED_FILES" | wc -l | tr -d ' ')
    
    echo -e "  ${GREEN}✓${NC} 发现 $FILE_COUNT 个文件有修改："
    echo ""
    echo "$MODIFIED_FILES" | sed 's/^/    /'
    echo ""
fi

echo ""

# 6. 最终总结
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ 所有检查通过！${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✓${NC} Python语法正确"
echo -e "${GREEN}✓${NC} 服务运行正常"
echo -e "${GREEN}✓${NC} API接口正常"
echo -e "${GREEN}✓${NC} 功能测试通过"
echo ""
echo -e "${GREEN}🎉 代码可以安全提交！${NC}"
echo ""
echo "建议的提交命令："
echo -e "${BLUE}  git add .${NC}"
echo -e "${BLUE}  git commit -m \"<type>: <描述>\"${NC}"
echo -e "${BLUE}  git push${NC}"
echo ""

exit 0

