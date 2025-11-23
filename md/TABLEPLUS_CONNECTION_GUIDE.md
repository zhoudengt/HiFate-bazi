# TablePlus 连接指南

## 📦 安装完成

TablePlus 已成功安装到 `/Applications/TablePlus.app`

## 🔌 连接 MySQL

### 步骤1：打开 TablePlus
- 在应用程序中找到 TablePlus 并打开
- 或使用 Spotlight 搜索 "TablePlus"

### 步骤2：创建 MySQL 连接
1. 点击 "Create a new connection"
2. 选择 **MySQL**
3. 填写连接信息：
   ```
   Name: HiFate MySQL
   Host: localhost
   Port: 3306
   User: root
   Password: 123456
   Database: hifate_bazi
   ```
4. 点击 "Test" 测试连接
5. 点击 "Connect" 连接

### 步骤3：查看数据库
连接成功后，你可以：
- 查看所有表：`bazi_rules`, `rizhu_gender_contents`, `rule_version` 等
- 查看表结构
- 执行 SQL 查询
- 编辑数据

## 🔴 连接 Redis

### 步骤1：创建 Redis 连接
1. 点击 "Create a new connection"
2. 选择 **Redis**
3. 填写连接信息：
   ```
   Name: HiFate Redis
   Host: localhost
   Port: 6379
   Password: (留空，如果没有设置密码)
   ```
4. 点击 "Test" 测试连接
5. 点击 "Connect" 连接

### 步骤2：查看 Redis 数据
连接成功后，你可以：
- 查看所有键（Keys）
- 查看键值对
- 执行 Redis 命令
- 查看缓存数据

## 🎯 快速连接配置

### MySQL 连接字符串
```
mysql://root:123456@localhost:3306/hifate_bazi
```

### Redis 连接字符串
```
redis://localhost:6379
```

## 📋 常用操作

### MySQL 操作
1. **查看表数据**：
   ```sql
   SELECT * FROM rizhu_gender_contents LIMIT 10;
   ```

2. **查看版本号**：
   ```sql
   SELECT * FROM rule_version;
   ```

3. **查看规则**：
   ```sql
   SELECT * FROM bazi_rules WHERE enabled = 1;
   ```

### Redis 操作
1. **查看所有键**：
   ```
   KEYS *
   ```

2. **查看特定键**：
   ```
   GET bazi:rules:xxxxx
   ```

3. **查看键的类型**：
   ```
   TYPE bazi:rules:xxxxx
   ```

## 🔧 项目相关表

### MySQL 表列表
- `bazi_rules` - 规则表
- `rizhu_gender_contents` - 日柱性别内容表
- `rule_version` - 版本号表
- `bazi_rule_matches` - 规则匹配日志表
- `cache_stats` - 缓存统计表

### Redis 键模式
- `bazi:rules:*` - 规则匹配缓存
- `bazi:*` - 八字相关缓存

## 💡 使用技巧

1. **保存连接**：连接成功后，TablePlus 会自动保存连接信息
2. **多窗口**：可以同时打开多个连接窗口
3. **SQL 历史**：TablePlus 会保存 SQL 查询历史
4. **数据导出**：可以导出查询结果为 CSV、JSON 等格式
5. **快捷键**：`Cmd + Enter` 执行 SQL/命令

## 🚀 开始使用

现在你可以：
1. 打开 TablePlus
2. 创建 MySQL 和 Redis 连接
3. 查看和管理数据库中的数据
4. 通过管理接口更新数据后，在 TablePlus 中查看变化

## 📝 注意事项

1. **MySQL 密码**：默认密码是 `123456`，生产环境建议修改
2. **Redis 密码**：如果设置了密码，需要在连接时填写
3. **端口**：确保 MySQL (3306) 和 Redis (6379) 服务正在运行

---

**安装时间**: 2025-11-05  
**版本**: TablePlus 最新版












