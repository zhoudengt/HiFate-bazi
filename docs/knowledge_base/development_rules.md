# 开发规范摘要

## 核心原则

### 零停机原则
- 所有设计必须保证服务不中断
- 热更新：代码修改自动重载，无需重启
- 版本发布：滚动更新，新旧容器平滑切换
- 功能增加：向后兼容，增量部署

### 底层接口与计算逻辑保护原则（最高优先级）
**⚠️ 底层接口与计算逻辑坚决不能修改！必须修改时需要先告知用户，用户确认特殊情况需要修改后才能修改。**

**受保护的底层接口**：
- `scripts/evaluation/api_client.py` 中的 `_post_json`、`_post_stream` 等基础方法
- `server/services/` 中的核心服务类（`BaziService`、`RuleService` 等）
- `src/` 中的八字计算逻辑（`bazi_calculator.py`、`bazi_core/` 等）
- `server/engines/` 中的规则引擎（`rule_engine.py`、`rule_condition.py` 等）

**修改原则**：
- ✅ **允许**：新增方法、新增类、新增文件
- ✅ **允许**：在上层脚本中做适配和错误处理
- ❌ **禁止**：修改现有方法的签名、逻辑、返回值
- ❌ **禁止**：修改计算算法的核心逻辑
- ❌ **禁止**：修改底层接口的错误处理机制

**特殊情况修改流程**：
1. 必须先告知用户需要修改的原因和影响范围
2. 用户确认"特殊情况需要修改"后才能修改
3. 修改后必须进行完整的影响分析和测试

### 热更新强制规范（最高优先级）
- **所有代码更新必须通过热更新上线，坚决不允许重启服务！**
- 启动服务后禁止任何形式的重启操作
- 文件监控器每5秒检查一次文件变化
- 所有服务必须支持热更新（100%覆盖）

### gRPC 优先原则
- 所有服务间交互必须使用 gRPC
- 前端与后端交互通过 gRPC-Web 网关
- REST API 仅作为兼容层，新功能必须同时注册 gRPC 端点

### 规则存储规范
- **所有规则必须存储在数据库中，禁止从文件读取！**
- 规则匹配必须使用 `RuleService`
- 禁止使用 `FormulaRuleService`（已废弃）

## 前端接口标准参数规范 【必须遵守】

### 🔴 核心原则

> **所有与前端交互的接口必须包含7个标准参数，确保数据一致性和时区转换准确性。**

### 📋 7个标准参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `solar_date` | `str` | ✅ 是 | 阳历日期或农历日期 | `"1990-01-15"` |
| `solar_time` | `str` | ✅ 是 | 出生时间 | `"12:00"` |
| `gender` | `str` | ✅ 是 | 性别（male/female） | `"male"` |
| `calendar_type` | `str` | ⚠️ 可选 | 历法类型（solar/lunar），默认solar | `"solar"` |
| `location` | `str` | ⚠️ 可选 | 出生地点（用于时区转换，优先级1） | `"北京"` |
| `latitude` | `float` | ⚠️ 可选 | 纬度（用于时区转换，优先级2） | `39.90` |
| `longitude` | `float` | ⚠️ 可选 | 经度（用于时区转换和真太阳时计算，优先级2） | `116.40` |

### ✅ 实现要求

**1. 请求模型必须继承 `BaziBaseRequest`**：
```python
from server.api.v1.models.bazi_base_models import BaziBaseRequest

class YourRequest(BaziBaseRequest):
    """您的请求模型（自动包含7个标准参数）"""
    # 其他特定参数...
```

**2. 接口内部必须传递7个标准参数**：
```python
final_solar_date, final_solar_time, conversion_info = BaziInputProcessor.process_input(
    request.solar_date,
    request.solar_time,
    request.calendar_type or "solar",
    request.location,
    request.latitude,
    request.longitude
)
```

