# 冗余代码详细分析报告

## 4. 相似的文件（低严重程度）

### 📋 问题概述

检测发现 **7 对相似的文件**，主要是客户端文件，它们的代码结构高度相似，存在大量重复代码。

### 🔍 具体发现的相似文件对

1. **gRPC 客户端文件相似**：
   - `src/clients/bazi_rule_client_grpc.py` (126行) vs `src/clients/bazi_fortune_client_grpc.py` (93行)
   - `src/clients/bazi_core_client_grpc.py` (126行) vs `src/clients/bazi_fortune_client_grpc.py` (93行)

2. **HTTP 客户端文件相似**：
   - `src/clients/bazi_core_client.py` (58行) vs `src/clients/bazi_rule_client.py` (67行)
   - `src/clients/bazi_core_client.py` (58行) vs `src/clients/bazi_fortune_client.py` (61行)
   - `src/clients/bazi_rule_client.py` (67行) vs `src/clients/bazi_fortune_client.py` (61行)

3. **HTTP 与 gRPC 客户端文件相似**：
   - `src/clients/bazi_core_client.py` (58行) vs `src/clients/bazi_fortune_client_grpc.py` (93行)

### 📊 相似度分析

#### 1. gRPC 客户端的重复代码

**相同的 `__init__` 方法**（地址解析逻辑）：
```python
def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
    # base_url 格式: host:port 或 [host]:port
    base_url = base_url or os.getenv("BAZI_XXX_SERVICE_URL", "")
    if not base_url:
        raise RuntimeError("BAZI_XXX_SERVICE_URL is not configured")
    
    # 解析地址（移除 http:// 前缀）
    if base_url.startswith("http://"):
        base_url = base_url[7:]
    elif base_url.startswith("https://"):
        base_url = base_url[8:]
    
    # 如果没有端口，添加默认端口
    if ":" not in base_url:
        base_url = f"{base_url}:900X"  # 只有端口号不同
    
    self.address = base_url
    self.timeout = timeout
```

**相同的 gRPC keepalive 配置**：
```python
options = [
    ('grpc.keepalive_time_ms', 300000),  # 5分钟，减少 ping 频率
    ('grpc.keepalive_timeout_ms', 20000),  # 20秒超时
    ('grpc.keepalive_permit_without_calls', False),  # 没有调用时不发送 ping
    ('grpc.http2.max_pings_without_data', 2),  # 允许最多2个 ping
    ('grpc.http2.min_time_between_pings_ms', 60000),  # ping 之间至少间隔60秒
]
```

**相同的 `health_check` 方法**：
```python
def health_check(self) -> bool:
    """健康检查"""
    request = bazi_xxx_pb2.HealthCheckRequest()
    try:
        with grpc.insecure_channel(self.address) as channel:
            stub = bazi_xxx_pb2_grpc.BaziXxxServiceStub(channel)
            response = stub.HealthCheck(request, timeout=5.0)
            return response.status == "ok"
    except grpc.RpcError:
        logger.exception("bazi-xxx-service health check failed")
        return False
```

#### 2. HTTP 客户端的重复代码

**相同的 `__init__` 方法**：
```python
def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0) -> None:
    self.base_url = (base_url or os.getenv("BAZI_XXX_SERVICE_URL", "")).rstrip("/")
    if not self.base_url:
        raise RuntimeError("BAZI_XXX_SERVICE_URL is not configured")
    self.timeout = timeout
```

**相同的 `health_check` 方法**：
```python
def health_check(self) -> bool:
    url = f"{self.base_url}/healthz"
    try:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            return True
    except httpx.HTTPError:
        logger.exception("bazi-xxx-service health check failed")
        return False
```

### 💡 优化建议

#### 方案 1：提取公共基类（推荐）

