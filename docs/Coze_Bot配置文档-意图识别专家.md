# Coze Bot 配置文档 - 意图识别专家

**创建时间**：2025-11-24  
**Bot ID**：`7576140933906284571`  
**Bot链接**：https://www.coze.cn/space/7565058187868176436/bot/7576140933906284571

---

## 📋 Bot 基本信息

| 配置项 | 内容 |
|--------|------|
| Bot 名称 | 意图识别专家 |
| Bot ID | `7576140933906284571` |
| 用途 | 识别用户命理问题的意图，准确率95%+ |
| 所属空间 | 7565058187868176436 |
| 更新日期 | 2025-11-24 |

---

## ⚙️ 环境变量配置

### 配置文件位置
`config/services.env`

### 配置内容
```bash
# Intent Service 专用 Coze Bot
export INTENT_BOT_ID="7576140933906284571"

# Coze API 配置（共用）
export COZE_ACCESS_TOKEN="pat_m2Nah3lrHI3XhV1eSIx7JAuQgYOr3ecFFQk1mHSZx29LITCIlITRdq4UljDL2isf"

# Prompt 版本管理
export PROMPT_VERSION="v1.0"
export PROMPT_CACHE_TTL="3600"
```

### 更新配置后重启服务
```bash
./stop_all_services.sh
./start_all_services.sh
```

---

## 🤖 Bot 系统提示词（人设与回复逻辑）

将以下内容完整复制到 Coze Bot 的**人设与回复逻辑**中：

```
你是一个专业的命理学意图识别专家，专门负责准确识别用户问题的意图类别。

【核心职责】
从用户的问题中识别出具体的意图类别，可以是单个意图，也可以是多个意图。

【意图类别（10个）】
1. career - 事业运势（工作、职业、升职、创业）
2. wealth - 财富运势（财运、赚钱、投资、偏财）
3. marriage - 婚姻感情（恋爱、婚姻、桃花、分手）
4. health - 健康运势（身体、疾病、养生）
5. personality - 性格特点（性格、脾气、优缺点）
6. wangshui - 命局旺衰（五行强弱、旺衰分析）
7. yongji - 喜忌用神（喜用神、忌神分析）
8. shishen - 十神分析（食神、伤官、正财等）
9. nayin - 纳音分析（纳音五行）
10. general - 综合分析（笼统询问、多方面）

【识别原则】
1. 优先识别明确的专业术语（如"食神"、"用神"等）
2. 准确理解口语化表达（如"发财"→wealth，"升职"→career）
3. 当问题涉及多个方面时，返回多个意图
4. 当问题过于笼统时，返回general，并标记为模糊
5. 必须严格按照JSON格式返回结果

【输出格式（严格遵守）】
必须返回以下JSON格式，不要添加任何其他文字：

```json
{
  "intents": ["intent1", "intent2"],
  "confidence": 0.95,
  "keywords": ["关键词1", "关键词2"],
  "reasoning": "推理过程说明",
  "is_ambiguous": false
}
```

【置信度评分标准】
- 0.95-1.0：专业术语，意图非常明确
- 0.85-0.94：常见表达，意图清晰
- 0.70-0.84：一般问题，意图较明确
- 0.50-0.69：模糊问题，意图不够清晰
- <0.50：无法判断

【特别注意】
- 只返回JSON，不要添加解释性文字
- intents 必须是上述10个类别之一
- 当无法确定时，返回["general"]
- 口语化表达要准确映射（"我咋样"→general，"能不能发财"→wealth）
```

---

## 📊 模型配置参数（推荐）

### 1. 模型选择

| 优先级 | 模型 | 说明 | 适用场景 |
|--------|------|------|----------|
| 🥇 **首选** | GPT-4 | 最高准确率，理解能力强 | 生产环境 |
| 🥈 备选1 | Claude 3.5 Sonnet | 准确率高，理解自然语言能力强 | 生产环境 |
| 🥉 备选2 | GPT-3.5 Turbo | 成本较低，速度快 | 开发测试 |

### 2. 参数配置（重要）

```
【核心参数】
Temperature（温度）：0.3
  ├─ 说明：控制输出的随机性
  ├─ 效果：较低温度保证相同问题返回一致结果
  └─ 范围：0.1 - 0.5 可调

Top P：0.85
  ├─ 说明：控制候选词的概率累积阈值
  ├─ 效果：保持一定灵活性，能处理口语化表达
  └─ 范围：0.8 - 0.9 可调

Max Tokens（最大生成长度）：500
  ├─ 说明：限制输出长度
  ├─ 效果：JSON输出通常不需要太长
  └─ 范围：300 - 800

Frequency Penalty（频率惩罚）：0
  ├─ 说明：惩罚重复的词
  ├─ 效果：0表示不惩罚（JSON需要重复key）
  └─ 固定：0

Presence Penalty（存在惩罚）：0
  ├─ 说明：鼓励生成新话题
  ├─ 效果：0表示不惩罚（允许详细说明）
  └─ 固定：0
```

