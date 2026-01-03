# gRPC 协议与序列化详细规范

> 本文档从 `.cursorrules` 提取，包含 gRPC 协议与序列化的完整规范。详见 `.cursorrules` 核心规范章节。

## 核心原则

> **所有 gRPC 协议开发、接口服务开发、序列化/反序列化必须遵循统一规范，禁止自作主张各自为政。**

---

## 1. gRPC Protocol Buffers 定义规范

### 1.1 Proto 文件命名规范

**文件命名**：
- 使用小写字母和下划线：`bazi_core.proto`、`bazi_fortune.proto`
- 文件名应反映服务功能

### 1.2 Proto 文件语法规范

```protobuf
syntax = "proto3";  // 必须使用 proto3

package bazi.core;  // 包名格式：功能.子功能

// 服务描述注释
// Bazi Core Service - 八字排盘核心计算服务
```

### 1.3 消息定义规范

```protobuf
// 请求消息命名：ServiceName + Request
message BaziCoreRequest {
  string solar_date = 1;  // 字段必须有注释
  string solar_time = 2;
  string gender = 3;
}

// 响应消息命名：ServiceName + Response
message BaziCoreResponse {
  map<string, string> basic_info = 1;  // 简单键值对使用 map
  string metadata_json = 2;             // 复杂结构使用 JSON 字符串
}
```

### 1.4 字段类型使用规范

| 数据类型 | 使用场景 | 示例 |
|---------|---------|------|
| `string` | 文本数据 | `solar_date`, `gender` |
| `int32` | 整数 | `element_counts` |
| `map<string, string>` | 简单键值对 | `basic_info` |
| `map<string, int32>` | 计数统计 | `element_counts` |
| `repeated string` | 字符串列表 | `rule_types` |
| `string` (JSON) | **复杂嵌套结构** | `metadata_json`, `detail_json` |
| 自定义 `message` | 固定结构 | `Pillar`, `PillarDetail` |

**重要原则**：
- ✅ **复杂嵌套结构必须使用 `string` 字段存储 JSON 字符串**
- ✅ 简单结构优先使用 protobuf 原生类型
- ❌ 禁止在 proto 中定义深度嵌套的 message

### 1.5 服务定义规范

```protobuf
service BaziCoreService {
  // 方法命名：动词 + 名词，驼峰命名
  rpc CalculateBazi(BaziCoreRequest) returns (BaziCoreResponse);
  
  // 所有服务必须提供健康检查
  rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
}
```

**健康检查标准**：
```protobuf
message HealthCheckRequest {}
message HealthCheckResponse {
  string status = 1;  // 通常为 "ok"
}
```

---

## 2. API 接口服务规范

### 2.1 请求模型规范（Pydantic）

```python
from pydantic import BaseModel, Field, validator

class BaziRequest(BaseModel):
    """八字计算请求模型"""
    solar_date: str = Field(..., description="阳历日期，格式：YYYY-MM-DD", example="1990-05-15")
    solar_time: str = Field(..., description="出生时间，格式：HH:MM", example="14:30")
    gender: str = Field(..., description="性别：male(男) 或 female(女)", example="male")
    
    @validator('solar_date')
    def validate_date(cls, v):
        """验证日期格式"""
        try:
            from datetime import datetime
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('日期格式错误，应为 YYYY-MM-DD')
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        """验证性别"""
        if v not in ['male', 'female']:
            raise ValueError('性别必须为 male 或 female')
        return v
```

**规范要求**：
- ✅ 所有字段必须使用 `Field` 提供 `description` 和 `example`
- ✅ 必须使用 `@validator` 验证关键字段
- ✅ 模型类必须有文档字符串

### 2.2 响应模型规范

```python
class BaziResponse(BaseModel):
    """八字计算响应模型"""
    success: bool  # 必须包含 success 字段
    data: Optional[dict] = None
    message: Optional[str] = None
    error: Optional[str] = None  # 错误信息
```

**规范要求**：
- ✅ 响应模型必须包含 `success: bool`
- ✅ 成功时返回 `data`，失败时返回 `error`
- ✅ 所有可选字段使用 `Optional[...] = None`

