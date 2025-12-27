# 撤回前端代理配置 - 快速参考

## ✅ 本地配置已撤回

本地配置文件 `frontend-config/nginx.conf` 已移除以下配置：
- `/nacos` -> `localhost:9060`
- `/destiny/api/grpc-web/` -> `localhost:9070`

## 🚀 在双机上撤回（3步）

### Node1 和 Node2 都执行：

```bash
# 1. SSH 连接到服务器
ssh root@8.210.52.217  # Node1
# 或
ssh root@47.243.160.43  # Node2

# 2. 拉取最新代码并重启服务
cd /opt/HiFate-bazi
git pull origin master
docker-compose -f docker-compose.frontend.yml restart nginx-frontend

# 3. 验证配置
docker exec hifate-frontend-nginx nginx -t
```

## ✅ 验证撤回

```bash
# 检查配置文件（应该没有输出）
grep "/nacos\|/destiny/api/grpc-web" /opt/HiFate-bazi/frontend-config/nginx.conf

# 测试代理（应该返回 404）
curl http://localhost/nacos/
curl http://localhost/destiny/api/grpc-web/frontend.gateway.FrontendGateway/Call
```

## 📚 详细文档

完整撤回指南：`docs/rollback_frontend_proxy_guide.md`

