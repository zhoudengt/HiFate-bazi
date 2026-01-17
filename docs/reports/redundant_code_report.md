# 冗余代码检测报告
**检测时间**: 2026-01-17 09:56:19
**发现问题数**: 7

## 📊 问题汇总

### 🟡 中等严重程度

### 发现重复的客户端实现：BaziCoreClient

- **类型**: duplicate_client
- **严重程度**: medium
- **涉及文件**: 2 个

**文件列表**:
- `src/clients/bazi_core_client.py`
- `src/clients/bazi_core_client_grpc.py`

**建议**: 考虑统一使用 gRPC 客户端（src/clients/bazi_core_client_grpc.py），移除 HTTP 客户端（src/clients/bazi_core_client.py）

### 发现重复的客户端实现：BaziFortuneClient

- **类型**: duplicate_client
- **严重程度**: medium
- **涉及文件**: 2 个

**文件列表**:
- `src/clients/bazi_fortune_client.py`
- `src/clients/bazi_fortune_client_grpc.py`

**建议**: 考虑统一使用 gRPC 客户端（src/clients/bazi_fortune_client_grpc.py），移除 HTTP 客户端（src/clients/bazi_fortune_client.py）

### 发现重复的客户端实现：BaziRuleClient

- **类型**: duplicate_client
- **严重程度**: medium
- **涉及文件**: 2 个

**文件列表**:
- `src/clients/bazi_rule_client.py`
- `src/clients/bazi_rule_client_grpc.py`

**建议**: 考虑统一使用 gRPC 客户端（src/clients/bazi_rule_client_grpc.py），移除 HTTP 客户端（src/clients/bazi_rule_client.py）

### 发现 33 个文件包含相同的地址解析逻辑

- **类型**: duplicate_code_block
- **严重程度**: medium
- **涉及文件**: 33 个

**文件列表**:
- `src/clients/bazi_rule_client_grpc.py`
- `src/clients/bazi_core_client_grpc.py`
- `src/clients/bazi_fortune_client_grpc.py`
- `.hot_reload_backups/bazi_analyzer/v0/src_clients_bazi_fortune_client_grpc.py`
- `.hot_reload_backups/bazi_analyzer/v0/src_clients_bazi_core_client_grpc.py`
- ... 还有 28 个文件

**建议**: 考虑将地址解析逻辑提取到公共工具函数中

### 🟢 低严重程度

### 发现 65 个文件包含相同的 gRPC keepalive 配置

- **类型**: duplicate_grpc_config
- **严重程度**: low
- **涉及文件**: 10 个

**文件列表**:
- `src/clients/bazi_rule_client_grpc.py`
- `src/clients/bazi_core_client_grpc.py`
- `src/clients/bazi_fortune_client_grpc.py`
- `services/bazi_rule/grpc_server.py`
- `services/fortune_rule/grpc_server.py`
- ... 还有 5 个文件

**建议**: 考虑将 gRPC 配置提取到公共工具类中，统一管理

### 发现 7 对相似的文件

- **类型**: similar_files
- **严重程度**: low
- **涉及文件**: 5 个

**文件列表**:
- `src/clients/bazi_rule_client_grpc.py (126行) vs src/clients/bazi_fortune_client_grpc.py (93行)`
- `src/clients/bazi_core_client.py (58行) vs src/clients/bazi_rule_client.py (67行)`
- `src/clients/bazi_core_client.py (58行) vs src/clients/bazi_fortune_client.py (61行)`
- `src/clients/bazi_core_client.py (58行) vs src/clients/bazi_fortune_client_grpc.py (93行)`
- `src/clients/bazi_rule_client.py (67行) vs src/clients/bazi_fortune_client.py (61行)`

**建议**: 检查这些文件是否可以合并或提取公共代码

### 发现 1284 个格式化函数

- **类型**: duplicate_format_functions
- **严重程度**: low
- **涉及文件**: 10 个

**文件列表**:
- `tests/test_special_liunian_service.py:test_format_special_liunians_for_prompt`
- `tests/test_special_liunian_service.py:test_format_special_liunians_for_prompt_empty`
- `scripts/test_format_loader.py:test_format_loader`
- `src/bazi_calculator.py:_format_result`
- `src/bazi_calculator.py:_format_requirement`
- ... 还有 5 个文件

**建议**: 考虑统一格式化函数的实现，提取到公共工具类中


## 💡 优化建议总结

1. 考虑将地址解析逻辑提取到公共工具函数中
2. 检查这些文件是否可以合并或提取公共代码
3. 考虑将 gRPC 配置提取到公共工具类中，统一管理
4. 考虑统一格式化函数的实现，提取到公共工具类中
5. 考虑统一使用 gRPC 客户端（src/clients/bazi_fortune_client_grpc.py），移除 HTTP 客户端（src/clients/bazi_fortune_client.py）
6. 考虑统一使用 gRPC 客户端（src/clients/bazi_core_client_grpc.py），移除 HTTP 客户端（src/clients/bazi_core_client.py）
7. 考虑统一使用 gRPC 客户端（src/clients/bazi_rule_client_grpc.py），移除 HTTP 客户端（src/clients/bazi_rule_client.py）
