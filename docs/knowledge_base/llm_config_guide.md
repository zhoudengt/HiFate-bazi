# 面相与风水大模型 ID 配置指南

> **最后更新**：2026-01-22

---

## 📍 配置位置

面相与风水的大模型 ID **配置在数据库的 `service_configs` 表中**，不在环境变量或配置文件中。

### 数据库表：`service_configs`

**表结构**：
- `config_key`: 配置键（字符串）
- `config_value`: 配置值（字符串）
- `description`: 配置描述
- `created_at`: 创建时间
- `updated_at`: 更新时间

---

## 🔧 配置项说明

### 面相分析配置

| 配置键 | 说明 | 默认值 | 用途 |
|--------|------|--------|------|
| `FACE_ANALYSIS_BOT_ID` | Coze Bot ID（用于日志记录） | `7597406985550282787` | Coze 平台使用时的 Bot ID |
| `FACE_ANALYSIS_LLM_PLATFORM` | LLM 平台选择 | `bailian` | 可选：`bailian` 或 `coze` |
| `BAILIAN_FACE_ANALYSIS_APP_ID` | 百炼应用 ID | `23f6ddd0ed1c4fb2aba2a21f238f1820` | 百炼平台使用时的 App ID |

### 办公桌风水配置

| 配置键 | 说明 | 默认值 | 用途 |
|--------|------|--------|------|
| `DESK_FENGSHUI_BOT_ID` | Coze Bot ID（用于日志记录） | `7597409425955127336` | Coze 平台使用时的 Bot ID |
| `DESK_FENGSHUI_LLM_PLATFORM` | LLM 平台选择 | `bailian` | 可选：`bailian` 或 `coze` |
| `BAILIAN_DESK_FENGSHUI_APP_ID` | 百炼应用 ID | `0a8d1685044d44a78628e427c98c901c` | 百炼平台使用时的 App ID |

---

## 📝 配置方式

### 方式 1：执行 SQL 脚本（推荐）

```bash
# 在服务器上执行
docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi < scripts/db/init_face_desk_stream_configs.sql
```

### 方式 2：直接 SQL 插入

```sql
USE hifate_bazi;

-- 面相分析配置
INSERT INTO service_configs (config_key, config_value, description, created_at, updated_at) 
VALUES 
('FACE_ANALYSIS_BOT_ID', '7597406985550282787', '面相分析 Bot ID（用于日志记录）', NOW(), NOW()),
('FACE_ANALYSIS_LLM_PLATFORM', 'bailian', '面相分析使用的LLM平台（bailian/coze）', NOW(), NOW()),
('BAILIAN_FACE_ANALYSIS_APP_ID', '23f6ddd0ed1c4fb2aba2a21f238f1820', '面相分析百炼应用ID', NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = NOW();

-- 办公桌风水配置
INSERT INTO service_configs (config_key, config_value, description, created_at, updated_at) 
VALUES 
('DESK_FENGSHUI_BOT_ID', '7597409425955127336', '办公桌风水 Bot ID（用于日志记录）', NOW(), NOW()),
('DESK_FENGSHUI_LLM_PLATFORM', 'bailian', '办公桌风水使用的LLM平台（bailian/coze）', NOW(), NOW()),
('BAILIAN_DESK_FENGSHUI_APP_ID', '0a8d1685044d44a78628e427c98c901c', '办公桌风水百炼应用ID', NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    config_value = VALUES(config_value),
    description = VALUES(description),
    updated_at = NOW();
```

### 方式 3：使用数据库同步脚本

```bash
# 从本地同步配置到生产环境
python3 scripts/db/sync_local_to_production.py --tables service_configs --prod-host 8.210.52.217 --prod-port 3306 --prod-user root --prod-password "Yuanqizhan@163" --use-python-exec
```

---

## 🔍 配置读取逻辑

### 代码位置

1. **配置加载器**：`server/config/config_loader.py`
   - `get_config_from_db_only()`: 只从数据库读取配置（不降级到环境变量）

2. **流式接口**：
   - 面相分析：`server/api/v2/face_analysis_stream.py`
   - 办公桌风水：`server/api/v2/desk_fengshui_stream.py`

3. **LLM 服务工厂**：`server/services/llm_service_factory.py`
   - 根据 `FACE_ANALYSIS_LLM_PLATFORM` 或 `DESK_FENGSHUI_LLM_PLATFORM` 选择平台

