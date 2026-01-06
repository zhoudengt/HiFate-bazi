# 后端 Nginx 端口修改说明

## 修改内容

已将后端 Docker Nginx 的端口从 `80` 改为 `8080`，避免与前端 Nginx 的 80 端口冲突。

## 修改的文件

1. **`deploy/docker/docker-compose.prod.yml`**
   - 端口映射从 `"80:80"` 改为 `"8080:80"`

2. **`docker-compose.nginx.yml`**
   - 端口映射从 `"80:80"` 改为 `"8080:80"`

## 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| **前端 Nginx** | **80, 443** | 对外提供前端页面和静态资源 |
| **后端 Nginx** | **8080, 443** | 负载均衡和 API 代理（仅内部使用或直接访问） |
| Web 服务 | 8001 | FastAPI 主服务 |
| 微服务 | 9001-9010 | 各种微服务 |

## 部署说明

### 重新部署后端 Nginx

修改配置后，需要重启后端 Nginx 容器使新端口生效：

```bash
# 在服务器上执行
cd /opt/HiFate-bazi/deploy/docker

# 停止并删除旧容器
docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml stop nginx
docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml rm -f nginx

# 重新创建并启动容器
docker-compose -f docker-compose.prod.yml -f docker-compose.node1.yml up -d nginx
```

### 验证新端口

```bash
# 检查容器端口映射
docker port hifate-nginx

# 检查 8080 端口是否被占用
sudo ss -tlnp | grep ":8080 "

# 测试后端 Nginx 是否正常工作
curl http://localhost:8080/health
```

## 影响说明

1. **前端访问不受影响**：前端仍然通过 80 端口提供服务
2. **后端 API 访问**：
   - 如果之前直接访问后端 Nginx（端口 80），现在需要改为端口 8080
   - 如果通过前端 Nginx 代理访问，不需要修改（前端 Nginx 代理到 8001 端口）
3. **内部服务通信**：不受影响，容器内部仍然使用 80 端口

## 注意事项

- 确保 8080 端口没有被其他服务占用
- 如果需要通过域名直接访问后端，需要在 DNS 或反向代理中配置 8080 端口
- 443 端口（HTTPS）保持不变，如果配置了 SSL，需要相应调整

## 回滚方法

如果需要回滚到原来的 80 端口：

```bash
# 修改配置文件，将 "8080:80" 改回 "80:80"
# 然后重新部署
```

