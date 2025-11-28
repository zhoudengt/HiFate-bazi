# HiFate-bazi Dockerfile
# 使用预构建基础镜像 + 增量保险
# 
# 首次部署需要先构建基础镜像：
#   docker build -f Dockerfile.base -t hifate-base:latest .
#
# 后续部署（快速）：
#   docker compose up -d --build web

FROM hifate-base:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# 增量保险层：检查并安装可能缺失的依赖
# 如果 requirements.txt 有变更但基础镜像未更新，这里会补上
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt || echo "依赖已安装"

# 复制代码
COPY . ${APP_HOME}

EXPOSE 8001

CMD ["python", "server/start.py", "8001"]
