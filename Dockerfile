# HiFate-bazi Dockerfile - 优化版
# 构建时间: ~3分钟（精简依赖）

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# 配置国内镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true

# 安装最小系统依赖
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 配置 pip 镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 先复制依赖文件（利用缓存）
COPY requirements.txt .

# 安装依赖
RUN pip install -r requirements.txt

# 复制代码
COPY . ${APP_HOME}

EXPOSE 8001

CMD ["python", "server/start.py", "8001"]
