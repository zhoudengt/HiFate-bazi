# LLM 平台切换功能测试指南

## 快速测试

### 1. 语法检查

```bash
# 检查新创建的文件语法
python3 -m py_compile server/services/base_llm_stream_service.py
python3 -m py_compile server/services/bailian_stream_service.py
python3 -m py_compile server/services/llm_service_factory.py
```

### 2. 运行测试脚本

```bash
# 测试平台选择逻辑
python3 scripts/test_llm_platform_switch.py
```

### 3. 测试 API 接口

#### 测试 Coze 平台（默认）

```bash
# 测试感情婚姻接口（使用 Coze）
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "10:00",
    "gender": "male"
  }'
```

#### 测试百炼平台

1. 先配置数据库：

```sql
-- 设置全局平台为百炼
UPDATE service_configs SET config_value='bailian' WHERE config_key='LLM_PLATFORM';

-- 或只让感情婚姻接口使用百炼
INSERT INTO service_configs (config_key, config_value, config_type, description, category, is_active, environment)
VALUES ('MARRIAGE_LLM_PLATFORM', 'bailian', 'string', '感情婚姻接口使用百炼', 'llm', 1, 'production')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);
```

2. 测试接口（应该使用百炼平台）：

```bash
curl -X POST "http://localhost:8001/api/v1/bazi/marriage-analysis/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "solar_date": "1990-05-15",
    "solar_time": "10:00",
    "gender": "male"
  }'
```

### 4. 检查日志

查看服务日志，确认使用的平台：

```bash
# 查看日志，应该看到类似信息：
# INFO: 为场景 marriage 选择平台: bailian
# INFO: 百炼流式服务初始化完成: scene=marriage
```

## 完整测试清单

- [ ] 语法检查通过
- [ ] 测试脚本运行成功
- [ ] Coze 平台接口正常（默认配置）
- [ ] 百炼平台接口正常（配置后）
- [ ] 场景级配置优先级正确
- [ ] 全局配置生效
- [ ] 配置热更新生效（修改配置后立即生效）
- [ ] 错误处理正常（配置缺失时返回友好错误）
- [ ] 回退机制正常（百炼失败时回退到 Coze）
- [ ] `bazi_evaluator.py` 不受影响

## 常见问题

### 问题 1：导入错误

**错误**：`ModuleNotFoundError: No module named 'server.services.llm_service_factory'`

**解决**：确保文件已创建，检查 Python 路径。

### 问题 2：百炼服务创建失败

**错误**：`ImportError: 百炼平台模块不可用`

**解决**：安装 dashscope SDK：`pip install dashscope`

### 问题 3：配置未生效

**解决**：
1. 检查数据库配置是否正确
2. 清除配置缓存（等待 5 分钟或重启服务）
3. 查看日志确认使用的平台

## 测试完成后

如果所有测试通过，可以：
1. 提交代码到 Git
2. 执行增量部署

详见部署指南。
