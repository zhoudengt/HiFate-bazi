# 基于大模型的开发流程详细规范

> 本文档从 `.cursorrules` 提取，包含基于大模型的开发流程完整规范。详见 `.cursorrules` 核心规范章节。

## 核心原则

> **所有基于大模型的功能开发必须遵循统一的7阶段开发流程，确保数据完整性、Prompt标准化、API调用规范化和错误处理完善性。**

**核心原则**：
- ✅ **数据准备完整性**：确保所有必需数据都已获取（包括大运、流年等需要 `BaziDetailService` 的数据）
- ✅ **Prompt 构建标准化**：将结构化 JSON 数据转换为自然语言格式，确保 Coze Bot 能正确理解
- ✅ **Coze API 调用规范化**：使用正确的端点（`/v3/chat`）和参数格式（`additional_messages`）
- ✅ **流式处理健壮性**：正确处理 SSE 流，错误消息不中断流处理
- ✅ **错误处理完善性**：覆盖数据获取、API 调用、流处理等所有错误场景

---

### 📋 开发流程（7个阶段）

## 阶段1：需求分析与数据准备规划

**目标**：明确需要哪些数据，如何获取这些数据。

**步骤**：

1. **识别所需数据类型**
   - 基础八字数据：`BaziService.calculate_bazi_full()`
   - 旺衰数据：`WangShuaiService.calculate_wangshuai()`
   - **大运流年数据**：`BaziDetailService.calculate_detail_full()` ⚠️ **必须！**
   - 规则匹配数据：`RuleService.match_rules()`
   - 其他业务数据（根据需求）

2. **确定数据获取方式**
   - 独立数据：使用 `asyncio.gather()` 并行获取
   - 依赖数据：先获取依赖数据，再获取被依赖数据
   - 性能优化：合并规则查询（一次查询多种类型）

3. **识别数据依赖关系**
   - 规则匹配需要八字数据 → 先获取八字，再匹配规则
   - 大运数据需要详细计算 → 必须调用 `BaziDetailService.calculate_detail_full()`

**检查清单**：
- [ ] 已列出所有需要的数据类型
- [ ] 已确定哪些数据可以并行获取
- [ ] 已识别数据依赖关系
- [ ] 已确认是否需要 `BaziDetailService.calculate_detail_full()`（大运、流年数据）

---

## 阶段2：数据获取与并行优化

**目标**：高效获取所有必需数据，使用并行优化提升性能。

**步骤**：

1. **并行获取独立数据**
   ```python
   # ✅ 正确：并行获取独立数据
   loop = asyncio.get_event_loop()
   executor = None
   
   bazi_result, wangshuai_result, detail_result = await asyncio.gather(
       loop.run_in_executor(executor, BaziService.calculate_bazi_full, final_solar_date, final_solar_time, gender),
       loop.run_in_executor(executor, WangShuaiService.calculate_wangshuai, final_solar_date, final_solar_time, gender),
       loop.run_in_executor(executor, BaziDetailService.calculate_detail_full, final_solar_date, final_solar_time, gender)  # ⚠️ 大运数据必须！
   )
   ```

2. **识别需要 `BaziDetailService.calculate_detail_full()` 的场景**
   - ✅ **需要大运序列**：必须调用 `BaziDetailService.calculate_detail_full()`
   - ✅ **需要流年数据**：必须调用 `BaziDetailService.calculate_detail_full()`
   - ✅ **需要流月/流日数据**：必须调用 `BaziDetailService.calculate_detail_full()`
   - ❌ **仅需要基础八字**：使用 `BaziService.calculate_bazi_full()` 即可

3. **性能优化：合并规则查询**
   ```python
   # ✅ 正确：合并为一次查询（性能优化）
   all_matched_rules = await loop.run_in_executor(
       executor,
       RuleService.match_rules,
       rule_data,
       ['marriage', 'peach_blossom'],  # 一次查询匹配多种类型
       True  # use_cache
   )
   
   # ❌ 错误：分别查询（性能差）
   marriage_rules = RuleService.match_rules(rule_data, ['marriage'])
   peach_rules = RuleService.match_rules(rule_data, ['peach_blossom'])
   ```

4. **数据提取和验证**
   ```python
   # 提取八字数据（可能包含 'bazi' 键）
   if isinstance(bazi_result, dict) and 'bazi' in bazi_result:
       bazi_data = bazi_result['bazi']
   else:
       bazi_data = bazi_result
   
   # 验证数据类型
   bazi_data = validate_bazi_data(bazi_data)
   
   # 从 detail_result 获取大运序列（⚠️ 不是从 bazi_data）
   dayun_sequence = detail_result.get('dayun_sequence', [])
   ```

