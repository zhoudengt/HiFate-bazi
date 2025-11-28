# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

# 使用阿里云镜像源加速 apt 安装（国内服务器）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统依赖
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        curl \
        cmake \
        libopenblas-dev \
        liblapack-dev \
        libatlas-base-dev \
        gfortran \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用清华大学镜像源（国内加速）
RUN python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 先复制 requirements.txt，利用 Docker 层缓存
# 只有当 requirements.txt 变化时才重新安装依赖
COPY requirements.txt .

# 安装 Python 依赖（启用缓存，加速后续构建）
# 分层安装：先安装基础依赖，再安装重型依赖
RUN pip install --no-cache-dir -r requirements.txt || \
    (echo "⚠️  使用镜像源安装失败，尝试使用官方源..." && \
     pip config unset global.index-url && \
     pip config unset global.trusted-host && \
     pip install --no-cache-dir -r requirements.txt)

# 复制项目代码（放在最后，代码变化不影响依赖层缓存）
COPY . ${APP_HOME}

EXPOSE 8001

ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8001

CMD ["python", "server/start.py", "8001"]





























