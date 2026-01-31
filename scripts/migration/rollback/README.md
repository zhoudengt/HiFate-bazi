# 数据库回滚脚本目录

## 📋 说明

此目录存放数据库回滚脚本，用于在部署失败或发现问题时回滚数据库变更。

## 📝 脚本命名规范

回滚脚本命名格式：`rollback_YYYYMMDD_HHMMSS_description.sql`

示例：
- `rollback_20250115_143000_add_user_table.sql` - 回滚添加用户表的操作
- `rollback_20250115_150000_add_index.sql` - 回滚添加索引的操作

## 🔄 使用方法

### 方式 1：使用回滚脚本

```bash
./scripts/deployment/rollback.sh
```

### 方式 2：手动执行

```bash
mysql -h localhost -u root -p database_name < scripts/migration/rollback/rollback_YYYYMMDD_HHMMSS_description.sql
```

## 📋 回滚脚本模板

```sql
-- ============================================
-- 回滚脚本: rollback_YYYYMMDD_HHMMSS_description.sql
-- 创建时间: YYYY-MM-DD HH:MM:SS
-- 描述: 回滚 XXX 操作
-- ============================================

-- 开始事务
START TRANSACTION;

-- 回滚操作 1: 删除表
DROP TABLE IF EXISTS `new_table`;

-- 回滚操作 2: 删除索引
ALTER TABLE `existing_table` DROP INDEX IF EXISTS `new_index`;

-- 回滚操作 3: 删除字段
ALTER TABLE `existing_table` DROP COLUMN IF EXISTS `new_column`;

-- 提交事务
COMMIT;

-- 验证回滚结果
-- SELECT * FROM information_schema.tables WHERE table_schema = 'database_name';
```

## ⚠️ 注意事项

1. **备份数据**：执行回滚前，确保已备份重要数据
2. **测试环境验证**：先在测试环境验证回滚脚本
3. **记录日志**：回滚操作会自动记录到 `rollback.log`
4. **不可逆操作**：某些操作（如删除数据）无法完全回滚

## 📚 相关文档

- [数据库迁移指南](../README.md)
- [部署文档](../../../deploy/docs/)、[standards/deployment.md](../../../standards/deployment.md)

