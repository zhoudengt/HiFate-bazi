# LLM 平台切换功能 - 快速开始

## 功能概述

系统现在支持在 Coze 和百炼（通义千问）两个 LLM 平台之间切换，**每个分析接口都可以独立配置**使用哪个平台。

## 快速测试

### 1. 验证代码完整性

```bash
# 检查导入
python3 -c "from server.services.llm_service_factory import LLMServiceFactory; print('✓ 导入成功')"
python3 -c "from server.services.bailian_stream_service import BailianStreamService; print('✓ 导入成功')"
python3 -c "from server.services.coze_stream_service import CozeStreamService; print('✓ 导入成功')"
```

### 2. 测试 API 接口（默认使用 Coze）

```bash
# 测试感情婚姻接口
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "10:00",
    "gender": "male"
  }'
```

### 3. 切换到百炼平台测试

```sql
-- 1. 配置数据库（让感情婚姻接口使用百炼）
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '感情婚姻接口使用百炼', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);

-- 2. 确保已配置百炼 API Key 和 App ID
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES 
  ('BAILIAN_API_KEY', 'sk-xxx', 'string', '百炼平台 API Key', 'bailian', 1, 'production'),
  ('BAILIAN_MARRIAGE_APP_ID', '4bf72d82f83d439cb575856e5bcb8502', 'string', '百炼-感情婚姻 App ID', 'bailian', 1, 'production')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);
```

```bash
# 3. 等待配置缓存过期（5分钟）或重启服务，然后测试
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "10:00",
    "gender": "male"
  }'
```

## Git 提交

### 检查修改的文件

```bash
git status
```

### 提交代码

```bash
# 添加所有修改
git add server/services/base_llm_stream_service.py
git add server/services/bailian_stream_service.py
git add server/services/llm_service_factory.py
git add server/services/coze_stream_service.py
git add server/api/v1/marriage_analysis.py
git add server/api/v1/career_wealth_analysis.py
git add server/api/v1/health_analysis.py
git add server/api/v1/health_analysis_v2.py
git add server/api/v1/children_study_analysis.py
git add server/api/v1/general_review_analysis.py
git add server/api/v1/daily_fortune_calendar.py
git add server/api/v1/wuxing_proportion.py
git add server/api/v1/xishen_jishen.py
git add server/api/v1/annual_report_analysis.py
git add docs/llm/

# 提交
git commit -m "feat: 支持 LLM 平台切换（Coze/百炼），每个接口可独立配置

- 新增 BaseLLMStreamService 抽象基类，定义统一接口
- 新增 BailianStreamService 百炼平台服务（复用 scripts/evaluation/bailian/）
- 新增 LLMServiceFactory 工厂类，根据配置自动选择平台
- 修改 CozeStreamService 继承基类并添加 stream_analysis 方法
- 更新 8 个分析 API 端点支持平台切换
- 添加完整的配置、使用和测试文档
- 保持向后兼容，不影响 bazi_evaluator.py"
```

## 增量部署

### 部署到生产环境

按照 `docs/knowledge_base/deployment_guide.md` 执行增量部署：

```bash
# 1. 连接到 Node1
sshpass -p '${SSH_PASSWORD}' ssh -o StrictHostKeyChecking=no root@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码
git pull origin main

# 4. 安装依赖（如果需要）
pip3 install dashscope>=1.14.0

# 5. 触发热更新（重要！）
python3 scripts/ai/auto_hot_reload.py --trigger

# 6. 验证热更新
python3 scripts/ai/auto_hot_reload.py --verify

# 7. 测试接口
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{"solar_date": "1990-05-15", "solar_time": "10:00", "gender": "male"}'
```

### 部署到 Node2

重复上述步骤，连接到 Node2（47.243.160.43）。

## 配置数据库

部署后，执行配置 SQL：

```bash
# 在服务器上执行
mysql -u your_user -p your_database < docs/llm/database_config.sql
```

或手动配置（见 `docs/llm/database_config.sql`）。

## 验证清单

- [ ] 代码导入测试通过
- [ ] API 接口测试通过（Coze 默认）
- [ ] 配置切换测试通过（切换到百炼）
- [ ] 日志显示正确的平台选择
- [ ] 热更新成功
- [ ] 生产环境接口正常

## 相关文档

- [配置指南](README.md) - 详细的配置说明
- [使用指南](usage_guide.md) - 使用示例和故障排查
- [测试指南](testing_guide.md) - 测试步骤
- [部署检查清单](deployment_checklist.md) - 部署前检查
