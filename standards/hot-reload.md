# 热更新详细规范

> 本文档从 `.cursorrules` 提取，包含热更新系统的完整规范。详见 `.cursorrules` 核心规范章节。

## 核心原则

> **⚠️ 所有代码更新必须通过热更新上线，坚决不允许重启服务！启动服务后禁止任何形式的重启操作！**

---

## 热更新架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          热更新系统架构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │   文件监控器    │────→│   版本管理器    │────→│   重载器        │       │
│  │ FileMonitor     │     │ VersionManager  │     │ Reloaders       │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
│         │                        │                        │                 │
│         ↓                        ↓                        ↓                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    热更新管理器 HotReloadManager                      │   │
│  │  - 统一协调所有模块热更新                                             │   │
│  │  - 管理更新顺序和依赖关系                                             │   │
│  │  - 触发单例重置和缓存清理                                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ↓                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 多 Worker 同步器 WorkerSyncManager                    │   │
│  │  - 使用信号文件实现跨进程通信                                         │   │
│  │  - 确保所有 Worker 进程同步更新                                       │   │
│  │  - 解决 uvicorn 多 worker 模式下热更新问题                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                   │
│         ↓                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    双机同步器 ClusterSynchronizer                     │   │
│  │  - 通过 Redis 发布/订阅同步更新事件                                   │   │
│  │  - 确保所有节点同时更新                                               │   │
│  │  - 分布式锁防止并发冲突                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 热更新覆盖范围（必须100%覆盖）

| 服务类型 | 服务名称 | 端口 | 热更新方式 | 状态 |
|---------|---------|------|-----------|------|
| **Web 主服务** | FastAPI | 8001 | HotReloadManager | ✅ 已支持 |
| **八字核心** | bazi_core | 9001 | 微服务热更新器 | ✅ 必须支持 |
| **运势计算** | bazi_fortune | 9002 | 微服务热更新器 | ✅ 必须支持 |
| **八字分析** | bazi_analyzer | 9003 | 微服务热更新器 | ✅ 必须支持 |
| **规则匹配** | bazi_rule | 9004 | 微服务热更新器 | ✅ 必须支持 |
| **运势分析** | fortune_analysis | 9005 | 微服务热更新器 | ✅ 必须支持 |
| **支付服务** | payment_service | 9006 | 微服务热更新器 | ✅ 必须支持 |
| **运势规则** | fortune_rule | 9007 | 微服务热更新器 | ✅ 必须支持 |
| **意图识别** | intent_service | 9008 | 微服务热更新器 | ✅ 必须支持 |
| **提示优化** | prompt_optimizer | 9009 | 微服务热更新器 | ✅ 必须支持 |
| **风水分析** | desk_fengshui | 9010 | 微服务热更新器 | ✅ 必须支持 |

**重要**：所有服务必须支持热更新，不允许存在任何不支持热更新的服务！

## 热更新 API 接口

| 接口 | 方法 | 功能 | 说明 |
|------|------|------|------|
| `/api/v1/hot-reload/status` | GET | 获取热更新状态 | 查看所有服务的热更新状态 |
| `/api/v1/hot-reload/check` | POST | 手动触发检查 | 立即检查并更新所有变化的模块 |
| `/api/v1/hot-reload/versions` | GET | 获取版本号 | 查看所有模块的当前版本号 |
| `/api/v1/hot-reload/reload/{module}` | POST | 重载指定模块 | 强制重载指定模块 |
| `/api/v1/hot-reload/reload-all` | POST | 重载所有模块 | **自动通知所有 Worker** |
| `/api/v1/hot-reload/rollback` | POST | 回滚到上一版本 | 紧急回滚到上一个稳定版本 |
| `/api/v1/hot-reload/sync` | POST | 同步所有节点 | 触发双机同步更新 |
| `/api/v1/hot-reload/health` | GET | 健康检查 | 检查热更新系统健康状态 |
| `/api/v1/hot-reload/worker-sync` | GET | 多 Worker 同步状态 | 查看 Worker 同步监控状态 |
| `/api/v1/hot-reload/trigger-all-workers` | POST | 触发所有 Worker | 手动触发所有 Worker 热更新 |

## 热更新模块类型

