# 热更新系统使用文档

## 📋 概述

热更新系统支持所有模块的自动更新，**无需重启服务**即可生效。系统采用模块化设计，每个模块独立管理，互不干扰。

## 🏗️ 架构设计

```
server/hot_reload/
├── __init__.py
├── version_manager.py      # 版本号管理模块
├── hot_reload_manager.py   # 热更新管理器（统一管理）
├── reloaders.py            # 各种重载器（规则/内容/配置/缓存）
└── api.py                  # 热更新API接口
```

## 🔧 模块说明

### 1. VersionManager（版本号管理器）

**功能**：
- 统一管理所有模块的版本号
- 检测版本号变化
- 支持自定义版本号检查器

**使用方法**：
```python
from server.hot_reload.version_manager import VersionManager

# 检查版本号是否变化
if VersionManager.check_version_changed('rules'):
    print("规则已更新，需要重新加载")

# 获取当前版本号
version = VersionManager.get_version('rules')
```

### 2. HotReloadManager（热更新管理器）

**功能**：
- 统一管理所有模块的热更新
- 定时检查版本号变化
- 自动触发重载
- 支持手动触发

**使用方法**：
```python
from server.hot_reload.hot_reload_manager import HotReloadManager

# 获取管理器实例
manager = HotReloadManager.get_instance(interval=300)  # 5分钟检查一次

# 启动热更新
manager.start()

# 手动触发检查
manager.check_and_reload()

# 重载指定模块
manager.check_and_reload('rules')

# 停止热更新
manager.stop()
```

### 3. Reloaders（重载器）

**支持的模块**：
- `rules` - 规则重载器（RuleReloader）
- `content` - 内容重载器（ContentReloader）
- `config` - 配置重载器（ConfigReloader）
- `cache` - 缓存重载器（CacheReloader）
- `source` - **源代码重载器（SourceCodeReloader）** - 支持Python源代码热更新

**扩展新重载器**：
```python
# 在 reloaders.py 中添加
class CustomReloader:
    @staticmethod
    def reload() -> bool:
        # 重载逻辑
        return True

# 注册重载器
RELOADERS['custom'] = CustomReloader
```

## 📡 API 接口

### 1. 获取热更新状态

**接口**: `GET /api/v1/hot-reload/status`

**响应示例**:
```json
{
  "success": true,
  "status": {
    "running": true,
    "interval": 300,
    "versions": {
      "rules": {
        "current": 1,
        "cached": 1,
        "changed": false
      },
      "content": {
        "current": 121,
        "cached": 121,
        "changed": false
      }
    }
  }
}
```

### 2. 手动触发热更新检查

**接口**: `POST /api/v1/hot-reload/check`

**请求参数**（可选）:
```json
{
  "module_name": "rules"  // 可选，不指定则检查所有模块
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "热更新检查完成",
  "reloaded_modules": ["rules"]
}
```

### 3. 获取所有模块版本号

**接口**: `GET /api/v1/hot-reload/versions`

**响应示例**:
```json
{
  "success": true,
  "versions": {
    "rules": {
      "current": 1,
      "cached": 1,
      "changed": false
    },
    "content": {
      "current": 121,
      "cached": 121,
      "changed": false
    }
  }
}
```

### 4. 手动重载指定模块

**接口**: `POST /api/v1/hot-reload/reload/{module_name}`

**路径参数**:
- `module_name`: 模块名称（rules/content/config/cache）

**响应示例**:
```json
{
  "success": true,
  "message": "模块 rules 重载成功",
  "reloaded_modules": ["rules"]
}
```

## 🔄 工作流程

### 自动热更新流程

```
1. 服务启动
   ↓
2. HotReloadManager 启动
   ↓
3. 初始化版本号（所有模块）
   ↓
4. 定时检查（每5分钟）
   ↓
5. 检测到版本号变化？
   ├─ 是 → 调用对应重载器 → 更新缓存版本号
   └─ 否 → 继续等待
```

### 手动触发流程

```
1. 调用 API 接口
   ↓
2. 检查版本号
   ↓
3. 如果有变化 → 重载
   ↓
4. 返回结果
```

## 📝 使用示例

### 更新规则

```bash
# 1. 在数据库中更新规则
# 规则版本号会自动增加

# 2. 等待自动热更新（最多5分钟）
# 或手动触发
curl -X POST http://127.0.0.1:8001/api/v1/hot-reload/reload/rules
```

### 更新内容