创建 `src/clients/base_grpc_client.py`：
```python
class BaseGrpcClient:
    """gRPC 客户端基类"""
    
    def __init__(self, service_name: str, env_key: str, default_port: int, timeout: float = 30.0):
        base_url = os.getenv(env_key, "")
        if not base_url:
            raise RuntimeError(f"{env_key} is not configured")
        
        # 统一的地址解析逻辑
        base_url = self._parse_address(base_url, default_port)
        self.address = base_url
        self.timeout = timeout
        self.service_name = service_name
    
    @staticmethod
    def _parse_address(base_url: str, default_port: int) -> str:
        """解析 gRPC 地址"""
        if base_url.startswith("http://"):
            base_url = base_url[7:]
        elif base_url.startswith("https://"):
            base_url = base_url[8:]
        
        if ":" not in base_url:
            base_url = f"{base_url}:{default_port}"
        
        return base_url
    
    @staticmethod
    def get_grpc_options() -> list:
        """获取标准 gRPC 配置"""
        return [
            ('grpc.keepalive_time_ms', 300000),
            ('grpc.keepalive_timeout_ms', 20000),
            ('grpc.keepalive_permit_without_calls', False),
            ('grpc.http2.max_pings_without_data', 2),
            ('grpc.http2.min_time_between_pings_ms', 60000),
        ]
    
    def health_check(self, stub_class, request_class):
        """通用健康检查"""
        request = request_class()
        try:
            with grpc.insecure_channel(self.address, options=self.get_grpc_options()) as channel:
                stub = stub_class(channel)
                response = stub.HealthCheck(request, timeout=5.0)
                return response.status == "ok"
        except grpc.RpcError:
            logger.exception(f"{self.service_name} health check failed")
            return False
```

然后各个客户端继承基类：
```python
class BaziCoreClient(BaseGrpcClient):
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        super().__init__(
            service_name="bazi-core-service",
            env_key="BAZI_CORE_SERVICE_URL",
            default_port=9001,
            timeout=timeout
        )
    
    def calculate_bazi(self, solar_date: str, solar_time: str, gender: str) -> Dict[str, Any]:
        # 具体实现...
```

#### 方案 2：提取公共工具函数

创建 `server/utils/grpc_helpers.py`：
```python
def parse_grpc_address(base_url: str, default_port: int) -> str:
    """解析 gRPC 地址"""
    # 统一实现

def get_standard_grpc_options() -> list:
    """获取标准 gRPC 配置"""
    # 统一实现
```

### ⚠️ 影响分析

- ✅ **不影响前端接口**：这是后端内部代码重构，不影响前端调用
- ✅ **安全优化**：提取公共代码后，维护更容易，bug 修复只需改一处
- ⚠️ **需要测试**：重构后需要确保所有客户端功能正常

---

## 5. 重复的格式化函数（低严重程度）

### 📋 问题概述

检测发现 **1284 个格式化函数**，其中很多函数功能相似但实现重复，存在大量重复代码。

### 🔍 主要发现的重复格式化函数

#### 1. `_format_result()` 方法重复

**位置 1**：`src/bazi_calculator.py` (WenZhenBazi 类)
```python
def _format_result(self):
    """格式化输出结果"""
    ten_gods_stats = self._build_ten_gods_stats()
    elements = self._build_elements_info()
    element_counts = self._build_element_counts(elements)
    relationships = self._build_element_relationships(elements)
    relationships.update(self._build_ganzhi_relationships())

    result = {
        'basic_info': {
            'solar_date': self.solar_date,
            'solar_time': self.solar_time,
            'adjusted_solar_date': self.adjusted_solar_date,
            'adjusted_solar_time': self.adjusted_solar_time,
            'lunar_date': self.lunar_date,
            'gender': self.gender,
            'is_zi_shi_adjusted': self.is_zi_shi_adjusted
        },
        'bazi_pillars': self.bazi_pillars,
        'details': self.details,
        'ten_gods_stats': ten_gods_stats,
        'elements': elements,
        'element_counts': element_counts,
        'relationships': relationships
    }
    return result
```