**检查清单**：
- [ ] 已使用 `asyncio.gather()` 并行获取独立数据
- [ ] 已调用 `BaziDetailService.calculate_detail_full()`（如需要大运数据）
- [ ] 已合并规则查询（如需要多种规则类型）
- [ ] 已正确提取数据（处理 `'bazi'` 键的情况）
- [ ] 已使用 `validate_bazi_data()` 验证数据类型

---

## 阶段3：数据验证与完整性检查

**目标**：确保所有必需数据都存在且格式正确，避免发送不完整数据给 Coze Bot。

**步骤**：

1. **创建 `validate_input_data()` 函数**
   ```python
   def validate_input_data(data: dict) -> tuple[bool, str]:
       """
       验证输入数据完整性
       
       Args:
           data: 输入数据字典
           
       Returns:
           (is_valid, error_message): 是否有效，错误信息（如果无效）
       """
       required_fields = {
           'mingpan_zonglun': {
               'bazi_pillars': '八字排盘',
               'ten_gods': '十神',
               'wangshuai': '旺衰',
               'dayun_list': '大运流年',  # ⚠️ 关键字段
               # ... 其他必需字段
           },
           # ... 其他部分
       }
       
       missing_fields = []
       
       for section, fields in required_fields.items():
           if section not in data:
               missing_fields.append(f"{section}（整个部分缺失）")
               continue
               
           section_data = data[section]
           if not isinstance(section_data, dict):
               missing_fields.append(f"{section}（格式错误，应为字典）")
               continue
               
           for field, field_name in fields.items():
               if field not in section_data:
                   missing_fields.append(f"{section}.{field}（{field_name}）")
               elif section_data[field] is None:
                   missing_fields.append(f"{section}.{field}（{field_name}为None）")
               elif isinstance(section_data[field], (list, dict)) and len(section_data[field]) == 0:
                   # 空列表/字典可能是正常的（如无匹配规则），不报错
                   pass
       
       if missing_fields:
           error_msg = f"数据不完整，缺失字段：{', '.join(missing_fields)}"
           return False, error_msg
       
       return True, ""
   ```

2. **定义必需字段清单**
   - 根据业务需求，明确每个部分需要哪些字段
   - 区分必需字段和可选字段
   - 记录字段的中文名称（用于错误提示）

3. **验证数据类型和格式**
   ```python
   # 验证数据类型
   bazi_data = validate_bazi_data(bazi_data)
   
   # 验证数据完整性
   is_valid, validation_error = validate_input_data(input_data)
   if not is_valid:
       logger.error(f"数据完整性验证失败: {validation_error}")
       error_msg = {
           'type': 'error',
           'content': f"数据计算不完整: {validation_error}。请检查生辰数据是否正确。"
       }
       yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
       return
   ```

**检查清单**：
- [ ] 已创建 `validate_input_data()` 函数
- [ ] 已定义所有必需字段清单
- [ ] 已区分必需字段和可选字段
- [ ] 已验证数据类型（使用 `validate_bazi_data()`）
- [ ] 已验证数据完整性（调用 `validate_input_data()`）
- [ ] 验证失败时已返回明确的错误信息

---

## 阶段4：Prompt 构建（结构化数据转自然语言）

**目标**：将 JSON 数据转换为自然语言格式，确保 Coze Bot 能正确理解和使用数据。

**核心原则**：
- ✅ **后端只提供元数据**：后端不构建完整的 prompt，只提供结构化数据
- ✅ **Prompt 模板在 Coze 中配置**：实际的 prompt 模板在 Coze Bot 中配置，使用变量引用后端数据
- ✅ **转换为自然语言格式**：将 JSON 数据转换为人类可读的自然语言字符串，作为变量值传递给 Coze Bot

**⚠️ 重要：方案选择**

系统支持两种方案：

### 方案1：自然语言 Prompt（传统方案）

- **特点**：代码中构建完整的自然语言 prompt，包含所有数据和指令
- **优点**：灵活，可以动态调整 prompt 内容
- **缺点**：代码中包含提示词，维护成本高，Token 使用较多
- **适用场景**：需要频繁调整 prompt 的场景

### 方案2：占位符模板（推荐方案）⭐