| 模块类型 | 模块名 | 说明 | 更新方式 |
|---------|--------|------|---------|
| `rules` | 规则模块 | 八字规则配置 | 数据库版本号检测 |
| `content` | 内容模块 | 规则描述内容 | 数据库版本号检测 |
| `config` | 配置模块 | 系统配置 | Redis/环境变量检测 |
| `cache` | 缓存模块 | 缓存数据 | 清空缓存 |
| `source` | 源代码模块 | Python源代码 | 文件修改时间检测 |
| `microservice` | 微服务模块 | gRPC微服务代码 | 文件修改时间检测 |

## 热更新检测机制

**检测间隔**：
- 文件监控器：每 **5秒** 检查一次文件变化
- 版本检查器：每 **60秒** 检查一次数据库版本号
- 微服务检查器：每 **30秒** 检查一次微服务代码变化

**检测范围**：
- `src/` - 核心计算模块
- `server/` - 服务层代码
- `services/` - 微服务代码（**必须包含！**）

## 热更新安全机制

### 1. 语法验证

```python
# 热更新前必须验证语法
import ast
try:
    ast.parse(source_code)  # 语法正确才允许更新
except SyntaxError:
    # 语法错误，拒绝更新，保持旧版本运行
```

### 2. 依赖顺序

```python
# 按依赖关系顺序更新
RELOAD_ORDER = [
    'config',      # 1. 先更新配置
    'rules',       # 2. 更新规则
    'content',     # 3. 更新内容
    'source',      # 4. 更新源代码
    'microservice', # 5. 更新微服务
    'cache',       # 6. 最后清理缓存
]
```

### 3. 单例重置

```python
# 热更新时自动重置所有单例
SINGLETON_RESET_LIST = [
    'RuleService._engine',
    'RuleService._cache',
    'MetricsCollector._instance',
    'AlertManager._instance',
    'Tracer._instance',
]
```

### 4. 回滚机制

```python
# 每次更新前自动备份所有监控文件到 .hot_reload_backups/
# 如果更新失败，自动回滚到上一版本
# 支持两种回滚方式：
#   - 文件备份回滚：恢复备份的文件
#   - Git 回滚：使用 git checkout 恢复文件（当备份不可用时）
```

### 5. 代码备份机制

```python
# 热更新前自动备份所有监控文件
# 备份位置：.hot_reload_backups/{service_name}/v{version}/
# 保留最近 10 个版本的备份
# 备份信息保存在 backup_info.json
```

### 6. 依赖关系管理

```python
# 自动检测共享文件变化（src/、server/）
# 自动触发所有依赖服务的热更新
# 依赖关系映射：DEPENDENCY_MAP
# 确保所有依赖服务同步更新
```

### 7. 错误处理和日志

```python
# 详细错误日志保存到 logs/hot_reload_errors/
# 错误日志包含：错误信息、堆栈跟踪、时间戳、版本号
# 支持告警机制（可通过环境变量启用）
# 自动清理旧日志（保留最近 50 个）
```

### 8. 并发安全

```python
# 使用双重检查锁定模式
# Servicer 实例验证（在替换前验证）
# 原子替换机制（确保版本号与实例一致性）
# 防止并发更新冲突
```

### 9. 性能优化

```python
# 优先使用文件修改时间（避免重复计算哈希）
# 只在必要时计算文件哈希
# 减少不必要的文件读取
# 方法缓存机制（DynamicServicer）
```

## 双机同步机制

**同步流程**：
```
1. Node1 检测到代码变化
2. Node1 执行热更新
3. Node1 验证更新成功
4. Node1 通过 Redis 发布更新事件
5. Node2 收到事件，执行相同的热更新
6. Node2 确认更新成功
7. 双机同步完成
```

**Redis 频道**：
- `hifate:hot-reload:trigger` - 触发更新事件
- `hifate:hot-reload:confirm` - 确认更新完成
- `hifate:hot-reload:rollback` - 回滚事件

**分布式锁**：
```python
# 防止并发更新冲突
LOCK_KEY = "hifate:hot-reload:lock"
LOCK_TIMEOUT = 60  # 60秒超时
```

## 多 Worker 同步机制（重要！）

> **⚠️ 这是解决 uvicorn 多 worker 模式下热更新问题的关键机制！**

### 问题背景

生产环境使用 `uvicorn` 多 worker 模式（8 个 worker 进程）提高并发性能：

```python
# server/start.py
uvicorn.run("server.main:app", workers=8, ...)
```

**问题**：
- 每个 worker 是独立的 Python 进程
- 调用热更新 API 时，只有处理该请求的 worker 会重载代码
- 其他 7 个 worker 仍运行旧代码
- 用户请求被负载均衡到不同 worker，大概率（87.5%）命中旧代码

### 解决方案