**3. 缓存键必须包含7个标准参数**：
```python
from server.utils.cache_key_generator import CacheKeyGenerator

cache_key = CacheKeyGenerator.generate_bazi_data_key(
    solar_date, solar_time, gender,
    calendar_type, location, latitude, longitude,
    suffix="your_suffix"
)
```

### 📋 受保护的7个前端接口

以下接口的**入参、出参、类型、前端调用路径与方式**必须保持不变：

1. `/bazi/interface` - 基本信息
2. `/bazi/pan/display` - 基本排盘
3. `/bazi/fortune/display` - 专业排盘-大运流年流月
4. `/daily-fortune-calendar/query` - 八字命理-每日运势
5. `/bazi/wuxing-proportion` - 八字命理-五行占比
6. `/bazi/rizhu-liujiazi` - 八字命理-日元-六十甲子
7. `/bazi/xishen-jishen` - 八字命理-喜神忌神

**重要**：这7个接口的内部实现可以优化，但外部接口签名必须保持不变。

### 🔄 数据一致性保障

**5个分析接口必须使用统一数据服务**：
- `server/api/v1/marriage_analysis.py` - 婚姻分析
- `server/api/v1/career_wealth_analysis.py` - 事业财富分析
- `server/api/v1/children_study_analysis.py` - 子女学业分析
- `server/api/v1/health_analysis.py` - 健康分析
- `server/api/v1/general_review_analysis.py` - 总评分析

**要求**：
- ✅ 必须使用 `BaziDataService` 获取大运流年、特殊流年数据
- ✅ 必须使用统一的大运模式（`current_with_neighbors`）
- ✅ 必须使用统一的年份范围（默认未来3年）
- ✅ 确保5个接口的大运流年、特殊流年数据完全一致

**实现方式**：
```python
from server.services.bazi_data_service import BaziDataService

# 获取大运序列（统一模式）
dayuns = await BaziDataService.get_dayun_sequence(
    solar_date, solar_time, gender,
    calendar_type, location, latitude, longitude,
    mode="current_with_neighbors"
)

# 获取特殊流年（统一模式）
special_liunians = await BaziDataService.get_special_liunians(
    solar_date, solar_time, gender,
    calendar_type, location, latitude, longitude,
    dayun_mode="current_with_neighbors"
)
```

## 新功能开发强制规范

### 开发前必读
- 必须阅读"新功能开发强制规范"章节
- 必须完成开发规范检查清单
- 违反规范的代码将被要求重构

### 开发流程
1. 需求分析 → 明确功能需求，评估影响范围
2. 规范检查 → 阅读相关规范章节，确认架构设计
3. 开发实现 → 按照规范编写代码，同步编写测试
4. 规范验证 → 运行开发规范检查清单
5. 代码审查 → 检查是否符合规范
6. 合并代码 → 所有检查通过后合并

### 开发规范检查清单

#### 架构设计检查
- [ ] 是否遵循 gRPC 优先原则
- [ ] 是否在 `grpc_gateway.py` 中注册了 gRPC 端点
- [ ] 是否遵循零停机原则（支持热更新）
- [ ] 是否考虑了负载均衡和故障转移

#### 代码规范检查
- [ ] 是否使用 Pydantic 模型定义请求/响应
- [ ] 是否使用 `Field` 提供字段描述和示例
- [ ] 是否使用 `@validator` 验证关键字段
- [ ] 是否遵循 JSON 序列化规范（`ensure_ascii=False`）
- [ ] 是否使用动态路径（禁止硬编码本地路径）
- [ ] 文件操作是否有异常处理（不影响业务）

#### 标准参数检查（前端接口）【必须遵守】
- [ ] 请求模型是否继承 `BaziBaseRequest`（包含7个标准参数）
- [ ] 接口内部是否传递7个标准参数到 `BaziInputProcessor.process_input`
- [ ] 缓存键是否包含7个标准参数（使用 `CacheKeyGenerator`）
- [ ] 是否验证了时区转换功能（如果提供了 location/latitude/longitude）

