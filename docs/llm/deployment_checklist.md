# LLM 平台切换功能部署检查清单

## 部署前检查

### 1. 代码检查

- [ ] 所有新文件已创建：
  - [ ] `server/services/base_llm_stream_service.py`
  - [ ] `server/services/bailian_stream_service.py`
  - [ ] `server/services/llm_service_factory.py`
- [ ] `server/services/coze_stream_service.py` 已修改（继承基类，添加 stream_analysis 方法）
- [ ] 所有 API 端点已更新（8个分析接口）
- [ ] 语法检查通过：`python3 -m py_compile server/services/*.py`

### 2. 依赖检查

- [ ] `requirements.txt` 中包含 `dashscope>=1.14.0`（已确认存在）
- [ ] 生产环境已安装 dashscope（如果使用百炼平台）

### 3. 数据库配置检查

- [ ] 已执行配置 SQL（`docs/llm/database_config.sql`）
- [ ] 至少配置了 Coze 平台（`COZE_ACCESS_TOKEN` 和 `COZE_BOT_ID`）
- [ ] 如果使用百炼，已配置 `BAILIAN_API_KEY` 和对应的 App IDs

### 4. 兼容性检查

- [ ] `scripts/evaluation/bazi_evaluator.py` 不受影响（使用独立的 bailian 模块）
- [ ] 默认行为保持不变（未配置时使用 Coze）

## 本地测试步骤

### 1. 语法检查

```bash
python3 -m py_compile server/services/base_llm_stream_service.py
python3 -m py_compile server/services/bailian_stream_service.py
python3 -m py_compile server/services/llm_service_factory.py
python3 -m py_compile server/services/coze_stream_service.py
```

### 2. 导入测试

```bash
python3 -c "from server.services.llm_service_factory import LLMServiceFactory; print('导入成功')"
python3 -c "from server.services.bailian_stream_service import BailianStreamService; print('导入成功')"
```

### 3. API 接口测试

```bash
# 测试感情婚姻接口（默认使用 Coze）
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "10:00", "gender": "male"}' \
  -v
```

### 4. 配置切换测试

```sql
-- 1. 设置场景级配置
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '测试：感情婚姻使用百炼', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);

-- 2. 等待配置缓存过期（5分钟）或清除缓存
-- 3. 再次测试接口，应该使用百炼平台
```

## Git 提交

### 1. 检查修改的文件

```bash
git status
```

应该看到以下新文件：
- `server/services/base_llm_stream_service.py`
- `server/services/bailian_stream_service.py`
- `server/services/llm_service_factory.py`
- `docs/llm/README.md`
- `docs/llm/database_config.sql`
- `docs/llm/usage_guide.md`
- `docs/llm/testing_guide.md`
- `docs/llm/deployment_checklist.md`

### 2. 提交代码

```bash
# 添加新文件
git add server/services/base_llm_stream_service.py
git add server/services/bailian_stream_service.py
git add server/services/llm_service_factory.py
git add server/services/coze_stream_service.py
git add server/api/v1/*.py  # 更新的 API 端点
git add docs/llm/

# 提交
git commit -m "feat: 支持 LLM 平台切换（Coze/百炼），每个接口可独立配置

- 新增 BaseLLMStreamService 抽象基类
- 新增 BailianStreamService 百炼平台服务
- 新增 LLMServiceFactory 工厂类
- 修改 CozeStreamService 继承基类
- 更新 8 个分析 API 端点支持平台切换
- 添加完整的配置和使用文档
- 保持向后兼容，不影响 bazi_evaluator.py"
```

## 增量部署步骤

### 1. 部署到 Node1（主节点）

```bash
# 1. 连接到 Node1
sshpass -p 'Yuanqizhan@163' ssh -o StrictHostKeyChecking=no root@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码
git pull origin main  # 或相应的分支

# 4. 安装依赖（如果需要）
pip3 install dashscope>=1.14.0

# 5. 触发热更新
python3 scripts/ai/auto_hot_reload.py --trigger

# 6. 验证热更新
python3 scripts/ai/auto_hot_reload.py --verify
```

### 2. 验证 Node1

```bash
# 测试接口
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "10:00", "gender": "male"}' \
  -v

# 查看日志
tail -f /opt/HiFate-bazi/logs/server.log | grep -i "llm\|platform\|bailian"
```

### 3. 部署到 Node2（备节点）

```bash
# 1. 连接到 Node2
sshpass -p 'Yuanqizhan@163' ssh -o StrictHostKeyChecking=no root@47.243.160.43

# 2. 重复 Node1 的步骤
cd /opt/HiFate-bazi
git pull origin main
pip3 install dashscope>=1.14.0
python3 scripts/ai/auto_hot_reload.py --trigger
python3 scripts/ai/auto_hot_reload.py --verify
```

### 4. 验证 Node2

同 Node1 的验证步骤。

## 部署后验证

### 1. 功能验证

- [ ] 默认接口使用 Coze（未配置时）
- [ ] 配置百炼后接口使用百炼
- [ ] 场景级配置优先级正确
- [ ] 配置热更新生效

### 2. 日志检查

查看服务日志，确认：
- [ ] 没有导入错误
- [ ] 平台选择逻辑正确
- [ ] 服务创建成功

### 3. 性能检查

- [ ] 接口响应时间正常
- [ ] 没有内存泄漏
- [ ] 错误处理正常

## 回滚方案

如果出现问题，可以快速回滚：

```sql
-- 1. 回滚全局配置到 Coze
UPDATE service_configs SET config_value='coze' WHERE config_key='LLM_PLATFORM';

-- 2. 删除场景级配置
DELETE FROM service_configs WHERE config_key LIKE '%_LLM_PLATFORM';

-- 3. 触发热更新（配置会立即生效）
```

或者回滚代码：

```bash
# 回滚到上一个版本
git revert HEAD
git push origin main

# 触发热更新
python3 scripts/ai/auto_hot_reload.py --trigger
```

## 注意事项

1. **热更新**：所有代码更新必须通过热更新，禁止重启服务
2. **配置缓存**：配置有 5 分钟缓存，修改配置后可能需要等待
3. **依赖安装**：如果使用百炼平台，确保已安装 dashscope
4. **向后兼容**：默认行为保持不变，不影响现有功能