- **特点**：代码只发送结构化 JSON 数据，提示词模板存储在 Coze Bot 的 System Prompt 中
- **优点**：
  - ✅ **提示词集中管理**：所有提示词在 Coze Bot 中统一管理，无需修改代码
  - ✅ **节省 Token**：使用引用避免数据重复，减少 Token 消耗
  - ✅ **易于维护**：修改提示词只需在 Coze Bot 中操作，无需重新部署代码
  - ✅ **版本控制**：提示词变更可以独立于代码版本
- **缺点**：需要确保 Coze Bot 配置正确
- **适用场景**：**所有新开发的 LLM 接口（推荐）**

**⚠️ 规范要求**：
- ✅ **所有新开发的 LLM 接口必须使用方案2**
- ✅ **提示词必须存储在 Coze Bot 的 System Prompt 中，不能写在代码中**
- ✅ **代码中只负责数据提取和格式化，不包含任何提示词模板**

**步骤（方案1：自然语言 Prompt）**：

1. **创建 `build_natural_language_prompt()` 函数**
   ```python
   def build_natural_language_prompt(data: dict) -> str:
       """
       将 JSON 数据转换为自然语言格式的提示词
       参考 wuxing_proportion_service.py 的 build_llm_prompt 实现
       
       Args:
           data: 分析所需的完整数据
           
       Returns:
           str: 自然语言格式的提示词
       """
       prompt_lines = []
       prompt_lines.append("请基于以下八字信息进行分析，分别从以下方面进行详细分析：")
       prompt_lines.append("")
       
       # 1. 第一部分
       prompt_lines.append("【第一部分】")
       section1 = data.get('section1', {})
       
       # 提取关键信息并转换为自然语言
       if section1.get('field1'):
           prompt_lines.append(f"字段1：{section1['field1']}")
       
       prompt_lines.append("")
       
       # 2. 第二部分
       # ... 类似处理
       
       return '\n'.join(prompt_lines)
   ```

2. **将 JSON 数据转换为自然语言格式**
   - 使用清晰的分节标题（`【标题】`）
   - 使用结构化的列表格式
   - 确保数据完整且易读
   - 处理空数据情况（显示"（数据待完善）"）

3. **确保 Prompt 格式清晰、结构化**
   ```python
   # ✅ 正确：清晰的结构化格式
   prompt_lines.append("【命盘总论】")
   prompt_lines.append("四柱排盘：")
   prompt_lines.append("  年柱：甲子")
   prompt_lines.append("  月柱：乙丑")
   prompt_lines.append("十神配置：")
   prompt_lines.append("  年柱：主星正官，副星偏印")
   
   # ❌ 错误：混乱的格式
   prompt_lines.append("命盘总论：年柱甲子，月柱乙丑，十神正官偏印...")
   ```

**步骤（方案2：占位符模板）⭐ 推荐**：

1. **创建 `build_xxx_input_data()` 函数**
   ```python
   def build_xxx_input_data(
       bazi_data: Dict[str, Any],
       wangshuai_result: Dict[str, Any],
       detail_result: Dict[str, Any],
       dayun_sequence: List[Dict[str, Any]],
       special_liunians: List[Dict[str, Any]],
       gender: str
   ) -> Dict[str, Any]:
       """
       构建XXX分析的输入数据
       
       Returns:
           dict: 结构化的 input_data
       """
       # 提取和构建所有必需数据
       # 使用工具函数（如 build_enhanced_dayun_structure）优化大运流年结构
       # 使用引用避免数据重复
       input_data = {
           'section1': {...},
           'section2': {...},
           # ...
       }
       return input_data
   ```

2. **创建 `format_input_data_for_coze()` 函数**
   ```python
   def format_input_data_for_coze(input_data: Dict[str, Any]) -> str:
       """
       将结构化数据格式化为 JSON 字符串（用于 Coze Bot System Prompt 的 {{input}} 占位符）
       
       ⚠️ 方案2：使用占位符模板，数据不重复，节省 Token
       提示词模板已配置在 Coze Bot 的 System Prompt 中，代码只发送数据
       
       Returns:
           str: JSON 格式的字符串，可以直接替换 {{input}} 占位符
       """
       import json
       
       # 优化数据结构，使用引用避免重复
       optimized_data = {
           'section1': input_data.get('section1', {}),
           'section2': {
               # 引用 section1 的数据，不重复存储
               'ten_gods': input_data.get('section1', {}).get('ten_gods', {}),
               # ... 其他字段
           }
       }
       
       # 格式化为 JSON 字符串（美化格式，便于 Bot 理解）
       return json.dumps(optimized_data, ensure_ascii=False, indent=2)
   ```