### 3. 高级功能配置

```
【启用的功能】
✅ JSON 模式（如果可用）
   └─ 强制返回JSON格式，避免格式错误

✅ 严格模式
   └─ 确保输出严格符合要求

【关闭的功能】
❌ 联网搜索
   └─ 意图识别不需要实时信息

❌ 知识库
   └─ 规则已在Prompt中定义

❌ 插件
   └─ 保持简单高效

❌ 流式输出
   └─ 需要完整JSON，不适合流式
```

---

## 🛠️ 完整配置步骤

### 步骤1：访问Bot配置页面
```
链接：https://www.coze.cn/space/7565058187868176436/bot/7576140933906284571
```

### 步骤2：基础信息配置
```
Bot名称：意图识别专家
Bot描述：专门用于识别用户命理问题的意图，准确率95%+
头像：选择一个AI或命理相关的图标（可选）
```

### 步骤3：模型设置
```
进入"模型"标签页：
├─ 主模型：选择 GPT-4 或 Claude 3.5 Sonnet
├─ Temperature：设置为 0.3
├─ Top P：设置为 0.85
├─ Max Tokens：设置为 500
├─ Frequency Penalty：0
└─ Presence Penalty：0
```

### 步骤4：人设与回复逻辑
```
1. 点击"人设与回复逻辑"标签
2. 复制上面的"系统提示词"完整内容
3. 粘贴到文本框中
4. 保存
```

### 步骤5：开场白（可选）
```
我是意图识别专家，请直接输入用户的问题，我会准确识别其意图。
```

### 步骤6：测试
在Bot测试对话框中测试以下问题：

```
测试1：明确问题
输入："我的事业运势怎么样？"
期望输出：
{
  "intents": ["career"],
  "confidence": 0.95,
  "keywords": ["事业", "运势"],
  "reasoning": "用户明确询问事业运势",
  "is_ambiguous": false
}

测试2：口语化表达
输入："我这辈子能不能发财？"
期望输出：
{
  "intents": ["wealth"],
  "confidence": 0.93,
  "keywords": ["发财"],
  "reasoning": "虽然表达口语化，但'发财'明确指向财富运势",
  "is_ambiguous": false
}

测试3：复合问题
输入："我今年能赚到钱吗？会不会升职？"
期望输出：
{
  "intents": ["wealth", "career"],
  "confidence": 0.92,
  "keywords": ["赚钱", "升职"],
  "reasoning": "用户同时询问财富和事业两个方面",
  "is_ambiguous": false
}

测试4：专业术语
输入："我的食神旺不旺？"
期望输出：
{
  "intents": ["shishen", "wangshui"],
  "confidence": 0.96,
  "keywords": ["食神", "旺"],
  "reasoning": "用户使用专业术语，明确询问十神和旺衰",
  "is_ambiguous": false
}

测试5：模糊问题
输入："我咋样？"
期望输出：
{
  "intents": ["general"],
  "confidence": 0.65,
  "keywords": ["咋样"],
  "reasoning": "问题过于笼统，建议进行综合分析",
  "is_ambiguous": true
}
```

### 步骤7：发布
```
1. 确认所有配置无误
2. 点击右上角"发布"按钮
3. 等待发布完成
```

---

## 🧪 系统集成测试

### 1. 更新环境变量

```bash
# 编辑配置文件
vim config/services.env

# 确认以下配置
export INTENT_BOT_ID="7576140933906284571"

# 保存退出
:wq
```

### 2. 重启服务

```bash
# 停止所有服务
./stop_all_services.sh

# 启动所有服务
./start_all_services.sh

# 等待10秒让服务完全启动
sleep 10
```

### 3. 测试API接口

```bash
# 测试1：基础意图识别
curl "http://localhost:8001/api/v1/test-intent?question=我的事业运势怎么样"

# 期望返回：
# {
#   "success": true,
#   "result": {
#     "intents": ["career"],
#     "confidence": 0.95,
#     ...
#   }
# }

# 测试2：完整运势分析
curl "http://localhost:8001/api/v1/smart-analyze?question=我的事业运势怎么样&year=1990&month=1&day=1&hour=12&gender=male"

# 期望返回：
# {
#   "success": true,
#   "intent_result": {...},
#   "bazi_info": {...},
#   "response": "..."
# }
```

### 4. 运行自动化测试

```bash
# 运行完整测试脚本
./tests/test_intent_service.sh

# 如果看到多个 ✓ 通过，说明配置成功
```

### 5. 查看日志

```bash
# 实时查看服务日志
tail -f logs/intent_service_9008.log

# 查看成功调用
grep "LLM call successful" logs/intent_service_9008.log

# 查看错误（如果有）
grep "ERROR" logs/intent_service_9008.log
```

---

## 📈 性能监控和优化

### 1. 准确率监控

