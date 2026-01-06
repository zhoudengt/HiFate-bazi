# MySQL 迁移指南

本文档记录 HiFate-bazi 项目的 MySQL 数据库迁移标准流程，供开发人员参考。

---

## 数据库架构

```
┌─────────────────────────────────────────┐
│       Node1 (8.210.52.217)              │
│       hifate-mysql-master               │
│       MySQL 8.0 - 主库 Master           │
│       端口：3306                         │
└───────────────┬─────────────────────────┘
                │ 自动同步（主从复制）
                ▼
┌─────────────────────────────────────────┐
│       Node2 (47.243.160.43)             │
│       MySQL 8.0 - 备库 Slave            │
│       端口：3306                         │
└─────────────────────────────────────────┘
```

**重要**：只需在 Node1 主库执行 SQL 迁移，备库会自动同步表结构和数据。

---

## 迁移文件规范

### 存放位置

```
server/db/migrations/
├── create_xxx.sql      # 创建新表
├── alter_xxx.sql       # 修改表结构
├── add_xxx.sql         # 添加字段/索引
└── drop_xxx.sql        # 删除表/字段（谨慎使用）
```

### 命名规范

| 操作类型 | 命名格式 | 示例 |
|---------|---------|------|
| 创建表 | `create_表名.sql` | `create_conversation_history.sql` |
| 修改表 | `alter_表名_描述.sql` | `alter_users_add_phone.sql` |
| 添加索引 | `add_index_表名_字段.sql` | `add_index_users_email.sql` |
| 删除表 | `drop_表名.sql` | `drop_temp_data.sql` |

### SQL 编写规范

1. **使用 IF NOT EXISTS / IF EXISTS**：确保脚本可重复执行
   ```sql
   CREATE TABLE IF NOT EXISTS `table_name` (...);
   DROP TABLE IF EXISTS `table_name`;
   ```

2. **指定数据库**：在脚本开头指定目标数据库
   ```sql
   USE `hifate_bazi`;
   ```

3. **添加注释**：表和关键字段必须有注释
   ```sql
   CREATE TABLE `table_name` (
       `id` BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
       ...
   ) COMMENT='表说明';
   ```

4. **字符集**：统一使用 `utf8mb4`
   ```sql
   ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
   ```

---

## 迁移流程

### 步骤1：本地开发和测试

```bash
# 在本地 MySQL 执行 SQL 迁移
cd /Users/zhoudt/Downloads/project/HiFate-bazi
mysql -u root -p123456 hifate_bazi < server/db/migrations/create_xxx.sql

# 验证表结构
mysql -u root -p123456 hifate_bazi -e "DESCRIBE table_name;"
```

### 步骤2：提交到 Git

```bash
# 添加迁移文件
git add server/db/migrations/create_xxx.sql

# 提交（附带清晰的提交信息）
git commit -m "feat: 添加xxx表"

# 推送到远程仓库
git push origin master
git push gitee master
```

### 步骤3：在生产主库执行迁移

```bash
# SSH 到 Node1 主库服务器
sshpass -p 'Yuanqizhan@163' ssh root@8.210.52.217

# 或手动 SSH
ssh root@8.210.52.217
# 密码：Yuanqizhan@163

# 拉取最新代码
cd /opt/HiFate-bazi
git pull origin master

# 在 Docker MySQL 主库中执行迁移
docker exec -i hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi < server/db/migrations/create_xxx.sql
```

### 步骤4：验证迁移结果

```bash
# 验证主库表结构
docker exec -i hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi -e "DESCRIBE table_name;"

# 验证主库表数据（可选）
docker exec -i hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi -e "SELECT COUNT(*) FROM table_name;"
```

---

## 常用命令参考

### 本地 MySQL 命令

```bash
# 连接本地 MySQL
mysql -u root -p123456 hifate_bazi

# 执行 SQL 文件
mysql -u root -p123456 hifate_bazi < file.sql

# 查看表结构
mysql -u root -p123456 hifate_bazi -e "DESCRIBE table_name;"

# 查看表列表
mysql -u root -p123456 hifate_bazi -e "SHOW TABLES;"
```

### 生产 Docker MySQL 命令

```bash
# 查看 MySQL 容器
docker ps | grep mysql

# 进入 MySQL 容器交互模式
docker exec -it hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi

# 执行 SQL 文件
docker exec -i hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi < file.sql

# 执行单条 SQL
docker exec -i hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi -e "SQL语句;"
```

### 一键迁移命令（本地执行）

```bash
# 一键 SSH 到 Node1 并执行迁移
sshpass -p 'Yuanqizhan@163' ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git pull origin master && docker exec -i hifate-mysql-master mysql -uroot -p'Yuanqizhan@163' hifate_bazi < server/db/migrations/create_xxx.sql"
```

---

## 注意事项

1. **只在主库执行**：所有 SQL 迁移只需在 Node1 主库执行，备库会自动同步

2. **可重复执行**：SQL 脚本使用 `IF NOT EXISTS` / `IF EXISTS`，确保可安全重复执行

3. **先测后产**：务必先在本地测试通过，再在生产环境执行

4. **备份重要表**：修改或删除重要表前，先备份数据
   ```bash
   docker exec -i hifate-mysql-master mysqldump -uroot -p'Yuanqizhan@163' hifate_bazi table_name > backup.sql
   ```

5. **大表迁移**：对于大表的结构修改，考虑在低峰期执行，或使用 `pt-online-schema-change` 工具

6. **敏感信息**：密码等敏感信息不要硬编码在脚本中，使用环境变量或配置文件

---

## 已执行的迁移记录

| 日期 | 迁移文件 | 说明 |
|------|---------|------|
| 2026-01-06 | `create_conversation_history.sql` | AI问答对话历史表 |

---

## 相关文档

- [部署指南](deployment_guide.md)
- [错误记录本](error_records.md)
- [开发规范](development_rules.md)