3. **在流式生成器中使用格式化数据**
   ```python
   # ⚠️ 方案2：格式化数据为 Coze Bot 输入格式
   formatted_data = format_input_data_for_coze(input_data)
   logger.info(f"格式化数据长度: {len(formatted_data)} 字符")
   
   # 直接发送格式化后的数据给 Bot
   async for chunk in coze_service.stream_custom_analysis(formatted_data, bot_id=bot_id):
       yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
   ```

4. **在 Coze Bot 中配置 System Prompt**
   - 登录 Coze 平台
   - 找到对应的 Bot（如"感情婚姻分析"）
   - 进入 Bot 设置 → System Prompt
   - 复制 `docs/需求/Coze_Bot_System_Prompt_XXX分析.md` 中的提示词
   - 粘贴到 System Prompt 中
   - 使用 `{{input}}` 占位符引用后端发送的数据
   - 保存设置

**检查清单（方案1：自然语言 Prompt）**：
- [ ] 已创建 `build_natural_language_prompt()` 函数
- [ ] 已将所有 JSON 数据转换为自然语言格式
- [ ] Prompt 格式清晰、结构化（使用分节标题）
- [ ] 已处理空数据情况（显示友好提示）
- [ ] 已记录 Prompt 前500字符到日志（便于调试）

**检查清单（方案2：占位符模板）⭐ 推荐**：
- [ ] 已创建 `build_xxx_input_data()` 函数
- [ ] 已创建 `format_input_data_for_coze()` 函数
- [ ] 已优化数据结构，使用引用避免重复
- [ ] 已创建 Coze Bot System Prompt 文档（`docs/需求/Coze_Bot_System_Prompt_XXX分析.md`）
- [ ] 已在 Coze Bot 中配置 System Prompt（使用 `{{input}}` 占位符）
- [ ] 已创建测试接口（`POST /api/v1/xxx/test`）用于验证格式化数据
- [ ] 已记录格式化数据长度到日志（便于调试）

---

## 阶段5：Coze API 调用（正确的端点和参数）

**目标**：使用正确的 Coze API 端点和参数格式，确保 API 调用成功。

**步骤**：

1. **使用 `/v3/chat` 端点**
   ```python
   # ✅ 正确：使用 v3 API
   possible_endpoints = [
       "/v3/chat",  # Coze v3 标准端点
   ]
   
   # ❌ 错误：使用 v2 API（不支持 additional_messages）
   possible_endpoints = [
       "/v2/chat",  # 不支持 additional_messages 格式
   ]
   ```

2. **使用 `additional_messages` 格式**
   ```python
   # ✅ 正确：使用 additional_messages 格式
   payload = {
       "bot_id": str(used_bot_id),
       "user_id": "system",
       "additional_messages": [
           {
               "role": "user",
               "content": prompt,  # 自然语言格式的 prompt
               "content_type": "text"
           }
       ],
       "stream": True
   }
   
   # ❌ 错误：使用 query 字段（不适合结构化数据）
   payload = {
       "bot_id": str(used_bot_id),
       "query": prompt,  # 不推荐，Bot 可能无法正确解析
       "stream": True
   }
   ```

3. **设置正确的请求头**
   ```python
   # ✅ 正确：设置 Accept 头
   self.headers = {
       "Authorization": f"Bearer {self.access_token}",
       "Content-Type": "application/json",
       "Accept": "text/event-stream"  # ⚠️ 必须！用于 SSE 流
   }
   
   # ❌ 错误：缺少 Accept 头
   self.headers = {
       "Authorization": f"Bearer {self.access_token}",
       "Content-Type": "application/json"
       # 缺少 Accept: text/event-stream
   }
   ```

4. **Bot ID 配置优先级**
   ```python
   # 确定使用的 bot_id（优先级：参数 > 专用环境变量 > 通用环境变量）
   if not bot_id:
       bot_id = os.getenv("SPECIFIC_BOT_ID")  # 专用 Bot ID（如 MARRIAGE_ANALYSIS_BOT_ID）
       if not bot_id:
           bot_id = os.getenv("COZE_BOT_ID")  # 通用 Bot ID
           if not bot_id:
               # 返回错误
               yield {'type': 'error', 'content': "Coze Bot ID 配置缺失"}
               return
   ```

**检查清单**：
- [ ] 已使用 `/v3/chat` 端点
- [ ] 已使用 `additional_messages` 格式（不是 `query`）
- [ ] 已设置 `Accept: text/event-stream` 请求头
- [ ] 已正确配置 Bot ID（优先级：参数 > 专用环境变量 > 通用环境变量）
- [ ] 已记录 API 调用日志（Bot ID、Prompt 长度、Payload 结构）

---

