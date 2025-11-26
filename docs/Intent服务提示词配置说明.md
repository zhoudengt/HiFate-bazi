# Intent服务提示词配置说明

## 📍 问题1：提示词到底在哪里？

### ✅ 答案：**在代码中**

**文件位置**：
```
services/intent_service/classifier.py
第13-200行：INTENT_CLASSIFICATION_PROMPT
```

**工作流程**：
```
用户问题 
  → IntentClassifier.classify() 
  → 填充INTENT_CLASSIFICATION_PROMPT模板 
  → 通过IntentLLMClient发送给Coze API
  → Coze Bot执行LLM推理
  → 返回JSON结果
```

---

## 🤖 问题2：Coze Bot提示词写什么？

### ✅ Coze Bot配置（极简版）

**Coze Bot基础配置**：
```
Bot名称：命理意图识别Bot
模型：豆包Pro或GPT-4
温度：0.3（低温度，保证稳定输出）

系统提示词（Coze端）：
你是一个专业的JSON解析助手。
接收用户发送的命理问题和识别规则，严格按照规则返回JSON格式的结果。
不要添加任何解释性文字，只返回纯JSON。
```

**为什么这么简单？**
因为**详细的业务逻辑都在代码的提示词中**（`classifier.py`第13-200行），Coze Bot只需要：
1. 接收完整的提示词（包含规则和示例）
2. 按规则解析
3. 返回JSON

---

## 🔧 修改提示词的步骤

### 1. 修改代码中的提示词
```bash
vim services/intent_service/classifier.py
# 修改第13-200行的INTENT_CLASSIFICATION_PROMPT
```

### 2. 重启Intent Service
```bash
# 方法1：快速重启
ps aux | grep intent_service | grep -v grep | awk '{print $2}' | xargs kill -9
nohup python3 -m services.intent_service.server > logs/intent_service_9008.log 2>&1 &

# 方法2：使用脚本（如果有）
./restart_intent_service.sh
```

### 3. 验证
```bash
# 测试Intent识别
curl -X POST http://localhost:9008/classify \
  -H "Content-Type: application/json" \
  -d '{"question":"我2028年的财运怎么样？","user_id":"test"}'

# 查看日志
tail -f logs/intent_service_9008.log
```

---

## 📊 日志位置汇总

### 主要日志文件

| 服务 | 日志路径 | 说明 |
|------|---------|------|
| **Intent Service** | `logs/intent_service_9008.log` | Intent识别详细日志 |
| **Web App** | `logs/web_app_8001.log` | 主服务日志（含详细阶段日志） |
| **LLM分析** | 包含在`web_app_8001.log`中 | LLM深度解读日志 |

### 查看实时日志
```bash
# Intent识别日志
tail -f logs/intent_service_9008.log | grep -E "target_years|时间意图"

# 主服务日志（含详细阶段分隔线）
tail -f logs/web_app_8001.log | grep -E "STEP|====|target_years"

# 搜索特定年份
grep "2028" logs/*.log

# 查看完整请求流程
grep -A 20 "STEP1.*Intent识别完成" logs/web_app_8001.log
```

---

## 🎯 本次修复内容

### 修复1：提示词优化
**问题**：LLM把"2028年"识别成`[2026, 2027, 2028]`

**修复**：
- 增加"特定年份"示例（示例3）
- 强调"单年vs多年"区别
- 添加⚠️警告标识

**新示例**：
```json
{
  "question": "我2028年的财运怎么样？",
  "target_years": [2028],  // ✅ 只有1年
  "reasoning": "2028是特定年份，只返回[2028]，不是[2026,2027,2028]"
}
```

### 修复2：数据为空防御
**问题**：即使时间对应不上，也不应该让LLM收到空数据

**修复**：
1. 当`liunian_list`为空时，从问题中提取年份，构造占位数据
2. 添加`data_completeness`字段，告诉LLM数据完整性
3. LLM可以根据`target_year_from_question`自行推理

**代码位置**：
```
server/services/fortune_llm_client.py
第286-340行：智能匹配年份 + 防御性数据构造
第344-351行：data_completeness字段
```

### 修复3：详细日志
**新增**：每个阶段都有清晰的分隔线和输入输出日志

**日志格式**：
```
================================================================================
[STEP1] Intent识别完成
================================================================================
输入问题: 我2028年的财运怎么样？
Intent结果: {...}
时间意图类型: specific_year
目标年份: [2028]
时间描述: 2028年
================================================================================

================================================================================
[STEP4] Fortune Context开始
================================================================================
输入target_years: [2028]
输入intent_types: ['wealth']
================================================================================

================================================================================
[STEP4] Fortune Context完成
================================================================================
返回流年数量: 1
流年列表: ['2028年戊申']
大运: 乙丑
喜忌神: xi=['正印', '偏印']
================================================================================
```

---

## ✅ 验证修复

### 测试用例
```bash
# 测试1：明年（应该是1年）
curl -X POST http://localhost:9008/classify \
  -H "Content-Type: application/json" \
  -d '{"question":"我明年的财运怎么样？","user_id":"test"}'
# 预期：target_years: [2026]

# 测试2：特定年份（应该是1年）
curl -X POST http://localhost:9008/classify \
  -H "Content-Type: application/json" \
  -d '{"question":"我2028年的财运怎么样？","user_id":"test"}'
# 预期：target_years: [2028]

# 测试3：后三年（应该是3年）
curl -X POST http://localhost:9008/classify \
  -H "Content-Type: application/json" \
  -d '{"question":"我后三年的财运如何？","user_id":"test"}'
# 预期：target_years: [2026, 2027, 2028]
```

---

## 🔑 关键配置文件

| 文件 | 作用 |
|------|------|
| `services/intent_service/classifier.py` | Intent提示词（核心） |
| `services/intent_service/llm_client.py` | Coze API调用 |
| `services/intent_service/config.py` | Coze Bot ID、API Key |
| `server/services/fortune_llm_client.py` | LLM深度分析提示词 |

---

## 📞 Coze Bot配置快速指南

### Coze平台配置
1. 登录Coze平台：https://www.coze.cn/
2. 创建Bot：命理意图识别Bot
3. 模型选择：豆包Pro（推荐）
4. 温度设置：0.3
5. 系统提示词：
   ```
   你是一个专业的JSON解析助手。
   接收用户发送的命理问题和识别规则，严格按照规则返回JSON格式的结果。
   不要添加任何解释性文字，只返回纯JSON。
   ```
6. 保存并获取Bot ID
7. 更新`services/intent_service/config.py`中的`COZE_BOT_ID`

**重要**：Coze Bot不需要复杂的业务逻辑，所有规则都在代码的提示词中！

---

## 🎓 总结

1. **提示词位置**：代码中（`classifier.py`）
2. **Coze Bot配置**：极简配置，只需JSON解析能力
3. **修改流程**：改代码 → 重启服务 → 验证
4. **日志位置**：`logs/intent_service_9008.log` + `logs/web_app_8001.log`
5. **防御机制**：数据不完整时自动构造占位数据
6. **详细日志**：每个阶段都有清晰的输入输出记录

---

更新时间：2025-11-25

