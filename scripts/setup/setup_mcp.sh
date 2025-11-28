#!/bin/bash
# 
# Cursor MCP 一键配置脚本
# 用于配置浏览器和数据库 MCP 服务器
#

set -e

PROJECT_DIR="/Users/zhoudt/Downloads/project/HiFate-bazi"
CURSOR_SETTINGS="$HOME/Library/Application Support/Cursor/User/settings.json"

echo "========================================="
echo "   Cursor MCP 配置脚本"
echo "========================================="
echo ""

# 1. 检查 Node.js 和 npm
echo "1. 检查环境..."
if ! command -v node &> /dev/null; then
    echo "❌ 未安装 Node.js，请先安装"
    exit 1
fi
if ! command -v npm &> /dev/null; then
    echo "❌ 未安装 npm，请先安装"
    exit 1
fi
echo "✅ Node.js: $(node -v)"
echo "✅ npm: $(npm -v)"
echo ""

# 2. 安装 Puppeteer MCP
echo "2. 安装 Puppeteer MCP Server..."
if npm list -g @modelcontextprotocol/server-puppeteer &> /dev/null; then
    echo "✅ Puppeteer MCP 已安装"
else
    echo "正在安装..."
    sudo npm install -g @modelcontextprotocol/server-puppeteer || {
        echo "⚠️  全局安装失败，尝试本地安装..."
        cd "$PROJECT_DIR"
        npm install --save-dev @modelcontextprotocol/server-puppeteer
    }
fi
echo ""

# 3. 安装 MySQL2（用于 MySQL MCP）
echo "3. 安装 MySQL2 依赖..."
cd "$PROJECT_DIR"
if ! npm list mysql2 &> /dev/null; then
    echo "正在安装 mysql2..."
    npm install --save mysql2
else
    echo "✅ mysql2 已安装"
fi
echo ""

# 4. 检查 MCP 脚本
echo "4. 检查 MCP 服务器脚本..."
if [ -f "$PROJECT_DIR/scripts/mcp-mysql-server.js" ]; then
    echo "✅ MySQL MCP 脚本已存在"
    chmod +x "$PROJECT_DIR/scripts/mcp-mysql-server.js"
else
    echo "❌ 未找到 MySQL MCP 脚本"
    exit 1
fi
echo ""

# 5. 备份 Cursor 配置
echo "5. 备份 Cursor 配置..."
if [ -f "$CURSOR_SETTINGS" ]; then
    cp "$CURSOR_SETTINGS" "$CURSOR_SETTINGS.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 已备份到: $CURSOR_SETTINGS.backup.*"
else
    echo "⚠️  未找到 Cursor 配置文件，将创建新配置"
fi
echo ""

# 6. 生成 MCP 配置
echo "6. 生成 MCP 配置..."
cat > "$PROJECT_DIR/.mcp-cursor-settings.json" << 'EOF'
{
  "mcp.servers": {
    "puppeteer": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-puppeteer"
      ],
      "env": {
        "PUPPETEER_HEADLESS": "false"
      }
    },
    "mysql-bazi": {
      "command": "node",
      "args": [
        "/Users/zhoudt/Downloads/project/HiFate-bazi/scripts/mcp-mysql-server.js"
      ],
      "env": {
        "MYSQL_HOST": "127.0.0.1",
        "MYSQL_PORT": "13306",
        "MYSQL_USER": "root",
        "MYSQL_PASSWORD": "root",
        "MYSQL_DATABASE": "bazi_system"
      }
    }
  }
}
EOF
echo "✅ 配置已生成: $PROJECT_DIR/.mcp-cursor-settings.json"
echo ""

# 7. 提示手动配置
echo "========================================="
echo "✅ MCP 服务器安装完成！"
echo "========================================="
echo ""
echo "📋 下一步操作："
echo ""
echo "1. 打开 Cursor 设置："
echo "   Command + , (Mac) 或 Ctrl + , (Windows/Linux)"
echo ""
echo "2. 点击右上角的 '打开设置 (JSON)' 按钮"
echo ""
echo "3. 将以下内容添加到配置文件中："
echo ""
cat "$PROJECT_DIR/.mcp-cursor-settings.json"
echo ""
echo "4. 保存并重启 Cursor"
echo ""
echo "5. 测试 MCP 连接："
echo "   在 Cursor 中询问 AI："
echo "   - '请访问 http://localhost:8000/frontend/formula-analysis.html 并截图'"
echo "   - '查询数据库中所有 FORMULA_HEALTH 类型的规则'"
echo ""
echo "========================================="
echo "📚 查看完整文档："
echo "   $PROJECT_DIR/docs/Cursor_MCP配置指南.md"
echo "========================================="