## 阶段6：流式处理（SSE 流处理）

**目标**：正确处理 Server-Sent Events (SSE) 流，确保前端能实时显示生成内容。

**后端处理**：

1. **使用 `CozeStreamService` 处理流式响应**
   ```python
   from server.services.coze_stream_service import CozeStreamService
   
   coze_service = CozeStreamService(bot_id=bot_id)
   
   async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=bot_id):
       if chunk.get('type') == 'progress':
           # 增量内容
           yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
       elif chunk.get('type') == 'complete':
           # 完整内容
           yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
           break
       elif chunk.get('type') == 'error':
           # 错误消息
           yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
           break
   ```

2. **错误消息处理（不中断流）**
   ```python
   # ✅ 正确：错误消息作为流的一部分，不抛出异常
   if chunk.get('type') == 'error':
       yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
       # 不抛出异常，让前端处理错误显示
   
   # ❌ 错误：抛出异常中断流
   if chunk.get('type') == 'error':
       raise Exception(chunk.get('content'))  # 会中断整个流
   ```

**前端处理**：

1. **使用 `fetch` + `getReader()` 处理 SSE**
   ```javascript
   const response = await fetch('/api/v1/xxx/stream', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify(requestData)
   });
   
   const reader = response.body.getReader();
   const decoder = new TextDecoder();
   let buffer = '';
   
   while (true) {
       const { done, value } = await reader.read();
       if (done) break;
       
       buffer += decoder.decode(value, { stream: true });
       const lines = buffer.split('\n');
       buffer = lines.pop() || '';
       
       for (const line of lines) {
           if (line.startsWith('data: ')) {
               const data = JSON.parse(line.substring(6));
               // 处理数据
           }
       }
   }
   ```

2. **错误消息处理（不中断流）**
   ```javascript
   // ✅ 正确：显示错误但不中断流处理
   if (data.type === 'error') {
       console.error('收到错误消息:', data.content);
       showError(data.content || '生成失败');
       return; // 结束流处理，但不抛出异常
   }
   
   // ❌ 错误：抛出异常中断流
   if (data.type === 'error') {
       throw new Error(data.content);  // 会中断流处理
   }
   ```

**检查清单**：
- [ ] 后端已使用 `CozeStreamService` 处理流式响应
- [ ] 后端错误消息不抛出异常（作为流的一部分）
- [ ] 前端已使用 `fetch` + `getReader()` 处理 SSE
- [ ] 前端错误消息不抛出异常（显示错误但继续处理）
- [ ] 已测试流式处理（增量内容实时显示）

---

## 阶段7：错误处理与测试验证

**目标**：覆盖所有错误场景，确保系统健壮性，并通过端到端测试验证功能。

**错误处理**：

1. **数据获取错误处理**
   ```python
   try:
       bazi_result, wangshuai_result, detail_result = await asyncio.gather(...)
   except Exception as e:
       import traceback
       error_msg = {
           'type': 'error',
           'content': f"获取数据失败: {str(e)}\n{traceback.format_exc()}"
       }
       yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
       return
   ```

2. **Coze API 错误处理**
   ```python
   try:
       coze_service = CozeStreamService(bot_id=bot_id)
       async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=bot_id):
           # 处理流式响应
           ...
   except ValueError as e:
       # 配置错误
       error_msg = {
           'type': 'error',
           'content': f"Coze API 配置缺失: {str(e)}"
       }
       yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
       return
   except Exception as e:
       # 其他错误
       error_msg = {
           'type': 'error',
           'content': f"Coze API 调用失败: {str(e)}"
       }
       yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
       return
   ```

3. **端到端测试验证**
   - 测试多个不同的生辰日期
   - 验证所有部分都能正常显示
   - 验证错误场景（无效日期、配置缺失等）
   - 验证流式处理（增量内容实时显示）

**检查清单**：
- [ ] 已处理数据获取错误（try-except + 错误消息）
- [ ] 已处理 Coze API 配置错误（Bot ID 缺失、Token 缺失等）
- [ ] 已处理 Coze API 调用错误（网络错误、API 错误等）
- [ ] 已处理流式处理错误（SSE 解析错误、连接中断等）
- [ ] 已进行端到端测试（多个生辰日期）
- [ ] 已测试错误场景（无效输入、配置缺失等）

---

### 📝 代码模板

## 模板1：完整的流式端点实现

