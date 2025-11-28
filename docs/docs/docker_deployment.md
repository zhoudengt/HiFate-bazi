# Docker 部署指南

## 1. 准备工作

- 安装 Docker 与 Docker Compose（Docker Desktop 已集成 Compose）。
- 在项目根目录存在 `requirements.txt`，容器会基于该文件安装依赖。
- 如需数据库等外部服务，请提前准备连接配置，并通过环境变量注入。

## 2. 构建镜像

```bash
docker build -t HiFate-bazi:latest .
```

镜像构建流程：
1. 基于 `python:3.11-slim`。
2. 安装必要的系统依赖（`build-essential` 等）。
3. 安装 `requirements.txt` 中定义的 Python 依赖。
4. 拷贝项目代码，开放 8001 端口，并默认运行 `python server/start.py 8001`。

## 3. 运行容器

```bash
docker run -d \
  --name HiFate-bazi \
  -p 8001:8001 \
  --env-file .env \
  HiFate-bazi:latest
```

- `-p 8001:8001` 将容器端口映射到宿主机。
- `--env-file .env` 可选，若希望使用项目根目录下的 `.env`。
- 健康检查与文档访问：
  - 健康检查：`http://localhost:8001/health`
  - Swagger 文档：`http://localhost:8001/docs`

## 4. 使用 Docker Compose（可选）

在项目根目录创建 `docker-compose.yml`：

```yaml
services:
  HiFate-bazi:
    build: .
    image: HiFate-bazi:latest
    container_name: HiFate-bazi
    ports:
      - "8001:8001"
    env_file:
      - .env
    restart: unless-stopped
```

启动：

```bash
docker compose up -d
```

## 5. 日志与调试

- 查看容器日志：`docker logs -f HiFate-bazi`
- 如果需要进入容器调试：`docker exec -it HiFate-bazi /bin/bash`

## 6. 常见问题

- **依赖缺失**：确保依赖已写入 `requirements.txt`；如需系统包，请在 `Dockerfile` 中追加 `apt-get install`。
- **端口冲突**：修改 `docker run` 或 `docker-compose.yml` 中的宿主机端口映射。
- **数据持久化**：如需持久化文件，可通过 Volume 方式挂载目录，例如报告输出目录等。

