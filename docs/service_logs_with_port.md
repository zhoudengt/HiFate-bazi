# 微服务日志文件名包含端口号

## 修改说明

为了更好地区分不同端口的服务实例，所有微服务的日志文件和PID文件现在都包含端口号。

## 修改内容

### 1. 启动脚本 (`start_all_services.sh`)

**修改前：**
- 日志文件：`logs/bazi_core.log`
- PID文件：`logs/bazi_core.pid`

**修改后：**
- 日志文件：`logs/bazi_core_9001.log`
- PID文件：`logs/bazi_core_9001.pid`

### 2. 停止脚本 (`stop_all_services.sh`)

同样更新为使用带端口号的文件名。

## 服务端口和日志文件对应关系

| 服务名称 | 端口 | 日志文件 | PID文件 |
|---------|------|---------|---------|
| bazi_core | 9001 | `logs/bazi_core_9001.log` | `logs/bazi_core_9001.pid` |
| bazi_fortune | 9002 | `logs/bazi_fortune_9002.log` | `logs/bazi_fortune_9002.pid` |
| bazi_analyzer | 9003 | `logs/bazi_analyzer_9003.log` | `logs/bazi_analyzer_9003.pid` |
| bazi_rule | 9004 | `logs/bazi_rule_9004.log` | `logs/bazi_rule_9004.pid` |
| web_app | 8001 | `logs/web_app_8001.log` | `logs/web_app_8001.pid` |

## 优势

1. **易于识别**：从文件名就能看出服务运行的端口
2. **支持多实例**：如果将来需要运行多个相同服务的实例（不同端口），日志文件不会冲突
3. **便于管理**：在查看日志时，可以快速定位到对应的服务端口

## 注意事项

- 旧的日志文件（不带端口号）需要手动清理或重命名
- 如果服务已经在运行，需要先停止服务，然后使用新的脚本重新启动
- 确保 `.gitignore` 中包含新的日志文件模式（如果适用）

## 使用示例

```bash
# 启动所有服务
./start_all_services.sh

# 停止所有服务
./stop_all_services.sh
```

启动后，日志文件将自动创建在 `logs/` 目录下，文件名包含端口号。