```python
@router.post("/xxx/stream", summary="流式生成XXX分析")
async def xxx_analysis_stream(request: XxxRequest):
    """
    流式生成XXX分析
    
    Args:
        request: 请求参数
    """
    return StreamingResponse(
        xxx_analysis_stream_generator(
            request.solar_date,
            request.solar_time,
            request.gender,
            request.bot_id
        ),
        media_type="text/event-stream"
    )

async def xxx_analysis_stream_generator(
    solar_date: str,
    solar_time: str,
    gender: str,
    bot_id: Optional[str] = None
):
    """流式生成XXX分析"""
    try:
        # 1. Bot ID 配置检查
        if not bot_id:
            bot_id = os.getenv("XXX_BOT_ID") or os.getenv("COZE_BOT_ID")
            if not bot_id:
                yield f"data: {json.dumps({'type': 'error', 'content': 'Bot ID 配置缺失'}, ensure_ascii=False)}\n\n"
                return
        
        # 2. 处理输入（农历转换等）
        final_solar_date, final_solar_time, _ = BaziInputProcessor.process_input(
            solar_date, solar_time, "solar", None, None, None
        )
        
        # 3. 并行获取数据
        loop = asyncio.get_event_loop()
        bazi_result, wangshuai_result, detail_result = await asyncio.gather(
            loop.run_in_executor(None, BaziService.calculate_bazi_full, final_solar_date, final_solar_time, gender),
            loop.run_in_executor(None, WangShuaiService.calculate_wangshuai, final_solar_date, final_solar_time, gender),
            loop.run_in_executor(None, BaziDetailService.calculate_detail_full, final_solar_date, final_solar_time, gender)  # ⚠️ 大运数据必须！
        )
        
        # 4. 提取和验证数据
        bazi_data = validate_bazi_data(bazi_result.get('bazi', bazi_result))
        dayun_sequence = detail_result.get('dayun_sequence', [])  # ⚠️ 从 detail_result 获取
        
        # 5. 构建输入数据
        input_data = {
            'section1': {...},
            'section2': {...},
            # ...
        }
        
        # 6. 验证数据完整性
        is_valid, validation_error = validate_input_data(input_data)
        if not is_valid:
            yield f"data: {json.dumps({'type': 'error', 'content': f'数据不完整: {validation_error}'}, ensure_ascii=False)}\n\n"
            return
        
        # 7. 构建自然语言 Prompt
        prompt = build_natural_language_prompt(input_data)
        
        # 8. 调用 Coze API
        coze_service = CozeStreamService(bot_id=bot_id)
        async for chunk in coze_service.stream_custom_analysis(prompt, bot_id=bot_id):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            if chunk.get('type') in ['complete', 'error']:
                break
                
    except Exception as e:
        import traceback
        yield f"data: {json.dumps({'type': 'error', 'content': f'处理失败: {str(e)}'}, ensure_ascii=False)}\n\n"
```

## 模板2：数据验证函数

```python
def validate_input_data(data: dict) -> tuple[bool, str]:
    """验证输入数据完整性"""
    required_fields = {
        'section1': {
            'field1': '字段1说明',
            'field2': '字段2说明',
        },
        'section2': {
            'field3': '字段3说明',
        }
    }
    
    missing_fields = []
    for section, fields in required_fields.items():
        if section not in data:
            missing_fields.append(f"{section}（整个部分缺失）")
            continue
        for field, field_name in fields.items():
            if field not in data[section]:
                missing_fields.append(f"{section}.{field}（{field_name}）")
    
    if missing_fields:
        return False, f"缺失字段：{', '.join(missing_fields)}"
    return True, ""
```

## 模板3：Prompt 构建函数

```python
def build_natural_language_prompt(data: dict) -> str:
    """将 JSON 数据转换为自然语言格式的提示词"""
    prompt_lines = []
    prompt_lines.append("请基于以下八字信息进行分析：")
    prompt_lines.append("")
    
    # 第一部分
    prompt_lines.append("【第一部分】")
    section1 = data.get('section1', {})
    if section1.get('field1'):
        prompt_lines.append(f"字段1：{section1['field1']}")
    prompt_lines.append("")
    
    # 第二部分
    # ... 类似处理
    
    return '\n'.join(prompt_lines)
```

## 模板4：前端 SSE 处理

```javascript
async function generateAnalysis(solarDate, solarTime, gender) {
    const response = await fetch('/api/v1/xxx/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ solar_date: solarDate, solar_time: solarTime, gender: gender })
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.substring(6));
                
                if (data.type === 'progress') {
                    fullContent += data.content;
                    updateUI(fullContent);
                } else if (data.type === 'complete') {
                    fullContent += data.content;
                    updateUI(fullContent);
                    return;
                } else if (data.type === 'error') {
                    showError(data.content);
                    return; // 不抛出异常
                }
            }
        }
    }
}
```

