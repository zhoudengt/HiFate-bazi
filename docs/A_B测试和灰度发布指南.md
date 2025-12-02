# A/B 测试和灰度发布指南

## 📋 目录

- [A/B 测试](#ab-测试)
- [功能开关](#功能开关)
- [灰度发布](#灰度发布)
- [数据库回滚](#数据库回滚)
- [使用示例](#使用示例)

---

## A/B 测试

### 概述

A/B 测试框架支持：
- 实验创建和管理
- 流量分配（百分比）
- 变体分配（A/B/C等）
- 事件记录和统计分析

### 创建实验

```python
from server.utils.ab_test import get_ab_test_manager, Experiment, ExperimentStatus

manager = get_ab_test_manager()

experiment = Experiment(
    name="新算法测试",
    description="测试新的八字计算算法",
    status=ExperimentStatus.RUNNING,
    traffic_percent=50.0,  # 50% 流量
    variants={"A": 50, "B": 50}  # A/B 各 50%
)

manager.create_experiment(experiment)
```

### 分配变体

```python
# 为用户分配变体
variant = manager.assign_variant("新算法测试", user_id="user123")
# 返回: "A" 或 "B"
```

### 记录事件

```python
# 记录用户行为事件
manager.record_event(
    experiment_name="新算法测试",
    user_id="user123",
    event_name="click",
    event_data={"button": "submit"}
)
```

### 获取统计

```python
# 获取实验统计
stats = manager.get_experiment_stats("新算法测试")
print(stats)
# {
#   'experiment': '新算法测试',
#   'total_users': 1000,
#   'variant_counts': {'A': 500, 'B': 500},
#   'variant_events': {'A': {'click': 50}, 'B': {'click': 60}},
#   'total_events': 110
# }
```

### API 接口

#### 创建实验

```bash
POST /api/v1/ab-test/experiments
{
  "name": "新算法测试",
  "description": "测试新的八字计算算法",
  "traffic_percent": 50.0,
  "variants": {"A": 50, "B": 50}
}
```

#### 分配变体

```bash
POST /api/v1/ab-test/assign
{
  "experiment_name": "新算法测试",
  "user_id": "user123"
}
```

#### 记录事件

```bash
POST /api/v1/ab-test/events
{
  "experiment_name": "新算法测试",
  "user_id": "user123",
  "event_name": "click",
  "event_data": {"button": "submit"}
}
```

#### 获取统计

```bash
GET /api/v1/ab-test/experiments/{experiment_name}/stats
```

---

## 功能开关

### 概述

功能开关支持：
- 布尔开关（开启/关闭）
- 百分比开关（灰度发布）
- 白名单/黑名单

### 创建功能开关

```python
from server.utils.feature_flag import get_feature_flag_manager, FeatureFlag, FlagType

manager = get_feature_flag_manager()

# 布尔开关
flag = FeatureFlag(
    name="新功能",
    description="新功能开关",
    enabled=True,
    flag_type=FlagType.BOOLEAN
)

# 百分比开关（10% 用户）
flag = FeatureFlag(
    name="新功能灰度",
    description="新功能灰度发布",
    enabled=True,
    flag_type=FlagType.PERCENTAGE,
    value=10.0  # 10%
)

# 白名单
flag = FeatureFlag(
    name="新功能白名单",
    description="新功能白名单",
    enabled=True,
    flag_type=FlagType.WHITELIST,
    value=["user1", "user2", "user3"]
)

manager.create_flag(flag)
```

### 检查功能开关

```python
# 检查功能是否启用
enabled = manager.is_enabled("新功能", user_id="user123")
if enabled:
    # 使用新功能
    pass
```

### API 接口

#### 创建功能开关

```bash
POST /api/v1/feature-flags
{
  "name": "新功能",
  "description": "新功能开关",
  "enabled": true,
  "flag_type": "boolean"
}
```

#### 检查功能开关

```bash
POST /api/v1/feature-flags/check
{
  "flag_name": "新功能",
  "user_id": "user123"
}
```

#### 切换功能开关

```bash
POST /api/v1/feature-flags/{flag_name}/toggle
{
  "enabled": false
}
```

---

## 灰度发布

### 概述

灰度发布流程：
1. 构建新版本容器
2. 启动灰度容器（不同端口）
3. 配置负载均衡器分配流量
4. 监控灰度版本运行情况
5. 逐步增加流量或回滚

### 执行灰度发布

```bash
# 方式 1：使用 deploy.sh
./deploy.sh
# 选择 8) 灰度发布

# 方式 2：直接执行脚本
./scripts/deployment/gray_release.sh
```

### 配置流量分配

灰度发布脚本会：
1. 构建新版本容器
2. 启动灰度容器（端口 8002）
3. 提示配置负载均衡器

**负载均衡器配置示例**（Nginx）：

```nginx
upstream backend {
    # 90% 流量到正式版本
    server localhost:8001 weight=90;
    # 10% 流量到灰度版本
    server localhost:8002 weight=10;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

### 监控和调整

1. **监控灰度版本**：
   - 查看日志：`docker logs hifate-bazi-web-gray`
   - 查看指标：访问监控面板

2. **逐步增加流量**：
   - 如果正常，调整负载均衡器权重
   - 例如：20% → 50% → 100%

3. **回滚**：
   - 如果异常，执行回滚脚本

### 回滚灰度发布

```bash
# 方式 1：使用 deploy.sh
./deploy.sh
# 选择 10) 灰度发布回滚

# 方式 2：直接执行脚本
./scripts/deployment/rollback_gray.sh
```

---

## 数据库回滚

### 概述

数据库回滚用于：
- 回滚失败的数据库迁移
- 恢复数据库到指定版本
- 紧急修复数据问题

### 创建回滚脚本

```bash
# 使用工具创建回滚脚本模板
./scripts/migration/create_rollback.sh
```

### 回滚脚本格式

```sql
-- ============================================
-- 回滚脚本: rollback_20250115_143000_add_user_table.sql
-- 创建时间: 2025-01-15 14:30:00
-- 描述: 回滚添加用户表的操作
-- ============================================

START TRANSACTION;

-- 回滚操作
DROP TABLE IF EXISTS `new_user_table`;
ALTER TABLE `existing_table` DROP COLUMN IF EXISTS `new_column`;

COMMIT;
```

### 执行回滚

```bash
# 方式 1：使用 deploy.sh
./deploy.sh
# 选择 9) 数据库回滚

# 方式 2：直接执行脚本
./scripts/deployment/rollback.sh
```

### 回滚脚本目录

回滚脚本存放在：`scripts/migration/rollback/`

命名规范：`rollback_YYYYMMDD_HHMMSS_description.sql`

---

## 使用示例

### 示例 1：新功能灰度发布

```python
# 1. 创建功能开关（10% 流量）
from server.utils.feature_flag import get_feature_flag_manager, FeatureFlag, FlagType

manager = get_feature_flag_manager()
flag = FeatureFlag(
    name="新算法",
    description="新的八字计算算法",
    enabled=True,
    flag_type=FlagType.PERCENTAGE,
    value=10.0
)
manager.create_flag(flag)

# 2. 在代码中使用
if manager.is_enabled("新算法", user_id=user_id):
    # 使用新算法
    result = new_algorithm.calculate()
else:
    # 使用旧算法
    result = old_algorithm.calculate()
```

### 示例 2：A/B 测试新 UI

```python
# 1. 创建 A/B 测试
from server.utils.ab_test import get_ab_test_manager, Experiment, ExperimentStatus

manager = get_ab_test_manager()
experiment = Experiment(
    name="新UI测试",
    description="测试新的用户界面",
    status=ExperimentStatus.RUNNING,
    traffic_percent=50.0,
    variants={"A": 50, "B": 50}
)
manager.create_experiment(experiment)

# 2. 分配变体
variant = manager.assign_variant("新UI测试", user_id=user_id)

# 3. 根据变体渲染不同 UI
if variant == "A":
    render_old_ui()
elif variant == "B":
    render_new_ui()

# 4. 记录用户行为
manager.record_event("新UI测试", user_id, "click", {"button": "submit"})
```

### 示例 3：完整灰度发布流程

```bash
# 1. 开发新功能
git checkout -b feature/new-algorithm
# ... 开发代码 ...

# 2. 创建功能开关
# 使用 API 或代码创建功能开关

# 3. 执行灰度发布
./deploy.sh
# 选择 8) 灰度发布

# 4. 监控灰度版本
docker logs -f hifate-bazi-web-gray

# 5. 如果正常，逐步增加流量
# 调整负载均衡器配置

# 6. 如果异常，回滚
./deploy.sh
# 选择 10) 灰度发布回滚
```

---

## ⚠️ 注意事项

### A/B 测试

1. **流量分配**：确保变体流量总和为 100%
2. **实验状态**：只有 RUNNING 状态的实验才会分配变体
3. **用户一致性**：同一用户在同一实验中总是分配到相同变体

### 功能开关

1. **百分比开关**：基于用户ID哈希，确保一致性
2. **白名单/黑名单**：需要明确的用户ID列表
3. **紧急开关**：可以快速关闭功能，无需重新部署

### 灰度发布

1. **流量分配**：建议从 10% 开始，逐步增加
2. **监控指标**：关注错误率、响应时间、业务指标
3. **回滚准备**：随时准备回滚，保留回滚脚本

### 数据库回滚

1. **备份数据**：执行回滚前必须备份
2. **测试验证**：先在测试环境验证回滚脚本
3. **不可逆操作**：某些操作（如删除数据）无法完全回滚

---

## 📚 相关文档

- [部署文档](./Docker生产部署完整指南.md)
- [测试指南](./测试和代码检查指南.md)
- [架构改进说明](./架构改进说明.md)

---

**最后更新**：2025-01-XX

