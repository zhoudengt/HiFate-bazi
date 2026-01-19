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

## 主备环境详细配置

### Node1 - 主库 (Master)

| 配置项 | 值 |
|--------|-----|
| 服务器IP（公网） | 8.210.52.217 |
| 服务器IP（内网） | 172.18.121.222 |
| SSH用户 | root |
| SSH密码 | ${SSH_PASSWORD} |
| Docker容器名 | hifate-mysql-master |
| MySQL版本 | 8.0 |
| MySQL端口 | 3306 |
| MySQL用户 | root |
| MySQL密码 | ${SSH_PASSWORD} |
| 数据库名 | hifate_bazi |
| 项目目录 | /opt/HiFate-bazi |

### Node2 - 备库 (Slave)

| 配置项 | 值 |
|--------|-----|
| 服务器IP（公网） | 47.243.160.43 |
| 服务器IP（内网） | 172.18.121.223 |
| SSH用户 | root |
| SSH密码 | ${SSH_PASSWORD} |
| Docker容器名 | hifate-mysql-slave |
| MySQL版本 | 8.0 |
| MySQL端口 | 3306 |
| MySQL用户 | root |
| MySQL密码 | ${SSH_PASSWORD} |
| 数据库名 | hifate_bazi |
| 项目目录 | /opt/HiFate-bazi |

---

## 数据同步方案

### 主从复制原理

```
┌─────────────────────────────────────────────────────────────┐
│                    MySQL 主从复制流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐                    ┌─────────────┐        │
│   │   Master    │                    │   Slave     │        │
│   │  (Node1)    │                    │  (Node2)    │        │
│   └──────┬──────┘                    └──────┬──────┘        │
│          │                                  │               │
│          │ 1. 写入操作                       │               │
│          ▼                                  │               │
│   ┌─────────────┐                           │               │
│   │ Binary Log  │ ──── 2. 传输日志 ────────▶│               │
│   └─────────────┘                           │               │
│                                             ▼               │
│                                      ┌─────────────┐        │
│                                      │ Relay Log   │        │
│                                      └──────┬──────┘        │
│                                             │               │
│                                             │ 3. 重放SQL    │
│                                             ▼               │
│                                      ┌─────────────┐        │
│                                      │   数据      │        │
│                                      │   同步完成  │        │
│                                      └─────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 同步特点

1. **异步复制**：主库写入后立即返回，不等待备库确认
2. **自动同步**：DDL（表结构）和 DML（数据操作）都会自动同步
3. **延迟极低**：正常情况下延迟在毫秒级别
4. **只读备库**：备库默认只读，避免数据冲突

### 同步内容

| 操作类型 | 是否自动同步 | 说明 |
|---------|-------------|------|
| CREATE TABLE | ✅ 是 | 表结构自动同步到备库 |
| ALTER TABLE | ✅ 是 | 表结构修改自动同步 |
| INSERT/UPDATE/DELETE | ✅ 是 | 数据操作自动同步 |
| DROP TABLE | ✅ 是 | 删除操作自动同步（谨慎！） |
| CREATE INDEX | ✅ 是 | 索引自动同步 |

### 检查主从同步状态

```bash
# 在主库查看主从状态
docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' -e "SHOW MASTER STATUS\G"

# 在备库查看同步状态
sshpass -p '${SSH_PASSWORD}' ssh root@47.243.160.43 "docker exec -i hifate-mysql-slave mysql -uroot -p'${SSH_PASSWORD}' -e 'SHOW SLAVE STATUS\G'"