---

### ✅ 开发检查清单

**阶段1：需求分析与数据准备规划**
- [ ] 已列出所有需要的数据类型
- [ ] 已确定哪些数据可以并行获取
- [ ] 已识别数据依赖关系
- [ ] 已确认是否需要 `BaziDetailService.calculate_detail_full()`（大运、流年数据）

**阶段2：数据获取与并行优化**
- [ ] 已使用 `asyncio.gather()` 并行获取独立数据
- [ ] 已调用 `BaziDetailService.calculate_detail_full()`（如需要大运数据）
- [ ] 已合并规则查询（如需要多种规则类型）
- [ ] 已正确提取数据（处理 `'bazi'` 键的情况）
- [ ] 已使用 `validate_bazi_data()` 验证数据类型

**阶段3：数据验证与完整性检查**
- [ ] 已创建 `validate_input_data()` 函数
- [ ] 已定义所有必需字段清单
- [ ] 已区分必需字段和可选字段
- [ ] 已验证数据类型（使用 `validate_bazi_data()`）
- [ ] 已验证数据完整性（调用 `validate_input_data()`）
- [ ] 验证失败时已返回明确的错误信息

**阶段4：Prompt 构建**
- [ ] 已创建 `build_natural_language_prompt()` 函数
- [ ] 已将所有 JSON 数据转换为自然语言格式
- [ ] Prompt 格式清晰、结构化（使用分节标题）
- [ ] 已处理空数据情况（显示友好提示）
- [ ] 已记录 Prompt 前500字符到日志（便于调试）

**阶段5：Coze API 调用**
- [ ] 已使用 `/v3/chat` 端点
- [ ] 已使用 `additional_messages` 格式（不是 `query`）
- [ ] 已设置 `Accept: text/event-stream` 请求头
- [ ] 已正确配置 Bot ID（优先级：参数 > 专用环境变量 > 通用环境变量）
- [ ] 已记录 API 调用日志（Bot ID、Prompt 长度、Payload 结构）

**阶段6：流式处理**
- [ ] 后端已使用 `CozeStreamService` 处理流式响应
- [ ] 后端错误消息不抛出异常（作为流的一部分）
- [ ] 前端已使用 `fetch` + `getReader()` 处理 SSE
- [ ] 前端错误消息不抛出异常（显示错误但继续处理）
- [ ] 已测试流式处理（增量内容实时显示）

**阶段7：错误处理与测试验证**
- [ ] 已处理数据获取错误（try-except + 错误消息）
- [ ] 已处理 Coze API 配置错误（Bot ID 缺失、Token 缺失等）
- [ ] 已处理 Coze API 调用错误（网络错误、API 错误等）
- [ ] 已处理流式处理错误（SSE 解析错误、连接中断等）
- [ ] 已进行端到端测试（多个生辰日期）
- [ ] 已测试错误场景（无效输入、配置缺失等）

---

### 🚨 常见问题和解决方案

## 问题1：大运数据为空，显示"（大运数据待完善）"

**症状**：前端显示"（大运数据待完善，暂无法详细分析）"

**原因**：
- 只调用了 `BaziService.calculate_bazi_full()`，该服务不返回大运序列
- 从 `bazi_data.get('details', {}).get('dayun_sequence', [])` 获取，但该路径不存在

**解决方案**：
```python
# ✅ 正确：调用 BaziDetailService.calculate_detail_full() 获取大运数据
detail_result = await loop.run_in_executor(
    None, BaziDetailService.calculate_detail_full, 
    final_solar_date, final_solar_time, gender
)
dayun_sequence = detail_result.get('dayun_sequence', [])

# ❌ 错误：从 bazi_data 获取（不存在）
dayun_sequence = bazi_data.get('details', {}).get('dayun_sequence', [])  # 返回空列表
```

**检查清单**：
- [ ] 已调用 `BaziDetailService.calculate_detail_full()`（如需要大运数据）
- [ ] 从 `detail_result` 而非 `bazi_data` 获取 `dayun_sequence`
- [ ] 已验证 `dayun_sequence` 不为空

---

## 问题2：Coze Bot 返回"对不起，我无法回答这个问题。"

**症状**：Coze Bot 返回固定的拒绝消息

**原因**：
- 使用了错误的 API 端点（`/v2/chat` 不支持 `additional_messages`）
- 使用了错误的 payload 格式（`query` 而非 `additional_messages`）
- Prompt 格式不符合 Bot 期望（JSON 字符串而非自然语言）

