# 快速修复前端容器内存限制

## 问题
容器退出代码 137（被 OOM Killer 杀死），内存限制不生效。

## 快速修复（3步）

### 步骤 1：在服务器上切换到 frontend-user

```bash
su - frontend-user
cd /opt/hifate-frontend
```

### 步骤 2：下载并执行修复脚本

```bash
# 从项目仓库下载脚本（或手动复制内容）
wget https://raw.githubusercontent.com/your-repo/HiFate-bazi/master/scripts/fix_frontend_memory_limit_local.sh
chmod +x fix_frontend_memory_limit_local.sh
bash fix_frontend_memory_limit_local.sh
```

或者手动修复：

```bash
# 备份配置
cp docker-compose.yml docker-compose.yml.backup

# 使用 sed 简单替换（如果配置简单）
sed -i 's/mem_limit:/# mem_limit:/g' docker-compose.yml
sed -i 's/mem_reservation:/# mem_reservation:/g' docker-compose.yml

# 然后手动添加 deploy.resources 配置
```

### 步骤 3：重启容器

```bash
docker-compose down
docker-compose up -d
docker stats --no-stream  # 验证内存限制
```

## 配置示例

修改前：
```yaml
services:
  frontend-mysql:
    mem_limit: 512m
    mem_reservation: 256m
```

修改后：
```yaml
services:
  frontend-mysql:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## 验证

```bash
# 检查容器状态（不应再出现 137 错误）
docker-compose ps

# 检查内存限制
docker stats --no-stream

# 检查日志
docker-compose logs frontend-gateway
```

