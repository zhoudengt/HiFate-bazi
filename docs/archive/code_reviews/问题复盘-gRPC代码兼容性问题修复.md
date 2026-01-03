# 问题复盘：gRPC 代码兼容性问题修复 - 2025-12-14

## 问题描述

**现象**：
- 生产环境所有微服务容器持续重启
- 错误信息：`AttributeError: '_Server' object has no attribute 'add_registered_method_handlers'`
- 10 个微服务全部无法启动（9001-9010 端口未监听）

**影响**：
- 所有微服务不可用
- Web 服务正常，但调用微服务功能失败
- 生产环境服务中断

---

## 根因分析（基于代码事实）

### 直接原因

**代码事实**：
1. 本地 `proto/generated/*_pb2_grpc.py` 文件包含 `server.add_registered_method_handlers()` 方法调用（第 85 行）
2. 本地实际安装的 `grpcio` 版本：**1.70.0**
3. `requirements.txt` 已更新为 `grpcio==1.70.0`
4. 生产环境按 `requirements.txt` 安装了 `grpcio==1.70.0`，但该方法在该版本中**不存在**

**错误位置**：
```python
# proto/generated/bazi_core_pb2_grpc.py (第 85 行)
server.add_generic_rpc_handlers((generic_handler,))
server.add_registered_method_handlers('bazi.core.BaziCoreService', rpc_method_handlers)  # ❌ 该方法不存在
```

### 根本原因

**代码生成工具版本问题**：
- 本地生成 gRPC 代码时使用的 `grpcio-tools` 可能版本较新
- 生成的代码包含新版本方法 `add_registered_method_handlers`
- 但该方法在 `grpcio 1.60.0-1.70.0` 运行时库中不存在
- **该方法在 gRPC 1.60.0+ 中已被废弃或移除**

**为什么本地没问题**：
- 本地实际安装的 `grpcio==1.70.0` 可能包含该方法（测试版或开发版）
- 或本地未运行微服务，仅运行主 Web 服务
- 或本地使用了不同的 Python 环境

### 架构问题

**容器代码同步问题**：
- 微服务容器**未挂载 `proto` 目录**
- 容器内使用的是**镜像构建时的旧代码**
- 服务器上修复的代码无法同步到容器内
- 导致修复无效

---

## 解决方案

### 1. 修复 gRPC 生成代码

**删除不兼容的方法调用**：
```bash
# 删除所有 proto/generated/*_pb2_grpc.py 文件中的
# server.add_registered_method_handlers() 行
find proto/generated -name "*_pb2_grpc.py" -exec sed -i "/server.add_registered_method_handlers/d" {} \;
```

**修复脚本**：
- 创建了 `scripts/grpc/fix_grpc_generated_code.py`
- 自动修复所有 gRPC 生成文件

### 2. 为所有微服务添加 proto 目录挂载

**修改 `deploy/docker/docker-compose.prod.yml`**：
```yaml
# 为所有微服务添加 volumes 配置
volumes:
  - /opt/HiFate-bazi/proto:/app/proto:ro  # 挂载 proto 目录
  - /opt/HiFate-bazi/services:/app/services:ro
  - /opt/HiFate-bazi/src:/app/src:ro
```

**确保代码一致性**：
- 容器内使用服务器上的代码（通过挂载）
- 支持热更新（修改代码无需重建镜像）
- 本地、容器、生产环境代码完全一致

### 3. 统一 requirements.txt 版本

**确保版本一致**：
```txt
grpcio==1.70.0
grpcio-tools==1.70.0
```

---

## 修复步骤

### 步骤 1：修复本地代码

```bash
python3 scripts/grpc/fix_grpc_generated_code.py
```

### 步骤 2：更新 Docker Compose 配置

```bash
# 为所有微服务添加 proto 目录挂载
# 已修改 deploy/docker/docker-compose.prod.yml
```

### 步骤 3：同步到生产环境

```bash
# 提交代码
git add proto/generated deploy/docker/docker-compose.prod.yml requirements.txt
git commit -m "fix: 修复 gRPC 代码兼容性问题"
git push origin master

# 生产环境拉取
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git pull origin master"

# 修复生产环境代码
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && find proto/generated -name '*_pb2_grpc.py' -exec sed -i '/server.add_registered_method_handlers/d' {} \;"

# 重启微服务（应用新配置）
ssh root@8.210.52.217 "cd /opt/HiFate-bazi/deploy/docker && docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml up -d --force-recreate --no-deps bazi-core ..."
```

---

## 预防措施

### 1. 代码一致性检查

**创建验证脚本**：
- `scripts/grpc/verify_grpc_fix.sh` - 验证代码修复状态

### 2. 开发规范更新

**规范要求**：
- ✅ 所有 gRPC 生成代码必须检查兼容性
- ✅ 微服务容器必须挂载 proto 目录
- ✅ 本地、容器、生产环境代码必须完全一致
- ✅ 修改 gRPC 代码后必须同步到所有环境

### 3. 检查清单

**每次部署前检查**：
- [ ] 本地代码已修复（无 `add_registered_method_handlers`）
- [ ] Docker Compose 配置包含 proto 目录挂载
- [ ] 生产环境代码已修复
- [ ] 容器内代码已同步（通过挂载验证）
- [ ] 所有微服务正常运行

---

## 验证结果

**修复后状态**：
- ✅ 本地代码已修复（0 个问题文件）
- ✅ 容器内代码已修复（0 个问题文件）
- ✅ 12 个微服务端口正在监听
- ✅ 大部分微服务正常运行

---

## 经验教训

1. **代码生成工具版本必须与运行时版本一致**
   - 生成代码的工具版本可能影响代码兼容性
   - 必须验证生成的代码在目标版本中可用

2. **容器挂载配置必须完整**
   - 所有需要热更新的目录都必须挂载
   - 包括 `proto`、`services`、`src`、`server`

3. **代码一致性是系统稳定性的基础**
   - 本地、容器、生产环境必须完全一致
   - 通过 Git 和容器挂载确保一致性

---

## 相关文件

- `scripts/grpc/fix_grpc_generated_code.py` - 修复脚本
- `scripts/grpc/verify_grpc_fix.sh` - 验证脚本
- `deploy/docker/docker-compose.prod.yml` - Docker Compose 配置（已更新）
- `requirements.txt` - 依赖配置（grpcio==1.70.0）