```bash
# 1. 通过管理接口更新内容
curl -X POST http://127.0.0.1:8001/api/v1/admin/rule-contents/rizhu-gender \
  -H "Content-Type: application/json" \
  -d '{
    "rizhu": "甲子",
    "gender": "male",
    "descriptions": ["新描述1", "新描述2"]
  }'

# 2. 内容版本号会自动增加
# 3. 等待自动热更新（最多5分钟）
# 或手动触发
curl -X POST http://127.0.0.1:8001/api/v1/hot-reload/reload/content
```

### 源代码热更新示例

源代码热更新基于文件修改时间自动检测，修改Python源代码文件后会自动重载：

```bash
# 1. 修改源代码文件（如 src/analyzers/bazi_interface_analyzer.py）

# 2. 系统会自动检测文件修改时间变化（最多5分钟）
# 或手动触发源代码热更新
curl -X POST http://127.0.0.1:8001/api/v1/hot-reload/reload/source

# 控制台会打印详细信息：
# ============================================================
# 🔄 源代码热更新开始 - 2024-01-01 12:00:00
# ============================================================
# 
#   📦 模块: src.analyzers.bazi_interface_analyzer
#      📄 文件: src/analyzers/bazi_interface_analyzer.py
#      📝 功能: 八字界面信息分析器 - 计算命宫、身宫、纳音等
#      🕒 修改时间: 2024-01-01 11:59:30
#      ✅ 重载成功
# 
# ------------------------------------------------------------
# ✅ 源代码热更新完成 - 成功重载 1 个模块:
#    • src.analyzers.bazi_interface_analyzer
#      文件: src/analyzers/bazi_interface_analyzer.py
#      功能: 八字界面信息分析器 - 计算命宫、身宫、纳音等
#      修改时间: 2024-01-01 11:59:30
# ============================================================
```

**监控的源代码模块**：
- `src.analyzers.bazi_interface_analyzer` - 八字界面信息分析器
- `src.bazi_interface_generator` - 八字界面信息生成器
- `src.analyzers.rizhu_gender_analyzer` - 日柱性别分析器
- `src.analyzers.deities_analyzer` - 神煞分析器
- `src.tool.BaziCalculator` - 八字计算器
- `src.ai.bazi_ai_analyzer` - 八字AI分析器

可以在 `server/hot_reload/reloaders.py` 的 `SourceCodeReloader.MONITORED_MODULES` 中添加更多模块。

### 检查热更新状态

```bash
# 查看所有模块版本号
curl http://127.0.0.1:8001/api/v1/hot-reload/versions

# 查看热更新管理器状态
curl http://127.0.0.1:8001/api/v1/hot-reload/status
```

## ✅ 优势

1. **无需重启**：所有更新都自动生效，无需重启服务
2. **模块化**：每个模块独立管理，互不干扰
3. **统一管理**：一个管理器管理所有模块
4. **灵活扩展**：可以轻松添加新的模块和重载器
5. **API支持**：提供完整的API接口，方便管理
6. **自动+手动**：支持自动检查和手动触发

## 🔍 支持的模块

| 模块名称 | 重载器 | 版本号来源 | 说明 |
|---------|--------|-----------|------|
| `rules` | RuleReloader | `rule_version` 表 | 规则配置 |
| `content` | ContentReloader | `rule_version` 表 | 规则内容 |
| `config` | ConfigReloader | 可扩展 | 系统配置 |
| `cache` | CacheReloader | 可扩展 | 缓存数据 |
| `source` | SourceCodeReloader | 文件修改时间 | **Python源代码** |

## 🎯 配置

### 检查间隔

默认检查间隔为 **5分钟（300秒）**，可以在启动时配置：

```python
manager = HotReloadManager.get_instance(interval=60)  # 1分钟检查一次
manager.start()
```

### 添加新模块

1. **创建重载器**（在 `reloaders.py` 中）：
```python
class MyModuleReloader:
    @staticmethod
    def reload() -> bool:
        # 重载逻辑
        return True

RELOADERS['my_module'] = MyModuleReloader
```

2. **注册版本号检查器**（在 `version_manager.py` 中）：
```python
def get_my_module_version() -> int:
    # 从数据库或文件获取版本号
    return 1

VersionManager.register_version_checker('my_module', get_my_module_version)
```

## 📚 相关文档

- **规则引擎使用**: `RULES_ENGINE_USAGE.md`
- **数据库存储方案**: `DATABASE_RULE_STORAGE_SOLUTION.md`

---

**文档版本**: 1.0  
**创建时间**: 2025-11-05



