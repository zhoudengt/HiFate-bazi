# 数据库导入脚本使用说明

## 📋 概述

已生成数据库导入脚本（INSERT ... ON DUPLICATE KEY UPDATE 模式），支持：
- ✅ 如果记录存在则更新（UPDATE）
- ✅ 如果记录不存在则插入（INSERT）
- ✅ 保留表结构（CREATE TABLE）
- ✅ 包含所有表和数据

## 📁 文件说明

### 1. 生成脚本
- **`generate_import_script_v2.py`** - Python 脚本，用于生成导入 SQL 文件
- **`generate_import_script.sh`** - Shell 脚本（备用）

### 2. 导入脚本
- **`hifate_db_import_20251231_182038.sql`** - 已生成的导入 SQL 文件（1.74 MB）
  - 已上传到 Node1: `/opt/HiFate-bazi/scripts/db/`
  - 需要手动上传到 Node2: `/opt/HiFate-bazi/scripts/db/`

### 3. 执行脚本
- **`import_database_production.sh`** - 生产环境执行脚本
  - 已上传到 Node1: `/opt/HiFate-bazi/scripts/db/`
  - 需要手动上传到 Node2: `/opt/HiFate-bazi/scripts/db/`

## 🚀 使用方法

### 方法 1：使用执行脚本（推荐）

**在 Node1 执行：**
```bash
cd /opt/HiFate-bazi
bash scripts/db/import_database_production.sh scripts/db/hifate_db_import_20251231_182038.sql
```

**在 Node2 执行：**
```bash
cd /opt/HiFate-bazi
bash scripts/db/import_database_production.sh scripts/db/hifate_db_import_20251231_182038.sql
```

### 方法 2：手动执行

**在 Node1 和 Node2 执行：**
```bash
cd /opt/HiFate-bazi
source .env
mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < scripts/db/hifate_db_import_20251231_182038.sql
```

## 📤 上传文件到 Node2（如果未上传）

如果 Node2 的文件未上传成功，请手动上传：

```bash
# 从本地 Mac 上传
scp /tmp/hifate_db_import_20251231_182038.sql root@47.243.160.43:/opt/HiFate-bazi/scripts/db/
scp scripts/db/import_database_production.sh root@47.243.160.43:/opt/HiFate-bazi/scripts/db/
```

## ✅ 验证导入结果

导入完成后，验证：

```bash
# 检查表数量
mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE \
  -e "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = DATABASE()"

# 检查 bazi_rules 表数据量
mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE \
  -e "SELECT COUNT(*) FROM bazi_rules WHERE enabled = 1"

# 测试接口
curl -X POST http://localhost:8001/api/v1/children-study/stream \
  -H 'Content-Type: application/json' \
  -d '{"solar_date": "1990-01-15", "solar_time": "12:00", "gender": "male"}'
```

## 🔄 重新生成导入脚本

如果需要重新生成导入脚本（本地数据库有更新）：

```bash
cd /Users/zhoudt/Downloads/project/HiFate-bazi
python3 scripts/db/generate_import_script_v2.py --password 123456
```

然后按照上述步骤上传和执行。

## ⚠️ 注意事项

1. **备份数据**：导入前建议备份生产数据库
2. **双机同步**：必须在 Node1 和 Node2 都执行导入
3. **执行顺序**：建议先执行 Node1，验证无误后再执行 Node2
4. **验证接口**：导入后必须测试接口是否正常

## 📊 导入脚本统计

- **文件大小**：1.74 MB
- **INSERT 语句数**：1253 条
- **ON DUPLICATE KEY UPDATE 语句数**：1253 条
- **包含表结构**：是
- **包含数据**：是

## 🐛 故障排查

### 问题 1：导入失败 - Access denied

**原因**：MySQL 密码错误或用户权限不足

**解决**：
```bash
# 检查 .env 文件中的 MySQL 配置
cat /opt/HiFate-bazi/.env | grep MYSQL

# 手动测试连接
mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD -e "SELECT 1"
```

### 问题 2：导入失败 - Table doesn't exist

**原因**：表结构未创建

**解决**：导入脚本包含 CREATE TABLE 语句，如果失败，检查 SQL 文件是否完整

### 问题 3：导入后接口仍报错

**原因**：数据未正确导入或缓存未清理

**解决**：
```bash
# 检查数据
mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE \
  -e "SELECT COUNT(*) FROM bazi_rules WHERE enabled = 1"

# 清理缓存（如果使用 Redis）
# 或重启服务
```

## 📞 支持

如有问题，请检查：
1. SQL 文件是否完整上传
2. MySQL 连接是否正常
3. 环境变量是否正确
4. 执行脚本权限是否正确（chmod +x）

