# Nginx HTTPS 和 www 域名重定向配置指南

> 本文档说明如何在生产服务器上配置 Nginx，实现 HTTP 到 HTTPS 以及非 www 到 www 的统一重定向。

## 1. 目标

实现以下重定向规则：

| 用户访问 | 重定向到 |
|---------|---------|
| `http://yuanqistation.com/*` | `https://www.yuanqistation.com/*` |
| `http://www.yuanqistation.com/*` | `https://www.yuanqistation.com/*` |
| `https://yuanqistation.com/*` | `https://www.yuanqistation.com/*` |

## 2. 当前架构

```
用户浏览器
    ↓
frontend-nginx 容器 (Docker)
├── 443 端口 (HTTPS) → /etc/nginx/conf.d/443.conf
└── 80 端口 (HTTP，映射到宿主机 9065) → /etc/nginx/conf.d/9065.conf
```

### 配置文件位置

| 宿主机路径 | 容器内路径 | 说明 |
|-----------|-----------|------|
| `/opt/hifate-frontend/nginx/conf.d/443.conf` | `/etc/nginx/conf.d/443.conf` | HTTPS 配置 |
| `/opt/hifate-frontend/nginx/conf.d/9065.conf` | `/etc/nginx/conf.d/9065.conf` | HTTP 配置 |
| `/opt/hifate-frontend/nginx/ssl/` | `/etc/nginx/ssl/` | SSL 证书目录 |

### 当前配置问题

1. **443.conf**：`server_name` 包含两个域名，但没有非 www → www 的重定向
2. **9065.conf**：`server_name localhost`，没有监听 `yuanqistation.com` 域名

## 3. 修改方案

### 方案概述

1. **新建 `redirect.conf`**：处理 HTTP 80 端口的域名重定向
2. **修改 `443.conf`**：添加非 www HTTPS 重定向的 server block

### 3.1 创建 redirect.conf（HTTP 重定向）

在 `/opt/hifate-frontend/nginx/conf.d/` 目录下新建文件 `redirect.conf`：

```nginx
# ============================================
# HTTP 重定向到 HTTPS
# 文件：/opt/hifate-frontend/nginx/conf.d/redirect.conf
# ============================================

server {
    listen 80;
    server_name yuanqistation.com www.yuanqistation.com;
    
    # 所有 HTTP 请求 301 永久重定向到 https://www.yuanqistation.com
    return 301 https://www.yuanqistation.com$request_uri;
}
```

### 3.2 修改 443.conf（HTTPS 重定向 + 主服务）

修改 `/opt/hifate-frontend/nginx/conf.d/443.conf`，在文件**开头**添加非 www 重定向的 server block，并修改原有 server block 的 `server_name`：

```nginx
# ============================================
# HTTPS 非 www 重定向到 www
# ============================================
server {
    listen 443 ssl;
    server_name yuanqistation.com;  # 只匹配非 www
    
    ssl_certificate /etc/nginx/ssl/yuanqistation.com.pem;
    ssl_certificate_key /etc/nginx/ssl/yuanqistation.com.key;
    
    ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # 重定向到 www 版本
    return 301 https://www.yuanqistation.com$request_uri;
}

# ============================================
# 主 HTTPS 服务（原有配置）
# ============================================
server {
    listen 443 ssl;
    server_name www.yuanqistation.com;  # 【修改】只保留 www 版本，删除 yuanqistation.com
    
    ssl_certificate /etc/nginx/ssl/yuanqistation.com.pem;
    ssl_certificate_key /etc/nginx/ssl/yuanqistation.com.key;
    
    # ... 以下保持原有配置不变 ...
```

### 3.3 完整的 443.conf 修改对比

**修改前（第 3 行）**：
```nginx
server_name  127.0.0.1 localhost yuanqistation.com www.yuanqistation.com;
```

**修改后**：
```nginx
server_name  127.0.0.1 localhost www.yuanqistation.com;
```