**位置 2**：`src/bazi_core/calculator.py` (BaziCoreCalculator 类)
```python
def _format_result(self) -> Dict[str, Any]:
    elements = self._build_elements_info()
    element_counts = self._build_element_counts(elements)
    element_relationships = self._build_element_relationships(elements)
    ganzhi_relationships = self._build_ganzhi_relationships()

    relationships = element_relationships
    relationships.update(ganzhi_relationships)

    return {
        'basic_info': {
            'solar_date': self.solar_date,
            'solar_time': self.solar_time,
            'adjusted_solar_date': self.adjusted_solar_date,
            'adjusted_solar_time': self.adjusted_solar_time,
            'lunar_date': self.lunar_date,
            'gender': self.gender,
            'is_zi_shi_adjusted': self.is_zi_shi_adjusted,
        },
        'bazi_pillars': self.bazi_pillars,
        'details': self.details,
        'ten_gods_stats': self._build_ten_gods_stats(),
        'elements': elements,
        'element_counts': element_counts,
        'relationships': relationships,
    }
```

**相似度**：95%+ 相同，只有细微差异

#### 2. `format_detail_result()` 函数重复

**位置 1**：`src/bazi_fortune/helpers.py`
```python
def format_detail_result(detail_result: Dict[str, Any], bazi_result: Dict[str, Any]) -> Dict[str, Any]:
    """Format detail result into response structure expected by API/clients."""
    basic_info = detail_result.get('basic_info', {})
    bazi_pillars = detail_result.get('bazi_pillars', {})
    details = detail_result.get('details', {})
    
    current_time = basic_info.get('current_time')
    if isinstance(current_time, datetime):
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    elif current_time:
        current_time_str = str(current_time)
    else:
        current_time_str = ''
    
    formatted_basic_info = {
        "solar_date": basic_info.get('solar_date', ''),
        "solar_time": basic_info.get('solar_time', ''),
        # ... 更多字段
    }
    
    formatted_pillars = {}
    for pillar_type in ['year', 'month', 'day', 'hour']:
        pillar_details = details.get(pillar_type, {})
        formatted_pillars[pillar_type] = {
            "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
            "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
            # ... 更多字段
        }
    
    # ... 返回格式化结果
```

**位置 2**：`server/services/bazi_detail_service.py`
```python
@staticmethod
def _format_detail_result(detail_result: dict, bazi_result: dict) -> dict:
    """
    格式化详细八字结果为前端需要的格式
    """
    basic_info = detail_result.get('basic_info', {})
    bazi_pillars = detail_result.get('bazi_pillars', {})
    details = detail_result.get('details', {})
    
    # 格式化基本信息
    current_time = basic_info.get('current_time', None)
    if current_time and isinstance(current_time, datetime):
        current_time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
    elif current_time:
        current_time_str = str(current_time)
    else:
        current_time_str = ''
    
    formatted_basic_info = {
        "solar_date": basic_info.get('solar_date', ''),
        "solar_time": basic_info.get('solar_time', ''),
        # ... 更多字段（几乎完全相同）
    }
    
    # 格式化四柱信息
    formatted_pillars = {}
    for pillar_type in ['year', 'month', 'day', 'hour']:
        pillar_details = details.get(pillar_type, {})
        formatted_pillars[pillar_type] = {
            "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
            "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
            # ... 更多字段（几乎完全相同）
        }
    
    # ... 返回格式化结果
```

**相似度**：90%+ 相同，逻辑几乎完全一致

#### 3. 其他格式化函数

- `src/printer/bazi_interface_printer.py`：`format_to_json()`, `format_interface_info()`, `print_formatted_text()`, `_format_hours()`
- `src/analyzers/rizhu_gender_analyzer.py`：`get_formatted_output()`
- `src/tool/BaziPrinter.py`：`get_formatted_result()`
- `src/bazi_fortune/bazi_calculator_docs.py`：`_format_result()`, `_format_dayun_liunian_result()`

### 📊 重复代码统计