# 关键指标：
# - Slave_IO_Running: Yes
# - Slave_SQL_Running: Yes
# - Seconds_Behind_Master: 0 (延迟秒数)
```

---

## 一键同步脚本

### 快速同步函数（添加到 ~/.bashrc 或 ~/.zshrc）

```bash
# MySQL 迁移同步函数
mysql_migrate() {
    local SQL_FILE=$1
    
    if [ -z "$SQL_FILE" ]; then
        echo "用法: mysql_migrate <sql文件路径>"
        echo "示例: mysql_migrate server/db/migrations/create_xxx.sql"
        return 1
    fi
    
    if [ ! -f "$SQL_FILE" ]; then
        echo "错误: 文件不存在 - $SQL_FILE"
        return 1
    fi
    
    echo "📤 开始同步 SQL 到生产主库..."
    echo "   文件: $SQL_FILE"
    
    # 1. 推送代码到远程
    echo "1️⃣ 推送代码到 Git..."
    git add "$SQL_FILE"
    git commit -m "db: 添加迁移文件 $(basename $SQL_FILE)" --no-verify 2>/dev/null || true
    git push origin master
    git push gitee master
    
    # 2. 在 Node1 主库执行迁移
    echo "2️⃣ 在 Node1 主库执行迁移..."
    sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@8.210.52.217 \
        "cd /opt/HiFate-bazi && git pull origin master && docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi < $SQL_FILE"
    
    # 3. 验证结果
    echo "3️⃣ 验证迁移结果..."
    sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@8.210.52.217 \
        "docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi -e 'SHOW TABLES;'"
    
    echo "✅ 迁移完成！备库将自动同步。"
}

# 检查主从同步状态
mysql_check_sync() {
    echo "🔍 检查主从同步状态..."
    
    echo "📊 主库状态 (Node1):"
    sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@8.210.52.217 \
        "docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' -e 'SHOW MASTER STATUS\G'" 2>/dev/null | grep -E "File|Position"
    
    echo ""
    echo "📊 备库状态 (Node2):"
    sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@47.243.160.43 \
        "docker exec -i hifate-mysql-slave mysql -uroot -p'${SSH_PASSWORD}' -e 'SHOW SLAVE STATUS\G'" 2>/dev/null | grep -E "Slave_IO_Running|Slave_SQL_Running|Seconds_Behind_Master"
}
```

### 使用方法

```bash
# 加载函数（首次使用或新终端）
source ~/.zshrc  # 或 source ~/.bashrc

# 执行迁移
cd /Users/zhoudt/Downloads/project/HiFate-bazi
mysql_migrate server/db/migrations/create_xxx.sql

# 检查同步状态
mysql_check_sync
```

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
sshpass -p '${SSH_PASSWORD}' ssh root@8.210.52.217

# 或手动 SSH
ssh root@8.210.52.217
# 密码：${SSH_PASSWORD}

# 拉取最新代码
cd /opt/HiFate-bazi
git pull origin master

# 在 Docker MySQL 主库中执行迁移
docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi < server/db/migrations/create_xxx.sql
```

### 步骤4：验证迁移结果

```bash
# 验证主库表结构
docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi -e "DESCRIBE table_name;"

# 验证主库表数据（可选）
docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi -e "SELECT COUNT(*) FROM table_name;"
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
docker exec -it hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi

# 执行 SQL 文件
docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi < file.sql

# 执行单条 SQL
docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi -e "SQL语句;"
```

### 一键迁移命令（本地执行）

```bash
# 一键 SSH 到 Node1 并执行迁移
sshpass -p '${SSH_PASSWORD}' ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git pull origin master && docker exec -i hifate-mysql-master mysql -uroot -p'${SSH_PASSWORD}' hifate_bazi < server/db/migrations/create_xxx.sql"
```

---

## 注意事项

1. **只在主库执行**：所有 SQL 迁移只需在 Node1 主库执行，备库会自动同步

2. **可重复执行**：SQL 脚本使用 `IF NOT EXISTS` / `IF EXISTS`，确保可安全重复执行

3. **先测后产**：务必先在本地测试通过，再在生产环境执行

4. **备份重要表**：修改或删除重要表前，先备份数据
   ```bash
   docker exec -i hifate-mysql-master mysqldump -uroot -p'${SSH_PASSWORD}' hifate_bazi table_name > backup.sql
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

