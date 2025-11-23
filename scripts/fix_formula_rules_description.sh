#!/bin/bash
# 一键修复FORMULA规则的description字段

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "🔧 修复FORMULA规则的description字段"
echo "============================================================"
echo ""

# 检查虚拟环境
if [ -d ".venv" ]; then
    echo "✓ 找到虚拟环境"
    source .venv/bin/activate
else
    echo "⚠️  未找到虚拟环境，使用系统Python"
fi

# 检查Python依赖
echo ""
echo "检查Python依赖..."
python3 -c "import pymysql" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少pymysql模块"
    echo "请运行: pip install pymysql"
    exit 1
fi
echo "✓ Python依赖检查通过"

# 执行步骤1：试运行
echo ""
echo "============================================================"
echo "步骤1：试运行（查看需要更新的规则）"
echo "============================================================"
python3 scripts/update_formula_rules_conditions.py --dry-run

echo ""
echo "============================================================"
echo "是否继续执行实际更新？(y/n)"
echo "============================================================"
read -p "请输入 (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 执行步骤2：实际更新
    echo ""
    echo "============================================================"
    echo "步骤2：实际更新数据库"
    echo "============================================================"
    python3 scripts/update_formula_rules_conditions.py
    
    # 执行步骤3：验证
    echo ""
    echo "============================================================"
    echo "步骤3：验证修复结果"
    echo "============================================================"
    python3 scripts/verify_migrated_rules.py
    
    # 提示重启服务
    echo ""
    echo "============================================================"
    echo "✅ 修复完成！"
    echo "============================================================"
    echo ""
    echo "建议操作："
    echo "1. 重启服务清除缓存："
    echo "   ./restart_server.sh"
    echo ""
    echo "2. 通过前端测试验证："
    echo "   http://localhost:8001/frontend/formula-analysis.html"
    echo ""
    echo "3. 或使用API测试："
    echo "   curl -X POST http://localhost:8003/api/v1/bazi/formula-analysis \\"
    echo "     -H 'Content-Type: application/json' \\"
    echo "     -d '{\"solar_date\": \"2025-11-23\", \"solar_time\": \"12:00\", \"gender\": \"male\"}'"
    echo ""
else
    echo ""
    echo "❌ 已取消更新"
    exit 0
fi