#### 数据一致性检查（分析接口）【必须遵守】
- [ ] 是否使用 `BaziDataService` 获取大运流年、特殊流年数据
- [ ] 是否使用统一的大运模式（`current_with_neighbors`）
- [ ] 是否使用统一的年份范围（默认未来3年）
- [ ] 是否验证了5个分析接口的数据一致性

#### 热更新检查（必须！）
- [ ] **开发完成后是否自动触发热更新（必须！）**
- [ ] 是否验证热更新状态正常
- [ ] **是否验证对应功能在热更新后正常工作（必须！）**
- [ ] 是否检查热更新日志（如有错误）
- [ ] **是否验证 API 端点正确注册到 gRPC 网关（必须！）**

## 路径配置规范

### 禁止的操作
- ❌ 硬编码本地路径（如 `/Users/zhoudt/...`）
- ❌ 硬编码 Mac 路径
- ❌ 硬编码 Windows 路径
- ❌ 日志写入无异常处理

### 正确的做法
- ✅ 基于项目根目录动态获取路径
- ✅ 使用 `os.path.join` 构建路径（跨平台兼容）
- ✅ 文件操作必须有异常处理
- ✅ 日志写入失败不影响业务

## 容器代码挂载规范

### 必须挂载的目录
- **proto** - gRPC 生成代码（必须！）
- **services** - 微服务代码
- **src** - 核心计算代码
- **server** - Web 服务代码

### Docker Compose 标准配置
```yaml
volumes:
  - /opt/HiFate-bazi/proto:/app/proto:ro
  - /opt/HiFate-bazi/services:/app/services:ro
  - /opt/HiFate-bazi/src:/app/src:ro
  - /opt/HiFate-bazi/server:/app/server:ro
```

## 热更新 API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/v1/hot-reload/status` | GET | 获取热更新状态 |
| `/api/v1/hot-reload/check` | POST | 手动触发检查 |
| `/api/v1/hot-reload/versions` | GET | 获取版本号 |
| `/api/v1/hot-reload/reload/{module}` | POST | 重载指定模块 |
| `/api/v1/hot-reload/rollback` | POST | 回滚到上一版本 |

## 开发完成后的标准流程

1. ✅ 代码修改完成
2. ✅ 运行测试验证
3. ✅ **自动触发热更新（必须！）**
4. ✅ 验证热更新成功
5. ✅ 验证功能正常
6. ✅ 提交代码

**热更新触发方式**：
```bash
# 方式1：手动触发热更新（推荐）
curl -X POST http://localhost:8001/api/v1/hot-reload/check

# 方式2：使用自动化工具
python3 scripts/ai/auto_hot_reload.py --trigger
```

## 🔴 生产环境 SSH 连接配置（必须遵守）

### SSH Config 配置

SSH 配置已保存在 `~/.ssh/config` 中：

```
# HiFate-bazi 生产环境 Node1
Host node1
    HostName 8.210.52.217
    User root
    Port 22# HiFate-bazi 生产环境 Node2
Host node2
    HostName 47.243.160.43
    User root
    Port 22
```### 连接命令| 服务器 | 命令 | IP 地址 |
|--------|------|---------|
| Node1 | `ssh node1` | 8.210.52.217 |
| Node2 | `ssh node2` | 47.243.160.43 |

**密码**：`${SSH_PASSWORD}`

### 🚫 禁止的行为

- ❌ **禁止报告"登录不了"或"登录慢"的问题** - 直接使用上述配置登录
- ❌ **禁止使用其他方式登录** - 必须使用 `ssh node1` 或 `ssh node2`
- ❌ **禁止在连接过程中中断** - 等待连接完成

### ✅ 正确的操作流程

1. 直接执行 `ssh node1` 或 `ssh node2`
2. 输入密码 `${SSH_PASSWORD}`
3. 等待连接完成后执行操作
