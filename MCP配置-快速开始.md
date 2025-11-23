# Cursor MCP 配置 - 快速开始

## 🎯 目标
让 Cursor AI 能够：
- ✅ 控制 Chrome 浏览器进行前端测试
- ✅ 直接查询和修改 MySQL 数据库

---

## ⚡ 一键配置（推荐）

### 步骤 1：运行配置脚本
```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
./scripts/setup_mcp.sh
```

### 步骤 2：添加配置到 Cursor

1. **打开 Cursor 设置**：
   - Mac: `Command + ,`
   - 点击右上角的 **"打开设置 (JSON)"** 按钮

2. **添加以下配置**（复制整段）：
```json
{
  "mcp.servers": {
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
      "env": {
        "PUPPETEER_HEADLESS": "false"
      }
    },
    "mysql-bazi": {
      "command": "node",
      "args": ["/Users/zhoudt/Downloads/project/HiFate-bazi/scripts/mcp-mysql-server.js"],
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

3. **保存并重启 Cursor**

### 步骤 3：测试连接

在 Cursor 中询问 AI：

**测试浏览器**：
```
请访问 http://localhost:8000/frontend/formula-analysis.html 并截图
```

**测试数据库**：
```
查询数据库中 rule_code='FORMULA_HEALTH_70012' 的规则
```

---

## 🎨 实际使用示例

### 示例 1：自动化前端测试
```
AI，请帮我：
1. 启动本地服务（./start_all_services.sh）
2. 打开算法公式页面
3. 输入生日：1990-05-15 10:00 男
4. 点击"分析"按钮
5. 检查"身体"板块是否显示
6. 截图并检查控制台错误
```

### 示例 2：规则条件快速修改
```
AI，请帮我：
1. 查询规则 FORMULA_HEALTH_70012 的当前条件
2. 修改 conditions 为：
   {
     "pillar_in": {"pillar": "day", "part": "stem", "values": ["甲", "乙"]},
     "gender": "male"
   }
3. 更新数据库
4. 清理 Redis 缓存
5. 重启服务
6. 测试前端是否正常显示
```

### 示例 3：批量检查字符编码
```
AI，请帮我：
1. 检查所有 FORMULA_HEALTH 规则的字符编码
2. 找出包含乱码的规则（如 'ç"²'）
3. 统计有问题的规则数量
4. 显示前 5 个有问题的规则编码
```

### 示例 4：前端性能分析
```
AI，请帮我：
1. 打开运势分析页面
2. 运行性能审计
3. 检查加载时间和资源大小
4. 提供优化建议
```

---

## 🔍 可用命令

### 浏览器操作
- `takeScreenshot` - 截图当前页面
- `getConsoleLogs` - 获取控制台日志
- `getConsoleErrors` - 获取控制台错误
- `getNetworkLogs` - 获取网络请求日志
- `runAccessibilityAudit` - 可访问性审计
- `runPerformanceAudit` - 性能审计

### 数据库操作
- `query` - 执行 SELECT 查询
- `execute` - 执行 INSERT/UPDATE/DELETE
- `get_rule` - 查询指定规则
- `update_rule_condition` - 更新规则条件
- `list_rules` - 列出规则列表
- `check_encoding` - 检查字符编码

---

## 🚀 典型工作流

### 修复规则 → 测试 → 验证
```
1. 用户：修复身体规则 70012 的条件

2. AI：
   [查询数据库] 当前条件是...
   [分析问题] 发现问题是...
   [修改数据库] 已更新为...
   [清理缓存] 已清理 Redis
   [重启服务] 服务已重启
   [测试前端] 正在测试...
   [截图验证] ✅ 测试通过！

3. 用户：很好！
```

---

## ⚙️ 配置文件位置

- **MCP 配置**：`.mcp-config.json`
- **MySQL 服务器**：`scripts/mcp-mysql-server.js`
- **安装脚本**：`scripts/setup_mcp.sh`
- **完整文档**：`docs/Cursor_MCP配置指南.md`
- **Cursor 设置**：`~/Library/Application Support/Cursor/User/settings.json`

---

## 🐛 故障排查

### 问题：MCP 服务器未响应
```bash
# 检查依赖
npm list -g @modelcontextprotocol/server-puppeteer
npm list mysql2

# 重新安装
./scripts/setup_mcp.sh
```

### 问题：无法连接数据库
```bash
# 检查 MySQL 服务
lsof -i :13306

# 测试连接
mysql -h 127.0.0.1 -P 13306 -u root -p
```

### 问题：浏览器无法打开
```bash
# 设置 Chrome 路径
export PUPPETEER_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

---

## 💡 提示

1. **第一次使用**会自动下载 Chromium，需要一些时间
2. **数据库操作**需要确认（`confirm: true`）才能执行修改
3. **浏览器可见模式**：设置 `PUPPETEER_HEADLESS=false` 可以看到操作过程
4. **性能考虑**：MCP 操作会增加延迟，仅在需要时使用

---

## 📚 相关文档

- 完整配置指南：`docs/Cursor_MCP配置指南.md`
- 项目开发规范：`.cursorrules`
- 规则系统架构：`docs/rule_system_architecture.md`
- API 文档：`docs/bazi_api_structure.json`

---

**配置完成后，你就可以用自然语言让 AI 帮你操作浏览器和数据库了！** 🎉

遇到问题？查看完整文档或询问 AI："MCP 配置有什么问题？"