使用 `WorkerSyncManager` 实现跨进程热更新同步：

```
热更新 API 被调用
       ↓
写入信号文件 (/tmp/hifate_hot_reload_signal.json)
       ↓
所有 Worker 的后台线程检测到信号（每 2 秒）
       ↓
各 Worker 独立执行模块重载
       ↓
全部 Worker 代码更新完成
```

### 信号文件格式

```json
{
  "version": 1,
  "timestamp": 1738756800.123,
  "modules": ["config", "singleton", "rules", "content", "source", "microservice", "cache"],
  "trigger_time": "2026-02-05 14:00:00",
  "trigger_pid": 12345
}
```

### 核心实现

**1. 信号文件位置**：
```python
SIGNAL_FILE = "/tmp/hifate_hot_reload_signal.json"
```

**2. 检测间隔**：每 2 秒检查一次信号文件

**3. 触发条件**：信号文件的 `version` 或 `timestamp` 比本地记录更新

### API 使用

```bash
# 查看当前 Worker 的同步状态
curl http://localhost:8001/api/v1/hot-reload/worker-sync
# 返回示例：
# {
#   "success": true,
#   "status": {
#     "worker_id": "12345",
#     "running": true,
#     "check_interval": 2,
#     "last_signal_version": 1,
#     "signal_file": "/tmp/hifate_hot_reload_signal.json"
#   }
# }

# 手动触发所有 Worker 热更新
curl -X POST http://localhost:8001/api/v1/hot-reload/trigger-all-workers

# 重载所有模块（自动通知所有 Worker）
curl -X POST http://localhost:8001/api/v1/hot-reload/reload-all
# 返回示例：
# {
#   "success": true,
#   "message": "重载完成: 7 成功, 0 失败 | 已通知所有 Worker (version: 1)"
# }
```

### 代码位置

- **核心模块**：`server/hot_reload/worker_sync.py`
- **集成点**：`server/hot_reload/hot_reload_manager.py`（在 `start()` 时自动启动）
- **API 端点**：`server/hot_reload/api.py`

### 验证方法

```bash
# 1. 多次调用 API，观察 worker_id 是否变化
for i in {1..5}; do
  curl -s http://localhost:8001/api/v1/hot-reload/worker-sync | jq '.status.worker_id'
done

# 2. 触发热更新后，确认所有 Worker 的 last_signal_version 都更新
curl -X POST http://localhost:8001/api/v1/hot-reload/reload-all
sleep 5
curl http://localhost:8001/api/v1/hot-reload/worker-sync
```

### 注意事项

1. **首次部署此功能需要重启**：因为旧代码不包含 `WorkerSyncManager`，需要重启容器加载新代码
2. **之后无需重启**：新的同步机制会确保所有 Worker 同步更新
3. **信号文件在 /tmp**：容器重启后会丢失，但这不影响功能（version 会从 0 开始）

## 热更新开发规范

### 1. 代码编写规范

- ✅ 避免在模块级别初始化全局状态
- ✅ 使用函数/类方法而不是模块级代码
- ✅ 单例类必须提供 `reset()` 方法
- ✅ 避免循环依赖
- ✅ 所有配置通过热加载机制获取

### 2. 单例类必须支持重置

```python
class MySingleton:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """热更新时调用，重置单例"""
        cls._instance = None
```

### 3. 缓存必须支持清理

```python
class MyService:
    _cache = {}
    
    @classmethod
    def clear_cache(cls):
        """热更新时调用，清理缓存"""
        cls._cache.clear()
```

### 4. 配置必须支持热加载

```python
# ✅ 正确：每次使用时获取配置
def get_config():
    return os.getenv("MY_CONFIG", "default")

# ❌ 错误：模块加载时固定配置
MY_CONFIG = os.getenv("MY_CONFIG", "default")  # 热更新后不会变化
```

## 热更新测试规范

**⚠️ 重要：每次开发完成后必须自动触发热更新！**

**每次代码修改后必须验证**：
```bash
# 1. 检查热更新状态
curl http://localhost:8001/api/v1/hot-reload/status

# 2. 手动触发热更新（必须！）
curl -X POST http://localhost:8001/api/v1/hot-reload/check

# 3. 验证版本号更新
curl http://localhost:8001/api/v1/hot-reload/versions

# 4. 验证功能正常
# 调用相关 API 测试功能
```

**开发完成后的标准流程**：
1. ✅ 代码修改完成
2. ✅ 运行测试验证
3. ✅ **自动触发热更新**（必须！）
4. ✅ 验证热更新成功
5. ✅ 验证功能正常
6. ✅ 提交代码