**解决方案**：
```python
# ✅ 正确：使用 v3 API + additional_messages + 自然语言 prompt
payload = {
    "bot_id": str(bot_id),
    "user_id": "system",
    "additional_messages": [
        {
            "role": "user",
            "content": prompt,  # 自然语言格式的字符串
            "content_type": "text"
        }
    ],
    "stream": True
}
url = f"{api_base}/v3/chat"

# ❌ 错误：使用 v2 API + query + JSON 字符串
payload = {
    "bot_id": str(bot_id),
    "query": json.dumps(data),  # JSON 字符串，Bot 无法解析
    "stream": True
}
url = f"{api_base}/v2/chat"
```

**检查清单**：
- [ ] 已使用 `/v3/chat` 端点
- [ ] 已使用 `additional_messages` 格式
- [ ] Prompt 是自然语言格式（不是 JSON 字符串）
- [ ] 已设置 `Accept: text/event-stream` 请求头

---

## 问题3：Coze API 返回 `code:4000` 错误

**症状**：`The field http body provided is not a valid json or chat request.`

**原因**：
- 使用了错误的 API 端点（`/v2/chat` 不支持 `additional_messages`）
- 缺少 `Accept: text/event-stream` 请求头

**解决方案**：
```python
# ✅ 正确：使用 v3 API + 正确的请求头
possible_endpoints = ["/v3/chat"]
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream"  # ⚠️ 必须！
}

# ❌ 错误：使用 v2 API 或缺少 Accept 头
possible_endpoints = ["/v2/chat"]  # 不支持 additional_messages
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
    # 缺少 Accept: text/event-stream
}
```

---

## 问题4：前端显示"未收到分析内容"

**症状**：前端显示"未收到分析内容"，但后端 API 调用正常

**原因**：
- 前端错误处理不正确（`throw new Error()` 中断流处理）
- 后端返回错误消息但前端未正确处理

**解决方案**：
```javascript
// ✅ 正确：显示错误但不中断流
if (data.type === 'error') {
    console.error('收到错误消息:', data.content);
    showError(data.content || '生成失败');
    return; // 结束流处理，但不抛出异常
}

// ❌ 错误：抛出异常中断流
if (data.type === 'error') {
    throw new Error(data.content);  // 会中断流处理，导致 fullContent 为空
}
```

**检查清单**：
- [ ] 前端错误处理不抛出异常（使用 `return` 而非 `throw`）
- [ ] 后端错误消息作为流的一部分（不抛出异常）
- [ ] 已测试错误场景（配置缺失、数据不完整等）

---

## 问题5：数据验证失败但原因不明确

**症状**：显示"数据不完整"但不知道缺少哪些字段

**原因**：
- `validate_input_data()` 函数未返回详细的错误信息
- 错误信息未包含缺失字段的具体名称

**解决方案**：
```python
# ✅ 正确：返回详细的错误信息
def validate_input_data(data: dict) -> tuple[bool, str]:
    missing_fields = []
    for section, fields in required_fields.items():
        if section not in data:
            missing_fields.append(f"{section}（整个部分缺失）")
        for field, field_name in fields.items():
            if field not in data[section]:
                missing_fields.append(f"{section}.{field}（{field_name}）")
    
    if missing_fields:
        return False, f"数据不完整，缺失字段：{', '.join(missing_fields)}"
    return True, ""

# ❌ 错误：只返回简单的错误信息
def validate_input_data(data: dict) -> tuple[bool, str]:
    if not data:
        return False, "数据为空"  # 不够详细
    return True, ""
```

---

### 📚 参考实现

**完整实现示例**：
- `server/api/v1/marriage_analysis.py` - 婚姻分析完整实现
- `server/api/v1/wuxing_proportion.py` - 五行占比分析实现

**关键服务**：
- `server/services/coze_stream_service.py` - Coze 流式服务
- `server/services/bazi_detail_service.py` - 详细八字服务（包含大运数据）
- `server/services/bazi_service.py` - 基础八字服务

**前端实现**：
- `local_frontend/js/marriage-analysis.js` - 婚姻分析前端 SSE 处理

---

**核心要点**：
- **所有基于大模型的功能必须遵循7阶段开发流程**
- **大运数据必须调用 `BaziDetailService.calculate_detail_full()`**
- **Prompt 必须转换为自然语言格式（不是 JSON 字符串）**
- **Coze API 必须使用 `/v3/chat` + `additional_messages` 格式**
- **错误处理必须完善（不中断流处理）**
- **必须进行端到端测试验证**

---

