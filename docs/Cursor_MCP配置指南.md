# Cursor MCP 配置指南

## 概述
将 Google Chrome（浏览器）和 MySQL（数据库）以 MCP（Model Context Protocol）方式集成到 Cursor，用于：
- **前端测试**：自动化浏览器操作、截图、调试
- **数据库操作**：直接查询和修改数据，替代 TablePlus

---

## 🎯 配置方案

### 方案 1：使用现有的 Browser Tools（推荐）
Cursor 已经集成了 browser-tools，可以直接使用：

**可用功能**：
- `mcp_browser-tools_takeScreenshot` - 截图
- `mcp_browser-tools_getConsoleLogs` - 获取控制台日志
- `mcp_browser-tools_getConsoleErrors` - 获取错误
- `mcp_browser-tools_getNetworkLogs` - 获取网络请求
- `mcp_browser-tools_runAccessibilityAudit` - 可访问性审计
- `mcp_browser-tools_runPerformanceAudit` - 性能审计

**使用方法**：
在 Cursor 中直接询问 AI：
```
请帮我测试 http://localhost:8000/frontend/formula-analysis.html
```

AI 会自动使用 browser-tools 进行测试。

---

### 方案 2：配置自定义 MCP 服务器（高级）

## 📦 安装 MCP 服务器

### 1. 安装 Puppeteer MCP（浏览器控制）
```bash
# 全局安装
npm install -g @modelcontextprotocol/server-puppeteer

# 或项目本地安装
cd ~/Downloads/project/HiFate-bazi
npm install --save-dev @modelcontextprotocol/server-puppeteer
```

### 2. 安装 MySQL MCP（数据库操作）
```bash
# 方案A：使用官方 MySQL MCP
npm install -g @modelcontextprotocol/server-mysql

# 方案B：使用自定义脚本（见下文）
```

---

## ⚙️ 配置 Cursor

### 步骤 1：打开 Cursor 设置
```bash
# Mac: Command + ,
# 或直接编辑配置文件
code ~/Library/Application\ Support/Cursor/User/settings.json
```

### 步骤 2：添加 MCP 配置
在 `settings.json` 中添加：

```json
{
  // ... 现有配置 ...
  
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
        "/Users/zhoudt/Downloads/project/HiFate-bazi/.mcp/mysql-server.js"
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
```

---

## 🔧 创建自定义 MySQL MCP 服务器

### 创建 `.mcp/mysql-server.js`
```bash
mkdir -p /Users/zhoudt/Downloads/project/HiFate-bazi/.mcp
```

然后创建文件（见配套的 `mysql-server.js`）

---

## 🧪 测试 MCP 连接

### 测试浏览器 MCP
在 Cursor 中询问 AI：
```
请访问 http://localhost:8000/frontend/formula-analysis.html，
输入测试数据（1990-01-01 12:00 男），
点击分析按钮，截图并检查控制台错误
```

### 测试数据库 MCP
在 Cursor 中询问 AI：
```
查询数据库中 rule_code='FORMULA_HEALTH_70012' 的规则条件
```

---

## 📋 实际使用场景

### 场景 1：前端测试自动化
```
AI，请帮我：
1. 打开算法公式测试页面
2. 输入生日 1990-05-15 10:00 男
3. 点击"分析"按钮
4. 检查是否有"身体"类规则匹配
5. 截图并检查控制台错误
```

### 场景 2：数据库快速查询
```
AI，请帮我：
1. 查询所有 FORMULA_HEALTH 类型的规则
2. 显示前 5 条规则的 rule_code 和 conditions
3. 检查是否有字符编码问题
```

### 场景 3：规则条件修改
```
AI，请帮我：
1. 查询 rule_code='FORMULA_HEALTH_70012' 的规则
2. 将 conditions 中的 values 改为 ["甲", "乙", "丙"]
3. 执行更新并确认
```

### 场景 4：前端调试
```
AI，请帮我：
1. 打开前端页面
2. 打开浏览器 DevTools
3. 监控 Network 请求
4. 点击分析按钮
5. 检查 API 响应是否正常
6. 如果有错误，显示完整的错误信息
```

---

## 🎨 配置完成后的工作流

### 典型开发流程
1. **修改后端规则** → AI 帮你更新数据库
2. **清理缓存** → AI 帮你执行 `redis-cli DEL "rules:FORMULA_HEALTH"`
3. **前端测试** → AI 帮你自动化测试
4. **查看结果** → AI 帮你截图和检查错误
5. **修复问题** → AI 帮你定位和修改代码

### 示例对话
```
你：修复身体规则 70012 的条件
AI：[读取数据库] 当前条件是...
AI：[分析问题] 发现问题是...
AI：[修改数据库] 已更新条件为...
AI：[清理缓存] 已清理 Redis 缓存
AI：[测试前端] 正在测试...
AI：[截图确认] 测试通过！[显示截图]
```

---

## 🚀 快速启动

### 一键配置脚本
```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
chmod +x scripts/setup_mcp.sh
./scripts/setup_mcp.sh
```

### 检查 MCP 状态
在 Cursor 中运行：
```
:mcp.list
```

---

## 🔍 故障排查

### 问题 1：MCP 服务器未启动
```bash
# 检查进程
ps aux | grep -E "(puppeteer|mysql-server)"

# 重启 Cursor
```

### 问题 2：无法连接数据库
```bash
# 检查 MySQL 是否运行
lsof -i :13306

# 测试连接
mysql -h 127.0.0.1 -P 13306 -u root -p
```

### 问题 3：浏览器无法打开
```bash
# 检查 Chrome 是否安装
which google-chrome-stable

# 手动测试 Puppeteer
npx @modelcontextprotocol/server-puppeteer --test
```

---

## 📚 参考资源

- [MCP 官方文档](https://modelcontextprotocol.io)
- [Cursor MCP 集成](https://docs.cursor.com/mcp)
- [Puppeteer MCP Server](https://github.com/modelcontextprotocol/servers)
- 项目规则系统：`docs/rule_system_architecture.md`

---

## 💡 提示

1. **性能优化**：MCP 服务器会增加一些延迟，仅在需要时使用
2. **安全性**：数据库 MCP 有完整的数据访问权限，谨慎使用
3. **调试模式**：设置 `PUPPETEER_HEADLESS=false` 可以看到浏览器操作过程
4. **日志查看**：MCP 服务器日志在 Cursor 的输出面板中

---

**配置完成后，你就可以通过自然语言让 AI 帮你操作浏览器和数据库了！** 🎉