**微服务热更新测试流程**：
```bash
# 1. 运行完整测试套件
python3 scripts/hot_reload/test_microservice_hot_reload.py

# 2. 测试基本功能
# - 基本热更新功能
# - 回滚机制
# - 依赖关系管理
# - 错误处理
# - 性能优化
# - 并发安全
# - DynamicServicer 方法转发

# 3. 验证微服务热更新状态
curl http://localhost:8001/api/v1/hot-reload/microservices

# 4. 测试实际热更新
# 修改微服务代码后，等待30秒自动更新，或手动触发：
curl -X POST http://localhost:8001/api/v1/hot-reload/reload/microservice
```

**测试检查清单**：
- [ ] 所有测试用例通过（7/7）
- [ ] 备份目录创建正常（`.hot_reload_backups/`）
- [ ] 错误日志目录创建正常（`logs/hot_reload_errors/`）
- [ ] 依赖关系识别正确
- [ ] 错误日志写入正常
- [ ] 文件修改时间检查正常
- [ ] 锁机制存在
- [ ] DynamicServicer 方法转发正常

## 微服务热更新测试流程

**标准测试流程**：
```bash
# 1. 运行完整测试套件
python3 scripts/hot_reload/test_microservice_hot_reload.py

# 2. 验证测试结果
# 应该看到：🎉 所有测试通过！（7/7 通过）

# 3. 测试实际热更新（可选）
# a. 修改微服务代码
vim services/bazi_core/grpc_server.py

# b. 等待自动更新（30秒）或手动触发
curl -X POST http://localhost:8001/api/v1/hot-reload/reload/microservice

# c. 验证更新成功
curl http://localhost:8001/api/v1/hot-reload/microservices

# d. 测试回滚（如果需要）
curl -X POST http://localhost:8001/api/v1/hot-reload/rollback
```

**测试覆盖范围**：
- ✅ 基本热更新功能
- ✅ 回滚机制（备份和 Git 回滚）
- ✅ 依赖关系管理
- ✅ 错误处理和日志
- ✅ 性能优化
- ✅ 并发安全
- ✅ DynamicServicer 方法转发

**测试文件位置**：
- `scripts/hot_reload/test_microservice_hot_reload.py` - 完整测试套件

## 热更新监控告警

**监控指标**：
- 热更新成功/失败次数
- 热更新延迟时间
- 模块版本号变化
- 双机同步状态

**告警条件**：
- 热更新失败 → 立即告警
- 双机版本不一致 → 立即告警
- 热更新延迟 > 5分钟 → 警告
- 回滚发生 → 立即告警

## 严格禁止的操作

| 操作 | 原因 | 替代方案 |
|------|------|---------|
| ❌ `docker restart` | 中断服务 | 使用热更新 API |
| ❌ `docker-compose restart` | 中断服务 | 使用热更新 API |
| ❌ `systemctl restart` | 中断服务 | 使用热更新 API |
| ❌ 手动停止启动服务 | 中断服务 | 使用热更新 API |
| ❌ 直接修改生产服务器代码 | 不可追溯 | 通过 Git 推送 |
| ❌ 跳过热更新直接部署 | 可能导致问题 | 必须经过热更新 |

## 唯一允许重启的例外情况

以下情况**必须经过审批**才能重启：
1. **新增依赖包**：需要安装新的 Python 包
2. **修改热更新系统本身**：`server/hot_reload/` 目录
3. **修改启动脚本**：`server/main.py` 的启动逻辑
4. **系统级别问题**：内存泄漏、进程僵死等

**即使允许重启，也必须**：
1. 选择低峰期（凌晨 2:00-6:00）
2. 使用滚动更新（双机轮流重启）
3. 准备回滚方案
4. 记录重启原因和时间

## 热更新检查清单

每次开发新功能时，必须检查：

- [ ] 代码是否在热更新监控范围内（`src/`, `server/`, `services/`）
- [ ] 是否引入了新的全局状态（需要支持重置）
- [ ] 单例类是否提供了 `reset()` 方法
- [ ] 缓存是否支持清理
- [ ] 配置是否支持热加载
- [ ] **开发完成后是否触发热更新（必须！）**
- [ ] **是否验证对应功能在热更新后正常工作（必须！）**
- [ ] **如果涉及 API 端点，是否验证端点正确注册到 gRPC 网关（必须！）**
- [ ] 是否检查热更新日志（如有错误）
- [ ] 是否更新了热更新文档

