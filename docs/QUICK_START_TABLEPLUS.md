# TablePlus 快速配置指南

## ✅ 软件已打开

TablePlus 应用应该已经打开。如果没有，请手动打开应用程序。

## 🔌 快速配置连接

### 方法1：使用图形界面（推荐）

#### 配置 MySQL 连接

1. 在 TablePlus 主界面，点击 **"Create a new connection"** 或 **"+"** 按钮
2. 选择 **MySQL**
3. 填写以下信息：

   ```
   Name: HiFate MySQL
   Host: localhost
   Port: 3306
   User: root
   Password: 123456
   Database: hifate_bazi
   ```

4. 点击 **"Test"** 测试连接
5. 如果测试成功，点击 **"Connect"** 连接

#### 配置 Redis 连接

1. 再次点击 **"Create a new connection"** 或 **"+"** 按钮
2. 选择 **Redis**
3. 填写以下信息：

   ```
   Name: HiFate Redis
   Host: localhost
   Port: 6379
   Password: (留空)
   ```

4. 点击 **"Test"** 测试连接
5. 如果测试成功，点击 **"Connect"** 连接

### 方法2：使用命令行（快速）

在终端中执行以下命令：

#### MySQL 连接
```bash
open "tableplus://?name=HiFate%20MySQL&host=localhost&port=3306&user=root&password=123456&database=hifate_bazi"
```

#### Redis 连接
```bash
open "tableplus://?name=HiFate%20Redis&host=localhost&port=6379"
```

## 📋 连接信息汇总

### MySQL
- **名称**: HiFate MySQL
- **主机**: localhost
- **端口**: 3306
- **用户**: root
- **密码**: 123456
- **数据库**: hifate_bazi

### Redis
- **名称**: HiFate Redis
- **主机**: localhost
- **端口**: 6379
- **密码**: (无)

## 🎯 验证连接

连接成功后，你应该能看到：

### MySQL 中可以看到的表：
- `bazi_rules` - 规则表
- `rizhu_gender_contents` - 日柱性别内容表
- `rule_version` - 版本号表
- `bazi_rule_matches` - 规则匹配日志表
- `cache_stats` - 缓存统计表

### Redis 中可以看到：
- 各种缓存键（如 `bazi:rules:*`）

## 🔍 快速测试

### MySQL 测试查询
在 TablePlus 的 SQL 编辑器中执行：

```sql
-- 查看所有表
SHOW TABLES;

-- 查看版本号
SELECT * FROM rule_version;

-- 查看日柱性别内容（示例）
SELECT * FROM rizhu_gender_contents LIMIT 5;
```

### Redis 测试命令
在 TablePlus 的 Redis 命令窗口中执行：

```redis
-- 查看所有键
KEYS *

-- 查看键数量
DBSIZE

-- 查看缓存统计
INFO stats
```

## 💡 使用提示

1. **保存连接**：连接成功后，TablePlus 会自动保存，下次可以直接使用
2. **多窗口**：可以同时打开多个连接窗口
3. **快捷键**：
   - `Cmd + Enter` - 执行 SQL/命令
   - `Cmd + K` - 新建查询
   - `Cmd + W` - 关闭窗口

## ❓ 遇到问题？

### MySQL 连接失败
- 检查 MySQL 是否运行：`brew services list | grep mysql`
- 检查端口是否被占用：`lsof -i :3306`

### Redis 连接失败
- 检查 Redis 是否运行：`redis-cli ping`
- 如果没有运行：`brew services start redis`

---

**配置完成时间**: 2025-11-05