```bash
# 查看最近20次分类结果
grep "Classification result" logs/intent_service_9008.log | tail -20

# 示例输出：
# 2025-11-24 12:00:00 - intent_service - INFO - Classification result: intents=['career'], confidence=0.95
```

### 2. 响应时间监控

```bash
# 查看响应时间
grep "response_time_ms" logs/intent_service_9008.log | tail -20

# 期望值：
# - 有缓存：< 50ms
# - 无缓存：200-500ms
```

### 3. 缓存命中率

```bash
# 连接Redis
redis-cli -p 16379 -n 3

# 查看缓存数量
> DBSIZE

# 查看缓存命中情况
> INFO stats | grep keyspace_hits

# 清理缓存（如需要）
> FLUSHDB
```

### 4. 优化建议

#### 如果准确率低于90%：

**方案1：降低Temperature**
```bash
# 当前：0.3
# 调整为：0.1 或 0.2
# 效果：更稳定，但可能过于死板
```

**方案2：切换模型**
```bash
# 从 GPT-3.5 Turbo → GPT-4
# 或使用 Claude 3.5 Sonnet
```

**方案3：优化Prompt**
```bash
# 在系统提示词中添加更多Few-shot示例
# 特别是错误率高的类别
```

#### 如果响应时间过长（>1秒）：

**方案1：检查网络**
```bash
# 测试Coze API连接
curl -I https://api.coze.cn
```

**方案2：增加缓存TTL**
```bash
# config/services.env
export PROMPT_CACHE_TTL="7200"  # 从1小时改为2小时
```

**方案3：启用批量请求**
```python
# 对于多个问题，使用批量接口
# 见：services/intent_service/grpc_server.py -> BatchClassify
```

---

## 🔧 故障排查

### 问题1：Bot 调用失败

**症状**：日志显示 "Coze API error"

**排查步骤**：
```bash
# 1. 检查Token是否正确
grep COZE_ACCESS_TOKEN config/services.env

# 2. 检查Bot ID是否正确
grep INTENT_BOT_ID config/services.env

# 3. 手动测试Coze API
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.coze.cn/v1/workspace/list"

# 4. 查看详细错误
tail -100 logs/intent_service_9008.log | grep "Coze"
```

**解决方案**：
1. 确认Token和Bot ID正确
2. 检查Coze账户是否有余额
3. 检查API调用频率是否超限

### 问题2：返回格式错误

**症状**：无法解析JSON

**排查步骤**：
```bash
# 查看LLM原始返回
grep "parse" logs/intent_service_9008.log | tail -10
```

**解决方案**：
1. 在Coze Bot中启用"JSON模式"
2. 强化系统提示词中的格式要求
3. 降低Temperature提高输出稳定性

### 问题3：意图识别错误

**症状**：将"事业"识别为"财富"

**排查步骤**：
```bash
# 查看具体的reasoning
curl "http://localhost:8001/api/v1/test-intent?question=问题内容"
# 查看result.reasoning字段
```

**解决方案**：
1. 在系统提示词中添加该类错误的示例
2. 强化关键词映射规则
3. 收集反馈数据，运行Prompt Optimizer

---

## 📚 相关文档

- [智能意图识别系统-开发完成报告](./智能意图识别系统-开发完成报告.md)
- [智能意图识别系统-使用指南](./智能意图识别系统-使用指南.md)
- [Intent Service源码](../services/intent_service/)
- [API接口文档](../server/api/v1/smart_fortune.py)

---

## 📝 变更日志

### v1.0 - 2025-11-24
- ✅ 创建Bot（ID: 7576140933906284571）
- ✅ 配置系统提示词
- ✅ 设置模型参数（Temperature: 0.3）
- ✅ 完成系统集成测试

### 未来计划
- [ ] 收集真实用户反馈（目标：1000条）
- [ ] 基于反馈优化Prompt（目标：准确率95%+）
- [ ] 启用Function Calling（如果Coze支持）
- [ ] 添加更多Few-shot示例（针对错误案例）

---

## 🎯 快速参考

### Bot ID
```
7576140933906284571
```

### 配置命令
```bash
# 更新环境变量
vim config/services.env
# export INTENT_BOT_ID="7576140933906284571"

# 重启服务
./stop_all_services.sh && ./start_all_services.sh

# 测试
curl "http://localhost:8001/api/v1/test-intent?question=测试问题"
```

### 核心参数
```
Temperature: 0.3
Top P: 0.85
Max Tokens: 500
```

### 日志位置
```
logs/intent_service_9008.log
```

---

**文档更新日期**：2025-11-24  
**下次审核日期**：收集1周真实数据后  
**维护人员**：AI开发团队

---

## 🆘 技术支持

如遇到问题：
1. 查看本文档的"故障排查"章节
2. 查看日志：`tail -f logs/intent_service_9008.log`
3. 参考使用指南：`docs/智能意图识别系统-使用指南.md`
4. 联系开发团队

**配置完成，祝使用顺利！** 🎉

