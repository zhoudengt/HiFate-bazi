# Nacos 代理配置部署指南

## 概述

本文档说明如何在生产环境部署 Nacos 代理配置，使 `http://8.210.52.217/nacos/index.html` 能够正常访问。

## 配置说明

已在 `deploy/nginx/conf.d/hifate.conf` 中添加了 `/nacos` location 配置：
- 代理到宿主机上的 Nacos 服务（`172.17.0.1:9060`）
- 支持 WebSocket（Nacos 实时更新需要）
- 配置位置在 `location /` 之前，避免被静态文件匹配

## 部署步骤

### 方式 1：使用部署脚本（推荐）

```bash
# 1. 确保代码已提交并推送到 GitHub
git add deploy/nginx/conf.d/hifate.conf
git commit -m "feat: 添加 Nacos 代理配置"
git push origin master

# 2. 在服务器上拉取最新代码
ssh root@8.210.52.217 "cd /opt/HiFate-bazi && git pull origin master"
ssh root@47.243.160.43 "cd /opt/HiFate-bazi && git pull origin master"

# 3. 运行部署脚本
bash scripts/deploy_nacos_proxy.sh
```

### 方式 2：手动部署

#### Node1 (8.210.52.217)

```bash
# 1. SSH 登录
ssh root@8.210.52.217

# 2. 进入项目目录
cd /opt/HiFate-bazi

# 3. 拉取最新代码
git pull origin master

# 4. 验证 Nginx 配置语法
docker exec hifate-nginx nginx -t

# 5. 重启 Nginx 容器
docker restart hifate-nginx

# 6. 测试访问
curl -v http://localhost/nacos/index.html
```

#### Node2 (47.243.160.43)

```bash
# 重复上述步骤
ssh root@47.243.160.43
cd /opt/HiFate-bazi
git pull origin master
docker exec hifate-nginx nginx -t
docker restart hifate-nginx
curl -v http://localhost/nacos/index.html
```

## 验证步骤

### 1. 检查配置语法

```bash
docker exec hifate-nginx nginx -t
```

**预期输出**：
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 2. 检查 Nacos 服务状态

```bash
# 检查 Nacos 是否在宿主机上运行
netstat -tlnp | grep 9060

# 或使用 ss 命令
ss -tlnp | grep 9060
```

**预期输出**：应该显示 Nacos 服务监听在 9060 端口

### 3. 测试访问

#### 从服务器内部测试

```bash
curl -v http://localhost/nacos/index.html
```

**预期结果**：
- HTTP 200：成功访问 Nacos 界面
- HTTP 302/301：重定向到登录页面（正常）
- HTTP 404：配置未生效或 Nacos 服务未运行

#### 从外部测试

```bash
# 测试 Node1
curl -v http://8.210.52.217/nacos/index.html

# 测试 Node2
curl -v http://47.243.160.43/nacos/index.html
```

#### 浏览器测试

1. 打开浏览器访问：`http://8.210.52.217/nacos/index.html`
2. 应该显示 Nacos 配置中心界面，而不是 404 错误

## 故障排查

### 问题 1：仍然返回 404

**可能原因**：
- 配置未部署到服务器
- Nginx 容器未重启
- 配置语法错误

**解决方案**：
```bash
# 1. 检查配置是否已部署
ssh root@8.210.52.217 "grep -n 'location /nacos' /opt/HiFate-bazi/deploy/nginx/conf.d/hifate.conf"

# 2. 检查 Nginx 配置语法
docker exec hifate-nginx nginx -t

# 3. 重启 Nginx 容器
docker restart hifate-nginx

# 4. 检查 Nginx 日志
docker logs hifate-nginx --tail 50
```

### 问题 2：连接被拒绝 (Connection refused)

**可能原因**：
- Nacos 服务未运行
- Docker 网络配置问题（`172.17.0.1` 不正确）

**解决方案**：
```bash
# 1. 检查 Nacos 服务状态
netstat -tlnp | grep 9060

# 2. 检查 Docker 网络网关
ip route | grep default

# 3. 如果 172.17.0.1 不可用，修改配置为：
#    - host.docker.internal:9060（Docker 20.10+）
#    - 或使用宿主机实际 IP（需要确认）
```

### 问题 3：WebSocket 连接失败

**可能原因**：
- 缺少 WebSocket 升级头配置

**解决方案**：
确保配置中包含：
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### 问题 4：配置语法错误

**错误信息**：
```
nginx: [emerg] unexpected "}" in /etc/nginx/conf.d/hifate.conf
```

**解决方案**：
```bash
# 1. 检查配置文件语法
docker exec hifate-nginx nginx -t

# 2. 查看详细错误信息
docker exec hifate-nginx nginx -T | grep -A 5 -B 5 error

# 3. 修复配置后重新部署
```

## 配置内容

已添加的配置（`deploy/nginx/conf.d/hifate.conf`）：

```nginx
# Nacos 配置中心代理（必须在 / 之前，避免被静态文件匹配）
location /nacos {
    proxy_pass http://172.17.0.1:9060;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket 支持（Nacos 需要）
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # 超时设置
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    
    # 禁用缓冲（实时更新）
    proxy_buffering off;
}
```

## 注意事项

1. **配置位置**：`/nacos` location 必须在 `location /` 之前，否则会被静态文件匹配规则拦截
2. **Docker 网络**：使用 `172.17.0.1` 作为 Docker 默认网关访问宿主机服务
3. **WebSocket 支持**：Nacos 需要 WebSocket 支持实时配置更新
4. **双机部署**：需要在 Node1 和 Node2 上都部署配置

## 相关文件

- `deploy/nginx/conf.d/hifate.conf` - Nginx 配置文件
- `scripts/deploy_nacos_proxy.sh` - 部署脚本
- `frontend-config/nginx.conf` - 前端 Nginx 配置（参考）