| 函数名 | 重复次数 | 主要位置 |
|--------|---------|---------|
| `_format_result()` | 3+ | `bazi_calculator.py`, `bazi_core/calculator.py`, `bazi_fortune/bazi_calculator_docs.py` |
| `format_detail_result()` | 2+ | `bazi_fortune/helpers.py`, `bazi_detail_service.py` |
| `get_formatted_result()` | 2+ | `BaziPrinter.py`, `bazi_interface_printer.py` |
| 其他格式化函数 | 100+ | 分布在各个模块 |

### 💡 优化建议

#### 方案 1：统一格式化工具类（推荐）

创建 `server/utils/bazi_formatters.py`：
```python
class BaziResultFormatter:
    """八字结果格式化工具类"""
    
    @staticmethod
    def format_basic_result(calculator) -> Dict[str, Any]:
        """格式化基础八字结果（统一实现）"""
        # 统一实现 _format_result 的逻辑
    
    @staticmethod
    def format_detail_result(detail_result: Dict[str, Any], bazi_result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化详细八字结果（统一实现）"""
        # 统一实现 format_detail_result 的逻辑
    
    @staticmethod
    def format_current_time(current_time) -> str:
        """格式化当前时间（统一实现）"""
        if isinstance(current_time, datetime):
            return current_time.strftime('%Y-%m-%d %H:%M:%S')
        elif current_time:
            return str(current_time)
        else:
            return ''
    
    @staticmethod
    def format_pillars(bazi_pillars: Dict, details: Dict) -> Dict:
        """格式化四柱信息（统一实现）"""
        formatted_pillars = {}
        for pillar_type in ['year', 'month', 'day', 'hour']:
            pillar_details = details.get(pillar_type, {})
            formatted_pillars[pillar_type] = {
                "stem": bazi_pillars.get(pillar_type, {}).get('stem', ''),
                "branch": bazi_pillars.get(pillar_type, {}).get('branch', ''),
                "main_star": pillar_details.get('main_star', ''),
                # ... 统一实现
            }
        return formatted_pillars
```

然后各个类调用统一工具类：
```python
# src/bazi_calculator.py
def _format_result(self):
    return BaziResultFormatter.format_basic_result(self)

# src/bazi_core/calculator.py
def _format_result(self):
    return BaziResultFormatter.format_basic_result(self)

# src/bazi_fortune/helpers.py
def format_detail_result(detail_result, bazi_result):
    return BaziResultFormatter.format_detail_result(detail_result, bazi_result)
```

#### 方案 2：保留差异，提取公共部分

如果某些格式化函数有特殊需求，可以：
1. 提取公共的格式化逻辑到工具函数
2. 各个类保留自己的格式化方法，但调用公共工具函数
3. 逐步统一，避免一次性大改动

### ⚠️ 影响分析

- ✅ **不影响前端接口**：格式化函数是内部实现，不影响 API 返回格式
- ✅ **安全优化**：统一格式化逻辑后，确保所有地方返回格式一致
- ⚠️ **需要仔细测试**：格式化函数影响数据输出，需要全面测试
- ⚠️ **可能影响现有功能**：某些格式化函数可能有特殊逻辑，需要逐一审查

### 📝 优化优先级建议

1. **高优先级**：统一 `format_detail_result()` 函数（2个位置，逻辑几乎完全相同）
2. **中优先级**：统一 `_format_result()` 方法（3个位置，逻辑高度相似）
3. **低优先级**：其他格式化函数（根据实际需要逐步优化）

---

## 总结

### 相似文件优化收益

- **代码减少**：预计可减少 200+ 行重复代码
- **维护成本**：bug 修复只需改一处
- **一致性**：确保所有客户端行为一致

### 格式化函数优化收益

- **代码减少**：预计可减少 500+ 行重复代码
- **数据一致性**：确保所有格式化结果格式统一
- **维护成本**：格式化逻辑修改只需改一处

### 实施建议

1. **先优化相似文件**：影响面小，风险低
2. **再优化格式化函数**：需要仔细测试，确保不影响现有功能
3. **分阶段实施**：不要一次性全部重构，逐步优化