### 2.3 gRPC 网关注册规范

**注册流程**：
```python
# 1. 在 server/api/grpc_gateway.py 中导入
from server.api.v1.bazi import BaziRequest, BaziResponse, calculate_bazi

# 2. 使用 @_register 装饰器注册
@_register("/bazi/calculate")
async def _handle_bazi_calculate(payload: Dict[str, Any]):
    """处理八字计算请求"""
    # 3. 转换为 Pydantic 模型
    request_model = BaziRequest(**payload)
    
    # 4. 调用原始 API 函数
    return await calculate_bazi(request_model)
```

**接口路径规范**：
- 格式：`/功能模块/操作`
- 示例：
  - `/bazi/calculate` - 计算八字
  - `/bazi/formula-analysis` - 公式分析
  - `/bazi/shengong-minggong` - 身宫命宫
  - `/payment/create-session` - 创建支付会话

**规范要求**：
- ✅ 所有 API 端点必须在 `grpc_gateway.py` 中注册
- ✅ 注册函数必须使用 `@_register` 装饰器
- ✅ 函数名格式：`_handle_功能模块_操作`
- ✅ 必须转换为 Pydantic 模型后再调用

---

## 3. 序列化/反序列化规范

### 3.1 服务端序列化规范（gRPC Server）

**字典序列化**：
```python
# ✅ 正确：复杂字典序列化为 JSON 字符串
if isinstance(value, dict):
    response.metadata_json = json.dumps(value, ensure_ascii=False)
else:
    response.metadata_json = str(value)

# ✅ 正确：简单键值对直接使用 map
response.basic_info[key] = str(value)

# ❌ 错误：不要直接将字典赋值给 string 字段
response.metadata_json = value  # 会导致序列化错误
```

**特殊字段处理**：
```python
# lunar_date 是字典，需要特殊处理
if key == "lunar_date" and isinstance(value, dict):
    response.basic_info[key] = json.dumps(value, ensure_ascii=False)
else:
    response.basic_info[key] = str(value)
```

**JSON 序列化标准**：
```python
import json

# ✅ 必须使用 ensure_ascii=False 支持中文
json.dumps(data, ensure_ascii=False)

# ✅ 处理不可序列化对象
json.dumps(data, ensure_ascii=False, default=str)
```

**规范要求**：
- ✅ 所有复杂结构必须使用 `json.dumps(ensure_ascii=False)` 序列化
- ✅ 必须使用 `default=str` 处理特殊类型（datetime、Decimal 等）
- ✅ 字符串类型字段只能存储字符串，不能存储对象

### 3.2 客户端反序列化规范（gRPC Client）

**JSON 字符串反序列化**：
```python
# ✅ 正确：安全地反序列化 JSON 字符串
try:
    if isinstance(value_json, str):
        result = json.loads(value_json) if value_json else {}
    else:
        result = value_json
except (json.JSONDecodeError, TypeError):
    result = {}  # 使用默认值
```

**类型验证和转换**：
```python
from server.utils.data_validator import DataValidator

# ✅ 使用 DataValidator 确保类型正确
bazi_data = DataValidator.ensure_dict(bazi_data)
ten_gods = DataValidator.ensure_list(ten_gods)

# ✅ 验证八字数据
bazi_data = DataValidator.validate_bazi_data(bazi_data)
```

**防御性编程**：
```python
# ✅ 检查字段是否存在
if response.basic_info:
    for key, value in response.basic_info.items():
        # 安全地处理每个字段
        if key == "lunar_date" and isinstance(value, str):
            try:
                parsed = json.loads(value) if value else {}
            except (json.JSONDecodeError, TypeError):
                parsed = {}
```

**规范要求**：
- ✅ 所有 JSON 反序列化必须使用 try-except
- ✅ 必须使用 `DataValidator` 进行类型验证
- ✅ 必须提供默认值，避免 None 导致的错误

### 3.3 数据验证规范