4. **百炼流式服务**：`server/services/bailian_stream_service.py`
   - 从数据库读取 `BAILIAN_FACE_ANALYSIS_APP_ID` 或 `BAILIAN_DESK_FENGSHUI_APP_ID`

### 读取流程

```
1. 流式接口调用 LLMServiceFactory.get_service(scene="face_analysis" 或 "desk_fengshui")
   ↓
2. LLMServiceFactory 读取 FACE_ANALYSIS_LLM_PLATFORM 或 DESK_FENGSHUI_LLM_PLATFORM
   ↓
3. 如果平台是 "bailian"：
   - 创建 BailianStreamService
   - 从数据库读取 BAILIAN_FACE_ANALYSIS_APP_ID 或 BAILIAN_DESK_FENGSHUI_APP_ID
   ↓
4. 如果平台是 "coze"：
   - 创建 CozeStreamService
   - 从数据库读取 FACE_ANALYSIS_BOT_ID 或 DESK_FENGSHUI_BOT_ID（或降级到 COZE_BOT_ID）
```

---

## ✅ 验证配置

### 查询配置

```sql
-- 查看面相和风水的所有配置
SELECT config_key, config_value, description 
FROM service_configs 
WHERE config_key IN (
    'FACE_ANALYSIS_BOT_ID',
    'FACE_ANALYSIS_LLM_PLATFORM',
    'BAILIAN_FACE_ANALYSIS_APP_ID',
    'DESK_FENGSHUI_BOT_ID',
    'DESK_FENGSHUI_LLM_PLATFORM',
    'BAILIAN_DESK_FENGSHUI_APP_ID'
)
ORDER BY config_key;
```

### 在服务器上验证

```bash
# 在服务器 Docker MySQL 中查询
docker exec hifate-mysql-master mysql -uroot -pYuanqizhan@163 hifate_bazi -e "
SELECT config_key, config_value, description 
FROM service_configs 
WHERE config_key LIKE '%FACE%' OR config_key LIKE '%DESK%' 
ORDER BY config_key;
"
```

---

## 🔄 修改配置

### 修改平台（从 Coze 切换到百炼）

```sql
UPDATE service_configs 
SET config_value = 'bailian', updated_at = NOW()
WHERE config_key = 'FACE_ANALYSIS_LLM_PLATFORM';

UPDATE service_configs 
SET config_value = 'bailian', updated_at = NOW()
WHERE config_key = 'DESK_FENGSHUI_LLM_PLATFORM';
```

### 修改百炼 App ID

```sql
UPDATE service_configs 
SET config_value = '新的App ID', updated_at = NOW()
WHERE config_key = 'BAILIAN_FACE_ANALYSIS_APP_ID';

UPDATE service_configs 
SET config_value = '新的App ID', updated_at = NOW()
WHERE config_key = 'BAILIAN_DESK_FENGSHUI_APP_ID';
```

### 修改 Coze Bot ID

```sql
UPDATE service_configs 
SET config_value = '新的Bot ID', updated_at = NOW()
WHERE config_key = 'FACE_ANALYSIS_BOT_ID';

UPDATE service_configs 
SET config_value = '新的Bot ID', updated_at = NOW()
WHERE config_key = 'DESK_FENGSHUI_BOT_ID';
```

---

## ⚠️ 注意事项

1. **配置修改后需要触发热更新**：
   ```bash
   curl -X POST http://8.210.52.217:8001/api/v1/hot-reload/trigger
   ```

2. **配置缓存**：配置有 5 分钟缓存，修改后可能需要等待缓存过期，或触发热更新立即生效

3. **必须配置项**：
   - 如果使用百炼平台：必须配置 `BAILIAN_API_KEY` 和对应的 `BAILIAN_*_APP_ID`
   - 如果使用 Coze 平台：必须配置 `COZE_ACCESS_TOKEN` 和对应的 `*_BOT_ID`（或 `COZE_BOT_ID`）

---

## 📚 相关文件

- **配置脚本**：`scripts/db/init_face_desk_stream_configs.sql`
- **配置加载器**：`server/config/config_loader.py`
- **流式接口**：
  - `server/api/v2/face_analysis_stream.py`
  - `server/api/v2/desk_fengshui_stream.py`
- **LLM 服务工厂**：`server/services/llm_service_factory.py`
- **百炼流式服务**：`server/services/bailian_stream_service.py`
