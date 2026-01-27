# HiFate-bazi 后端压力测试工具

基于 Locust 的压力测试框架，用于测试 HiFate-bazi 后端 API 的性能和并发能力。

## 📋 目录结构

```
stress_test/
├── README.md                 # 本文档
├── requirements.txt          # Python 依赖包
├── config.py                 # 配置管理（支持多环境）
├── locustfile.py             # Locust 主入口文件
├── run_test.py               # 快捷运行脚本
├── tasks/                    # 测试任务模块
│   ├── __init__.py
│   ├── bazi_tasks.py         # 八字计算测试任务
│   ├── fortune_tasks.py     # 运势分析测试任务
│   └── health_tasks.py       # 健康检查测试任务
├── utils/                    # 工具模块
│   ├── __init__.py
│   ├── data_generator.py     # 测试数据生成器
│   └── report_helper.py      # 报告辅助工具
└── reports/                  # 测试报告输出目录
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd stress_test
pip install -r requirements.txt
```

### 2. 运行测试

#### 方式1：使用快捷脚本（推荐）

```bash
# 使用默认配置（本地环境）
python run_test.py

# 指定目标服务器
python run_test.py --host http://your-server:8001

# 指定环境配置
python run_test.py --env production --host http://production-server:8001

# 自定义并发参数
python run_test.py --users 30 --spawn-rate 5 --run-time 5m
```

#### 方式2：直接使用 Locust

```bash
# Web UI 模式（推荐，可视化监控）
locust -f locustfile.py --host=http://your-server:8001

# 命令行模式（无UI，适合自动化）
locust -f locustfile.py --host=http://your-server:8001 \
    --users 30 --spawn-rate 5 --run-time 5m --headless
```

## 📊 测试接口

| 接口 | 路径 | 类型 | 权重 | 说明 |
|------|------|------|------|------|
| 八字计算 | `/api/v1/bazi/calculate` | POST | 40% | 核心业务接口 |
| 八字界面数据 | `/api/v1/bazi/interface` | POST | 30% | 核心业务接口 |
| 每日运势查询 | `/api/v1/daily-fortune-calendar/query` | POST | 20% | 常用接口 |
| 健康检查 | `/health` | GET | 10% | 系统监控 |

## ⚙️ 配置说明

### 环境配置

支持以下环境配置（在 `config.py` 中定义）：

- **default**: 默认配置（30用户，5分钟）
- **local**: 本地开发环境（15用户，3分钟）
- **staging**: 测试/预发布环境（30用户，5分钟）
- **production**: 生产环境（30用户，5分钟）
- **high_load**: 高并发测试（50用户，10分钟）

### 配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `host` | 目标服务器地址 | `http://localhost:8001` |
| `users` | 并发用户数 | `30` |
| `spawn_rate` | 每秒启动用户数 | `5` |
| `run_time` | 测试持续时间 | `5m` |
| `wait_time_min` | 最小请求间隔(秒) | `1` |
| `wait_time_max` | 最大请求间隔(秒) | `3` |

### 环境变量

可以通过环境变量覆盖配置：

```bash
export STRESS_TEST_HOST=http://your-server:8001
export STRESS_TEST_USERS=50
export STRESS_TEST_SPAWN_RATE=10
export STRESS_TEST_RUN_TIME=10m
```

## 📈 性能指标

测试会收集以下性能指标：

- **QPS**（每秒请求数）
- **响应时间分布**（P50/P95/P99）
- **错误率统计**
- **并发用户数追踪**

### 性能阈值

默认性能阈值（可在 `config.py` 中调整）：

- P50 响应时间 < 1秒
- P95 响应时间 < 2秒
- P99 响应时间 < 5秒
- 错误率 < 1%
- 最小 QPS > 10

## 📝 使用示例

### 示例1：本地环境测试

```bash
# 测试本地开发服务器
python run_test.py --env local
```

### 示例2：生产环境测试（谨慎使用）

```bash
# 测试生产服务器（30用户并发，5分钟）
python run_test.py --env production --host http://production-server:8001
```

### 示例3：高并发测试

```bash
# 50用户并发，持续10分钟
python run_test.py --env high_load --host http://test-server:8001
```

### 示例4：生成报告

```bash
# 生成 HTML 报告
python run_test.py --headless --html-report reports/report.html

# 生成 CSV 报告
python run_test.py --headless --csv-report reports/stats
```

## 🔍 Web UI 使用

启动 Web UI 模式后，访问 `http://localhost:8089` 可以看到：

1. **实时统计**：请求数、响应时间、错误率等
2. **图表展示**：响应时间分布、QPS 趋势等
3. **手动控制**：可以动态调整并发用户数
4. **导出报告**：可以导出 HTML/CSV 格式报告

## ⚠️ 注意事项

### 限流配置

- 当前限流配置：**60次/分钟/IP**
- 如果从单个 IP 发起压测，建议：
  - 设置合理的请求间隔（默认 1-3 秒）
  - 或临时提高限流阈值

### 服务器资源

- 确保目标服务器有足够的资源（CPU、内存、数据库连接池）
- 建议在非生产时间进行压测
- 监控服务器资源使用情况

### 数据库连接

- 生产环境 MySQL 连接池：最大 50 连接
- 30 用户并发通常足够，但需注意连接池是否耗尽

## 🐛 故障排查

### 问题1：连接被拒绝

```
Error: Connection refused
```

**解决方案**：
- 检查目标服务器地址是否正确
- 确认服务器是否正在运行
- 检查防火墙设置

### 问题2：触发限流（429错误）

```
HTTP错误: 429
```

**解决方案**：
- 增加请求间隔时间
- 提高限流阈值（修改 `server/api/v1/bazi_rules.py`）
- 使用多个 IP 地址发起压测

### 问题3：响应时间过长

**解决方案**：
- 检查服务器资源使用情况
- 检查数据库连接池状态
- 查看服务器日志，定位性能瓶颈

## 📚 相关文档

- [Locust 官方文档](https://docs.locust.io/)
- [项目开发规范](../docs/standards/)
- [API 文档](../docs/api/)

## 📄 许可证

与主项目保持一致。
