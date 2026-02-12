#!/bin/bash
# 在 /opt/hifate-frontend 目录下创建 Docker 使用指南和模板
# 使用：bash scripts/create_frontend_docker_guide.sh

set -e

NODE1_PUBLIC_IP="8.210.52.217"
NODE2_PUBLIC_IP="47.243.160.43"
SSH_PASSWORD="${SSH_PASSWORD:?SSH_PASSWORD env var required}"
FRONTEND_DIR="/opt/hifate-frontend"
FRONTEND_NETWORK="frontend-network"

ssh_exec() {
    local host=$1
    shift
    local cmd="$@"
    if command -v sshpass &> /dev/null; then
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    else
        ssh -o StrictHostKeyChecking=no root@$host "$cmd"
    fi
}

create_guide_on_node() {
    local host=$1
    local node_name=$2
    
    echo "📝 在 $node_name ($host) 上创建使用指南..."
    echo "----------------------------------------"
    
    # 1. 确保目录存在
    echo "1. 检查 $FRONTEND_DIR 目录..."
    if ssh_exec $host "test -d $FRONTEND_DIR" 2>/dev/null; then
        echo "   ✅ 目录存在"
    else
        echo "   ⚠️  目录不存在，创建目录..."
        ssh_exec $host "mkdir -p $FRONTEND_DIR"
        ssh_exec $host "chmod 775 $FRONTEND_DIR"
        echo "   ✅ 目录已创建"
    fi
    
    # 2. 创建 docker-compose.yml 模板
    echo ""
    echo "2. 创建 docker-compose.yml 模板..."
    ssh_exec $host "cat > $FRONTEND_DIR/docker-compose.yml << 'EOF'
# 前端 Docker Compose 配置
# 项目名：frontend
# 使用方式：docker-compose -p frontend up -d

version: '3.8'

networks:
  frontend-network:
    external: true
    name: $FRONTEND_NETWORK

services:
  # 示例：前端应用服务
  frontend-app:
    image: nginx:alpine
    container_name: frontend-app
    ports:
      - \"8080:80\"  # 注意：不要占用后端端口（8001, 9001-9010, 3306, 6379）
    volumes:
      - ./html:/usr/share/nginx/html:ro
    networks:
      - frontend-network
    restart: unless-stopped
    labels:
      - \"owner=frontend\"
      - \"environment=production\"
    healthcheck:
      test: [\"CMD\", \"wget\", \"--quiet\", \"--tries=1\", \"--spider\", \"http://localhost:80\"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # 示例：前端 API 服务（如果需要）
  # frontend-api:
  #   image: node:18-alpine
  #   container_name: frontend-api
  #   ports:
  #     - \"8081:3000\"
  #   volumes:
  #     - ./api:/app
  #   networks:
  #     - frontend-network
  #   restart: unless-stopped
  #   labels:
  #     - \"owner=frontend\"
EOF
" 2>/dev/null || {
        echo "   ⚠️  创建 docker-compose.yml 失败，使用备用方法..."
        # 备用方法：逐行写入
        ssh_exec $host "echo 'version: \"3.8\"' > $FRONTEND_DIR/docker-compose.yml"
        ssh_exec $host "echo '' >> $FRONTEND_DIR/docker-compose.yml"
        ssh_exec $host "echo 'networks:' >> $FRONTEND_DIR/docker-compose.yml"
        ssh_exec $host "echo '  frontend-network:' >> $FRONTEND_DIR/docker-compose.yml"
        ssh_exec $host "echo '    external: true' >> $FRONTEND_DIR/docker-compose.yml"
        ssh_exec $host "echo '    name: $FRONTEND_NETWORK' >> $FRONTEND_DIR/docker-compose.yml"
    }
    echo "   ✅ docker-compose.yml 已创建"
    
    # 3. 创建 README.md 使用指南
    echo ""
    echo "3. 创建 README.md 使用指南..."
    ssh_exec $host "cat > $FRONTEND_DIR/README.md << 'EOF'
# 前端 Docker 部署指南

## 📋 目录说明

本目录（\`$FRONTEND_DIR\`）是前端用户（frontend-user）的专用 Docker 部署目录。

## 🔒 权限说明

- ✅ **可以做的**：
  - 在 \`$FRONTEND_DIR\` 目录下创建和管理 Docker 容器
  - 使用 \`frontend-*\` 前缀命名容器
  - 使用 \`$FRONTEND_NETWORK\` 网络
  - 查看所有容器（\`docker ps\`）

- ❌ **禁止做的**：
  - 操作 \`hifate-*\` 前缀的容器（后端容器）
  - 占用后端服务端口（8001, 9001-9010, 3306, 6379）
  - 访问 \`/opt/HiFate-bazi\` 目录
  - 删除后端镜像

## 🐳 Docker 使用规范

### 容器命名规范

- **必须使用前缀**：\`frontend-*\`（如 \`frontend-app\`, \`frontend-nginx\`）
- **禁止使用前缀**：\`hifate-*\`（后端容器专用）

### 网络使用规范

- **必须使用网络**：\`$FRONTEND_NETWORK\`（前端专用网络）
- **禁止使用网络**：\`hifate-network\`（后端专用网络）

### 端口使用规范

- **可用端口**：8080, 8081, 8082, 9000, 9001（前端端口范围）
- **禁止端口**：8001, 9001-9010, 3306, 6379（后端服务端口）

## 📝 使用示例

### 方式 1：使用 Docker Compose（推荐）

\`\`\`bash
# 进入目录
cd $FRONTEND_DIR

# 启动服务（使用项目名 frontend）
docker-compose -p frontend up -d

# 查看服务状态
docker-compose -p frontend ps

# 查看日志
docker-compose -p frontend logs -f

# 停止服务
docker-compose -p frontend down

# 停止并删除卷
docker-compose -p frontend down -v
\`\`\`

### 方式 2：使用 docker run（独立容器）

\`\`\`bash
# 使用前端网络和命名规范
docker run -d \\
  --name frontend-app \\
  --network $FRONTEND_NETWORK \\
  -p 8080:80 \\
  -v \$(pwd)/html:/usr/share/nginx/html:ro \\
  nginx:alpine

# 查看容器日志
docker logs frontend-app

# 停止容器
docker stop frontend-app

# 删除容器
docker rm frontend-app
\`\`\`

## 🔍 常用命令

### 查看容器

\`\`\`bash
# 查看所有容器
docker ps -a

# 查看前端容器（使用命名规范筛选）
docker ps -a | grep frontend-

# 查看容器详细信息
docker inspect frontend-app
\`\`\`

### 管理容器

\`\`\`bash
# 启动容器
docker start frontend-app

# 停止容器
docker stop frontend-app

# 重启容器
docker restart frontend-app

# 删除容器
docker rm frontend-app

# 删除容器和镜像
docker rm -f frontend-app
docker rmi frontend-app-image
\`\`\`

### 查看日志

\`\`\`bash
# 查看容器日志
docker logs frontend-app

# 实时查看日志
docker logs -f frontend-app

# 查看最近 100 行日志
docker logs --tail 100 frontend-app
\`\`\`

### 执行命令

\`\`\`bash
# 进入容器
docker exec -it frontend-app sh

# 执行命令
docker exec frontend-app ls -la /usr/share/nginx/html
\`\`\`

## 🌐 网络管理

### 查看网络

\`\`\`bash
# 查看所有网络
docker network ls

# 查看前端网络
docker network inspect $FRONTEND_NETWORK
\`\`\`

### 连接容器到网络

\`\`\`bash
# 将容器连接到前端网络
docker network connect $FRONTEND_NETWORK frontend-app

# 断开容器与网络的连接
docker network disconnect $FRONTEND_NETWORK frontend-app
\`\`\`

## ⚠️ 重要提醒

1. **命名规范**：
   - 所有前端容器必须使用 \`frontend-*\` 前缀
   - 禁止使用 \`hifate-*\` 前缀（后端容器专用）

2. **端口管理**：
   - 确保前端容器不占用后端服务端口
   - 后端服务端口：8001, 9001-9010, 3306, 6379

3. **资源限制**：
   - 建议前端容器设置资源限制（CPU、内存）
   - 避免影响后端服务性能

4. **定期检查**：
   - 定期检查前端容器状态
   - 确保没有影响后端服务

## 📚 相关文档

- Docker 官方文档：https://docs.docker.com/
- Docker Compose 文档：https://docs.docker.com/compose/

## 🔧 故障排查

### 容器无法启动

\`\`\`bash
# 查看容器日志
docker logs frontend-app

# 查看容器详细信息
docker inspect frontend-app

# 检查网络连接
docker network inspect $FRONTEND_NETWORK
\`\`\`

### 端口冲突

\`\`\`bash
# 检查端口占用
netstat -tlnp | grep 8080

# 修改 docker-compose.yml 中的端口映射
# 或使用其他可用端口
\`\`\`

### 权限问题

\`\`\`bash
# 检查目录权限
ls -la $FRONTEND_DIR

# 检查 Docker 权限
groups
docker ps
\`\`\`

---

**最后更新**：$(date +%Y-%m-%d)
EOF
" 2>/dev/null || {
        echo "   ⚠️  创建 README.md 失败，使用备用方法..."
        ssh_exec $host "echo '# 前端 Docker 部署指南' > $FRONTEND_DIR/README.md"
    }
    echo "   ✅ README.md 已创建"
    
    # 4. 设置文件权限
    echo ""
    echo "4. 设置文件权限..."
    ssh_exec $host "chmod 644 $FRONTEND_DIR/docker-compose.yml $FRONTEND_DIR/README.md" 2>/dev/null || true
    ssh_exec $host "chown root:root $FRONTEND_DIR/docker-compose.yml $FRONTEND_DIR/README.md" 2>/dev/null || true
    echo "   ✅ 文件权限已设置"
    
    # 5. 验证文件
    echo ""
    echo "5. 验证文件..."
    if ssh_exec $host "test -f $FRONTEND_DIR/docker-compose.yml && test -f $FRONTEND_DIR/README.md" 2>/dev/null; then
        echo "   ✅ 文件创建成功"
        echo "      - $FRONTEND_DIR/docker-compose.yml"
        echo "      - $FRONTEND_DIR/README.md"
    else
        echo "   ❌ 文件创建失败"
        return 1
    fi
    
    echo ""
    echo "=========================================="
}

echo "=========================================="
echo "创建前端 Docker 使用指南（双机）"
echo "=========================================="
echo ""
echo "目标："
echo "  - 在 $FRONTEND_DIR 目录下创建 docker-compose.yml 模板"
echo "  - 在 $FRONTEND_DIR 目录下创建 README.md 使用指南"
echo ""

# 在 Node1 上创建
create_guide_on_node $NODE1_PUBLIC_IP "Node1"

# 在 Node2 上创建
create_guide_on_node $NODE2_PUBLIC_IP "Node2"

echo "=========================================="
echo "完成"
echo "=========================================="
echo "✅ 前端 Docker 使用指南创建完成（双机）"
echo ""
echo "文件位置："
echo "  - $FRONTEND_DIR/docker-compose.yml"
echo "  - $FRONTEND_DIR/README.md"
echo ""
echo "使用方式："
echo "  cd $FRONTEND_DIR"
echo "  docker-compose -p frontend up -d"
echo ""