**微服务热更新专项检查**：
- [ ] 微服务是否已集成热更新（使用 `create_hot_reload_server`）
- [ ] 是否注册了热更新器（`register_microservice_reloader`）
- [ ] 依赖对象是否支持重置（单例、缓存等）
- [ ] 是否测试了回滚机制
- [ ] 是否验证了依赖关系管理
- [ ] 是否检查了错误日志
- [ ] 是否运行了完整测试套件（`test_microservice_hot_reload.py`）

## 微服务热更新缺陷修复清单

**已修复的缺陷**（2026-02-05）：

0. ✅ **多 Worker 热更新不同步**（🔴 关键修复）
   - 问题：uvicorn 多 worker 模式下，热更新只影响单个 worker
   - 解决：新增 `WorkerSyncManager` 实现跨进程信号机制
   - 信号文件：`/tmp/hifate_hot_reload_signal.json`
   - 检测间隔：每 2 秒检查一次
   - 新增 API：`/api/v1/hot-reload/worker-sync`、`/api/v1/hot-reload/trigger-all-workers`

1. ✅ **回滚机制不完整**
   - 添加代码备份机制（`.hot_reload_backups/`）
   - 支持 Git 回滚（当备份不可用时）
   - 改进回滚逻辑，恢复备份文件

2. ✅ **DynamicServicer 方法转发**
   - 使用 `__getattribute__` 确保所有属性访问都经过转发
   - 添加方法缓存机制（性能优化）
   - 支持动态方法绑定

3. ✅ **依赖对象不更新**
   - 自动检测依赖对象（Servicer 实例的所有属性）
   - 重置单例对象（自动检测并重置 `_instance`）
   - 支持重置方法（自动调用 `reset()` 和 `clear_cache()`）

4. ✅ **单例不重置**
   - 集成 SingletonReloader
   - 在热更新时自动重置所有注册的单例

5. ✅ **依赖模块不同步**
   - 添加依赖关系映射（DEPENDENCY_MAP）
   - 自动触发更新（检测到共享文件变化时）
   - 同步更新（确保所有依赖服务使用最新代码）

6. ✅ **错误处理**
   - 详细错误日志（保存到 `logs/hot_reload_errors/`）
   - 告警机制（支持告警，可通过环境变量启用）
   - 错误恢复（改进错误恢复流程，自动清理旧日志）

7. ✅ **并发安全**
   - 原子替换机制（使用双重检查锁定模式）
   - Servicer 验证（在替换前验证新实例是否可用）
   - 版本一致性（确保版本号与实例的一致性）

8. ✅ **性能优化**
   - 优化文件扫描（优先使用修改时间，只在必要时计算哈希）
   - 减少文件读取（避免重复读取文件内容）
   - 缓存优化（复用已读取的文件内容）

**测试验证**：
- ✅ 所有测试用例通过（7/7）
- ✅ 备份机制正常
- ✅ 错误日志正常
- ✅ 依赖关系识别正确
- ✅ 性能优化有效

## 本地/测试/生产一致性规范

**🔴 核心原则**：本地、测试、生产环境的代码和配置必须完全一致！**坚决禁止直接在服务器上修改代码！**

**🔴 严格禁止的操作**：

| 操作 | 状态 | 原因 | 正确方式 |
|------|------|------|---------|
| ❌ **直接在服务器上修改代码** | **禁止** | 破坏代码一致性，无法版本控制 | 本地修改 → GitHub → 服务器 |
| ❌ **直接在服务器上修改配置文件** | **禁止** | 配置不一致，难以追踪 | 本地修改 → GitHub → 服务器 |
| ❌ **在服务器上手动编辑文件** | **禁止** | 无法版本控制，容易丢失 | 本地修改 → GitHub → 服务器 |
| ❌ **跳过 Git 直接部署** | **禁止** | 无法追踪变更，无法回滚 | 必须通过 Git 版本控制 |
| ❌ **服务器代码与 GitHub 不一致** | **禁止** | 破坏一致性原则 | 必须保持一致 |

**✅ 唯一正确的代码修改流程**：

```
本地开发 → 提交到 Git → 推送到 GitHub → 服务器拉取 → 热更新
   ↓           ↓              ↓              ↓           ↓
 修改代码    git commit    git push      git pull    自动更新
```

**详细流程**：

1. **本地开发**
   ```bash
   # 在本地 Mac 上修改代码
   vim server/api/v1/bazi.py
   ```

