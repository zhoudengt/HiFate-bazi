# 前端文件部署问题诊断指南

## 问题描述

前端打包文件已放在 `/opt/hifate-frontend/nginx/html/dist` 下，但访问网站时文件不生效。

**重要说明**：
- `/usr/share/nginx/html/local_frontend` 是**后端 Nginx**（Docker）的路径
- 前端有**独立的 Nginx 部署**，配置应该在 `/opt/hifate-frontend/nginx/` 目录下

## 快速诊断

### 使用诊断脚本（推荐）

在服务器 Node1 上执行：

```bash
# 下载或复制诊断脚本到服务器
# 执行诊断（需要 sudo 权限）
bash scripts/diagnose_frontend_deployment.sh
```

脚本会自动执行以下检查：
1. ✅ 检查文件是否存在及目录结构
2. ✅ 检查 Nginx 配置文件路径
3. ✅ 检查 Nginx 实际使用的 root 路径
4. ✅ 检查文件权限和 Nginx 用户权限
5. ✅ 检查 Nginx 错误日志和访问日志

## 手动诊断步骤

如果无法运行脚本，可以手动执行以下命令：

### 步骤 1: 检查文件是否存在

```bash
ls -la /opt/hifate-frontend/nginx/html/dist
# 应该能看到 index.html 等打包文件
```

### 步骤 2: 检查前端独立 Nginx 配置

```bash
# 优先检查前端目录下的 Nginx 配置
ls -la /opt/hifate-frontend/nginx/

# 检查前端 Nginx 配置文件
cat /opt/hifate-frontend/nginx/nginx.conf | grep -A 5 "root\|location"

# 检查前端 conf.d 目录（如果有）
ls -la /opt/hifate-frontend/nginx/conf.d/
cat /opt/hifate-frontend/nginx/conf.d/*.conf | grep -A 5 "root\|location"

# 也检查系统 Nginx 配置（可能是后端）
sudo cat /etc/nginx/nginx.conf | grep -A 10 "server\|location"
ls -la /etc/nginx/conf.d/
sudo cat /etc/nginx/conf.d/*.conf | grep -A 5 "root\|location"

# 查找包含 hifate-frontend 或 dist 的配置
find /opt/hifate-frontend/nginx -name "*.conf" -exec grep -l "dist\|html" {} \;
find /etc/nginx -name "*.conf" -exec grep -l "hifate-frontend\|dist" {} \;
```

### 步骤 3: 检查 Nginx 实际使用的 root 路径

```bash
# 查看完整的 Nginx 配置（包含所有 root 和 location）
sudo nginx -T | grep -A 5 "root\|location /"

# 查看监听 80 端口的服务器配置
sudo nginx -T 2>/dev/null | grep -B 5 -A 10 "listen.*80"
```

### 步骤 4: 检查文件权限

```bash
# 检查目录权限
ls -la /opt/hifate-frontend/nginx/html/
ls -la /opt/hifate-frontend/nginx/html/dist/

# 检查 Nginx 进程用户
ps aux | grep nginx

# 检查 Nginx 用户能否访问文件（假设 Nginx 用户是 nginx）
sudo -u nginx test -r /opt/hifate-frontend/nginx/html/dist && echo "可读" || echo "不可读"
```

### 步骤 5: 检查 Nginx 错误日志

```bash
# 检查前端 Nginx 日志（优先）
ls -la /opt/hifate-frontend/nginx/logs/
tail -50 /opt/hifate-frontend/nginx/logs/error.log
tail -50 /opt/hifate-frontend/nginx/logs/access.log | grep "404"

# 也检查系统 Nginx 日志（可能是后端）
sudo tail -50 /var/log/nginx/error.log
sudo tail -50 /var/log/nginx/access.log | grep "404"
```

## 后端 Nginx 对前端的影响

**重要**：后端 Nginx 可能会影响前端 Nginx，主要场景：

### 1. **端口冲突（最常见）**

如果后端 Nginx 和前端 Nginx 都监听 80 端口，会导致冲突：
- 只有第一个启动的 Nginx 能成功绑定 80 端口
- 后启动的 Nginx 会失败或无法访问

**检查方法**：
```bash
# 检查端口占用
sudo netstat -tlnp | grep ":80 "
# 或
sudo ss -tlnp | grep ":80 "

# 检查所有 Nginx 进程
ps aux | grep nginx | grep -v grep
```

### 2. **Docker 容器端口映射冲突**

后端 Nginx 可能在 Docker 容器中运行并映射了 80 端口：
```bash
# 检查 Docker 容器
docker ps | grep nginx
docker port <容器名> | grep "80"
```

### 3. **反向代理配置冲突**

后端 Nginx 可能配置了反向代理，影响了前端路由：
```bash
# 检查后端 Nginx 配置
sudo nginx -T | grep -E "proxy_pass|upstream"
```

### 4. **配置文件冲突**

如果前端和后端都在使用系统级 Nginx，配置可能互相覆盖。

## 常见问题诊断

### 问题 1: 路径不匹配

**症状**：
- 文件存在于 `/opt/hifate-frontend/nginx/html/dist`
- 但前端 Nginx 配置指向其他路径

