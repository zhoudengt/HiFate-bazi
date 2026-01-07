# 端口冲突检查指令

## 快速检查命令

在服务器 Node1 上执行以下命令来检查端口冲突：

### 方法 1: 使用检查脚本（推荐）

```bash
# 1. 将脚本上传到服务器或直接在服务器上创建
# 2. 执行脚本
bash scripts/check_port_conflict.sh
```

### 方法 2: 手动执行检查命令

```bash
# 1. 检查 80 端口占用
sudo ss -tlnp | grep ":80 "
# 或
sudo netstat -tlnp | grep ":80 "

# 2. 检查 Docker 容器
docker ps | grep nginx
docker port hifate-nginx 2>/dev/null

# 3. 检查所有 Nginx 进程
ps aux | grep nginx | grep -v grep

# 4. 检查前端 Nginx 配置
cat /opt/hifate-frontend/nginx/nginx.conf | grep -E "listen|root"
```

## 预期结果

如果发现端口冲突，应该会看到：

1. **80 端口被 Docker 容器占用**：
   ```
   0.0.0.0:80  ->  docker-proxy 或 nginx
   ```

2. **后端 Docker Nginx 容器运行中**：
   ```
   hifate-nginx   0.0.0.0:80->80/tcp
   ```

3. **前端 Nginx 进程可能无法启动或报错**

## 如果确认是端口冲突

执行以下命令停止后端 Docker Nginx：

```bash
docker stop hifate-nginx
```

然后检查前端 Nginx 是否能正常工作。

