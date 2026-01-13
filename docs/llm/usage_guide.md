# LLM 平台切换使用指南

## 快速开始

### 1. 安装依赖

如果使用百炼平台，需要确保已安装 `dashscope`：

```bash
pip install dashscope
```

### 2. 配置数据库

执行配置脚本（根据实际情况修改配置值）：

```bash
mysql -u your_user -p your_database < docs/llm/database_config.sql
```

或手动执行 SQL（见 `docs/llm/database_config.sql`）。

### 3. 验证配置

```sql
-- 查看全局平台配置
SELECT config_key, config_value FROM service_configs WHERE config_key='LLM_PLATFORM';

-- 查看场景级配置
SELECT config_key, config_value FROM service_configs WHERE config_key LIKE '%_LLM_PLATFORM';
```

## 常见使用场景

### 场景 1：全部使用 Coze（默认）

无需配置，系统默认使用 Coze。

### 场景 2：全部切换到百炼

```sql
-- 1. 设置全局平台
UPDATE service_configs SET config_value='bailian' WHERE config_key='LLM_PLATFORM';

-- 2. 确保已配置百炼 API Key 和 App IDs
SELECT config_key, config_value FROM service_configs WHERE category='bailian';
```

### 场景 3：混合使用

让部分接口使用百炼，其他接口使用 Coze：

```sql
-- 1. 全局默认使用 Coze
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';

-- 2. 只让感情婚姻和事业财富使用百炼
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '感情婚姻接口使用百炼', 'llm', 1, 'production'),
  ('CAREER_WEALTH_LLM_PLATFORM', 'bailian', 'string', '事业财富接口使用百炼', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);
```

### 场景 4：A/B 测试

可以快速切换平台进行对比测试：

```sql
-- 切换到百炼
UPDATE service_configs SET config_value='bailian' WHERE config_key='LLM_PLATFORM';

-- 切换回 Coze
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';
```

## 配置修改操作

### 修改全局平台

```sql
-- 切换到百炼
UPDATE service_configs SET config_value='bailian' WHERE config_key='LLM_PLATFORM';

-- 切换回 Coze
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';
```

### 修改场景级平台

```sql
-- 让感情婚姻接口使用百炼
UPDATE service_configs SET config_value='bailian' WHERE config_key='MARRIAGE_LLM_PLATFORM';

-- 让感情婚姻接口使用 Coze（或删除配置使用全局默认）
DELETE FROM service_configs WHERE config_key='MARRIAGE_LLM_PLATFORM';
```

### 更新 API Key 或 App ID

```sql
-- 更新百炼 API Key
UPDATE service_configs SET config_value='sk-new_api_key' WHERE config_key='BAILIAN_API_KEY';

-- 更新感情婚姻 App ID
UPDATE service_configs SET config_value='new_app_id' WHERE config_key='BAILIAN_MARRIAGE_APP_ID';
```

## 热更新

配置修改后立即生效，无需重启服务。系统每次调用时都会从数据库读取最新配置（有 5 分钟缓存）。

## 故障排查

### 问题 1：接口返回错误，提示配置缺失

**解决方案**：

1. 检查是否配置了对应平台的必要参数：
   - Coze：`COZE_ACCESS_TOKEN` 和 `COZE_BOT_ID`
   - 百炼：`BAILIAN_API_KEY` 和对应的 `BAILIAN_*_APP_ID`

2. 检查配置是否正确：

```sql
-- 检查 Coze 配置
SELECT config_key, config_value FROM service_configs 
WHERE config_key IN ('COZE_ACCESS_TOKEN', 'COZE_BOT_ID');

-- 检查百炼配置
SELECT config_key, config_value FROM service_configs 
WHERE config_key LIKE 'BAILIAN_%';
```

### 问题 2：接口仍然使用 Coze，没有切换到百炼

**解决方案**：

1. 检查场景级配置是否存在（优先级高于全局配置）：

```sql
SELECT config_key, config_value FROM service_configs 
WHERE config_key LIKE '%_LLM_PLATFORM';
```

2. 检查全局配置：

```sql
SELECT config_key, config_value FROM service_configs 
WHERE config_key='LLM_PLATFORM';
```

3. 查看服务日志，确认实际使用的平台：

```
INFO: 为场景 marriage 选择平台: bailian
```

### 问题 3：百炼服务创建失败，自动回退到 Coze

**可能原因**：

1. 未安装 `dashscope` SDK
2. `BAILIAN_API_KEY` 配置错误
3. 对应的 `BAILIAN_*_APP_ID` 未配置

**解决方案**：

```bash
# 安装依赖
pip install dashscope

# 检查配置
SELECT config_key, config_value FROM service_configs 
WHERE config_key IN ('BAILIAN_API_KEY', 'BAILIAN_MARRIAGE_APP_ID');
```

### 问题 4：需要快速回滚

**解决方案**：

```sql
-- 回滚全局配置到 Coze
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';

-- 删除所有场景级配置（让它们使用全局配置）
DELETE FROM service_configs WHERE config_key LIKE '%_LLM_PLATFORM';
```

## 性能优化建议

1. **配置缓存**：系统有 5 分钟配置缓存，频繁修改配置可能不会立即生效
2. **批量配置**：如果需要修改多个场景，建议使用事务批量更新
3. **监控日志**：关注服务日志，确认平台切换是否成功

## 注意事项

1. **评测脚本兼容性**：`scripts/evaluation/bazi_evaluator.py` 不受影响，它直接使用 `scripts/evaluation/bailian/` 目录下的代码
2. **配置优先级**：场景级配置 > 全局配置 > 默认值（coze）
3. **错误处理**：如果百炼服务创建失败，系统会自动回退到 Coze
4. **配置验证**：修改配置后建议查看日志确认生效

## 相关文档

- [配置指南](README.md) - 详细的配置说明
- [数据库配置 SQL](database_config.sql) - 完整的配置 SQL 脚本