2. **提交到 Git**
   ```bash
   git add server/api/v1/bazi.py
   git commit -m "feat: 新功能"
   ```

3. **推送到 GitHub**
   ```bash
   git push origin master
   ```

4. **服务器拉取（自动或手动）**
   ```bash
   # 增量部署脚本会自动拉取
   bash deploy/scripts/incremental_deploy_production.sh
   
   # 或手动拉取
   ssh root@server "cd /opt/HiFate-bazi && git pull origin master"
   ```

5. **热更新（自动）**
   ```bash
   # 热更新系统自动检测并更新（30秒内）
   # 或手动触发
   curl -X POST http://server:8001/api/v1/hot-reload/check
   ```

**一致性要求**：
| 项目 | 要求 | 检查方式 | 违反后果 |
|------|------|---------|---------|
| **代码版本** | 三环境完全一致 | `git log --oneline -1` | 可能导致功能不一致 |
| **文件内容** | 三环境完全一致 | `git diff` 检查服务器代码 | 可能导致 Bug |
| **配置文件** | 三环境完全一致 | 对比配置文件内容 | 可能导致配置错误 |
| **热更新配置** | 三环境完全一致 | 检查 `HOT_RELOAD_*` 环境变量 | 可能导致热更新失败 |
| **依赖包版本** | 三环境完全一致 | 检查 `requirements.txt` | 可能导致依赖问题 |

**服务器代码检查机制**：

增量部署脚本会自动检查并处理服务器上的本地更改：

```bash
# 在拉取代码前，自动保存服务器上的本地更改
git stash || true

# 拉取最新代码（确保与 GitHub 一致）
git pull origin master

# 如果服务器上有本地更改，会显示警告
```

**如果发现服务器上有本地更改**：

1. **检查更改内容**：
   ```bash
   ssh root@server "cd /opt/HiFate-bazi && git stash list"
   ssh root@server "cd /opt/HiFate-bazi && git stash show -p"
   ```

2. **判断是否需要保留**：
   - 如果是必要的配置（如 IP 地址），应该在本地修改并提交到 GitHub
   - 如果是临时修改，应该删除

3. **正确处理**：
   ```bash
   # 如果需要保留，在本地修改并提交
   # 1. 在本地修改相同文件
   # 2. 提交到 GitHub
   git add deploy/nginx/conf.d/hifate.conf
   git commit -m "配置生产环境 Nginx 配置"
   git push origin master
   
   # 3. 服务器上删除 stash
   ssh root@server "cd /opt/HiFate-bazi && git stash drop"
   ```

**禁止的操作**：
- ❌ 本地代码与生产不同
- ❌ 本地热更新配置与生产不同
- ❌ 本地测试通过但生产失败
- ❌ 跳过测试环境直接部署生产
- ❌ **直接在服务器上修改代码（最高优先级禁止）**
- ❌ **跳过 Git 直接部署**
- ❌ **服务器代码与 GitHub 不一致**

**正确的部署流程**：
```
1. 本地开发 → 本地热更新测试通过
2. 提交到 Git → git commit
3. 推送到 GitHub → git push origin master
4. 测试环境自动热更新（或手动触发）
5. 测试环境验证 → 通过后推送到生产分支
6. 生产环境增量部署 → 自动拉取 GitHub 代码
7. 生产环境自动热更新 → 双机同步
8. 验证生产环境功能正常
```

**代码一致性检查清单**：

每次部署前必须检查：
- [ ] 本地代码已提交到 Git
- [ ] 本地代码已推送到 GitHub
- [ ] 服务器代码与 GitHub 一致（`git status` 无本地更改）
- [ ] 三环境代码版本一致（`git log --oneline -1`）
- [ ] 配置文件三环境一致
- [ ] 无服务器本地未提交的更改

**违反一致性原则的处理**：

如果发现服务器上有本地更改：
1. **立即停止部署**
2. **检查更改内容**：`git stash show -p`
3. **判断是否需要保留**：
   - 需要保留 → 在本地修改并提交到 GitHub
   - 不需要保留 → 删除服务器上的更改
4. **确保一致性后继续部署**

**核心要点**：
- 🔴 **最高优先级**：**坚决禁止直接在服务器上修改代码**
- ✅ **唯一正确方式**：本地修改 → GitHub → 服务器拉取
- 🔒 **强制要求**：本地、GitHub、服务器三处代码必须完全一致
- 📋 **必须检查**：每次部署前检查服务器代码与 GitHub 是否一致