## 4. 操作步骤

### 步骤 1：SSH 连接到服务器

```bash
ssh root@8.210.52.217
```

### 步骤 2：备份当前配置

```bash
cd /opt/hifate-frontend/nginx/conf.d/
cp 443.conf 443.conf.bak.$(date +%Y%m%d%H%M%S)
```

### 步骤 3：创建 HTTP 重定向配置

```bash
cat > /opt/hifate-frontend/nginx/conf.d/redirect.conf << 'EOF'
# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name yuanqistation.com www.yuanqistation.com;
    
    return 301 https://www.yuanqistation.com$request_uri;
}
EOF
```

### 步骤 4：修改 443.conf

使用 `vim` 或 `nano` 编辑 443.conf：

```bash
vim /opt/hifate-frontend/nginx/conf.d/443.conf
```

在文件**开头**（第 1 行之前）添加：

```nginx
# HTTPS 非 www 重定向
server {
    listen 443 ssl;
    server_name yuanqistation.com;
    
    ssl_certificate /etc/nginx/ssl/yuanqistation.com.pem;
    ssl_certificate_key /etc/nginx/ssl/yuanqistation.com.key;
    
    ssl_protocols TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    return 301 https://www.yuanqistation.com$request_uri;
}

```

然后找到原有 server block 的 `server_name` 行，修改为：

```nginx
server_name  127.0.0.1 localhost www.yuanqistation.com;
```

### 步骤 5：测试配置语法

```bash
docker exec frontend-nginx nginx -t
```

期望输出：
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 步骤 6：热重载 Nginx（无需重启）

```bash
docker exec frontend-nginx nginx -s reload
```

### 步骤 7：验证重定向

```bash
# 测试 HTTP 非 www
curl -I http://yuanqistation.com
# 期望：301 重定向到 https://www.yuanqistation.com/

# 测试 HTTP www
curl -I http://www.yuanqistation.com
# 期望：301 重定向到 https://www.yuanqistation.com/

# 测试 HTTPS 非 www
curl -I https://yuanqistation.com
# 期望：301 重定向到 https://www.yuanqistation.com/

# 测试 HTTPS www（主站）
curl -I https://www.yuanqistation.com
# 期望：200 OK
```

## 5. 回滚方案

如果配置出现问题，执行以下命令回滚：

```bash
# 恢复备份
cp /opt/hifate-frontend/nginx/conf.d/443.conf.bak.* /opt/hifate-frontend/nginx/conf.d/443.conf

# 删除新建的重定向配置
rm /opt/hifate-frontend/nginx/conf.d/redirect.conf

# 重载配置
docker exec frontend-nginx nginx -s reload
```

## 6. 注意事项

1. **SSL 证书**：确保 SSL 证书支持 `yuanqistation.com` 和 `www.yuanqistation.com` 两个域名（通配符证书或 SAN 多域名证书）

2. **301 vs 302**：使用 301 永久重定向，浏览器会缓存重定向结果，有利于 SEO

3. **热重载**：使用 `nginx -s reload` 而非重启容器，确保零停机

4. **DNS 解析**：确保 `yuanqistation.com` 和 `www.yuanqistation.com` 两个域名都解析到服务器 IP

## 7. 常见问题

### Q1: 为什么不直接在阿里云 CDN/SLB 配置重定向？

当前架构是 SSL 在 Nginx 容器层终结，不使用阿里云 CDN/SLB 做 SSL 终结，所以重定向配置在 Nginx 层面最合适。

### Q2: 修改后 localhost 和 127.0.0.1 访问会受影响吗？

不会。localhost 和 127.0.0.1 保留在 www 版本的 server block 中，本地访问不受影响。

### Q3: 9065.conf 需要修改吗？

不需要。9065.conf 的 `server_name localhost` 用于容器内部通信，新建的 redirect.conf 会处理外部域名的 HTTP 请求。