**确认方法**：
```bash
# 检查前端 Nginx 配置中的 root 路径
cat /opt/hifate-frontend/nginx/nginx.conf | grep "root"

# 如果前端 Nginx 正在运行，检查实际使用的配置
# 首先找到前端 Nginx 进程使用的配置文件
ps aux | grep nginx
# 然后根据进程信息检查对应配置文件
```

**可能的原因**：
- 前端 Nginx 配置文件（`/opt/hifate-frontend/nginx/nginx.conf`）中的 `root` 路径未更新
- 配置文件指向了错误的目录（可能指向 `/opt/hifate-frontend/nginx/html` 而不是 `/opt/hifate-frontend/nginx/html/dist`）
- 前端 Nginx 进程未重新加载配置

### 问题 2: 文件权限问题

**症状**：
- 文件存在但 Nginx 无法读取
- 错误日志显示 "Permission denied"

**确认方法**：
```bash
# 查看 Nginx 用户
ps aux | grep "nginx: master"

# 测试权限
NGINX_USER=$(ps aux | grep "nginx: master" | grep -v grep | awk '{print $1}' | head -1)
sudo -u $NGINX_USER test -r /opt/hifate-frontend/nginx/html/dist
```

**解决方法**：
```bash
# 确保 Nginx 用户有读取权限
sudo chmod -R o+r /opt/hifate-frontend/nginx/html/dist
# 或者
sudo chown -R nginx:nginx /opt/hifate-frontend/nginx/html/dist
```

### 问题 3: Nginx 配置未重新加载

**症状**：
- 配置已修改但未生效
- 访问网站仍然返回旧内容或 404

**解决方法**：
```bash
# 测试配置
sudo nginx -t

# 重新加载配置
sudo systemctl reload nginx
# 或
sudo service nginx reload
```

### 问题 4: 目录结构错误

**症状**：
- 文件在 `dist` 子目录下
- 但 Nginx 配置指向父目录

**确认方法**：
```bash
# 查看配置中的 root 路径
sudo nginx -T | grep "root"

# 查看实际文件位置
ls -la /opt/hifate-frontend/nginx/html/dist/
```

**解决方法**：
- 方法 1: 修改 Nginx 配置指向 `dist` 目录
- 方法 2: 将文件从 `dist` 移到父目录

## 诊断结果分析

执行诊断后，请检查以下关键信息：

### 必须确认的信息

1. **文件位置**：
   - [ ] 文件确实在 `/opt/hifate-frontend/nginx/html/dist`
   - [ ] `index.html` 文件存在

2. **Nginx 配置路径**：
   - [ ] Nginx 配置中的 `root` 路径是什么？
   - [ ] 是否匹配实际文件位置？

3. **文件权限**：
   - [ ] Nginx 进程用户是什么？
   - [ ] 该用户能否读取目标目录？

4. **日志信息**：
   - [ ] 错误日志中有哪些错误？
   - [ ] 访问日志中有 404 错误吗？

### 问题 5: 后端 Nginx 影响前端（端口冲突）

**症状**：
- 前端文件存在且配置正确
- 但访问网站返回后端内容或无法访问
- 多个 Nginx 进程在运行

**确认方法**：
```bash
# 检查端口占用
sudo netstat -tlnp | grep ":80 "

# 检查所有 Nginx 进程
ps aux | grep nginx | grep -v grep

# 检查 Docker 容器
docker ps | grep nginx
```

**解决方法**：
1. **确认前端和后端 Nginx 的端口分配**：
   - 前端：监听 80 端口（对外提供服务）
   - 后端：监听其他端口（如 8000）或仅在 Docker 内部

2. **停止冲突的后端 Nginx**：
   ```bash
   # 如果后端 Docker Nginx 占用 80 端口
   docker stop <后端nginx容器名>
   
   # 如果系统级后端 Nginx 占用 80 端口
   sudo systemctl stop nginx
   ```

3. **修改端口配置**：
   - 确保只有前端 Nginx 监听 80 端口
   - 后端 Nginx 使用其他端口或仅在 Docker 网络内部

## 可能的原因总结

根据诊断结果，最可能的原因是：

1. **路径不匹配**（最可能）
   - Nginx 配置指向：`/usr/share/nginx/html/local_frontend`
   - 实际文件在：`/opt/hifate-frontend/nginx/html/dist`

2. **配置未重新加载**
   - 修改文件后未执行 `nginx -s reload`

3. **权限问题**
   - Nginx 用户无法读取 `/opt/hifate-frontend/nginx/html/dist`

4. **目录结构不匹配**
   - 配置指向父目录，但文件在 `dist` 子目录

## 后续步骤

诊断完成后：
1. 根据诊断结果确定问题原因
2. 参考解决方案进行修复（需在服务器上手动执行）
3. 修复后验证是否生效

## 注意事项

⚠️ **本诊断脚本只执行只读检查，不会修改任何配置或文件**

如果需要修改配置，请：
1. 先备份原配置
2. 修改配置后测试：`sudo nginx -t`
3. 确认无误后重新加载：`sudo systemctl reload nginx`