**使用 DataValidator**：
```python
from server.utils.data_validator import (
    ensure_dict,
    ensure_list,
    validate_bazi_data,
    safe_get_nested
)

# ✅ 确保字典类型
data = ensure_dict(data, default={})

# ✅ 确保列表类型
items = ensure_list(items, default=[])

# ✅ 验证八字数据
bazi_data = validate_bazi_data(bazi_data)

# ✅ 安全地获取嵌套值
stem = safe_get_nested(bazi_data, 'bazi_pillars', 'day', 'stem', default='')
```

**验证时机**：
- ✅ gRPC 客户端接收响应后立即验证
- ✅ API 函数处理数据前验证
- ✅ 缓存数据前验证

---

## 4. 开发规范强制要求

### 4.1 gRPC 协议开发检查清单

每次开发 gRPC 服务时必须检查：
- [ ] Proto 文件定义是否符合命名规范
- [ ] 消息定义是否有完整注释
- [ ] 复杂结构是否使用 JSON 字符串字段
- [ ] 是否实现 `HealthCheck` 方法
- [ ] 服务方法命名是否符合规范

### 4.2 API 接口开发检查清单

每次开发 API 接口时必须检查：
- [ ] 是否使用 Pydantic `BaseModel` 定义模型
- [ ] 所有字段是否使用 `Field` 提供描述和示例
- [ ] 关键字段是否使用 `@validator` 验证
- [ ] 响应模型是否包含 `success` 字段
- [ ] 是否在 `grpc_gateway.py` 中注册端点

### 4.3 序列化/反序列化检查清单

每次处理数据序列化时必须检查：
- [ ] 复杂结构是否使用 `json.dumps(ensure_ascii=False)` 序列化
- [ ] JSON 反序列化是否有 try-except 错误处理
- [ ] 是否使用 `DataValidator` 进行类型验证
- [ ] 是否提供默认值，避免 None 错误
- [ ] 是否进行防御性编程（None 检查、类型检查）

### 4.4 gRPC 代码兼容性检查清单

每次生成或修改 gRPC 代码时必须检查：
- [ ] grpcio 版本与 requirements.txt 一致
- [ ] grpcio-tools 版本与 grpcio 版本一致
- [ ] 生成的代码中无 `add_registered_method_handlers` 方法调用
- [ ] 运行修复脚本验证兼容性：`python3 scripts/grpc/fix_grpc_generated_code.py`
- [ ] 容器内代码已同步（通过挂载验证）：`bash scripts/grpc/verify_grpc_fix.sh`

---

## 5. 相关文件和工具

| 文件/工具 | 用途 |
|----------|------|
| `proto/*.proto` | gRPC 协议定义文件 |
| `server/api/grpc_gateway.py` | gRPC-Web 网关，统一注册端点 |
| `server/utils/data_validator.py` | 数据验证工具类 |
| `server/api/v1/*.py` | REST API 定义（Pydantic 模型） |
| `services/*/grpc_server.py` | gRPC 服务端实现 |
| `src/clients/*_client_grpc.py` | gRPC 客户端实现 |

---

## 6. 违反规范的后果

**禁止行为**：
- ❌ 禁止在 proto 中定义深度嵌套的 message（应使用 JSON 字符串）
- ❌ 禁止直接使用 `str()` 序列化字典（应使用 `json.dumps`）
- ❌ 禁止忽略 JSON 反序列化错误处理
- ❌ 禁止绕过 `DataValidator` 直接操作数据
- ❌ 禁止在 `grpc_gateway.py` 外直接处理 gRPC 请求

**违反规范的代码将被要求重构**：
- 所有不符合规范的代码必须按照本规范重构
- 重构时必须进行完整的测试验证
- 重构后必须通过代码审查

---

**核心原则**：
- 🔒 **严格类型**：所有数据必须有明确的类型定义和验证
- 🔄 **统一规范**：所有服务遵循相同的序列化/反序列化规范
- 🛡️ **防御编程**：所有数据操作必须有错误处理和默认值
- 📝 **完整文档**：所有模型和接口必须有清晰的注释和文档
- ⚠️ **强制遵守**：所有功能开发必须按照本规范执行，禁止自作主张

