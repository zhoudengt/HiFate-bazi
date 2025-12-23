# 域名配置说明 - yuanqistation.com

## 概述

本文档说明如何为域名 `yuanqistation.com` 配置 DNS 解析，使前端可以通过该域名访问服务。

## 服务器端配置状态

✅ **已完成**：
- Node1 (8.210.52.217) Nginx 配置已更新
- Node2 (47.243.160.43) Nginx 配置已更新
- 域名 `yuanqistation.com` 和 `www.yuanqistation.com` 已添加到 Nginx 配置
- Nginx 容器已重启，配置已生效

## DNS 解析配置（域名注册商处）

**重要说明**：DNS 解析需要在域名注册商（如阿里云、腾讯云等）的 DNS 管理界面配置，不是在服务器上配置。

### 需要配置的 DNS 记录

#### 1. A 记录（主域名）

- **记录类型**：A
- **主机记录**：@（或留空，表示主域名）
- **记录值**：`8.210.52.217`（Node1 公网 IP）
- **TTL**：600（10分钟，建议值）

#### 2. A 记录（www 子域名）

- **记录类型**：A
- **主机记录**：www
- **记录值**：`8.210.52.217`（Node1 公网 IP）
- **TTL**：600（10分钟，建议值）

### DNS 配置位置

根据域名注册商不同，配置位置如下：

#### 阿里云

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 进入 **域名** → **域名解析**
3. 找到域名 `yuanqistation.com`
4. 点击 **解析设置**
5. 点击 **添加记录**
6. 配置 A 记录（主域名和 www 子域名）

#### 腾讯云

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入 **域名注册** → **我的域名**
3. 找到域名 `yuanqistation.com`
4. 点击 **解析**
5. 点击 **添加记录**
6. 配置 A 记录（主域名和 www 子域名）

#### 其他服务商

操作类似：
1. 登录域名注册商控制台
2. 找到域名管理/DNS 解析设置
3. 添加 A 记录

### 可选：负载均衡配置

如果需要更好的可用性，可以配置两条 A 记录：

**方案 1：DNS 负载均衡**
- 主域名：两条 A 记录，分别指向 `8.210.52.217` 和 `47.243.160.43`
- www 子域名：两条 A 记录，分别指向 `8.210.52.217` 和 `47.243.160.43`

**方案 2：单 IP（当前推荐）**
- 由于 Nginx 已配置负载均衡，DNS 只需指向一个 IP 即可
- 推荐指向 Node1 (8.210.52.217)

## DNS 生效时间

- **通常**：5-30 分钟
- **最长**：48 小时（全球 DNS 缓存刷新）
- **检查方法**：
  ```bash
  # 检查 DNS 解析
  nslookup yuanqistation.com
  dig yuanqistation.com
  
  # 或使用在线工具
  # https://www.whatsmydns.net/
  ```

## 验证配置

### 1. 检查 DNS 解析

```bash
# 检查主域名
nslookup yuanqistation.com

# 检查 www 子域名
nslookup www.yuanqistation.com
```

**预期结果**：
```
Name:   yuanqistation.com
Address: 8.210.52.217
```

### 2. 测试域名访问

```bash
# 测试主域名
curl http://yuanqistation.com/health

# 测试 www 子域名
curl http://www.yuanqistation.com/health
```

**预期结果**：返回健康检查 JSON 响应

### 3. 浏览器访问测试

1. 打开浏览器
2. 访问 `http://yuanqistation.com`
3. 应该能看到前端页面

## 防火墙配置

确保服务器防火墙开放以下端口：

- **80 端口**（HTTP）：必须开放
- **443 端口**（HTTPS）：如果后续配置 HTTPS，需要开放

**检查方法**：
```bash
# 检查防火墙状态
systemctl status firewalld

# 检查端口是否开放
netstat -tlnp | grep -E ':(80|443)'
```

## 后续 HTTPS 配置（可选）

如果需要配置 HTTPS：

1. **获取 SSL 证书**
   - 阿里云证书服务
   - Let's Encrypt（免费）
   - 其他证书服务商

2. **上传证书到服务器**
   ```bash
   # 创建证书目录
   mkdir -p /opt/HiFate-bazi/deploy/nginx/ssl
   
   # 上传证书文件
   # cert.pem - 证书文件
   # key.pem - 私钥文件
   ```

3. **修改 Nginx 配置**
   - 添加 HTTPS server 块
   - 配置 HTTP 到 HTTPS 的重定向

4. **重启 Nginx 容器**
   ```bash
   docker restart hifate-nginx
   ```

## 故障排查

### 问题 1：DNS 解析不生效

**症状**：`nslookup yuanqistation.com` 返回错误或旧 IP

**解决方案**：
1. 检查 DNS 记录是否正确配置
2. 等待 DNS 缓存刷新（最长 48 小时）
3. 清除本地 DNS 缓存：
   ```bash
   # Windows
   ipconfig /flushdns
   
   # macOS/Linux
   sudo dscacheutil -flushcache
   ```

### 问题 2：域名无法访问

**症状**：DNS 解析正常，但无法访问网站

**解决方案**：
1. 检查服务器防火墙是否开放 80 端口
2. 检查 Nginx 容器是否运行：
   ```bash
   docker ps | grep nginx
   ```
3. 检查 Nginx 配置：
   ```bash
   docker exec hifate-nginx nginx -t
   ```
4. 查看 Nginx 日志：
   ```bash
   docker logs hifate-nginx --tail 100
   ```

### 问题 3：502 Bad Gateway

**症状**：域名可以访问，但返回 502 错误

**解决方案**：
1. 检查后端服务是否运行：
   ```bash
   docker ps | grep hifate-web
   ```
2. 检查后端服务健康状态：
   ```bash
   curl http://localhost:8001/health
   ```
3. 检查 Nginx 负载均衡配置是否正确

## 联系支持

如果遇到问题，请提供以下信息：
- DNS 解析结果（`nslookup yuanqistation.com`）
- Nginx 日志（`docker logs hifate-nginx --tail 100`）
- 服务器防火墙状态
- 错误截图或错误信息

## 更新记录

- **2025-01-XX**：初始配置完成
  - Node1 和 Node2 Nginx 配置已更新
  - 域名 `yuanqistation.com` 和 `www.yuanqistation.com` 已添加
  - Nginx 容器已重启

