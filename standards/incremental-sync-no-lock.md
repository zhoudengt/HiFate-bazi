# 无锁表增量数据同步和配置同步规范

## 概述

本文档描述无锁表的MySQL增量数据同步方案和配置同步方案，解决导入阶段锁表问题，并支持bot_id等配置的同步。

## 问题背景

### MySQL数据同步锁表问题

- **问题**：导入阶段可能锁表，影响生产环境
- **原因**：现有方案使用 `mysqldump --add-drop-database` 会删除数据库，直接导入可能锁表

### 配置同步需求

- 需要同步 bot_id 等配置到生产环境
- 需要支持配置验证和服务重启

## 解决方案

### 1. 无锁表增量数据同步方案

#### 核心原则

- ✅ 使用增量同步，只同步变更的数据
- ✅ 导入时使用事务和 `INSERT ... ON DUPLICATE KEY UPDATE` 避免锁表
- ✅ 支持按表同步，可以选择性同步
- ✅ 支持数据对比，只导出差异数据

#### 技术实现

**数据导出（无锁）**：
```bash
mysqldump --single-transaction --skip-lock-tables --no-create-info --skip-triggers
```

- `--single-transaction`：使用事务快照，不锁表
- `--skip-lock-tables`：跳过锁表操作
- `--no-create-info`：不导出表结构（只导出数据）
- `--skip-triggers`：跳过触发器（避免触发器执行时锁表）

**数据导入（无锁）**：
- 使用 `INSERT ... ON DUPLICATE KEY UPDATE` 语句
- 使用事务包装，确保原子性
- 分批导入，避免长时间锁表

#### 实现文件

1. **`scripts/db/sync_incremental_data_no_lock.py`** - Python增量同步脚本
   - 对比本地和生产数据
   - 生成增量SQL（使用 `INSERT ... ON DUPLICATE KEY UPDATE`）
   - 支持按表同步
   - 支持按条件同步（如按时间戳）

2. **`scripts/db/sync_incremental_data_no_lock.sh`** - Shell包装脚本
   - 调用Python脚本
   - 处理SSH连接
   - 执行同步到Node1和Node2

3. **`scripts/db/compare_data.py`** - 数据对比工具
   - 对比本地和生产数据
   - 生成差异报告
   - 支持按表、按字段对比

#### 同步流程

```
1. 数据对比（本地 vs 生产）
   ├─ 检测新增数据
   ├─ 检测修改数据
   └─ 检测删除数据（可选）
   ↓
2. 生成增量SQL
   ├─ 使用 INSERT ... ON DUPLICATE KEY UPDATE
   ├─ 使用事务包装
   └─ 分批生成（避免单次导入过大）
   ↓
3. 同步到Node1（灰度节点）
   ├─ 上传增量SQL
   ├─ 执行导入（事务）
   └─ 验证同步结果
   ↓
4. Node1功能测试
   ├─ 如果测试通过 → 继续到步骤5
   └─ 如果测试失败 → 回滚事务
   ↓
5. 同步到Node2（生产节点）
   ├─ 上传增量SQL
   ├─ 执行导入（事务）
   └─ 验证同步结果
```

### 2. 配置同步方案

#### 现有功能

**已有工具**：
- `scripts/config/detect_config_changes.py` - 配置变更检测
- `scripts/config/sync_production_config.sh` - 配置同步脚本

**功能确认**：
- ✅ 支持检测配置变更（新增、修改、删除）
- ✅ 支持同步到Node1和Node2
- ✅ 支持备份生产配置
- ✅ 支持配置格式验证

#### 增强功能

**新增功能**：
- ✅ 支持配置同步后验证（如验证bot_id是否生效）
- ✅ 支持自动重启相关服务（可选）
- ✅ 支持配置同步回滚

**配置同步流程**：
```
1. 检测配置变更
   ├─ 运行 detect_config_changes.py
   └─ 查看变更报告
   ↓
2. 同步到Node1（灰度节点）
   ├─ 备份生产配置
   ├─ 上传配置文件
   ├─ 验证配置格式
   └─ 验证配置生效（如测试bot_id）
   ↓
3. Node1功能测试
   ├─ 如果测试通过 → 继续到步骤4
   └─ 如果测试失败 → 回滚配置
   ↓
4. 同步到Node2（生产节点）
   ├─ 备份生产配置
   ├─ 上传配置文件
   ├─ 验证配置格式
   └─ 验证配置生效
```

## 使用方式

### 增量数据同步

#### 1. 检测数据差异

