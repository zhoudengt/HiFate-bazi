# Docker Compose buildx 版本问题 - 快速参考

## 问题
```
compose build requires buildx 0.17 or later
```

## 快速修复（3步）

### 1. 运行自动修复脚本
```bash
cd /opt/HiFate-bazi
bash scripts/fix_buildx_version.sh
```

### 2. 如果脚本无法自动升级，手动升级
```bash
# Alibaba Cloud Linux 3
sudo yum update -y docker-buildx-plugin

# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y docker-buildx-plugin
```

### 3. 验证修复
```bash
docker buildx version  # 应该显示 v0.17.0 或更高
docker-compose up -d frontend-gateway  # 再次尝试
```

## 关于 frontend-gateway

**重要**：`frontend-gateway` 是 **gRPC 服务**，不是 Docker Compose 服务。

- gRPC 服务定义：`proto/frontend_gateway.proto`
- 访问路径：`/api/grpc-web/frontend.gateway.FrontendGateway/Call`

如果确实需要 Docker Compose 服务，请先创建配置文件。

## 详细文档

完整修复指南：`docs/fix_buildx_version_guide.md`

