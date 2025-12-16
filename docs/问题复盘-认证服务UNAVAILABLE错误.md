# 问题复盘：认证服务 UNAVAILABLE 错误 - 2025-01-16

## 问题描述

- **现象**：前端调用 API 时频繁出现 `StatusCode.UNAVAILABLE` 错误
- **错误信息**：`认证服务错误: StatusCode.UNAVAILABLE`
- **影响**：所有需要认证的 API 调用失败，用户无法正常使用系统
- **复现**：任何需要 Token 验证的请求都会失败

## 根因分析

### 直接原因

1. **认证服务未启动**（最严重）：
   - 认证服务没有包含在 `start.sh` 启动脚本中
   - 服务根本没有启动，导致所有认证请求失败
   - 这是导致 `StatusCode.UNAVAILABLE` 错误的**主要原因**

2. **认证服务监听地址配置错误**：
   - 认证服务使用 `localhost:9011` 监听
   - 在 Docker 容器中，`localhost` 只监听容器内部接口
   - 其他容器（如 Web 服务）无法连接到认证服务

3. **gRPC 客户端连接失败**：
   - Web 服务容器尝试连接 `auth-service:9011`
   - 但认证服务未启动或只监听 `localhost:9011`
   - 导致连接被拒绝，返回 `StatusCode.UNAVAILABLE`

### 根本原因

1. **服务启动脚本不完整**（最严重）：
   - 认证服务没有添加到 `start.sh` 和 `stop.sh` 脚本中
   - 导致服务根本没有启动，所有认证请求都失败
   - 这是**最根本的问题**，需要立即修复

2. **监听地址配置不规范**：
   - 认证服务显式传入 `listen_addr = f"localhost:{port}"`
   - 覆盖了 `create_hot_reload_server` 的默认值 `[::]:port`
   - 在 Docker 容器环境中，应该监听 `0.0.0.0` 或 `[::]` 才能被其他容器访问

3. **缺少微服务监听地址配置规范**：
   - 没有统一的监听地址配置规范
   - 部分微服务使用 `localhost`，部分使用 `[::]`
   - 导致容器间通信问题

4. **开发规范不完整**：
   - 开发规范中缺少微服务监听地址配置要求
   - 没有明确说明 Docker 容器环境下的监听地址要求
   - 没有要求所有微服务必须添加到启动/停止脚本中

### 规范违反

- ❌ **违反了服务启动规范**（所有微服务必须添加到启动/停止脚本中）
- ❌ 违反了 Docker 容器网络规范（服务应该监听 `0.0.0.0` 或 `[::]`）
- ❌ 违反了微服务配置规范（监听地址配置不统一）
- ❌ 违反了开发规范完整性要求（缺少监听地址配置规范）

## 解决方案

### 1. 修复认证服务监听地址

**修改文件**：`services/auth_service/grpc_server.py`

**修改内容**：
```python
# 修改前（错误）
listen_addr = f"localhost:{port}"

# 修改后（正确）
listen_addr = f"[::]:{port}"  # 支持 IPv4 和 IPv6
```

**修改位置**：
- 热更新模式：第 454 行
- 普通模式：第 474 行

### 2. 添加认证服务到启动/停止脚本

**问题**：认证服务没有包含在 `start.sh` 和 `stop.sh` 脚本中，导致服务根本没有启动！

**修改文件**：
- `scripts/services/start_all_services.sh`
- `scripts/services/stop_all_services.sh`

**修改内容**：

**启动脚本**（`start_all_services.sh`）：
```bash
# 添加环境变量
export AUTH_SERVICE_URL="${AUTH_SERVICE_URL:-127.0.0.1:9011}"

# 添加服务启动
start_grpc_service "auth_service" "services/auth_service/main.py" 9011
```

**停止脚本**（`stop_all_services.sh`）：
```bash
# 添加服务停止
stop_service "auth_service" 9011

# 添加进程查找逻辑
elif [[ "${name}" == "auth_service" ]]; then
  pid="$(find_pid_by_name "services/auth_service/main.py")"
```

### 2. 验证修复效果

**检查服务监听地址**：
```bash
# 检查容器内服务监听地址
docker exec hifate-auth-service netstat -tlnp | grep 9011

# 应该显示：
# tcp6       0      0 :::9011                 :::*                    LISTEN
```

**测试服务连接**：
```bash
# 从 Web 服务容器测试连接
docker exec hifate-web python -c "
import grpc
import sys
sys.path.insert(0, '/app/proto/generated')
import auth_pb2, auth_pb2_grpc
channel = grpc.insecure_channel('auth-service:9011')
stub = auth_pb2_grpc.AuthServiceStub(channel)
response = stub.HealthCheck(auth_pb2.HealthCheckRequest(), timeout=5.0)
print('✅ 连接成功:', response.status)
"
```

### 3. 更新开发规范

在 `.cursorrules` 中添加"微服务监听地址配置规范"章节。

## 预防措施

### 1. 规范更新

**添加微服务监听地址配置规范**：

1. **Docker 容器环境**：
   - ✅ 必须使用 `0.0.0.0` 或 `[::]` 监听所有接口
   - ❌ 禁止使用 `localhost` 或 `127.0.0.1`

2. **本地开发环境**：
   - ✅ 可以使用 `localhost` 或 `0.0.0.0`
   - ⚠️ 建议统一使用 `[::]` 保持一致性

3. **配置方式**：
   - ✅ 使用环境变量 `SERVICE_HOST` 控制监听地址
   - ✅ 默认值：`[::]`（支持 IPv4 和 IPv6）

### 2. 检查清单

每次开发新微服务时，必须检查：

- [ ] 监听地址是否使用 `[::]` 或 `0.0.0.0`（Docker 环境）
- [ ] 是否支持通过环境变量配置监听地址
- [ ] 是否在 Docker Compose 中正确配置服务地址
- [ ] 是否测试了容器间连接

### 3. 代码审查

**审查要点**：
- 检查所有微服务的监听地址配置
- 确保 Docker 容器环境使用正确的监听地址
- 验证容器间连接测试

### 4. 自动化检查

**添加启动检查**：
```python
# 在服务启动时检查监听地址
if listen_addr.startswith("localhost") or listen_addr.startswith("127.0.0.1"):
    import os
    if os.getenv("APP_ENV") == "production":
        raise ValueError(f"生产环境禁止使用 localhost 监听地址: {listen_addr}")
```

## 相关文件

- `services/auth_service/grpc_server.py` - 认证服务 gRPC 服务器
- `services/auth_service/config.py` - 认证服务配置
- `deploy/docker/docker-compose.prod.yml` - Docker Compose 配置
- `server/hot_reload/microservice_reloader.py` - 热更新服务器创建函数

## 总结

**问题根源**：认证服务使用 `localhost` 监听，导致 Docker 容器间无法通信。

**解决方案**：修改监听地址为 `[::]`，支持 IPv4 和 IPv6，确保容器间可以连接。

**预防措施**：
1. 更新开发规范，明确监听地址配置要求
2. 添加检查清单，确保新服务配置正确
3. 添加自动化检查，防止类似问题再次发生

**核心要点**：
- 🔴 **Docker 容器环境必须使用 `[::]` 或 `0.0.0.0` 监听**
- ✅ **禁止使用 `localhost` 在容器环境中监听**
- 📋 **所有新微服务必须遵守监听地址配置规范**