```bash
# 对比本地和生产数据
python3 scripts/db/sync_incremental_data_no_lock.py --compare --node node1

# 对比指定表
python3 scripts/db/sync_incremental_data_no_lock.py --compare --node node1 --tables bazi_rules,daily_fortune_jianchu
```

#### 2. 生成增量SQL

```bash
# 生成所有表的增量SQL
python3 scripts/db/sync_incremental_data_no_lock.py --sync

# 生成指定表的增量SQL
python3 scripts/db/sync_incremental_data_no_lock.py --sync --tables bazi_rules,daily_fortune_jianchu

# 指定输出文件
python3 scripts/db/sync_incremental_data_no_lock.py --sync --output /tmp/my_sync.sql
```

#### 3. 同步到生产环境

```bash
# 同步到Node1（预览模式）
bash scripts/db/sync_incremental_data_no_lock.sh --node node1 --dry-run

# 同步到Node1（执行模式）
bash scripts/db/sync_incremental_data_no_lock.sh --node node1

# 同步到Node2（执行模式）
bash scripts/db/sync_incremental_data_no_lock.sh --node node2

# 同步指定表
bash scripts/db/sync_incremental_data_no_lock.sh --node node1 --tables bazi_rules,daily_fortune_jianchu
```

### 配置同步

#### 1. 检测配置变更

```bash
# 检测配置变更
python3 scripts/config/detect_config_changes.py

# 检测指定节点的配置变更
python3 scripts/config/detect_config_changes.py --prod-host 8.210.52.217

# 保存报告到文件
python3 scripts/config/detect_config_changes.py --output config_changes_report.txt
```

#### 2. 同步配置到生产环境

```bash
# 同步到Node1（预览模式）
bash scripts/config/sync_production_config.sh --node node1 --dry-run

# 同步到Node1（执行模式）
bash scripts/config/sync_production_config.sh --node node1

# 同步到Node1并验证配置
bash scripts/config/sync_production_config.sh --node node1 --verify

# 同步到Node1并自动重启服务
bash scripts/config/sync_production_config.sh --node node1 --auto-restart

# 同步到Node1并验证配置和自动重启服务
bash scripts/config/sync_production_config.sh --node node1 --verify --auto-restart

# 同步到Node2（执行模式）
bash scripts/config/sync_production_config.sh --node node2

# 回滚配置
bash scripts/config/sync_production_config.sh --node node1 --rollback
```

## 关键特性

### 无锁表同步

- **导出阶段**：使用 `--single-transaction` 和 `--skip-lock-tables`，不锁表
- **导入阶段**：使用 `INSERT ... ON DUPLICATE KEY UPDATE` 和事务，避免锁表
- **分批处理**：支持分批导入，避免长时间锁表

### 增量同步

- **数据对比**：快速对比表数据（使用行数和校验和）
- **差异检测**：检测新增、修改、删除的数据
- **选择性同步**：支持按表同步，只同步需要的表

### 配置验证

- **格式验证**：验证配置文件格式正确性
- **配置验证**：验证关键配置是否生效（如bot_id）
- **服务重启**：可选自动重启相关服务

### 回滚支持

- **配置回滚**：支持快速回滚到备份配置
- **数据回滚**：支持事务回滚（如果同步失败）

## 注意事项

### 数据同步注意事项

1. **主键要求**：表必须有主键才能使用 `INSERT ... ON DUPLICATE KEY UPDATE`
2. **数据一致性**：同步前建议先对比数据，确认需要同步的内容
3. **事务支持**：确保MySQL支持事务（InnoDB引擎）
4. **备份建议**：重要数据同步前建议先备份

### 配置同步注意事项

1. **敏感信息**：配置文件中包含敏感信息（密码、密钥等），注意保护
2. **服务重启**：修改应用配置（如bot_id）可能需要重启Web服务
3. **配置验证**：同步后建议验证配置是否生效
4. **备份保留**：备份文件会保留，可以用于回滚

## 故障排查

### 数据同步失败

1. **检查数据库连接**：确认本地和生产数据库连接正常
2. **检查表结构**：确认表有主键
3. **检查SQL文件**：查看生成的SQL文件是否有语法错误
4. **查看错误日志**：查看MySQL错误日志

### 配置同步失败

1. **检查配置文件格式**：确认配置文件格式正确
2. **检查SSH连接**：确认SSH连接正常
3. **检查文件权限**：确认配置文件权限正确
4. **查看备份文件**：如有问题，可以回滚到备份

## 相关文档

- **数据库同步规范**：`standards/deployment.md`（数据库同步部分）
- **配置同步规范**：`standards/deployment.md`（配置同步部分）
- **增量部署规范**：`standards/deployment.md`（增量部署部分）

