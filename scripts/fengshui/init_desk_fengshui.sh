#!/bin/bash
# 办公桌风水系统初始化脚本

set -e

echo "================================================"
echo "  办公桌风水分析系统 - 初始化脚本"
echo "================================================"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 1. 创建数据库表
echo ""
echo "【步骤1】创建数据库表..."
mysql -h 127.0.0.1 -P 13306 -u root -proot123456 --default-character-set=utf8mb4 bazi_system < server/db/migrations/create_desk_fengshui_tables.sql
echo "✅ 数据库表创建成功"

# 2. 检查规则数据
echo ""
echo "【步骤2】检查规则数据..."
RULE_COUNT=$(mysql -h 127.0.0.1 -P 13306 -u root -proot123456 -N -e "SELECT COUNT(*) FROM bazi_system.desk_fengshui_rules")
echo "   当前规则数: $RULE_COUNT 条"

if [ "$RULE_COUNT" -gt 0 ]; then
    echo "✅ 规则数据已存在"
else
    echo "⚠️  规则数据为空（示例规则已在SQL脚本中插入）"
fi

# 3. 安装Python依赖
echo ""
echo "【步骤3】安装Python依赖..."
pip3 install -r services/desk_fengshui/requirements.txt -q
echo "✅ Python依赖安装完成"

# 4. 生成gRPC代码
echo ""
echo "【步骤4】生成gRPC代码..."
python3 -m grpc_tools.protoc \
    -I=proto \
    --python_out=proto/generated \
    --grpc_python_out=proto/generated \
    proto/desk_fengshui.proto
echo "✅ gRPC代码生成完成"

# 5. 创建日志目录
echo ""
echo "【步骤5】创建日志目录..."
mkdir -p logs
echo "✅ 日志目录已创建"

echo ""
echo "================================================"
echo "  ✅ 初始化完成！"
echo "================================================"
echo ""
echo "下一步："
echo "  1. 启动微服务: ./scripts/start_desk_fengshui_service.sh"
echo "  2. 访问前端页面: http://localhost:8001/frontend/desk-fengshui.html"
echo ""

