# TablePlus MySQL 连接配置步骤

## ✅ 快速连接（已自动配置）

如果 TablePlus 已经打开并显示了连接窗口，请直接点击 "Connect" 连接。

## 📋 手动配置步骤（如果自动配置失败）

### 步骤1：打开 TablePlus
- TablePlus 应该已经打开
- 如果没有，请在应用程序中找到 TablePlus 并打开

### 步骤2：创建 MySQL 连接

1. **点击创建连接按钮**
   - 在 TablePlus 主界面，点击 "Create a new connection" 或 "+" 按钮
   - 或者使用快捷键 `Cmd + N`

2. **选择 MySQL**
   - 在连接类型列表中选择 **MySQL**

3. **填写连接信息**
   ```
   Name（名称）: HiFate MySQL
   Host（主机）: localhost
   Port（端口）: 3306
   User（用户）: root
   Password（密码）: 123456
   Database（数据库）: hifate_bazi
   ```

4. **测试连接**
   - 点击 "Test" 按钮测试连接
   - 如果显示 "Connection successful"，说明连接配置正确

5. **保存并连接**
   - 点击 "Connect" 按钮连接数据库
   - 连接成功后，TablePlus 会自动保存连接信息

## 🎯 连接信息汇总

| 项目 | 值 |
|------|-----|
| **名称** | HiFate MySQL |
| **主机** | localhost |
| **端口** | 3306 |
| **用户** | root |
| **密码** | 123456 |
| **数据库** | hifate_bazi |

## ✅ 验证连接

连接成功后，你应该能看到：

### 数据库中的表：
- `bazi_rules` - 规则表
- `rizhu_gender_contents` - 日柱性别内容表
- `rule_version` - 版本号表
- `bazi_rule_matches` - 规则匹配日志表
- `cache_stats` - 缓存统计表

### 快速测试查询

在 TablePlus 的 SQL 编辑器中执行以下查询：

```sql
-- 查看所有表
SHOW TABLES;

-- 查看版本号
SELECT * FROM rule_version;

-- 查看日柱性别内容（前5条）
SELECT rizhu, gender, enabled, version 
FROM rizhu_gender_contents 
LIMIT 5;

-- 查看规则（前5条）
SELECT rule_code, rule_name, rule_type, enabled 
FROM bazi_rules 
LIMIT 5;
```

## 💡 使用技巧

1. **保存连接**：连接成功后会自动保存，下次可以直接使用
2. **SQL 编辑器**：点击工具栏的 "Query" 按钮或使用快捷键 `Cmd + K` 打开 SQL 编辑器
3. **执行查询**：在 SQL 编辑器中输入 SQL，按 `Cmd + Enter` 执行
4. **查看数据**：在左侧导航栏点击表名，可以查看表结构和数据
5. **编辑数据**：双击单元格可以直接编辑数据

## ❓ 常见问题

### 连接失败？
- 检查 MySQL 是否运行：在终端执行 `brew services list | grep mysql`
- 检查端口是否被占用：`lsof -i :3306`
- 确认密码是否正确：`123456`

### 找不到数据库？
- 确认数据库名称：`hifate_bazi`
- 如果数据库不存在，需要先执行初始化脚本：
  ```bash
  mysql -u root -p123456 < server/db/schema.sql
  ```

### 连接测试失败？
- 检查 MySQL 服务状态：`brew services start mysql`
- 检查防火墙设置
- 确认 MySQL 用户权限

---


**配置完成时间**: 2025-11-05












